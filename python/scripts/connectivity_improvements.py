#!/usr/bin/env python3
"""
Connectivity Improvements Analyzer

Builds a lightweight knowledge graph snapshot from keeper_knowledge.db and
produces actionable connectivity suggestions for small/isolated clusters.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def table_columns(conn: sqlite3.Connection, table: str) -> Set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def safe_load_refs(raw: str | None) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data]
    except Exception:
        pass
    return []


VALID_ID_RE = re.compile(
    r"^(TASK_\d+|ARCHIV_\d+(?:_[A-Za-z0-9_]+)?|BUG_\d+(?:_L\d+)?|CODE_[A-Za-z0-9_]+|report_[A-Za-z0-9_]+)$"
)


def normalize_ref_target(ref: str) -> str:
    token = (ref or "").split("|", 1)[0].strip()
    if token.startswith("[ref:"):
        token = token[5:]
    if token.endswith("]"):
        token = token[:-1]

    # Resolve common path-like refs to basename stem.
    token = token.replace("\\", "/").strip()
    if "/" in token:
        token = token.rsplit("/", 1)[-1]
    if token.endswith(".md"):
        token = token[:-3]

    return token if VALID_ID_RE.match(token) else ""


def build_graph(db_path: Path) -> Tuple[Set[str], Dict[str, Set[str]], Dict[str, str]]:
    conn = sqlite3.connect(str(db_path))
    nodes: Set[str] = set()
    edges: Dict[str, Set[str]] = defaultdict(set)
    node_types: Dict[str, str] = {}

    table_specs = [
        ("docs", "id"),
        ("reports", "id"),
        ("tasks", "id"),
        ("archives", "id"),
        ("bugs", "id"),
        ("code", "id"),
    ]

    try:
        for table, id_col in table_specs:
            cols = table_columns(conn, table)
            if id_col not in cols:
                continue
            has_refs = "refs" in cols
            query = f"SELECT {id_col}" + (", refs" if has_refs else "") + f" FROM {table}"
            for row in conn.execute(query):
                node = str(row[0])
                nodes.add(node)
                node_types[node] = table
                refs = safe_load_refs(row[1]) if has_refs else []
                for ref in refs:
                    target = normalize_ref_target(ref)
                    if target:
                        edges[node].add(target)
                        edges[target].add(node)

        # Ensure all referenced nodes are in node set.
        for src, targets in list(edges.items()):
            nodes.add(src)
            for tgt in targets:
                nodes.add(tgt)
                node_types.setdefault(tgt, "external_ref")
    finally:
        conn.close()

    return nodes, edges, node_types


def connected_components(nodes: Set[str], edges: Dict[str, Set[str]]) -> List[List[str]]:
    remaining = set(nodes)
    comps: List[List[str]] = []

    while remaining:
        root = next(iter(remaining))
        stack = [root]
        comp = []
        remaining.remove(root)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in edges.get(cur, set()):
                if nxt in remaining:
                    remaining.remove(nxt)
                    stack.append(nxt)
        comps.append(sorted(comp))
    return comps


def density(nodes: Set[str], edges: Dict[str, Set[str]]) -> float:
    n = len(nodes)
    if n <= 1:
        return 0.0
    undirected_edge_count = sum(len(v) for v in edges.values()) / 2.0
    max_edges = (n * (n - 1)) / 2.0
    return undirected_edge_count / max_edges if max_edges else 0.0


def suggest_links(components: List[List[str]], node_types: Dict[str, str], max_suggestions: int = 20) -> List[Dict[str, str]]:
    small = [c for c in components if len(c) <= 3]
    large = [c for c in components if len(c) > 3]
    suggestions: List[Dict[str, str]] = []

    if not large:
        return suggestions

    # Suggest linking small-cluster nodes to same-type nodes in large clusters.
    large_nodes = [n for comp in large for n in comp]
    by_type: Dict[str, List[str]] = defaultdict(list)
    for n in large_nodes:
        by_type[node_types.get(n, "unknown")].append(n)

    for comp in small:
        for node in comp:
            typ = node_types.get(node, "unknown")
            candidates = by_type.get(typ) or large_nodes
            if not candidates:
                continue
            target = candidates[0]
            suggestions.append(
                {
                    "source": node,
                    "target": target,
                    "reason": f"Connect small cluster node ({typ}) into main graph",
                }
            )
            if len(suggestions) >= max_suggestions:
                return suggestions
    return suggestions


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze knowledge graph connectivity and emit improvement suggestions.")
    parser.add_argument("--db", default="keeper_knowledge.db", help="Path to knowledge DB.")
    parser.add_argument("--output", default="", help="Output JSON path (default: reports/connectivity_improvements_<ts>.json)")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 0

    nodes, edges, node_types = build_graph(db_path)
    comps = connected_components(nodes, edges)
    graph_density = density(nodes, edges)
    small_components = [c for c in comps if len(c) <= 3]
    suggestions = suggest_links(comps, node_types, max_suggestions=25)

    payload = {
        "generated_at": utc_now_iso(),
        "db_path": str(db_path),
        "nodes": len(nodes),
        "components": len(comps),
        "small_components": len(small_components),
        "density": graph_density,
        "largest_component_size": max((len(c) for c in comps), default=0),
        "suggestions": suggestions,
    }

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    output = Path(args.output) if args.output else reports_dir / f"connectivity_improvements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"nodes={payload['nodes']} components={payload['components']} small_components={payload['small_components']} density={payload['density']:.4f}")
    print(f"suggestions={len(suggestions)}")
    print(f"report={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
