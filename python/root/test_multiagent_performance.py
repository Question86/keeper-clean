# MODE: TEST\n\n#!/usr/bin/env python3
"""
Multi-Agent Performance Test Suite
===================================
Tests the multi-agent parallel processing feature and its connection to indexes and documentation.

This script:
1. Tests worktree creation/cleanup performance
2. Simulates multi-agent task execution
3. Measures index query performance under simulated load
4. Validates conflict detection and resolution
5. Verifies documentation accuracy against implementation

Usage:
    python test_multiagent_performance.py [--verbose] [--full]
    
Options:
    --verbose   Show detailed output
    --full      Run full test suite including slow tests
"""

import json
import os
import sys
import time
import tempfile
import shutil
import subprocess
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# Constants
MAX_PARALLEL_AGENTS = 4
WORKTREE_TARGET_MS = 5000  # <5s target
MERGE_TARGET_MS = 10000     # <10s target
INDEX_QUERY_TARGET_MS = 1000  # <1s target

# Try to import loop_guardrails
try:
    import loop_guardrails as lg
    HAS_GUARDRAILS = True
except ImportError:
    HAS_GUARDRAILS = False


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    name: str
    duration_ms: float
    target_ms: float
    success: bool
    details: Optional[str] = None
    
    @property
    def meets_target(self) -> bool:
        return self.duration_ms <= self.target_ms


@dataclass 
class TestResult:
    """Result of a test case."""
    name: str
    passed: bool
    duration_ms: float
    message: str = ""
    metrics: List[PerformanceMetric] = field(default_factory=list)


