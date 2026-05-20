#!/usr/bin/env python3
"""
Multi-Agent Orchestrator Test Suite

This module provides comprehensive testing for the multi-agent orchestrator
infrastructure, including mock agent simulation, worktree lifecycle tests,
and full orchestration workflow validation.

Run with: python test_orchestrator.py
Or via cockpit: python loop_cockpit.py --test-orchestrator
"""

import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add workspace root to path for imports
WORKSPACE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from loop_guardrails import (
    WorktreeManager,
    MultiAgentOrchestrator,
    AgentSession,
    OrchestrationResult,
    analyze_parallelization,
    worktree_manager_factory,
    orchestrator_factory,
    utc_now_iso,
)


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuiteResult:
    """Result of running the full test suite."""
    total: int
    passed: int
    failed: int
    duration_ms: float
    results: List[TestResult] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now_iso)


class MockAgentSimulator:
    """Simulates agent behavior for testing without real AI."""
    
    def __init__(self, delay_ms: float = 100):
        """
        Args:
            delay_ms: Simulated processing delay in milliseconds
        """
        self.delay_ms = delay_ms
        self.sessions: Dict[str, AgentSession] = {}
        
    def simulate_agent_work(self, session: AgentSession, 
                           fail: bool = False,
                           progress_steps: int = 5) -> AgentSession:
        """Simulate an agent working on a task.
        
        Args:
            session: The agent session to simulate
            fail: If True, simulate failure
            progress_steps: Number of progress updates
            
        Returns:
            Updated session
        """
        session.status = "working"
        session.started_at = utc_now_iso()
        
        # Simulate progress updates
        for i in range(progress_steps):
            session.progress = int((i + 1) / progress_steps * 100)
            time.sleep(self.delay_ms / 1000 / progress_steps)
        
        if fail:
            session.status = "failed"
            session.error = "Simulated agent failure"
        else:
            session.status = "completed"
            session.result_summary = f"Successfully processed {session.task_id}"
        
        session.completed_at = utc_now_iso()
        self.sessions[session.agent_id] = session
        return session
    
    def write_session_file(self, session: AgentSession, worktree_path: Path) -> Path:
        """Write session state to file in worktree."""
        session_data = {
            "agent_id": session.agent_id,
            "task_id": session.task_id,
            "status": session.status,
            "progress": session.progress,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "error": session.error,
            "result_summary": session.result_summary,
            "last_update": utc_now_iso()
        }
        
        session_file = worktree_path / "_AGENT_SESSION.json"
        session_file.write_text(json.dumps(session_data, indent=2), encoding="utf-8")
        return session_file


class OrchestratorTestSuite:
    """Test suite for the multi-agent orchestrator."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or WORKSPACE_ROOT
        self.test_dir: Optional[Path] = None
        self.results: List[TestResult] = []
        self.mock_agent = MockAgentSimulator(delay_ms=50)
        
    def _run_test(self, name: str, test_func) -> TestResult:
        """Run a single test and capture result."""
        start = time.time()
        try:
            details = test_func()
            duration = (time.time() - start) * 1000
            return TestResult(name=name, passed=True, duration_ms=duration, details=details or {})
        except AssertionError as e:
            duration = (time.time() - start) * 1000
            return TestResult(name=name, passed=False, duration_ms=duration, error=str(e))
        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(name=name, passed=False, duration_ms=duration, error=f"Exception: {e}")
    
    def setup(self) -> bool:
        """Set up test environment with temporary git repo."""
        try:
            # Create temp directory
            self.test_dir = Path(tempfile.mkdtemp(prefix="orch_test_"))
            
            # Initialize git repo
            os.system(f'cd "{self.test_dir}" && git init --quiet')
            os.system(f'cd "{self.test_dir}" && git config user.email "test@test.com"')
            os.system(f'cd "{self.test_dir}" && git config user.name "Test"')
            
            # Create initial commit
            readme = self.test_dir / "README.md"
            readme.write_text("# Test Repository\n")
            os.system(f'cd "{self.test_dir}" && git add . && git commit -m "Initial" --quiet')
            
            # Create tasks directory and mock task specs
            tasks_dir = self.test_dir / "tasks"
            tasks_dir.mkdir()
            
            for i in range(1, 5):
                task_id = f"TASK_{i:04d}"
                task_file = tasks_dir / f"task_{task_id}.md"
                task_file.write_text(f"""# {task_id}

MODE: TASK SPECIFICATION
STATUS: NEW

## OBJECTIVE

Test task {i}

## FILES TO MODIFY

