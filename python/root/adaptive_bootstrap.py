#!/usr/bin/env python3
"""Adaptive Bootstrap Predictor - ML-powered file selection for bootstrap optimization.

Implements TASK_0156: Dynamic file selection based on task context, usage patterns,
and predicted needs. Moves from static exclusion lists to intelligent, context-aware
bootstrap that learns what files are actually needed.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# Optional: embeddings + similarity (Phase 2)
import json
import numpy as np
from typing import Any

from knowledge_db import KnowledgeDB


@dataclass
class FilePrediction:
    """Prediction result for a single file."""
    file_path: str
    predicted_needed: bool
    confidence: float
    roi_score: float
    relevance_score: float
    usage_probability: float
    recency_score: float
    final_score: float
    reasoning: str


class EmbeddingStore:
    """Manage sentence-transformer model and cached file embeddings.

    - Embeddings are cached to `<workspace>/.bootstrap_embeddings.npz` as arrays and a names list.
    - If `sentence-transformers` is not available, `model` will be None and the store is inert.
    """

    def __init__(self, workspace: Path, model_name: str = "all-MiniLM-L6-v2"):
        self.workspace = workspace
        self.model_name = model_name
        self.cache_path = workspace / ".bootstrap_embeddings.npz"
        self.model = None
        self.names: list[str] = []
        self.vectors: dict[str, np.ndarray] = {}

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except Exception:
            # Model not available; the embedding store will be a no-op
            self.model = None

        self._load_cache()

    def _load_cache(self) -> None:
        try:
            if self.cache_path.exists():
                arr = np.load(self.cache_path, allow_pickle=True)
                self.names = arr['names'].tolist()
                vectors = arr['vectors']
                if len(self.names) == len(vectors):
                    self.vectors = {n: vectors[i] for i, n in enumerate(self.names)}
        except Exception:
            self.names = []
            self.vectors = {}

    def _persist_cache(self) -> None:
        try:
            names = np.array(self.names)
            vectors = np.array([self.vectors[n] for n in self.names]) if self.names else np.array([])
            np.savez_compressed(self.cache_path, names=names, vectors=vectors)
        except Exception:
            pass

    def ensure_embeddings(self, file_paths: list[str]) -> None:
        """Ensure embeddings exist for the given file_paths; compute with model when missing."""
        if self.model is None:
            return

        to_compute = []
        to_names = []
        for p in file_paths:
            if p not in self.vectors:
                to_compute.append(str(self.workspace / p))
                to_names.append(p)

        if not to_compute:
            return

        # Read text and compute embeddings in batch
        texts = []
        for fp in to_compute:
            try:
                texts.append(Path(fp).read_text(encoding='utf-8'))
            except Exception:
                texts.append("")
        try:
            embeds = self.model.encode(texts, show_progress_bar=False)
            for name, vec in zip(to_names, embeds):
                self.vectors[name] = np.asarray(vec, dtype=np.float32)
                if name not in self.names:
                    self.names.append(name)
            self._persist_cache()
        except Exception:
            # Swallow model errors; leave store partially filled
            pass

    def get_vector(self, file_path: str) -> Optional[np.ndarray]:
        return self.vectors.get(file_path)


class BootstrapPredictor:
    """Predicts which files should be included in bootstrap based on task context."""

    def __init__(self, workspace_root: Path, penalty_scale: float = 5000.0, roi_weights: List[float] = None, embed_model_name: str = "all-MiniLM-L6-v2"):
        self.workspace = workspace_root
        self.db = KnowledgeDB(workspace_root)
        self.penalty_scale = penalty_scale
        self.roi_weights = roi_weights or [0.35, 0.10, 0.30, 0.20, 0.05]  # Default weights

        # Embedding store (optional). If sentence-transformers isn't available, this is inert.
        try:
            self.embedding_store = EmbeddingStore(workspace_root, model_name=embed_model_name)
            self.use_embeddings = self.embedding_store.model is not None
        except Exception:
            self.embedding_store = None
            self.use_embeddings = False

        self._load_history()

    def _load_history(self) -> None:
        """Load usage history from database."""
        # This will be populated as we track actual usage
        self.usage_history = self.db.get_bootstrap_prediction_history(limit=50)

    def _get_bootstrap_predictions_history(self) -> List[Dict]:
        """Get historical bootstrap prediction data."""
        return self.db.get_bootstrap_prediction_history(limit=50)

    def predict_needed_files(
        self,
        task_context: str,
        task_type: str = "unknown",
        budget_tokens: int = 60000,
        dry_run: bool = False
    ) -> List[str]:
        """Predict which files will be needed for this task.

        Args:
            task_context: Description of the current task
            task_type: Type of task (implementation, debugging, analysis, etc.)
            budget_tokens: Token budget for bootstrap

        Returns:
            List of file paths that should be included
        """
        # Get candidate files
        candidates = self._get_bootstrap_candidates()

        # Score each candidate
        predictions = []
        for candidate in candidates:
            prediction = self._score_file(candidate, task_context, task_type)
            predictions.append(prediction)

        # Select files within budget using knapsack algorithm
        selected = self._knapsack_pack(predictions, budget_tokens)

        # Log prediction for learning (unless dry-run)
        if dry_run:
            try:
                log_path = self.workspace / ".bootstrap_dry_runs.jsonl"
                entry = {
                    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'task_context': task_context,
                    'task_type': task_type,
                    'loop': None,
                    'selected_files': selected,
                    'predictions': [p.__dict__ for p in predictions]
                }
                # Try to include current loop when available
                try:
                    current_text = (self.workspace / "current.json").read_text(encoding='utf-8')
                    current = json.loads(current_text)
                    entry['loop'] = current.get('STATE', {}).get('loop')
                except Exception:
                    entry['loop'] = None

                with open(log_path, 'a', encoding='utf-8') as fh:
                    fh.write(json.dumps(entry) + "\n")
            except Exception:
                pass
        else:
            self._log_prediction(task_context, selected)

            # Breadcrumb tracking: mark predicted files for TASK_0156 (non-fatal)
            try:
                from ai_breadcrumb_tracker import track_file_access
                for f in selected:
                    try:
                        # Record predicted file access (will inject breadcrumb if file exists)
                        track_file_access(str(self.workspace / f), source_context="TASK_0156_predict")
                    except Exception:
                        # Don't fail prediction on tracking errors
                        pass
            except Exception:
                pass

        return selected

    def _get_bootstrap_candidates(self) -> List[str]:
        """Get all files that might be loaded during bootstrap."""
        patterns = [
            'reports/report_*.md',
            'tasks/task_*.md',
            'docs/*.md',
            'archive/ARCHIV_*.md',
            '*.md'  # Other markdown files in root
        ]

        candidates = []
        for pattern in patterns:
            for file_path in self.workspace.glob(pattern):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(self.workspace))
                    candidates.append(rel_path)

        return candidates

    def _score_file(
        self,
        file_path: str,
        task_context: str,
        task_type: str
    ) -> FilePrediction:
        """Score a single file for likelihood of being needed."""
        # Get ROI score from chain_costs table
        roi_score = self._get_roi_score(file_path)

        # Calculate relevance to task context
        relevance_score = self._calculate_relevance(file_path, task_context)

        # Get historical usage probability
        usage_probability = self._get_usage_probability(file_path, task_type)

        # Calculate recency score
        recency_score = self._get_recency_score(file_path)

        # Estimate token cost for this file and compute ROI per token
        estimated_tokens = max(1, self._estimate_token_cost(file_path))
        roi_per_token = roi_score / (estimated_tokens + 1)

        # Ensemble scoring (use ROI-per-token to penalize large files)
        final_score = self._calculate_final_score(
            roi_per_token, roi_score, relevance_score, usage_probability, recency_score
        )



        # Determine if needed (simple threshold for now)
        predicted_needed = final_score > 0.3
        confidence = min(final_score, 1.0)

        reasoning = self._generate_reasoning(
            roi_score, relevance_score, usage_probability, recency_score, final_score
        )

        return FilePrediction(
            file_path=file_path,
            predicted_needed=predicted_needed,
            confidence=confidence,
            roi_score=roi_score,
            relevance_score=relevance_score,
            usage_probability=usage_probability,
            recency_score=recency_score,
            final_score=final_score,
            reasoning=reasoning
        )

    def _get_roi_score(self, file_path: str) -> float:
        """Get ROI score from chain_costs table."""
        try:
            result = self.db.conn.execute("""
                SELECT roi FROM chain_costs
                WHERE chain_root = ?
                ORDER BY roi DESC
                LIMIT 1
            """, (file_path,)).fetchone()

            return result[0] if result else 0.1  # Default low score
        except:
            return 0.1

    def _calculate_relevance(self, file_path: str, task_context: str) -> float:
        """Calculate semantic relevance to task context.

        Enhanced strategy (Phase 2):
        - If embeddings are available, compute cosine similarity between task context and file content embeddings.
        - Fall back to knowledge-db semantic search presence and lightweight keyword overlap.
        - Combine signals into a 0..1 relevance score, favoring embeddings when present.
        """
        try:
            # 1) Embedding similarity (preferred when available)
            embed_score = 0.0
            try:
                if self.use_embeddings and self.embedding_store is not None and self.embedding_store.model is not None:
                    # Ensure file embedding exists
                    self.embedding_store.ensure_embeddings([file_path])

                    task_vec = None
                    try:
                        task_vec = self.embedding_store.model.encode([task_context], show_progress_bar=False)[0]
                    except Exception:
                        task_vec = None

                    file_vec = self.embedding_store.get_vector(file_path)
                    if task_vec is not None and file_vec is not None:
                        try:
                            from sklearn.metrics.pairwise import cosine_similarity
                            s = cosine_similarity([np.asarray(task_vec, dtype=np.float32)], [np.asarray(file_vec, dtype=np.float32)])[0, 0]
                            # Clip and normalize to 0..1
                            embed_score = float(max(0.0, min(1.0, s)))
                        except Exception:
                            embed_score = 0.0
            except Exception:
                embed_score = 0.0

            # 2) If DB supports semantic search, look for file presence in top results
            search_presence = 0.0
            try:
                top = self.db.search(task_context, limit=50, semantic=True)
                for r in top:
                    ctx = getattr(r, 'context', {}) if hasattr(r, 'context') else (r.get('context') if isinstance(r, dict) else {})
                    if isinstance(ctx, dict):
                        path_vals = [ctx.get('path') or ctx.get('task_id') or ctx.get('source_id') or ctx.get('goal')]
                    else:
                        path_vals = []
                    id_val = getattr(r, 'id', None) if hasattr(r, 'id') else (r.get('id') if isinstance(r, dict) else None)

                    vals = [id_val] + [v for v in path_vals if v]
                    for v in vals:
                        if not v:
                            continue
                        vstr = str(v)
                        if file_path in vstr or Path(file_path).name in vstr:
                            search_presence = 1.0
                            break
                    if search_presence >= 1.0:
                        break
            except Exception:
                search_presence = 0.0

            # 3) Keyword-based fallback (lightweight)
            kw_score = 0.0
            try:
                full_path = self.workspace / file_path
                if full_path.exists():
                    content = full_path.read_text(encoding='utf-8').lower()
                    task_words = [w for w in task_context.lower().split() if len(w) > 2]
                    if task_words:
                        matches = sum(1 for word in task_words if word in content)
                        kw_score = matches / len(task_words)
                        kw_score = min(kw_score, 1.0)
            except Exception:
                kw_score = 0.0

            # Combine signals. Favor embeddings when available.
            if embed_score > 0:
                relevance = 0.7 * embed_score + 0.2 * search_presence + 0.1 * kw_score
            else:
                relevance = 0.6 * search_presence + 0.4 * kw_score

            return min(max(relevance, 0.0), 1.0)
        except Exception:
            return 0.0

    def _get_usage_probability(self, file_path: str, task_type: str) -> float:
        """Get historical usage probability for this file type and task type.

        Implemented using `bootstrap_predictions` history from KnowledgeDB.
        Returns frequency of the file appearing in past `predicted_files` or `actual_files` entries.
        Falls back to a conservative default (0.2) when history is sparse.
        """
        try:
            history = self._get_bootstrap_predictions_history() or []
            if not history:
                return 0.2

            count = 0
            total = 0
            for entry in history:
                total += 1
                pf = entry.get('predicted_files') or entry.get('predicted_files_json') or []
                af = entry.get('actual_files') or []
                # Normalize representation (strings -> json parse)
                try:
                    if isinstance(pf, str):
                        import json as _json
                        pf = _json.loads(pf)
                except Exception:
                    pf = []

                if file_path in pf or file_path in af:
                    count += 1

            prob = (count / total) if total > 0 else 0.2
            # Smooth toward base probability
            return max(0.05, min(1.0, (0.7 * prob) + (0.3 * 0.2)))
        except Exception:
            return 0.2

    def _get_recency_score(self, file_path: str) -> float:
        """Get recency score based on file modification time."""
        try:
            full_path = self.workspace / file_path
            if not full_path.exists():
                return 0.0

            mtime = full_path.stat().st_mtime
            now = datetime.now().timestamp()

            # Score based on days since modification
            days_old = (now - mtime) / (24 * 3600)

            # Exponential decay: newer files score higher
            recency = max(0.1, 1.0 / (1.0 + days_old / 30.0))  # 30-day half-life

            return recency
        except:
            return 0.1

    def _calculate_final_score(
        self,
        roi_per_token: float,
        roi_score: float,
        relevance_score: float,
        usage_probability: float,
        recency_score: float
    ) -> float:
        """Calculate final ensemble score.

        We combine both ROI-per-token (to penalize large files) and absolute ROI
        (to prefer high-quality candidates). Weights chosen to prioritize
        token-aware ROI while preserving relevance and usage signals.
        """
        final_score = (
            self.roi_weights[0] * roi_per_token +   # token-aware ROI
            self.roi_weights[1] * roi_score +        # absolute ROI
            self.roi_weights[2] * relevance_score +
            self.roi_weights[3] * usage_probability +
            self.roi_weights[4] * recency_score
        )

        return final_score

    def _generate_reasoning(
        self,
        roi_score: float,
        relevance_score: float,
        usage_probability: float,
        recency_score: float,
        final_score: float
    ) -> str:
        """Generate human-readable reasoning for the prediction."""
        reasons = []

        if relevance_score > 0.5:
            reasons.append(f"High relevance ({relevance_score:.2f}) to task context")
        elif relevance_score < 0.1:
            reasons.append(f"Low relevance ({relevance_score:.2f}) to task context")

        if roi_score > 0.001:
            reasons.append(f"Good ROI ({roi_score:.6f})")
        else:
            reasons.append(f"Poor ROI ({roi_score:.6f})")

        if recency_score > 0.7:
            reasons.append("Recently modified")
        elif recency_score < 0.3:
            reasons.append("Old file")

        if usage_probability > 0.5:
            reasons.append("Frequently used historically")

        return "; ".join(reasons) if reasons else "Default scoring"

    def _knapsack_pack(self, predictions: List[FilePrediction], budget_tokens: int) -> List[str]:
        """Select files within token budget using a token-aware density packing.

        We prioritize files by value-per-token (density = final_score / adjusted_token_cost)
        to avoid selecting a few large, high-score files that consume the budget.
        """
        candidates = []

        for p in predictions:
            if not p.predicted_needed:
                continue

            est_tokens = self._estimate_token_cost(p.file_path)

            # Apply a stronger soft penalty for large files so they are deprioritized
            # in density calculation without making the selection impossible.
            # Scales roughly: +1 per scale tokens, up to +4x penalty for very large files.
            penalty = 1.0 + min(4.0, est_tokens / self.penalty_scale)
            adjusted_cost = est_tokens * penalty

            # Density = value per (adjusted) token
            density = p.final_score / (adjusted_cost + 1)

            candidates.append((p, density, est_tokens, adjusted_cost))

        # Sort by density (value per token) descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        selected = []
        total_tokens = 0

        for p, density, est_tokens, adjusted_cost in candidates:
            # Use the raw estimated tokens for budget accounting (more conservative)
            if total_tokens + est_tokens <= budget_tokens:
                selected.append(p.file_path)
                total_tokens += est_tokens

        return selected

    def _estimate_token_cost(self, file_path: str) -> int:
        """Estimate token cost of a file with smoothing and caps.

        - Base estimate: 1 token per 4 characters
        - Minimum floor to avoid treating tiny files as zero-cost
        - Maximum cap to prevent very large files from dominating heuristics
        """
        try:
            full_path = self.workspace / file_path
            if not full_path.exists():
                return 0

            content = full_path.read_text(encoding='utf-8')
            base = max(len(content) // 4, 64)  # floor of 64 tokens

            # Apply a cap so single huge files don't break budgets
            capped = min(base, 20000)

            # Small heuristic: markdown files are slightly cheaper due to token density
            if file_path.endswith('.md'):
                capped = int(capped * 0.9)

            return int(capped)
        except:
            return 1000  # Default estimate (conservative)

    def _log_prediction(self, task_context: str, selected_files: List[str]) -> None:
        """Log prediction for future learning."""
        # Save to database for learning
        task_id = f"TASK_0156_test_{int(datetime.now().timestamp())}"  # Generate a test task ID

        # Determine current loop from current.json if available
        try:
            import json
            current_text = (self.workspace / "current.json").read_text(encoding='utf-8')
            current = json.loads(current_text)
            loop_num = current.get('STATE', {}).get('loop')
        except Exception:
            loop_num = None

        self.db.save_bootstrap_prediction(
            task_id=task_id,
            task_context=task_context,
            predicted_files=selected_files,
            loop_num=loop_num
        )

    def track_actual_usage(self, task_id: str, accessed_files: List[str]) -> None:
        """Track which files were actually accessed during a task."""
        # Find the most recent prediction for this task and update accuracy
        history = self.db.get_bootstrap_prediction_history(task_id=task_id, limit=1)
        if history:
            prediction_id = history[0]['id']
            self.db.update_bootstrap_prediction_accuracy(prediction_id, accessed_files)


# CLI interface for testing
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Run BootstrapPredictor (Phase 2)')
    parser.add_argument('task_context', help='Task context string')
    parser.add_argument('--budget', type=int, default=60000, help='Token budget')
    parser.add_argument('--dry-run', action='store_true', help='Do not log to DB; write dry-run JSONL instead')
    args = parser.parse_args()

    task_context = args.task_context
    workspace = Path('.').resolve()

    predictor = BootstrapPredictor(workspace)
    selected_files = predictor.predict_needed_files(task_context, budget_tokens=args.budget, dry_run=args.dry_run)

    print(f"Selected files for '{task_context}':")
    for file_path in selected_files:
        print(f"  - {file_path}")

    if args.dry_run:
        print(f"Dry-run logged to {workspace / '.bootstrap_dry_runs.jsonl'}")

    # Autostart-safe CLI behavior: only print/log predictions.
    # Service startup is handled by dedicated supervisors.


def start_essential_services(selected_files: List[str], workspace: Path) -> None:
    """Start essential services that are predicted to be needed."""
    import subprocess
    from pathlib import Path

    # Essential services that should be started if their files are selected
    essential_services = {
        'token_monitor.py': 'Token Monitor Service',
        'loop_guardrails.py': 'Loop Guardrails Service',
        'checkpoint_manager.py': 'Checkpoint Manager Service',
        'ai_integrity_protector.py': 'AI Integrity Protector Service',
        'consistency_auditor.py': 'Consistency Auditor Service',
        'service_orchestrator.py': 'Service Orchestrator Service',
        'backup/backup_manager.py': ('Backup Manager Service', ['--start-auto']),
    }

    selected_basenames = {Path(f).name for f in selected_files}

    print("\nStarting essential services...")
    started_count = 0

    for script, service_info in essential_services.items():
        script_path = workspace / script
        if script_path.exists() and script_path.name in selected_basenames:
            if isinstance(service_info, tuple):
                desc, args = service_info
            else:
                desc, args = service_info, None

            if start_script(str(script_path), desc, args):
                started_count += 1
        else:
            print(f"  - {script} not selected or not found")

    print(f"Started {started_count} essential services.")


def is_script_running(script_name: str) -> bool:
    """Check if a script is already running."""
    try:
        result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq python.exe', '/FO', 'CSV'],
                              capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        for line in lines[1:]:  # Skip header
            if script_name in line:
                return True
    except:
        pass
    return False


def start_script(script_path: str, description: str, args: List[str] = None) -> bool:
    """Start a script if not already running."""
    script_name = Path(script_path).name
    if is_script_running(script_name):
        print(f"  ✓ {description} already running")
        return True

    print(f"  Starting: {description}")
    try:
        cmd = ['python', script_path]
        if args:
            cmd.extend(args)
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  ✓ Started {description} (PID: {process.pid})")
        return True
    except Exception as e:
        print(f"  ✗ Failed to start {description}: {e}")
        return False
