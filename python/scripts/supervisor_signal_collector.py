#!/usr/bin/env python3
"""
Supervisor Analysis Signal Collector

Collects lightweight operational signals from selected analysis modules and
writes a machine-readable snapshot for the autostart supervisor.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.code_bloat_detector import CodeBloatDetector
from analysis.dimensional_mapper import DimensionalMapper
from analysis.loop_insight_extractor import LoopInsightExtractor
from analysis.trend_analyzer import TrendAnalyzer


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def collect_bloat_signal(workspace_root: Path) -> Dict[str, Any]:
    target_files = [
        workspace_root / "analysis" / "code_bloat_detector.py",
        workspace_root / "analysis" / "connectivity_mapper.py",
        workspace_root / "analysis" / "dimensional_mapper.py",
        workspace_root / "analysis" / "loop_insight_extractor.py",
        workspace_root / "analysis" / "pattern_recognizer.py",
        workspace_root / "analysis" / "quality_correlator.py",
        workspace_root / "analysis" / "search_synergy.py",
        workspace_root / "analysis" / "statistical_sampler.py",
        workspace_root / "analysis" / "trend_analyzer.py",
        workspace_root / "analysis" / "analyze_breadcrumb_data.py",
        workspace_root / "analysis" / "breadcrumb_scanner.py",
    ]

    detector = CodeBloatDetector()
    analyzed: List[Dict[str, Any]] = []
    missing = 0

    for file_path in target_files:
        if not file_path.exists():
            missing += 1
            continue
        result = detector.analyze_file(str(file_path))
        if "error" in result or "syntax_error" in result:
            continue
        analyzed.append(result)

    if not analyzed:
        return {
            "ok": False,
            "error": "no analyzable analysis files found",
            "missing_files": missing,
        }

    overall = detector.calculate_overall_bloat(analyzed)
    top_files = sorted(analyzed, key=lambda r: r.get("bloat_score", 0), reverse=True)[:5]

    return {
        "ok": True,
        "analyzed_files": len(analyzed),
        "missing_files": missing,
        "average_bloat_score": round(overall.get("average_bloat_score", 0), 3),
        "ghost_code_percentage": round(overall.get("ghost_code_percentage", 0), 3),
        "top_bloat_files": [
            {
                "file": Path(item.get("file", "")).name,
                "bloat_score": item.get("bloat_score", 0),
            }
            for item in top_files
        ],
    }


def collect_trend_signal(workspace_root: Path, loops: int) -> Dict[str, Any]:
    archive_dir = workspace_root / "archive"
    analyzer = TrendAnalyzer(str(archive_dir))
    trends = analyzer.analyze_trends(loops_to_analyze=loops)

    if "error" in trends:
        return {"ok": False, "error": trends["error"]}

    productivity = trends.get("productivity_trends", {})
    complexity = trends.get("complexity_trends", {})
    behavioral = trends.get("behavioral_trends", {})

    return {
        "ok": True,
        "analyzed_loops": trends.get("analyzed_loops", 0),
        "completion_trend": productivity.get("completion_trend"),
        "word_count_trend": complexity.get("word_count_trend"),
        "incident_trend": behavioral.get("incident_trend"),
        "insight_count": len(trends.get("insights", [])),
    }


def collect_loop_insight_signal(workspace_root: Path) -> Dict[str, Any]:
    archive_dir = workspace_root / "archive"
    archive_loops: List[int] = []
    for file_path in archive_dir.glob("ARCHIV_*.md"):
        try:
            archive_loops.append(int(file_path.stem.split("_")[1]))
        except Exception:
            continue

    if not archive_loops:
        return {"ok": False, "error": "no archive files found"}

    latest_loop = max(archive_loops)
    extractor = LoopInsightExtractor(str(archive_dir), str(workspace_root / "_transaction_log.jsonl"))
    insights = extractor.extract_insights_for_loop(latest_loop)

    return {
        "ok": True,
        "source_loop": latest_loop,
        "insight_count": len(insights),
        "top_insights": [
            {
                "type": item.get("type"),
                "title": item.get("title"),
                "confidence": item.get("confidence"),
            }
            for item in insights[:3]
        ],
    }


def _parse_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def collect_behavioral_zone_signal(workspace_root: Path) -> Dict[str, Any]:
    tx_log = workspace_root / "_transaction_log.jsonl"
    if not tx_log.exists():
        return {"ok": False, "error": "transaction log missing"}

    entries: List[Dict[str, Any]] = []
    try:
        with tx_log.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    except Exception as error:
        return {"ok": False, "error": f"failed to read transaction log: {error}"}

    if not entries:
        return {"ok": False, "error": "no transaction entries"}

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    recent = []
    for entry in entries[-1000:]:
        ts = _parse_timestamp(str(entry.get("timestamp", "")))
        if ts and ts >= one_hour_ago:
            recent.append(entry)

    ops_last_hour = len(recent)
    successful = sum(1 for item in recent if str(item.get("outcome", "")).upper() == "SUCCESS")
    success_ratio = (successful / ops_last_hour) if ops_last_hour else 0.5
    arousal = min(1.0, ops_last_hour / 120.0)
    functionality = max(0.0, min(1.0, success_ratio))

    mapper = DimensionalMapper()
    mapper.add_behavioral_point(
        arousal=arousal,
        functionality=functionality,
        confidence=0.8,
        metadata={"source": "supervisor_signal_collector", "ops_last_hour": ops_last_hour},
    )
    zone_name, zone = mapper.get_current_zone()
    trend = mapper.analyze_trajectory_trends()

    return {
        "ok": True,
        "zone": zone_name,
        "risk_level": zone.risk_level,
        "ops_last_hour": ops_last_hour,
        "success_ratio_last_hour": round(success_ratio, 3),
        "trend": trend.get("pattern_type", "unknown"),
    }


def collect_breadcrumb_gap_signal(workspace_root: Path) -> Dict[str, Any]:
    try:
        from analysis.breadcrumb_scanner import BreadcrumbScanner
    except Exception:
        return {"ok": False, "error": "breadcrumb scanner unavailable"}

    try:
        scanner = BreadcrumbScanner(workspace_root)
        gaps = scanner.scan_for_gaps()
    except Exception as error:
        return {"ok": False, "error": f"breadcrumb scan failed: {error}"}

    return {
        "ok": True,
        "gap_count": len(gaps),
        "top_gaps": [
            {
                "topic": gap.topic,
                "priority": gap.priority,
                "confidence": gap.confidence,
            }
            for gap in gaps[:3]
        ],
    }


def collect_supervisor_signals(workspace_root: Path, loops: int = 8) -> Dict[str, Any]:
    return {
        "generated_at": utc_now_iso(),
        "workspace": str(workspace_root),
        "signals": {
            "code_bloat": collect_bloat_signal(workspace_root),
            "trend_analysis": collect_trend_signal(workspace_root, loops=loops),
            "loop_insights": collect_loop_insight_signal(workspace_root),
            "behavioral_zone": collect_behavioral_zone_signal(workspace_root),
            "breadcrumb_gaps": collect_breadcrumb_gap_signal(workspace_root),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect supervisor analysis signals.")
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    parser.add_argument(
        "--output",
        default="logs/supervisor_analysis_signals.json",
        help="Output JSON path (relative to workspace if not absolute)",
    )
    parser.add_argument("--loops", type=int, default=8, help="Number of loops for trend analysis")
    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = workspace_root / output_path

    payload = collect_supervisor_signals(workspace_root, loops=max(1, args.loops))
    _write_json(output_path, payload)
    print(f"wrote supervisor analysis signals: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