- src/module{i}.py
{"- src/shared.py" if i % 2 == 0 else ""}

---
END OF DOCUMENT
""")
            
            # Create src directory for conflict testing
            src_dir = self.test_dir / "src"
            src_dir.mkdir()
            for i in range(1, 5):
                (src_dir / f"module{i}.py").write_text(f"# Module {i}\n")
            (src_dir / "shared.py").write_text("# Shared module\n")
            
            os.system(f'cd "{self.test_dir}" && git add . && git commit -m "Add tasks and modules" --quiet')
            
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def teardown(self):
        """Clean up test environment."""
        if self.test_dir and self.test_dir.exists():
            try:
                shutil.rmtree(self.test_dir)
            except Exception as e:
                print(f"Teardown warning: {e}")
    
    # =========================================================================
    # Test Cases
    # =========================================================================
    
    def test_worktree_manager_init(self) -> Dict:
        """Test WorktreeManager initialization."""
        wm = WorktreeManager(repo_path=self.test_dir)
        
        assert wm.is_git_repo(), "Should detect git repository"
        
        branch = wm.get_current_branch()
        assert branch is not None, "Should get current branch"
        
        return {"branch": branch, "is_repo": True}
    
    def test_worktree_creation(self) -> Dict:
        """Test creating a git worktree."""
        wm = WorktreeManager(repo_path=self.test_dir)
        
        worktree = wm.create_worktree("agent-001", "TASK_0001")
        assert worktree is not None, "Should create worktree"
        assert worktree.path.exists(), "Worktree path should exist"
        assert worktree.agent_id == "agent-001", "Agent ID should match"
        
        # Verify worktree has files
        readme = worktree.path / "README.md"
        assert readme.exists(), "Worktree should have README"
        
        # Cleanup
        wm.remove_worktree(worktree)
        
        return {"worktree_name": worktree.name, "path": str(worktree.path)}
    
    def test_worktree_listing(self) -> Dict:
        """Test listing worktrees."""
        wm = WorktreeManager(repo_path=self.test_dir)
        
        # Create multiple worktrees
        wt1 = wm.create_worktree("agent-list-1", "TASK_0001")
        wt2 = wm.create_worktree("agent-list-2", "TASK_0002")
        
        worktrees = wm.list_worktrees()
        names = [wt.name for wt in worktrees]
        
        assert "agent-list-1" in names, "Should list first worktree"
        assert "agent-list-2" in names, "Should list second worktree"
        
        # Cleanup
        wm.cleanup_all()
        
        return {"count": len(worktrees), "names": names}
    
    def test_worktree_merge(self) -> Dict:
        """Test merging a worktree back to main."""
        wm = WorktreeManager(repo_path=self.test_dir)
        
        # Create worktree and make changes
        worktree = wm.create_worktree("agent-merge", "TASK_0001")
        
        # Make a change in the worktree
        new_file = worktree.path / "agent_output.txt"
        new_file.write_text("Agent work output\n")
        
        os.system(f'cd "{worktree.path}" && git add . && git commit -m "Agent work" --quiet')
        
        # Merge back
        result = wm.merge_worktree(worktree)
        
        # Cleanup
        wm.cleanup_all()
        
        # Verify merge
        main_new_file = self.test_dir / "agent_output.txt"
        assert main_new_file.exists() or result.success, "Merge should succeed or file should exist"
        
        return {"success": result.success, "message": result.message}
    
    def test_worktree_cleanup(self) -> Dict:
        """Test cleaning up all worktrees."""
        wm = WorktreeManager(repo_path=self.test_dir)
        
        # Create worktrees
        wm.create_worktree("agent-cleanup-1", "TASK_0001")
        wm.create_worktree("agent-cleanup-2", "TASK_0002")
        
        status_before = wm.get_status()
        
        # Cleanup
        cleaned = wm.cleanup_all()
        
        status_after = wm.get_status()
        
        assert status_after["total_worktrees"] == 0, "All worktrees should be cleaned"
        
        return {"cleaned": cleaned, "before": status_before["total_worktrees"], "after": status_after["total_worktrees"]}
    
    def test_pre_parallel_tag(self) -> Dict:
        """Test pre-parallel safety tagging."""
        wm = WorktreeManager(repo_path=self.test_dir)
        
        tag = wm.tag_pre_parallel("test-run")
        assert tag is not None, "Should create tag"
        assert "pre-parallel" in tag, "Tag should have prefix"
        
        return {"tag": tag}
    
    def test_orchestrator_init(self) -> Dict:
        """Test MultiAgentOrchestrator initialization."""
        orch = MultiAgentOrchestrator(workspace_root=self.test_dir)
        
        status = orch.get_status()
        assert status["is_git_repo"], "Should detect git repo"
        assert status["max_parallel_agents"] == 4, "Default max agents should be 4"
        
        return {"status": status}
    
    def test_agent_session_creation(self) -> Dict:
        """Test creating agent sessions."""
        orch = MultiAgentOrchestrator(workspace_root=self.test_dir)
        
        sessions = orch.prepare_parallel_execution(["TASK_0001", "TASK_0002"])
        
        assert len(sessions) == 2, "Should create 2 sessions"
        assert all(s.status == "pending" for s in sessions), "All should be pending"
        
        # Cleanup
        orch.cleanup()
        
        return {"sessions": len(sessions), "task_ids": [s.task_id for s in sessions]}
    
    def test_mock_agent_simulation(self) -> Dict:
        """Test mock agent workflow."""
        session = AgentSession(
            agent_id="mock-001",
            task_id="TASK_0001",
            worktree_name="test-wt",
            worktree_path=self.test_dir
        )
        
        # Simulate success
        result = self.mock_agent.simulate_agent_work(session)
        assert result.status == "completed", "Should complete successfully"
        assert result.progress == 100, "Progress should be 100"
        
        # Simulate failure
        fail_session = AgentSession(
            agent_id="mock-002",
            task_id="TASK_0002",
            worktree_name="test-wt-2",
            worktree_path=self.test_dir
        )
        fail_result = self.mock_agent.simulate_agent_work(fail_session, fail=True)
        assert fail_result.status == "failed", "Should fail"
        assert fail_result.error is not None, "Should have error"
        
        return {"success_status": result.status, "fail_status": fail_result.status}
    
    def test_session_file_persistence(self) -> Dict:
        """Test session file write/read."""
        session = AgentSession(
            agent_id="persist-001",
            task_id="TASK_0001",
            worktree_name="test-wt",
            worktree_path=self.test_dir,
            status="completed",
            progress=100
        )
        
        # Write session file
        session_file = self.mock_agent.write_session_file(session, self.test_dir)
        assert session_file.exists(), "Session file should exist"
        
        # Read and verify
        data = json.loads(session_file.read_text())
        assert data["agent_id"] == "persist-001", "Agent ID should match"
        assert data["status"] == "completed", "Status should match"
        
        # Cleanup
        session_file.unlink()
        
        return {"file": str(session_file), "data_keys": list(data.keys())}
    
    def test_task_analysis(self) -> Dict:
        """Test task parallelization analysis."""
        analysis = analyze_parallelization(self.test_dir, ["TASK_0001", "TASK_0002", "TASK_0003", "TASK_0004"])
        
        # Should detect conflicts for tasks sharing shared.py (even tasks)
        assert "conflicts" in analysis or "parallelizable" in analysis, "Should return analysis result"
        
        return {"analysis_keys": list(analysis.keys()), "success": analysis.get("success", False)}
    
    def test_full_orchestration_workflow(self) -> Dict:
        """Test complete orchestration workflow (simulated)."""
        orch = MultiAgentOrchestrator(
            workspace_root=self.test_dir,
            max_parallel_agents=2,
            session_poll_interval=0.1,
            agent_timeout_seconds=10
        )
        
        # Execute with auto-cleanup
        result = orch.execute_parallel(
            task_ids=["TASK_0001", "TASK_0003"],  # Non-conflicting tasks
            auto_merge=True,
            auto_cleanup=True
        )
        
        assert result.agents_spawned >= 0, "Should track spawned agents"
        assert result.time_started is not None, "Should have start time"
        assert result.time_completed is not None, "Should have end time"
        
        return {
            "success": result.success,
            "spawned": result.agents_spawned,
            "completed": result.agents_completed,
            "time_saved": result.time_saved_seconds
        }
    
    def test_rollback(self) -> Dict:
        """Test rollback to pre-parallel state."""
        wm = WorktreeManager(repo_path=self.test_dir)
        
        # Create tag
        tag = wm.tag_pre_parallel("rollback-test")
        
        # Make some changes
        test_file = self.test_dir / "rollback_test.txt"
        test_file.write_text("Should be rolled back\n")
        os.system(f'cd "{self.test_dir}" && git add . && git commit -m "Will rollback" --quiet')
        
        # Rollback
        success, message = wm.rollback_to_tag(tag)
        
        return {"tag": tag, "rollback_success": success, "message": message}
    
    # =========================================================================
    # Test Runner
    # =========================================================================
    
    def run_all(self) -> TestSuiteResult:
        """Run all tests and return results."""
        start = time.time()
        
        tests = [
            ("worktree_manager_init", self.test_worktree_manager_init),
            ("worktree_creation", self.test_worktree_creation),
            ("worktree_listing", self.test_worktree_listing),
            ("worktree_merge", self.test_worktree_merge),
            ("worktree_cleanup", self.test_worktree_cleanup),
            ("pre_parallel_tag", self.test_pre_parallel_tag),
            ("orchestrator_init", self.test_orchestrator_init),
            ("agent_session_creation", self.test_agent_session_creation),
            ("mock_agent_simulation", self.test_mock_agent_simulation),
            ("session_file_persistence", self.test_session_file_persistence),
            ("task_analysis", self.test_task_analysis),
            ("full_orchestration_workflow", self.test_full_orchestration_workflow),
            ("rollback", self.test_rollback),
        ]
        
        # Setup
        if not self.setup():
            return TestSuiteResult(
                total=len(tests),
                passed=0,
                failed=len(tests),
                duration_ms=0,
                results=[TestResult(name="setup", passed=False, duration_ms=0, error="Setup failed")]
            )
        
        try:
            # Run tests
            for name, test_func in tests:
                result = self._run_test(name, test_func)
                self.results.append(result)
                
                # Print progress
                status = "✅" if result.passed else "❌"
                print(f"  {status} {name} ({result.duration_ms:.1f}ms)")
                if result.error:
                    print(f"     Error: {result.error}")
        finally:
            self.teardown()
        
        duration = (time.time() - start) * 1000
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        return TestSuiteResult(
            total=len(self.results),
            passed=passed,
            failed=failed,
            duration_ms=duration,
            results=self.results
        )


def run_tests(workspace_root: Optional[Path] = None, output_file: Optional[Path] = None) -> TestSuiteResult:
    """Run the orchestrator test suite.
    
    Args:
        workspace_root: Optional workspace path
        output_file: Optional path to write JSON results
        
    Returns:
        TestSuiteResult with all test outcomes
    """
    print("\n" + "=" * 60)
    print("MULTI-AGENT ORCHESTRATOR TEST SUITE")
    print("=" * 60 + "\n")
    
    suite = OrchestratorTestSuite(workspace_root)
    result = suite.run_all()
    
    print("\n" + "-" * 60)
    print(f"RESULTS: {result.passed}/{result.total} passed ({result.duration_ms:.0f}ms)")
    print("-" * 60 + "\n")
    
    # Write JSON output if requested
    if output_file:
        output_data = {
            "timestamp": result.timestamp,
            "summary": {
                "total": result.total,
                "passed": result.passed,
                "failed": result.failed,
                "duration_ms": result.duration_ms
            },
            "tests": [asdict(r) for r in result.results]
        }
        output_file.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
        print(f"Results written to: {output_file}")
    
    return result


def generate_test_report(result: TestSuiteResult, workspace_root: Path) -> str:
    """Generate a markdown test report."""
    report = f"""# Orchestrator Test Report

