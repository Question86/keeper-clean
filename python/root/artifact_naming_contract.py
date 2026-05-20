from pathlib import Path
from typing import Dict, List, Optional, Tuple


CANONICAL_BOOTSTRAP = "_BOOTSTRAP.md"
BOOTSTRAP_ALIASES = ["bootstrap.md"]

CANONICAL_LITTLEBOOT = "Littleboot.md"
LITTLEBOOT_ALIASES = ["littleboot.md", "reports/Littleboot.md"]

CANONICAL_FINALIZATION_REPORT_TEMPLATE = "reports/report_LOOP_{loop}_FINALIZATION_v{version:02d}.md"
FINALIZATION_REPORT_ALIAS_TEMPLATES = [
    "report_LOOP_{loop}_FINALIZATION_v{version:02d}.md",
    "report_LOOP_{loop}_FINALIZATION_L{loop}_v{version:02d}.md",
    "reports/report_LOOP_{loop}_FINALIZATION_L{loop}_v{version:02d}.md",
]

CANONICAL_APPROVAL_TEMPLATE = "approvals/FINALIZE_APPROVAL_L{loop}.json"
APPROVAL_ALIAS_TEMPLATES = [
    "approvals/finalize_approval_L{loop}.json",
]

CANONICAL_BUG_PATTERN = "bugs/BUG_XXXX_LYYY.md"
CANONICAL_CODE_PATTERN = "code/CODE_XXXX_LYYY.md"


def canonical_bootstrap_path(workspace_root: Path) -> Path:
    return workspace_root / CANONICAL_BOOTSTRAP


def bootstrap_candidates(workspace_root: Path) -> List[Path]:
    return [workspace_root / CANONICAL_BOOTSTRAP] + [workspace_root / alias for alias in BOOTSTRAP_ALIASES]


def resolve_bootstrap_path(workspace_root: Path) -> Optional[Path]:
    for candidate in bootstrap_candidates(workspace_root):
        if candidate.exists():
            return candidate
    return None


def canonical_littleboot_path(workspace_root: Path) -> Path:
    return workspace_root / CANONICAL_LITTLEBOOT


def littleboot_candidates(workspace_root: Path) -> List[Path]:
    return [workspace_root / CANONICAL_LITTLEBOOT] + [workspace_root / alias for alias in LITTLEBOOT_ALIASES]


def resolve_littleboot_path(workspace_root: Path) -> Optional[Path]:
    for candidate in littleboot_candidates(workspace_root):
        if candidate.exists():
            return candidate
    return None


def canonical_finalization_report_path(workspace_root: Path, loop_num: int, version: int = 1) -> Path:
    rel = CANONICAL_FINALIZATION_REPORT_TEMPLATE.format(loop=int(loop_num), version=int(version))
    return workspace_root / rel


def finalization_report_candidates(workspace_root: Path, loop_num: int, version: int = 1) -> List[Path]:
    canonical = canonical_finalization_report_path(workspace_root, loop_num, version)
    aliases = [
        workspace_root / template.format(loop=int(loop_num), version=int(version))
        for template in FINALIZATION_REPORT_ALIAS_TEMPLATES
    ]
    return [canonical] + aliases


def find_finalization_reports(workspace_root: Path, loop_num: int) -> List[Path]:
    loop = int(loop_num)
    reports_dir = workspace_root / "reports"
    patterns = [
        f"report_LOOP_{loop}_FINALIZATION_v*.md",
        f"report_LOOP_{loop}_FINALIZATION_L{loop}_v*.md",
    ]
    matches: List[Path] = []
    for pattern in patterns:
        matches.extend(workspace_root.glob(pattern))
        if reports_dir.exists():
            matches.extend(reports_dir.glob(pattern))
    dedup: Dict[str, Path] = {}
    for path in matches:
        dedup[str(path.resolve())] = path
    return list(dedup.values())


def canonical_approval_path(workspace_root: Path, loop_num: int) -> Path:
    rel = CANONICAL_APPROVAL_TEMPLATE.format(loop=int(loop_num))
    return workspace_root / rel


def approval_candidates(workspace_root: Path, loop_num: int) -> List[Path]:
    canonical = canonical_approval_path(workspace_root, loop_num)
    aliases = [
        workspace_root / template.format(loop=int(loop_num))
        for template in APPROVAL_ALIAS_TEMPLATES
    ]
    return [canonical] + aliases


def normalize_legacy_artifacts(workspace_root: Path, apply_changes: bool = False) -> Dict[str, List[Tuple[str, str]]]:
    actions: List[Tuple[str, str]] = []
    skipped: List[Tuple[str, str]] = []

    def _plan_move(src: Path, dst: Path) -> None:
        if not src.exists():
            return
        if src.resolve() == dst.resolve():
            return
        if dst.exists():
            skipped.append((str(src), f"target exists: {dst}"))
            return
        actions.append((str(src), str(dst)))
        if apply_changes:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.replace(dst)

    _plan_move(workspace_root / "bootstrap.md", workspace_root / CANONICAL_BOOTSTRAP)
    _plan_move(workspace_root / "littleboot.md", workspace_root / CANONICAL_LITTLEBOOT)
    _plan_move(workspace_root / "reports" / "Littleboot.md", workspace_root / CANONICAL_LITTLEBOOT)

    reports_dir = workspace_root / "reports"
    if reports_dir.exists():
        for legacy in reports_dir.glob("report_LOOP_*_FINALIZATION_L*_v*.md"):
            # Convert report_LOOP_140_FINALIZATION_L140_v01.md -> report_LOOP_140_FINALIZATION_v01.md
            name = legacy.name.replace("_FINALIZATION_L", "_FINALIZATION_")
            parts = name.split("_FINALIZATION_")
            if len(parts) != 2:
                skipped.append((str(legacy), "unexpected finalization report format"))
                continue
            # Remove the duplicated loop token that comes before _vNN
            tail = parts[1]
            if "_v" not in tail:
                skipped.append((str(legacy), "missing version token"))
                continue
            loop_dup, version_part = tail.split("_v", 1)
            if not loop_dup.isdigit():
                skipped.append((str(legacy), "unexpected duplicated loop token"))
                continue
            dst_name = f"{parts[0]}_FINALIZATION_v{version_part}"
            _plan_move(legacy, reports_dir / dst_name)

    return {"actions": actions, "skipped": skipped}