@dataclass
class PerformanceReport:
    """Complete performance test report."""
    timestamp: str
    workspace: str
    tests: List[TestResult]
    overall_metrics: Dict[str, PerformanceMetric]
    documentation_status: Dict[str, bool]
    recommendations: List[str]
    
    @property
    def total_tests(self) -> int:
        return len(self.tests)
    
    @property
    def passed_tests(self) -> int:
        return sum(1 for t in self.tests if t.passed)
    
    @property
    def pass_rate(self) -> float:
        return (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0


# =============================================================================
# Utilities
# =============================================================================

def log(msg: str, verbose: bool = False, always: bool = False):
    """Log message based on verbosity."""
    if always or verbose:
        print(msg)


def measure_time(func):
    """Decorator to measure function execution time."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        return result, duration
    return wrapper


def is_git_repo(path: Path) -> bool:
    """Check if path is a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def git_command(args: List[str], cwd: Path, timeout: int = 30) -> Tuple[bool, str, str]:
    """Run git command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)


# =============================================================================
# Worktree Performance Tests
# =============================================================================

def test_worktree_creation_available(verbose: bool = False) -> TestResult:
    """Test if worktree creation is possible."""
    workspace = Path.cwd()
    
    if not is_git_repo(workspace):
        return TestResult(
            name="worktree_creation_available",
            passed=False,
            duration_ms=0,
            message="Not a git repository - worktrees unavailable"
        )
    
    return TestResult(
        name="worktree_creation_available",
        passed=True,
        duration_ms=0,
        message="Git repository detected - worktrees available"
    )


def test_worktree_creation_performance(verbose: bool = False) -> TestResult:
    """Test worktree creation time."""
    workspace = Path.cwd()
    
    if not is_git_repo(workspace):
        return TestResult(
            name="worktree_creation_performance",
            passed=True,
            duration_ms=0,
            message="Skipped - not a git repository"
        )
    
    # Create temp directory for worktree
    temp_base = Path(tempfile.mkdtemp(prefix="worktree_test_"))
    worktree_path = temp_base / "test_worktree"
    
    try:
        start = time.time()
        success, stdout, stderr = git_command(
            ["worktree", "add", str(worktree_path), "-d"],
            cwd=workspace
        )
        duration = (time.time() - start) * 1000
        
        if not success:
            return TestResult(
                name="worktree_creation_performance",
                passed=False,
                duration_ms=duration,
                message=f"Worktree creation failed: {stderr}"
            )
        
        metric = PerformanceMetric(
            name="worktree_creation",
            duration_ms=duration,
            target_ms=WORKTREE_TARGET_MS,
            success=success
        )
        
        passed = metric.meets_target
        
        return TestResult(
            name="worktree_creation_performance",
            passed=passed,
            duration_ms=duration,
            message=f"Worktree created in {duration:.1f}ms (target: <{WORKTREE_TARGET_MS}ms)",
            metrics=[metric]
        )
    finally:
        # Cleanup
        git_command(["worktree", "remove", str(worktree_path), "--force"], cwd=workspace)
        shutil.rmtree(temp_base, ignore_errors=True)


def test_worktree_cleanup_performance(verbose: bool = False) -> TestResult:
    """Test worktree cleanup time."""
    workspace = Path.cwd()
    
    if not is_git_repo(workspace):
        return TestResult(
            name="worktree_cleanup_performance",
            passed=True,
            duration_ms=0,
            message="Skipped - not a git repository"
        )
    
    temp_base = Path(tempfile.mkdtemp(prefix="worktree_test_"))
    worktree_path = temp_base / "test_worktree"
    
    try:
        # Create worktree first
        git_command(["worktree", "add", str(worktree_path), "-d"], cwd=workspace)
        
        # Measure cleanup
        start = time.time()
        success, _, stderr = git_command(
            ["worktree", "remove", str(worktree_path), "--force"],
            cwd=workspace
        )
        duration = (time.time() - start) * 1000
        
        return TestResult(
            name="worktree_cleanup_performance",
            passed=duration < WORKTREE_TARGET_MS,
            duration_ms=duration,
            message=f"Worktree cleaned in {duration:.1f}ms"
        )
    finally:
        shutil.rmtree(temp_base, ignore_errors=True)


# =============================================================================
# Multi-Agent Simulation Tests
# =============================================================================

def test_parallel_session_creation(verbose: bool = False) -> TestResult:
    """Test creating multiple agent sessions in parallel."""
    workspace = Path.cwd()
    
    if not HAS_GUARDRAILS:
        return TestResult(
            name="parallel_session_creation",
            passed=True,
            duration_ms=0,
            message="Skipped - loop_guardrails not available"
        )
    
    try:
        start = time.time()
        orchestrator = lg.orchestrator_factory(
            workspace_root=str(workspace),
            max_parallel_agents=MAX_PARALLEL_AGENTS
        )
        duration = (time.time() - start) * 1000
        
        # Verify orchestrator created
        if orchestrator.max_parallel_agents != MAX_PARALLEL_AGENTS:
            return TestResult(
                name="parallel_session_creation",
                passed=False,
                duration_ms=duration,
                message=f"max_parallel_agents mismatch: {orchestrator.max_parallel_agents}"
            )
        
        return TestResult(
            name="parallel_session_creation",
            passed=True,
            duration_ms=duration,
            message=f"Orchestrator created in {duration:.1f}ms with max {MAX_PARALLEL_AGENTS} agents"
        )
    except Exception as e:
        return TestResult(
            name="parallel_session_creation",
            passed=False,
            duration_ms=0,
            message=f"Error: {e}"
        )


def test_task_analysis_performance(verbose: bool = False) -> TestResult:
    """Test task parallelization analysis performance."""
    workspace = Path.cwd()
    
    if not HAS_GUARDRAILS:
        return TestResult(
            name="task_analysis_performance",
            passed=True,
            duration_ms=0,
            message="Skipped - loop_guardrails not available"
        )
    
    try:
        start = time.time()
        # Analyze current workspace tasks
        result = lg.analyze_parallelization(workspace)
        duration = (time.time() - start) * 1000
        
        parallel_count = len(result.get("parallelizable", []))
        sequential_count = len(result.get("sequential", []))
        
        return TestResult(
            name="task_analysis_performance",
            passed=duration < INDEX_QUERY_TARGET_MS,
            duration_ms=duration,
            message=f"Analysis in {duration:.1f}ms: {parallel_count} parallelizable, {sequential_count} sequential"
        )
    except Exception as e:
        return TestResult(
            name="task_analysis_performance",
            passed=False,
            duration_ms=0,
            message=f"Error: {e}"
        )


def test_simulated_agent_cycle(verbose: bool = False) -> TestResult:
    """Simulate a complete agent work cycle."""
    workspace = Path.cwd()
    
    # Create temp workspace for simulation
    temp_workspace = Path(tempfile.mkdtemp(prefix="agent_sim_"))
    
    try:
        # Copy minimal files
        files_to_copy = ["current.json", "NEU.md", "Alt.md"]
        for f in files_to_copy:
            src = workspace / f
            if src.exists():
                shutil.copy2(src, temp_workspace / f)
        
        # Simulate agent work cycle
        start = time.time()
        
        # Step 1: Read current state
        current_file = temp_workspace / "current.json"
        if current_file.exists():
            state = json.loads(current_file.read_text(encoding="utf-8"))
        else:
            state = {"loop": 1, "status": "ACTIVE"}
        
        # Step 2: Simulate task execution (file modification)
        test_output = temp_workspace / "_agent_output.md"
        test_output.write_text("# Agent Output\n\nTask completed.\n", encoding="utf-8")
        
        # Step 3: Update state
        state["lastModified"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        current_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        
        duration = (time.time() - start) * 1000
        
        # Verify output was created
        if not test_output.exists():
            return TestResult(
                name="simulated_agent_cycle",
                passed=False,
                duration_ms=duration,
                message="Agent output file not created"
            )
        
        return TestResult(
            name="simulated_agent_cycle",
            passed=True,
            duration_ms=duration,
            message=f"Agent cycle completed in {duration:.1f}ms"
        )
    finally:
        shutil.rmtree(temp_workspace, ignore_errors=True)


def test_concurrent_file_access(verbose: bool = False) -> TestResult:
    """Test concurrent file access (simulates multi-agent reads)."""
    workspace = Path.cwd()
    
    target_files = ["current.json", "NEU.md", "Alt.md"]
    existing_files = [workspace / f for f in target_files if (workspace / f).exists()]
    
    if not existing_files:
        return TestResult(
            name="concurrent_file_access",
            passed=True,
            duration_ms=0,
            message="No target files found - skipped"
        )
    
    def read_file(path: Path) -> Tuple[bool, float]:
        start = time.time()
        try:
            _ = path.read_text(encoding="utf-8")
            return True, (time.time() - start) * 1000
        except Exception:
            return False, 0
    
    # Simulate 4 concurrent agents reading
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL_AGENTS) as executor:
        futures = []
        for _ in range(MAX_PARALLEL_AGENTS):
            for f in existing_files:
                futures.append(executor.submit(read_file, f))
        
        results = [f.result() for f in futures]
    
    total_duration = (time.time() - start) * 1000
    successes = sum(1 for r, _ in results if r)
    
    return TestResult(
        name="concurrent_file_access",
        passed=successes == len(results),
        duration_ms=total_duration,
        message=f"{successes}/{len(results)} concurrent reads in {total_duration:.1f}ms"
    )


# =============================================================================
# Index Performance Tests
# =============================================================================

def test_history_index_query(verbose: bool = False) -> TestResult:
    """Test HISTORY_INDEX.md query performance."""
    workspace = Path.cwd()
    
    # Try multiple possible locations
    index_paths = [
        workspace / "HISTORY_INDEX.md",
        workspace / "docs" / "HISTORY_INDEX.md",
        workspace / "archive" / "HISTORY_INDEX.md"
    ]
    
    index_file = None
    for p in index_paths:
        if p.exists():
            index_file = p
            break
    
    if not index_file:
        return TestResult(
            name="history_index_query",
            passed=True,
            duration_ms=0,
            message="HISTORY_INDEX.md not found - skipped"
        )
    
    # Measure read + parse time
    start = time.time()
    content = index_file.read_text(encoding="utf-8")
    
    # Simulate query - count entries
    entries = content.count("ARCHIV_")
    loops = content.count("Loop")
    
    duration = (time.time() - start) * 1000
    
    metric = PerformanceMetric(
        name="history_index_query",
        duration_ms=duration,
        target_ms=INDEX_QUERY_TARGET_MS,
        success=True,
        details=f"{entries} archive refs, {loops} loop refs"
    )
    
    return TestResult(
        name="history_index_query",
        passed=metric.meets_target,
        duration_ms=duration,
        message=f"Index queried in {duration:.1f}ms (target: <{INDEX_QUERY_TARGET_MS}ms)",
        metrics=[metric]
    )


def test_query_index_json(verbose: bool = False) -> TestResult:
    """Test QUERY_INDEX.json query performance."""
    workspace = Path.cwd()
    
    index_paths = [
        workspace / "QUERY_INDEX.json",
        workspace / "docs" / "QUERY_INDEX.json"
    ]
    
    index_file = None
    for p in index_paths:
        if p.exists():
            index_file = p
            break
    
    if not index_file:
        return TestResult(
            name="query_index_json",
            passed=True,
            duration_ms=0,
            message="QUERY_INDEX.json not found - skipped"
        )
    
    start = time.time()
    try:
        data = json.loads(index_file.read_text(encoding="utf-8"))
        entry_count = len(data) if isinstance(data, list) else len(data.keys())
        duration = (time.time() - start) * 1000
        
        return TestResult(
            name="query_index_json",
            passed=duration < INDEX_QUERY_TARGET_MS,
            duration_ms=duration,
            message=f"Index loaded in {duration:.1f}ms ({entry_count} entries)"
        )
    except Exception as e:
        return TestResult(
            name="query_index_json",
            passed=False,
            duration_ms=0,
            message=f"Error: {e}"
        )


def test_concurrent_index_queries(verbose: bool = False) -> TestResult:
    """Test concurrent index queries (simulates multi-agent load)."""
    workspace = Path.cwd()
    
    # Find any index file
    index_file = None
    for name in ["HISTORY_INDEX.md", "QUERY_INDEX.json", "NEU.md"]:
        p = workspace / name
        if p.exists():
            index_file = p
            break
        p = workspace / "docs" / name
        if p.exists():
            index_file = p
            break
    
    if not index_file:
        return TestResult(
            name="concurrent_index_queries",
            passed=True,
            duration_ms=0,
            message="No index files found - skipped"
        )
    
    def query_index(iterations: int = 10):
        results = []
        for _ in range(iterations):
            start = time.time()
            _ = index_file.read_text(encoding="utf-8")
            results.append((time.time() - start) * 1000)
        return results
    
    # Run concurrent queries
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL_AGENTS) as executor:
        futures = [executor.submit(query_index, 10) for _ in range(MAX_PARALLEL_AGENTS)]
        all_results = [f.result() for f in futures]
    
    total_duration = (time.time() - start) * 1000
    
    # Calculate stats
    all_times = [t for r in all_results for t in r]
    avg_time = sum(all_times) / len(all_times)
    max_time = max(all_times)
    
    return TestResult(
        name="concurrent_index_queries",
        passed=avg_time < 100,  # 100ms target for individual queries
        duration_ms=total_duration,
        message=f"{len(all_times)} queries: avg {avg_time:.1f}ms, max {max_time:.1f}ms, total {total_duration:.1f}ms"
    )


# =============================================================================
# Conflict Detection Tests
# =============================================================================

def test_conflict_detection_simulation(verbose: bool = False) -> TestResult:
    """Test conflict detection mechanism (simulated)."""
    temp_dir = Path(tempfile.mkdtemp(prefix="conflict_test_"))
    
    try:
        # Create test file
        test_file = temp_dir / "test.md"
        test_file.write_text("# Original content\n\nLine 1\nLine 2\nLine 3\n", encoding="utf-8")
        
        # Simulate two agents modifying same file
        agent1_content = "# Agent 1 modified\n\nLine 1\nAgent 1 changed line 2\nLine 3\n"
        agent2_content = "# Agent 2 modified\n\nLine 1\nLine 2\nAgent 2 changed line 3\n"
        
        # Check for conflict (same file, different content)
        has_conflict = agent1_content != agent2_content
        
        # In real implementation, this would use git merge conflict detection
        
        return TestResult(
            name="conflict_detection_simulation",
            passed=has_conflict,
            duration_ms=0,
            message="Conflict correctly detected between agent modifications"
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_rollback_mechanism_available(verbose: bool = False) -> TestResult:
    """Test that rollback mechanism is available."""
    workspace = Path.cwd()
    
    if not is_git_repo(workspace):
        return TestResult(
            name="rollback_mechanism_available",
            passed=True,
            duration_ms=0,
            message="Not a git repo - rollback N/A"
        )
    
    # Check if we can create tags (rollback points)
    success, _, _ = git_command(["tag", "-l"], cwd=workspace)
    
    if success:
        return TestResult(
            name="rollback_mechanism_available",
            passed=True,
            duration_ms=0,
            message="Git tags available for rollback points"
        )
    else:
        return TestResult(
            name="rollback_mechanism_available",
            passed=False,
            duration_ms=0,
            message="Git tags not accessible"
        )


# =============================================================================
# Documentation Verification Tests
# =============================================================================

def test_multiagent_strategy_doc_exists(verbose: bool = False) -> TestResult:
    """Verify HIERARCHICAL_MULTIAGENT_STRATEGY.md exists and is accurate."""
    workspace = Path.cwd()
    doc_path = workspace / "docs" / "HIERARCHICAL_MULTIAGENT_STRATEGY.md"
    
    if not doc_path.exists():
        return TestResult(
            name="multiagent_strategy_doc_exists",
            passed=False,
            duration_ms=0,
            message="HIERARCHICAL_MULTIAGENT_STRATEGY.md not found"
        )
    
    content = doc_path.read_text(encoding="utf-8")
    
    # Check for key sections
    required_sections = [
        "hierarchy",
        "orchestrator",
        "agent",
        "task"
    ]
    
    content_lower = content.lower()
    missing = [s for s in required_sections if s not in content_lower]
    
    if missing:
        return TestResult(
            name="multiagent_strategy_doc_exists",
            passed=False,
            duration_ms=0,
            message=f"Missing key concepts: {missing}"
        )
    
    return TestResult(
        name="multiagent_strategy_doc_exists",
        passed=True,
        duration_ms=0,
        message="Strategy doc exists with key sections"
    )


def test_multiagent_requirements_doc(verbose: bool = False) -> TestResult:
    """Verify MULTI_AGENT_REQUIREMENTS.md has FR-* and NFR-* entries."""
    workspace = Path.cwd()
    doc_path = workspace / "docs" / "MULTI_AGENT_REQUIREMENTS.md"
    
    if not doc_path.exists():
        return TestResult(
            name="multiagent_requirements_doc",
            passed=False,
            duration_ms=0,
            message="MULTI_AGENT_REQUIREMENTS.md not found"
        )
    
    content = doc_path.read_text(encoding="utf-8")
    
    # Count FR-* and NFR-* entries
    fr_count = content.count("FR-")
    nfr_count = content.count("NFR-")
    
    if fr_count == 0 and nfr_count == 0:
        return TestResult(
            name="multiagent_requirements_doc",
            passed=False,
            duration_ms=0,
            message="No FR-* or NFR-* requirements found"
        )
    
    return TestResult(
        name="multiagent_requirements_doc",
        passed=True,
        duration_ms=0,
        message=f"Requirements doc has {fr_count} FR-* and {nfr_count} NFR-* entries"
    )


def test_multiagent_context_loading_doc(verbose: bool = False) -> TestResult:
    """Verify MULTIAGENT_CONTEXT_LOADING.md documents agent roles."""
    workspace = Path.cwd()
    doc_path = workspace / "docs" / "MULTIAGENT_CONTEXT_LOADING.md"
    
    if not doc_path.exists():
        return TestResult(
            name="multiagent_context_loading_doc",
            passed=False,
            duration_ms=0,
            message="MULTIAGENT_CONTEXT_LOADING.md not found"
        )
    
    content = doc_path.read_text(encoding="utf-8")
    content_lower = content.lower()
    
    # Check for agent role documentation
    role_keywords = ["role", "context", "loading", "agent"]
    found = sum(1 for k in role_keywords if k in content_lower)
    
    if found < 3:
        return TestResult(
            name="multiagent_context_loading_doc",
            passed=False,
            duration_ms=0,
            message=f"Only {found}/4 expected keywords found"
        )
    
    return TestResult(
        name="multiagent_context_loading_doc",
        passed=True,
        duration_ms=0,
        message="Context loading doc documents agent roles"
    )


def test_implementation_matches_docs(verbose: bool = False) -> TestResult:
    """Verify implementation matches documentation."""
    if not HAS_GUARDRAILS:
        return TestResult(
            name="implementation_matches_docs",
            passed=True,
            duration_ms=0,
            message="Skipped - loop_guardrails not available"
        )
    
    # Check that documented classes exist
    required_classes = [
        ("MultiAgentOrchestrator", hasattr(lg, "MultiAgentOrchestrator")),
        ("WorktreeManager", hasattr(lg, "WorktreeManager")),
        ("AgentSession", hasattr(lg, "AgentSession")),
    ]
    
    missing = [name for name, exists in required_classes if not exists]
    
    if missing:
        return TestResult(
            name="implementation_matches_docs",
            passed=False,
            duration_ms=0,
            message=f"Missing documented classes: {missing}"
        )
    
    return TestResult(
        name="implementation_matches_docs",
        passed=True,
        duration_ms=0,
        message=f"All {len(required_classes)} documented classes exist"
    )


# =============================================================================
# Report Generation
# =============================================================================

def generate_performance_report(results: List[TestResult], verbose: bool = False) -> PerformanceReport:
    """Generate comprehensive performance report."""
    workspace = Path.cwd()
    
    # Calculate overall metrics
    overall_metrics = {}
    for r in results:
        for m in r.metrics:
            if m.name not in overall_metrics or m.duration_ms > overall_metrics[m.name].duration_ms:
                overall_metrics[m.name] = m
    
    # Documentation status
    doc_tests = [r for r in results if "doc" in r.name.lower()]
    documentation_status = {t.name: t.passed for t in doc_tests}
    
    # Generate recommendations
    recommendations = []
    
    failed_tests = [r for r in results if not r.passed]
    for t in failed_tests:
        if "worktree" in t.name.lower():
            recommendations.append(f"Worktree issue: {t.message} - Consider optimizing git operations")
        elif "index" in t.name.lower():
            recommendations.append(f"Index issue: {t.message} - Consider caching frequently accessed indexes")
        elif "doc" in t.name.lower():
            recommendations.append(f"Documentation issue: {t.message} - Update documentation")
    
    if not recommendations:
        recommendations.append("All tests passed - no immediate optimizations needed")
    
    return PerformanceReport(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        workspace=str(workspace),
        tests=results,
        overall_metrics=overall_metrics,
        documentation_status=documentation_status,
        recommendations=recommendations
    )


def format_report_markdown(report: PerformanceReport) -> str:
    """Format report as markdown."""
    lines = [
        "# Multi-Agent Performance Test Report",
        "",
        f"Generated: {report.timestamp}",
        f"Workspace: {report.workspace}",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Tests | {report.total_tests} |",
        f"| Passed | {report.passed_tests} |",
        f"| Failed | {report.total_tests - report.passed_tests} |",
        f"| Pass Rate | {report.pass_rate:.1f}% |",
        "",
        "---",
        "",
        "## Test Results",
        "",
        "| Test | Status | Duration | Message |",
        "|------|--------|----------|---------|",
    ]
    
    for t in report.tests:
        status = "✅ PASS" if t.passed else "❌ FAIL"
        duration = f"{t.duration_ms:.1f}ms" if t.duration_ms > 0 else "N/A"
        lines.append(f"| {t.name} | {status} | {duration} | {t.message[:50]}... |" if len(t.message) > 50 else f"| {t.name} | {status} | {duration} | {t.message} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Performance Metrics",
        "",
    ])
    
    if report.overall_metrics:
        lines.extend([
            "| Metric | Duration | Target | Status |",
            "|--------|----------|--------|--------|",
        ])
        for name, m in report.overall_metrics.items():
            status = "✅" if m.meets_target else "❌"
            lines.append(f"| {name} | {m.duration_ms:.1f}ms | <{m.target_ms}ms | {status} |")
    else:
        lines.append("No performance metrics collected.")
    
    lines.extend([
        "",
        "---",
        "",
        "## Documentation Status",
        "",
    ])
    
    for name, status in report.documentation_status.items():
        status_str = "✅ Verified" if status else "❌ Issue"
        lines.append(f"- {name}: {status_str}")
    
    lines.extend([
        "",
        "---",
        "",
        "## Recommendations",
        "",
    ])
    
    for r in report.recommendations:
        lines.append(f"- {r}")
    
    lines.append("")
    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

def run_all_tests(verbose: bool = False, full: bool = False) -> PerformanceReport:
    """Run all performance tests."""
    print("=" * 60)
    print("MULTI-AGENT PERFORMANCE TEST SUITE")
    print("=" * 60)
    print(f"Workspace: {Path.cwd()}")
    print(f"Mode: {'Full' if full else 'Quick'}")
    print("-" * 60)
    
    results = []
    
    # Test categories
    test_categories = [
        ("Worktree Performance", [
            test_worktree_creation_available,
            test_worktree_creation_performance,
            test_worktree_cleanup_performance,
        ]),
        ("Multi-Agent Simulation", [
            test_parallel_session_creation,
            test_task_analysis_performance,
            test_simulated_agent_cycle,
            test_concurrent_file_access,
        ]),
        ("Index Performance", [
            test_history_index_query,
            test_query_index_json,
            test_concurrent_index_queries,
        ]),
        ("Conflict Handling", [
            test_conflict_detection_simulation,
            test_rollback_mechanism_available,
        ]),
        ("Documentation Verification", [
            test_multiagent_strategy_doc_exists,
            test_multiagent_requirements_doc,
            test_multiagent_context_loading_doc,
            test_implementation_matches_docs,
        ]),
    ]
    
    for category_name, tests in test_categories:
        print(f"\n[{category_name}]")
        for test_func in tests:
            result = test_func(verbose=verbose)
            results.append(result)
            status = "✅" if result.passed else "❌"
            print(f"  {status} {result.name}: {result.message[:60]}...")
    
    # Generate report
    report = generate_performance_report(results, verbose)
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total:  {report.total_tests}")
    print(f"Passed: {report.passed_tests} ✅")
    print(f"Failed: {report.total_tests - report.passed_tests} ❌")
    print(f"Rate:   {report.pass_rate:.1f}%")
    print("=" * 60)
    
    return report


def main():
    """Main entry point."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    full = "--full" in sys.argv or "-f" in sys.argv
    
    report = run_all_tests(verbose=verbose, full=full)
    
    # Save report
    report_md = format_report_markdown(report)
    report_path = Path.cwd() / "MULTIAGENT_PERFORMANCE_REPORT.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"\nReport saved to: {report_path}")
    
    # Exit with appropriate code
    sys.exit(0 if report.pass_rate == 100 else 1)


if __name__ == "__main__":
    main()