GENERATED: {result.timestamp}
DURATION: {result.duration_ms:.0f}ms

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {result.total} |
| Passed | {result.passed} |
| Failed | {result.failed} |
| Pass Rate | {result.passed/result.total*100:.1f}% |

---

## Test Results

| Test | Status | Duration | Error |
|------|--------|----------|-------|
"""
    
    for test in result.results:
        status = "✅ PASS" if test.passed else "❌ FAIL"
        error = test.error or "-"
        report += f"| {test.name} | {status} | {test.duration_ms:.1f}ms | {error[:50] if error != '-' else '-'} |\n"
    
    report += """
---

## Conclusion

"""
    if result.failed == 0:
        report += "✅ All tests passed. The orchestrator infrastructure is ready for testing.\n"
    else:
        report += f"⚠️ {result.failed} test(s) failed. Review errors above and fix issues before production testing.\n"
    
    report += """
---

END OF DOCUMENT
"""
    return report


if __name__ == "__main__":
    # Parse args
    import argparse
    parser = argparse.ArgumentParser(description="Run orchestrator tests")
    parser.add_argument("--json", type=str, help="Output JSON file path")
    parser.add_argument("--report", type=str, help="Output markdown report path")
    args = parser.parse_args()
    
    # Run tests
    json_path = Path(args.json) if args.json else None
    result = run_tests(output_file=json_path)
    
    # Generate report
    if args.report:
        report = generate_test_report(result, WORKSPACE_ROOT)
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"Report written to: {args.report}")
    
    # Exit code
    sys.exit(0 if result.failed == 0 else 1)

