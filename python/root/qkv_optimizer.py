"""
QKV Optimizer for Mega.md Methodology
Transformer-inspired attention mechanism for depth-first knowledge graph traversal
"""

import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import math
from datetime import datetime, timezone

class QKVOptimizer:
    """
    Query-Key-Value optimization framework for conceptual understanding.

    Unifies mega.md depth-first methodology with transformer attention mechanisms
    to enable predictive conceptual processing.
    """

    def __init__(self, workspace_root: Path, embedding_dim: int = 128):
        self.workspace_root = workspace_root
        self.embedding_dim = embedding_dim
        self.knowledge_db = self._load_knowledge_base()
        self.conceptual_embeddings = self._build_embeddings()

    def _load_knowledge_base(self) -> Dict:
        """Load knowledge base from keeper_knowledge.db"""
        try:
            import sqlite3
            db_path = self.workspace_root / 'keeper_knowledge.db'
            if not db_path.exists():
                return {}

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get all sections
            cursor.execute('SELECT id, content, metadata FROM sections')
            rows = cursor.fetchall()

            knowledge = {}
            for row in rows:
                section_id, content, metadata = row
                knowledge[section_id] = {
                    'content': content,
                    'metadata': json.loads(metadata) if metadata else {}
                }

            conn.close()
            return knowledge

        except Exception as e:
            print(f"Warning: Could not load knowledge base: {e}")
            return {}

    def _build_embeddings(self) -> Dict[str, np.ndarray]:
        """Build conceptual embeddings for knowledge nodes"""
        embeddings = {}

        for section_id, data in self.knowledge_db.items():
            # Simple hash-based embedding (can be improved with sentence-transformers)
            content = data['content']
            hash_val = hash(content) % (2**32)
            np.random.seed(hash_val)

            # Create deterministic embedding from content hash
            embedding = np.random.normal(0, 1, self.embedding_dim)
            embedding = embedding / np.linalg.norm(embedding)  # Normalize

            embeddings[section_id] = embedding

        return embeddings

    def compute_attention(self, query_embedding: np.ndarray,
                         key_embeddings: List[np.ndarray],
                         value_embeddings: List[np.ndarray],
                         mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Compute scaled dot-product attention

        Args:
            query_embedding: Query vector (d_k,)
            key_embeddings: Key vectors (num_keys, d_k)
            value_embeddings: Value vectors (num_keys, d_v)
            mask: Optional attention mask

        Returns:
            Attention output (d_v,)
        """
        # Scaled dot-product attention
        d_k = query_embedding.shape[0]

        # Compute attention scores
        scores = np.dot(key_embeddings, query_embedding) / math.sqrt(d_k)

        # Apply mask if provided
        if mask is not None:
            scores = scores * mask + (1 - mask) * (-1e9)

        # Softmax
        attention_weights = self._softmax(scores)

        # Apply attention to values
        output = np.dot(attention_weights, value_embeddings)

        return output

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Compute softmax"""
        exp_x = np.exp(x - np.max(x))  # Numerical stability
        return exp_x / np.sum(exp_x)

    def multi_head_attention(self, query: np.ndarray,
                           keys: List[np.ndarray],
                           values: List[np.ndarray],
                           num_heads: int = 8) -> np.ndarray:
        """
        Multi-head attention mechanism

        Args:
            query: Query embedding
            keys: List of key embeddings
            values: List of value embeddings
            num_heads: Number of attention heads

        Returns:
            Multi-head attention output
        """
        head_dim = self.embedding_dim // num_heads
        head_outputs = []

        for h in range(num_heads):
            # Split embeddings for this head
            start_idx = h * head_dim
            end_idx = (h + 1) * head_dim

            query_head = query[start_idx:end_idx]
            key_heads = [k[start_idx:end_idx] for k in keys]
            value_heads = [v[start_idx:end_idx] for v in values]

            # Compute attention for this head
            head_output = self.compute_attention(query_head, key_heads, value_heads)
            head_outputs.append(head_output)

        # Concatenate heads
        multi_head_output = np.concatenate(head_outputs)

        # Final linear transformation (simplified - identity for now)
        return multi_head_output

    def predict_concept_relationships(self, current_concept: str,
                                    candidate_concepts: List[str],
                                    max_depth: int = 5) -> List[Tuple[str, float]]:
        """
        Predict conceptual relationships using QKV attention

        Args:
            current_concept: Current concept/section ID
            candidate_concepts: Candidate related concepts
            max_depth: Maximum depth for relationship exploration

        Returns:
            List of (concept_id, relevance_score) tuples
        """
        if current_concept not in self.conceptual_embeddings:
            return []

        query_embedding = self.conceptual_embeddings[current_concept]

        # Get embeddings for candidates
        key_embeddings = []
        value_embeddings = []
        valid_candidates = []

        for candidate in candidate_concepts:
            if candidate in self.conceptual_embeddings:
                key_embeddings.append(self.conceptual_embeddings[candidate])
                value_embeddings.append(self.conceptual_embeddings[candidate])
                valid_candidates.append(candidate)

        if not key_embeddings:
            return []

        # Convert to numpy arrays
        key_embeddings = np.array(key_embeddings)
        value_embeddings = np.array(value_embeddings)

        # Compute multi-head attention
        attended_output = self.multi_head_attention(
            query_embedding, key_embeddings.tolist(), value_embeddings.tolist()
        )

        # Compute relevance scores (cosine similarity with attended output)
        scores = []
        for i, candidate in enumerate(valid_candidates):
            similarity = np.dot(attended_output, value_embeddings[i]) / (
                np.linalg.norm(attended_output) * np.linalg.norm(value_embeddings[i])
            )
            scores.append((candidate, float(similarity)))

        # Sort by relevance
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores

    def depth_first_concept_exploration(self, start_concept: str,
                                      max_depth: int = 5,
                                      branching_factor: int = 5) -> Dict:
        """
        Depth-first conceptual exploration using QKV optimization

        Args:
            start_concept: Starting concept ID
            max_depth: Maximum exploration depth
            branching_factor: Maximum concepts to explore per level

        Returns:
            Exploration results with predicted relationships
        """
        explored = set()
        concept_tree = {}

        def explore_concept(concept_id: str, depth: int, path: List[str]):
            if depth > max_depth or concept_id in explored:
                return

            explored.add(concept_id)
            path = path + [concept_id]

            # Get all available concepts as candidates
            all_concepts = list(self.conceptual_embeddings.keys())
            candidates = [c for c in all_concepts if c not in explored]

            # Predict most relevant relationships
            predictions = self.predict_concept_relationships(
                concept_id, candidates, max_depth
            )

            # Take top branching_factor predictions
            top_predictions = predictions[:branching_factor]

            concept_tree[concept_id] = {
                'depth': depth,
                'path': path,
                'predictions': top_predictions,
                'children': []
            }

            # Recursively explore children
            for child_concept, score in top_predictions:
                if child_concept not in explored:
                    explore_concept(child_concept, depth + 1, path)
                    concept_tree[concept_id]['children'].append(child_concept)

        explore_concept(start_concept, 0, [])

        return {
            'start_concept': start_concept,
            'max_depth': max_depth,
            'total_explored': len(explored),
            'concept_tree': concept_tree,
            'explored_concepts': list(explored)
        }

    def optimize_task_sequence(self, task_ids: List[str]) -> List[str]:
        """
        Optimize task execution sequence using conceptual relationships

        Args:
            task_ids: List of task IDs to optimize

        Returns:
            Optimized task sequence
        """
        if len(task_ids) <= 1:
            return task_ids

        # Build relationship graph
        relationship_graph = {}

        for task in task_ids:
            candidates = [t for t in task_ids if t != task]
            predictions = self.predict_concept_relationships(task, candidates, max_depth=3)
            relationship_graph[task] = [pred[0] for pred in predictions[:3]]  # Top 3 relationships

        # Simple topological sort based on relationships (can be improved)
        optimized_sequence = []
        remaining = set(task_ids)

        while remaining:
            # Find task with fewest dependencies
            best_task = min(remaining, key=lambda t: len([r for r in relationship_graph[t] if r in remaining]))
            optimized_sequence.append(best_task)
            remaining.remove(best_task)

        return optimized_sequence

    def save_model(self, filepath: str):
        """Save QKV optimizer state"""
        state = {
            'embedding_dim': self.embedding_dim,
            'conceptual_embeddings': {k: v.tolist() for k, v in self.conceptual_embeddings.items()},
            'knowledge_base_size': len(self.knowledge_db),
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

    def load_model(self, filepath: str):
        """Load QKV optimizer state"""
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)

        self.embedding_dim = state['embedding_dim']
        self.conceptual_embeddings = {k: np.array(v) for k, v in state['conceptual_embeddings'].items()}


def demo_qkv_optimization():
    """Demonstration of QKV optimization framework"""
    workspace = Path(__file__).parent

    # Initialize optimizer
    optimizer = QKVOptimizer(workspace)

    print(f"Loaded {len(optimizer.knowledge_db)} knowledge sections")
    print(f"Built embeddings for {len(optimizer.conceptual_embeddings)} concepts")

    # Get some concept IDs for demonstration
    concept_ids = list(optimizer.conceptual_embeddings.keys())[:10]

    if len(concept_ids) >= 2:
        start_concept = concept_ids[0]

        # Depth-first exploration
        exploration = optimizer.depth_first_concept_exploration(start_concept, max_depth=3)
        print(f"\nExplored {exploration['total_explored']} concepts from {start_concept}")

        # Task sequence optimization (using concept IDs as proxy)
        if len(concept_ids) > 3:
            original_sequence = concept_ids[:5]
            optimized_sequence = optimizer.optimize_task_sequence(original_sequence)
            print(f"\nOriginal sequence: {original_sequence}")
            print(f"Optimized sequence: {optimized_sequence}")

    # Save model
    optimizer.save_model(str(workspace / 'qkv_model.json'))
    print("\nQKV model saved to qkv_model.json")


if __name__ == "__main__":
    demo_qkv_optimization()