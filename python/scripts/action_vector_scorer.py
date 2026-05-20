#!/usr/bin/env python3
"""
TASK_0259 - Soft action-vector scorer

Builds a reasoned action recommendation:
- reuse_existing
- adapt_existing
- create_new

Inputs:
- similarity
- recency
- regression history
- divergence risk
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parent.parent


def _load_problem_preflight():
    import importlib.util
    import sys

    module_path = ROOT / "scripts" / "problem_preflight.py"
    spec = importlib.util.spec_from_file_location("problem_preflight", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load problem_preflight module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_knowledge_db():
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from knowledge_db import KnowledgeDB  # type: ignore

    return KnowledgeDB


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_current_loop() -> int:
    current_path = ROOT / "current.json"
    if not current_path.exists():
        return 0
    try:
        data = json.loads(current_path.read_text(encoding="utf-8"))
        return int(data.get("STATE", {}).get("loop", 0) or 0)
    except Exception:
        return 0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass(frozen=True)
class ActionScore:
    action: str
    score: float
    reasons: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "score": round(self.score, 4),
            "reasons": self.reasons,
        }


def _compute_regression_risk(query: str, limit: int = 30) -> float:
    KnowledgeDB = _load_knowledge_db()
    db = KnowledgeDB(ROOT)
    try:
        fails = db.search(
            query,
            types=["lesson"],
            category="failure",
            semantic=True,
            limit=limit,
        )
        warns = db.search(
            query,
            types=["lesson"],
            category="warning",
            semantic=True,
            limit=limit,
        )
    finally:
        db.close()

    weighted = len(fails) + (0.5 * len(warns))
    # Saturate around 10 weighted hits.
    return _clamp01(weighted / 10.0)


def _compute_recency(matches: Sequence[Dict[str, Any]], current_loop: int) -> float:
    if current_loop <= 0:
        return 0.5
    deltas: List[float] = []
    for m in matches:
        loop = m.get("loop")
        if isinstance(loop, int) and loop > 0:
            delta = max(0, current_loop - loop)
            # Fresh loops => score near 1.0, decays with age.
            deltas.append(1.0 / (1.0 + (delta / 12.0)))
    return _mean(deltas) if deltas else 0.35


def _compute_divergence_risk(matches: Sequence[Dict[str, Any]], similarity_top: float) -> float:
    if not matches:
        return 0.8
    type_diversity = len({str(m.get("type", "")) for m in matches}) / 5.0
    confidence_spread = 1.0 - _mean([float(m.get("confidence", 0.0)) for m in matches[:5]])
    base = 0.45 * type_diversity + 0.35 * confidence_spread + 0.20 * (1.0 - similarity_top)
    return _clamp01(base)


def score_actions(
    *,
    problem: str,
    surface: Optional[str],
    keywords: Sequence[str],
    files: Sequence[str],
    limit: int = 5,
) -> Dict[str, Any]:
    preflight = _load_problem_preflight()
    fp = preflight.build_fingerprint(
        problem=problem,
        surface=surface,
        keywords=keywords,
        files=files,
    )
    preflight_result = preflight.similarity_probe(
        workspace_root=ROOT,
        fingerprint=fp,
        limit=max(3, limit),
    )
    matches = preflight_result.get("matches", [])
    similarity_top = float(matches[0]["confidence"]) if matches else 0.0
    similarity_avg = _mean([float(m.get("confidence", 0.0)) for m in matches[:3]])

    current_loop = _read_current_loop()
    recency = _compute_recency(matches, current_loop=current_loop)
    regression_risk = _compute_regression_risk(fp.query)
    divergence_risk = _compute_divergence_risk(matches, similarity_top=similarity_top)

    reuse_score = _clamp01(
        0.50 * similarity_top
        + 0.25 * recency
        + 0.15 * (1.0 - regression_risk)
        + 0.10 * (1.0 - divergence_risk)
    )
    adapt_score = _clamp01(
        0.35 * similarity_avg
        + 0.20 * recency
        + 0.20 * (1.0 - regression_risk)
        + 0.25 * (1.0 - abs(0.5 - similarity_avg))
    )
    create_new_score = _clamp01(
        0.45 * (1.0 - similarity_top)
        + 0.20 * regression_risk
        + 0.35 * divergence_risk
    )

    vectors = [
        ActionScore(
            action="reuse_existing",
            score=reuse_score,
            reasons=[
                f"similarity_top={similarity_top:.3f}",
                f"recency={recency:.3f}",
                f"regression_risk={regression_risk:.3f}",
                f"divergence_risk={divergence_risk:.3f}",
            ],
        ),
        ActionScore(
            action="adapt_existing",
            score=adapt_score,
            reasons=[
                f"similarity_avg_top3={similarity_avg:.3f}",
                f"recency={recency:.3f}",
                f"regression_risk={regression_risk:.3f}",
                f"divergence_risk={divergence_risk:.3f}",
            ],
        ),
        ActionScore(
            action="create_new",
            score=create_new_score,
            reasons=[
                f"novelty_pressure={1.0 - similarity_top:.3f}",
                f"regression_risk={regression_risk:.3f}",
                f"divergence_risk={divergence_risk:.3f}",
            ],
        ),
    ]
    ranked = sorted(vectors, key=lambda s: s.score, reverse=True)

    return {
        "timestamp": _utc_now(),
        "current_loop": current_loop,
        "fingerprint": fp.as_dict(),
        "inputs": {
            "similarity_top": round(similarity_top, 4),
            "similarity_avg_top3": round(similarity_avg, 4),
            "recency": round(recency, 4),
            "regression_risk": round(regression_risk, 4),
            "divergence_risk": round(divergence_risk, 4),
        },
        "action_vector": [r.as_dict() for r in ranked],
        "top_action": ranked[0].action if ranked else "create_new",
        "preflight_matches": matches,
    }


def _persist_decision(metadata: Dict[str, Any]) -> Path:
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    out_path = logs_dir / "action_vector_decisions.jsonl"
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
    return out_path


def _csv_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Soft action-vector scorer (TASK_0259).")
    parser.add_argument("--problem", required=True, help="Problem summary.")
    parser.add_argument("--surface", help="Optional surface area.")
    parser.add_argument("--keywords", help="Comma-separated keywords.")
    parser.add_argument("--files", help="Comma-separated file paths.")
    parser.add_argument("--limit", type=int, default=5, help="Number of preflight matches.")
    parser.add_argument(
        "--chosen-action",
        choices=["reuse_existing", "adapt_existing", "create_new"],
        help="Optional selected action to record.",
    )
    parser.add_argument(
        "--rationale",
        help="Short rationale (required when choosing lower-ranked create_new).",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON output.")
    args = parser.parse_args()

    result = score_actions(
        problem=args.problem,
        surface=args.surface,
        keywords=_csv_list(args.keywords),
        files=_csv_list(args.files),
        limit=max(3, args.limit),
    )

    ranked = [row["action"] for row in result.get("action_vector", [])]
    top = ranked[0] if ranked else "create_new"
    requires_rationale = False
    validation_error = None

    if args.chosen_action:
        result["chosen_action"] = args.chosen_action
        if args.chosen_action == "create_new" and top != "create_new":
            requires_rationale = True
            rationale = (args.rationale or "").strip()
            if len(rationale) < 20:
                validation_error = (
                    "RATIONALE_REQUIRED: choosing lower-ranked create_new requires rationale >= 20 chars."
                )
            else:
                result["chosen_rationale"] = rationale
        elif args.rationale:
            result["chosen_rationale"] = args.rationale.strip()

    result["requires_rationale"] = requires_rationale
    if validation_error:
        result["validation_error"] = validation_error

    _persist_decision(result)

    payload = json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False)
    try:
        print(payload)
    except UnicodeEncodeError:
        print(payload.encode("utf-8", errors="backslashreplace").decode("ascii", errors="ignore"))

    return 2 if validation_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
