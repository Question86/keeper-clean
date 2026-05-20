#!/usr/bin/env python3
"""
Soft preflight for TASK_0258:
- Build deterministic problem fingerprint
- Probe similar prior solutions in keeper_knowledge.db
- Return top matches with confidence and artifact pointers
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _workspace_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge_db import KnowledgeDB, SearchResult  # noqa: E402


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class Fingerprint:
    error_class: str
    surface: str
    keywords: Tuple[str, ...]
    files: Tuple[str, ...]
    query: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "error_class": self.error_class,
            "surface": self.surface,
            "keywords": list(self.keywords),
            "files": list(self.files),
            "query": self.query,
        }


def _norm_text(value: Optional[str]) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9_./\\ ]+", " ", value.strip().lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _tokenize(value: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9_./\\-]+", value.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def _dedupe_sorted(values: Sequence[str]) -> Tuple[str, ...]:
    return tuple(sorted({v for v in values if v}))


def _infer_error_class(problem: str, keywords: Sequence[str]) -> str:
    text = f"{problem} {' '.join(keywords)}".lower()
    heuristics = [
        ("state_mismatch", ("stale", "mismatch", "inconsistent", "drift")),
        ("bootstrap_flow", ("bootstrap", "loop_gate", "confirm-bootstrap")),
        ("validation_failure", ("validation", "blocked", "gate")),
        ("indexing_gap", ("index", "indexed", "knowledge db")),
        ("runtime_error", ("exception", "traceback", "error", "failed")),
    ]
    for label, signals in heuristics:
        if any(sig in text for sig in signals):
            return label
    return "general"


def build_fingerprint(
    *,
    problem: str,
    error_class: Optional[str] = None,
    surface: Optional[str] = None,
    keywords: Optional[Sequence[str]] = None,
    files: Optional[Sequence[str]] = None,
) -> Fingerprint:
    norm_problem = _norm_text(problem)
    key_tokens = list(_tokenize(norm_problem))
    if keywords:
        key_tokens.extend(_tokenize(" ".join(keywords)))
    dedup_keywords = _dedupe_sorted(key_tokens)[:20]

    norm_files = [_norm_text(f).replace("\\", "/") for f in (files or [])]
    dedup_files = _dedupe_sorted(norm_files)[:12]

    resolved_surface = _norm_text(surface) if surface else "general"
    resolved_error_class = _norm_text(error_class) if error_class else _infer_error_class(norm_problem, dedup_keywords)

    query_parts: List[str] = [resolved_error_class, resolved_surface]
    query_parts.extend(dedup_keywords[:8])
    query_parts.extend([Path(f).name for f in dedup_files[:4]])
    query = " ".join(p for p in query_parts if p).strip()

    return Fingerprint(
        error_class=resolved_error_class or "general",
        surface=resolved_surface or "general",
        keywords=dedup_keywords,
        files=dedup_files,
        query=query,
    )


def _result_pointer(result: SearchResult) -> str:
    rtype = result.type
    rid = result.id
    ctx = result.context or {}

    if rtype == "report":
        return f"reports/{rid}.md" if not rid.endswith(".md") else f"reports/{rid}"
    if rtype == "archive":
        return f"archive/{rid}.md" if not rid.endswith(".md") else f"archive/{rid}"
    if rtype == "task":
        task_id = rid if rid.startswith("TASK_") else f"TASK_{rid}"
        return f"tasks/task_{task_id}.md"
    if rtype == "doc":
        if "/" in rid:
            return rid
        return f"docs/{rid}.md" if not rid.endswith(".md") else f"docs/{rid}"
    if rtype == "lesson":
        source_type = str(ctx.get("source_type") or "")
        source_id = str(ctx.get("source_id") or "")
        if source_type == "report" and source_id:
            return f"reports/{source_id}.md"
        if source_type == "archive" and source_id:
            return f"archive/{source_id}.md"
        return "keeper_knowledge.db#lessons"
    return f"keeper_knowledge.db#{rtype}:{rid}"


def _candidate_text(result: SearchResult) -> str:
    ctx = result.context or {}
    ctx_values = " ".join(str(v) for v in ctx.values() if isinstance(v, (str, int, float)))
    return f"{result.id} {result.snippet} {ctx_values}".lower()


def _overlap_score(fingerprint: Fingerprint, result: SearchResult) -> float:
    query_tokens = set(fingerprint.keywords)
    file_tokens = {Path(f).name.lower() for f in fingerprint.files}
    focus = query_tokens.union(file_tokens)
    if not focus:
        return 0.0

    text = _candidate_text(result)
    hits = sum(1 for token in focus if token and token in text)
    return min(1.0, hits / max(1, len(focus)))


def _normalize_relevance(values: Sequence[float]) -> List[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high == low:
        return [0.6 for _ in values]
    return [(v - low) / (high - low) for v in values]


def similarity_probe(
    *,
    workspace_root: Path,
    fingerprint: Fingerprint,
    limit: int = 5,
) -> Dict[str, Any]:
    variants: List[str] = [
        fingerprint.query,
        " ".join(fingerprint.keywords[:8]),
        f"{fingerprint.error_class} {fingerprint.surface}".strip(),
        " ".join(Path(f).stem for f in fingerprint.files[:3]),
    ]
    # Keep deterministic order but drop empty/duplicate variants.
    query_variants: List[str] = []
    seen = set()
    for v in variants:
        vv = _norm_text(v)
        if vv and vv not in seen:
            query_variants.append(vv)
            seen.add(vv)

    db = KnowledgeDB(workspace_root)
    try:
        raw: List[SearchResult] = []
        for q in query_variants:
            chunk = db.search(
                q,
                types=["report", "archive", "lesson", "task", "doc"],
                semantic=True,
                limit=max(limit * 3, 15),
            )
            raw.extend(chunk)
    finally:
        db.close()

    relevances = [float(r.relevance) for r in raw]
    rel_norm = _normalize_relevance(relevances)

    enriched: List[Dict[str, Any]] = []
    for idx, result in enumerate(raw):
        overlap = _overlap_score(fingerprint, result)
        confidence = round(0.65 * rel_norm[idx] + 0.35 * overlap, 4)
        enriched.append(
            {
                "rank": idx + 1,
                "type": result.type,
                "id": result.id,
                "loop": result.context.get("loop_num"),
                "artifact_pointer": _result_pointer(result),
                "relevance": round(float(result.relevance), 4),
                "confidence": confidence,
                "snippet": result.snippet[:220],
            }
        )

    # Deduplicate by pointer, keep highest confidence.
    dedup: Dict[str, Dict[str, Any]] = {}
    for item in enriched:
        key = item["artifact_pointer"]
        prior = dedup.get(key)
        if prior is None or item["confidence"] > prior["confidence"]:
            dedup[key] = item

    top = sorted(dedup.values(), key=lambda r: r["confidence"], reverse=True)[:limit]
    for i, item in enumerate(top, start=1):
        item["rank"] = i

    return {
        "fingerprint": fingerprint.as_dict(),
        "matches": top,
        "match_count": len(top),
        "mode": "soft_preflight",
        "recommendation": "Use top matches as reuse/adapt guidance before creating net-new implementations.",
    }


def _parse_csv_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Soft preflight fingerprint + similarity probe (TASK_0258).")
    parser.add_argument("--problem", required=True, help="Short description of the current problem.")
    parser.add_argument("--error-class", dest="error_class", help="Optional explicit error_class override.")
    parser.add_argument("--surface", help="Optional surface area (api, bootstrap, docs, db, ui, etc).")
    parser.add_argument("--keywords", help="Comma-separated keywords.")
    parser.add_argument("--files", help="Comma-separated file paths.")
    parser.add_argument("--limit", type=int, default=5, help="Top matches to return.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    fingerprint = build_fingerprint(
        problem=args.problem,
        error_class=args.error_class,
        surface=args.surface,
        keywords=_parse_csv_list(args.keywords),
        files=_parse_csv_list(args.files),
    )
    result = similarity_probe(workspace_root=ROOT, fingerprint=fingerprint, limit=max(1, args.limit))
    payload = json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False)
    try:
        print(payload)
    except UnicodeEncodeError:
        # Windows cp1252 fallback
        print(payload.encode("utf-8", errors="backslashreplace").decode("ascii", errors="ignore"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
