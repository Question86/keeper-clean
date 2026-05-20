#!/usr/bin/env python3
"""
Unit Tests for Isolated Database Performance Benchmark

Tests the isolated_db_benchmark.py functionality to ensure correct
measurement operations and error handling.
"""

import unittest
import tempfile
import sqlite3
import json
import subprocess
import sys
from pathlib import Path


class TestIsolatedDatabaseBenchmark(unittest.TestCase):
    """Test cases for isolated database benchmarking"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Create test database with sample data
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        ''')
        # Insert sample data
        for i in range(100):
            conn.execute('INSERT INTO test_table (name, value) VALUES (?, ?)',
                        (f'test_{i}', i * 10))
        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up temporary database"""
        Path(self.db_path).unlink(missing_ok=True)

    def run_subprocess_benchmark(self, operation: str, iterations: int = 10) -> dict:
        """Helper to run benchmark in subprocess and parse result"""
        cmd = [
            sys.executable, 'isolated_db_benchmark.py',
            '--db', self.db_path,
            '--operation', operation,
            '--iterations', str(iterations)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Subprocess failed: {result.stderr}")

        return json.loads(result.stdout)

    def test_connection_overhead_measurement(self):
        """Test connection overhead measurement"""
        result = self.run_subprocess_benchmark('connection_overhead', 5)

        self.assertIn('operation', result)
        self.assertEqual(result['operation'], 'connection_overhead')
        self.assertIn('avg_time', result)
        self.assertIn('iterations', result)
        self.assertEqual(result['iterations'], 5)
        self.assertGreater(result['avg_time'], 0)

    def test_invalid_operation(self):
        """Test error handling for invalid operation"""
        cmd = [
            sys.executable, 'isolated_db_benchmark.py',
            '--db', self.db_path,
            '--operation', 'invalid_op'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)

        error_result = json.loads(result.stdout)
        self.assertIn('error', error_result)

    def test_nonexistent_database(self):
        """Test error handling for nonexistent database"""
        cmd = [
            sys.executable, 'isolated_db_benchmark.py',
            '--db', '/nonexistent/path.db',
            '--operation', 'connection_overhead'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)

        error_result = json.loads(result.stdout)
        self.assertIn('error', error_result)

    # TODO: Add tests for query_performance and write_performance
    # once those methods are implemented


if __name__ == '__main__':
    unittest.main()</content>
<parameter name="filePath">d:\Keeper-Clean-Loop1\tests\test_isolated_db_benchmark.py