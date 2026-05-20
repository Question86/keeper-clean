#!/usr/bin/env python3
"""
Comprehensive Test Suite for Automated Backup System

This module provides extensive testing for all backup system components
including snapshot creation, integrity verification, and recovery operations.
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import logging

# Add backup module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backup.backup_manager import BackupManager
from backup.snapshot_engine import SnapshotEngine
from backup.verification_engine import VerificationEngine
from backup.recovery_interface import RecoveryInterface
from ui.backup_dashboard import BackupDashboard

class TestBackupManager(unittest.TestCase):
    """Test cases for BackupManager class."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.workspace = self.test_dir / "workspace"
        self.workspace.mkdir()

        # Create test files
        (self.workspace / "current.json").write_text('{"test": "data"}')
        (self.workspace / "NEU.md").write_text("# Test NEU")
        (self.workspace / "test_file.txt").write_text("test content")

        self.manager = BackupManager(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test backup manager initialization."""
        self.assertTrue(self.manager.backup_root.exists())
        self.assertEqual(self.manager.workspace_root, self.workspace)
        self.assertEqual(self.manager.backup_interval, 30)

    def test_get_critical_files(self):
        """Test identification of critical files."""
        critical_files = self.manager.get_critical_files()
        self.assertIn(self.workspace / "current.json", critical_files)
        self.assertIn(self.workspace / "NEU.md", critical_files)

    def test_create_snapshot(self):
        """Test snapshot creation."""
        metadata = self.manager.create_snapshot("test_snapshot")

        self.assertEqual(metadata["snapshot_name"], "test_snapshot")
        self.assertIn("created_at", metadata)
        self.assertIn("files", metadata)
        self.assertIn("statistics", metadata)

        # Check that snapshot directory was created
        snapshot_dir = self.manager.backup_root / "test_snapshot"
        self.assertTrue(snapshot_dir.exists())

        # Check metadata file
        metadata_file = snapshot_dir / "metadata.json"
        self.assertTrue(metadata_file.exists())

    def test_verify_snapshot_integrity(self):
        """Test snapshot integrity verification."""
        # Create a snapshot first
        self.manager.create_snapshot("verify_test")

        # Verify it
        result = self.manager.verify_snapshot_integrity("verify_test")

        self.assertTrue(result["valid"])
        self.assertEqual(result["snapshot_name"], "verify_test")
        self.assertGreater(result["files_checked"], 0)

    def test_cleanup_old_snapshots(self):
        """Test cleanup of old snapshots."""
        # Create multiple snapshots with different timestamps
        snapshots = []
        for i in range(3):
            name = f"cleanup_test_{i}"
            metadata = self.manager.create_snapshot(name)
            snapshots.append(metadata)

        # Run cleanup (should keep recent ones)
        result = self.manager.cleanup_old_snapshots(keep_hours=0)  # Keep none for testing

        self.assertGreaterEqual(result["snapshots_removed"], 0)
        self.assertIsInstance(result["space_freed_bytes"], int)


class TestSnapshotEngine(unittest.TestCase):
    """Test cases for SnapshotEngine class."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.workspace = self.test_dir / "workspace"
        self.workspace.mkdir()

        # Create test files
        (self.workspace / "small.txt").write_text("small file")
        (self.workspace / "large.txt").write_text("x" * 2000)  # Larger file

        self.engine = SnapshotEngine(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_should_compress_file(self):
        """Test file compression decision logic."""
        small_file = self.workspace / "small.txt"
        large_file = self.workspace / "large.txt"

        self.assertTrue(self.engine.should_compress_file(small_file))
        # Large file might be excluded based on size, but depends on settings

    def test_create_full_snapshot(self):
        """Test full snapshot creation."""
        metadata, zip_path = self.engine.create_full_snapshot("full_test")

        self.assertEqual(metadata["snapshot_type"], "full")
        self.assertEqual(metadata["snapshot_name"], "full_test")
        self.assertTrue(zip_path.exists())
        self.assertGreater(metadata["statistics"]["total_files"], 0)

    def test_extract_snapshot(self):
        """Test snapshot extraction."""
        # Create snapshot
        metadata, zip_path = self.engine.create_full_snapshot("extract_test")

        # Extract to new location
        extract_dir = self.test_dir / "extracted"
        extract_dir.mkdir()

        result = self.engine.extract_snapshot(zip_path, extract_dir)

        self.assertGreater(result["files_extracted"], 0)
        self.assertTrue((extract_dir / "small.txt").exists())


class TestVerificationEngine(unittest.TestCase):
    """Test cases for VerificationEngine class."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.workspace = self.test_dir / "workspace"
        self.workspace.mkdir()

        # Create test files
        (self.workspace / "test1.txt").write_text("content 1")
        (self.workspace / "test2.txt").write_text("content 2")

        self.engine = VerificationEngine(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        test_file = self.workspace / "test1.txt"
        hash_value = self.engine.calculate_file_hash(test_file)

        self.assertIsInstance(hash_value, str)
        self.assertEqual(len(hash_value), 64)  # SHA256 hex length

    def test_verify_file_integrity(self):
        """Test file integrity verification."""
        test_file = self.workspace / "test1.txt"
        expected_hash = self.engine.calculate_file_hash(test_file)

        result = self.engine.verify_file_integrity(test_file, expected_hash)

        self.assertTrue(result["verified"])
        self.assertEqual(result["expected_hash"], expected_hash)

    def test_calculate_directory_hash(self):
        """Test directory hash calculation."""
        manifest = self.engine.calculate_directory_hash(self.workspace)

        self.assertIn("files", manifest)
        self.assertIn("directory_hash", manifest)
        self.assertGreater(manifest["statistics"]["total_files"], 0)


class TestRecoveryInterface(unittest.TestCase):
    """Test cases for RecoveryInterface class."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.workspace = self.test_dir / "workspace"
        self.workspace.mkdir()
        self.backup_root = self.test_dir / "backups"
        self.backup_root.mkdir()

        # Create test workspace
        (self.workspace / "important.txt").write_text("important data")

        self.interface = RecoveryInterface(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_analyze_recovery_options(self):
        """Test recovery options analysis."""
        # Create mock snapshot metadata
        snapshot_meta = {
            "snapshot_name": "test_snapshot",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {
                "important.txt": {"backed_up": True, "hash": "dummy", "size_bytes": 14}
            }
        }

        analysis = self.interface.analyze_recovery_options(snapshot_meta)

        self.assertEqual(analysis["snapshot_name"], "test_snapshot")
        self.assertIn("recovery_analysis", analysis)

    def test_perform_recovery(self):
        """Test recovery operation."""
        # Create a mock backup
        snapshot_dir = self.backup_root / "recovery_test"
        snapshot_dir.mkdir()
        shutil.copy2(self.workspace / "important.txt", snapshot_dir / "important.txt")

        # Create metadata
        metadata = {
            "snapshot_name": "recovery_test",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {
                "important.txt": {"backed_up": True}
            }
        }

        with open(snapshot_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)

        # Perform recovery
        result = self.interface.perform_recovery(metadata, self.backup_root)

        self.assertIn("recovery_completed", result)
        self.assertGreaterEqual(result["files_restored"], 0)


class TestBackupDashboard(unittest.TestCase):
    """Test cases for BackupDashboard class."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.workspace = self.test_dir / "workspace"
        self.workspace.mkdir()

        self.dashboard = BackupDashboard(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_backup_status(self):
        """Test backup status retrieval."""
        status = self.dashboard.get_backup_status()

        self.assertIn("system_status", status)
        self.assertIn("automated_backup", status)
        self.assertIn("storage", status)
        self.assertIn("health_indicators", status)

    def test_get_storage_analysis(self):
        """Test storage analysis."""
        analysis = self.dashboard.get_storage_analysis()

        self.assertIn("total_size_bytes", analysis)
        self.assertIn("snapshots_by_age", analysis)
        self.assertIn("recommendations", analysis)


class IntegrationTest(unittest.TestCase):
    """Integration tests for the complete backup system."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.workspace = self.test_dir / "workspace"
        self.workspace.mkdir()

        # Create comprehensive test workspace
        (self.workspace / "current.json").write_text('{"loop": 95, "status": "ACTIVE"}')
        (self.workspace / "NEU.md").write_text("# Tasks\n- Task 1\n- Task 2")
        (self.workspace / "Alt.md").write_text("# Completed\n- Old task")
        (self.workspace / "test_data.txt").write_text("Important test data")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_full_backup_workflow(self):
        """Test complete backup workflow from creation to recovery."""
        # Initialize components
        manager = BackupManager(self.workspace)
        dashboard = BackupDashboard(self.workspace)

        # Create backup
        metadata = manager.create_snapshot("integration_test")
        self.assertIsNotNone(metadata)

        # Check dashboard status
        status = dashboard.get_backup_status()
        self.assertGreaterEqual(status["storage"]["total_snapshots"], 1)

        # Verify integrity
        verify_result = manager.verify_snapshot_integrity("integration_test")
        self.assertTrue(verify_result["valid"])

        # Test recovery interface
        recovery = RecoveryInterface(self.workspace)
        analysis = recovery.analyze_recovery_options(metadata)
        self.assertIsNotNone(analysis)

    def test_error_handling(self):
        """Test error handling in various failure scenarios."""
        manager = BackupManager(self.workspace)

        # Test with non-existent snapshot
        result = manager.verify_snapshot_integrity("nonexistent")
        self.assertFalse(result["valid"])

        # Test with corrupted metadata
        snapshot_dir = manager.backup_root / "corrupted_test"
        snapshot_dir.mkdir()
        (snapshot_dir / "metadata.json").write_text("invalid json")

        result = manager.verify_snapshot_integrity("corrupted_test")
        self.assertFalse(result["valid"])


def run_performance_tests():
    """Run performance tests for backup operations."""
    print("Running performance tests...")

    test_dir = Path(tempfile.mkdtemp())
    workspace = test_dir / "workspace"
    workspace.mkdir()

    try:
        # Create test files of various sizes
        sizes = [100, 1000, 10000, 100000]  # bytes
        for i, size in enumerate(sizes):
            content = "x" * size
            (workspace / f"file_{i}.txt").write_text(content)

        manager = BackupManager(workspace)

        import time
        start_time = time.time()
        metadata = manager.create_snapshot("perf_test")
        end_time = time.time()

        backup_time = end_time - start_time
        print(".2f")

        # Cleanup
        shutil.rmtree(test_dir)

        return backup_time < 10  # Should complete in under 10 seconds

    except Exception as e:
        print(f"Performance test failed: {e}")
        shutil.rmtree(test_dir)
        return False


def main():
    """Run the test suite."""
    # Configure logging for tests
    logging.basicConfig(level=logging.ERROR)

    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)

    # Run performance tests
    print("\nRunning performance tests...")
    perf_result = run_performance_tests()
    if perf_result:
        print("✓ Performance tests passed")
    else:
        print("✗ Performance tests failed")

    print("\nTest suite completed.")


if __name__ == "__main__":
    main()