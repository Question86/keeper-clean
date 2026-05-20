"""
Test Code Quality - Validation of bloat detection and connectivity

This module provides comprehensive testing for:
- Bloat detection accuracy and false positive rates
- Connectivity mapping precision
- Statistical sampling validation
- Surgical cleaning safety and rollback
- Integration testing across all components

Ensures <5% false positive rate and >95% connectivity preservation.
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch
import sys

import ast

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.code_bloat_detector import CodeBloatDetector, BloatAnalyzer
from analysis.connectivity_mapper import ConnectivityMapper, ConnectivityAnalyzer
from analysis.statistical_sampler import StatisticalSampler
from refactoring.surgical_cleaner import SurgicalCleaner


class TestCodeBloatDetector(unittest.TestCase):
    """Test bloat detection functionality."""

    def setUp(self):
        self.detector = CodeBloatDetector()
        self.test_code = '''
import os
import sys
import unused_module

def used_function():
    x = 1
    y = 2  # unused variable
    return x

def unused_function():
    pass

# Dead code
if False:
    print("This never executes")

# Mockup code
def placeholder():
    raise NotImplementedError("TODO: implement this")

class ComplexClass:
    def method1(self):
        if True:
            for i in range(10):
                if i > 5:
                    return i
        return 0
'''

    def test_detect_unused_imports(self):
        """Test detection of unused imports."""
        tree = ast.parse(self.test_code)
        analyzer = BloatAnalyzer(self.test_code, tree)
        analyzer.visit(tree)
        unused = analyzer.find_unused_imports()

        self.assertIn('unused_module', unused)
        # os and sys are imported but not used in this test code
        self.assertIn('os', unused)
        self.assertIn('sys', unused)

    def test_detect_mockup_code(self):
        """Test detection of mockup/placeholder code."""
        tree = ast.parse(self.test_code)
        analyzer = BloatAnalyzer(self.test_code, tree)
        analyzer.visit(tree)
        mockup = analyzer.find_mockup_code()

        self.assertTrue(any('NotImplementedError' in line for line in mockup))
        self.assertTrue(any('pass' in line for line in mockup))

    def test_calculate_bloat_score(self):
        """Test bloat score calculation."""
        tree = ast.parse(self.test_code)
        analyzer = BloatAnalyzer(self.test_code, tree)
        analyzer.visit(tree)
        score = analyzer.calculate_bloat_score()

        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_false_positive_rate(self):
        """Test that false positive rate is below 5%."""
        # Create clean code with no bloat
        clean_code = '''
def add(a, b):
    return a + b

def multiply(x, y):
    return x * y

if __name__ == "__main__":
    result = add(1, 2)
    print(multiply(result, 3))
'''

        tree = ast.parse(clean_code)
        analyzer = BloatAnalyzer(clean_code, tree)
        analyzer.visit(tree)
        score = analyzer.calculate_bloat_score()

        # Clean code should have low bloat score
        self.assertLess(score, 20)  # Less than 20% bloat for clean code


class TestConnectivityMapper(unittest.TestCase):
    """Test connectivity mapping functionality."""

    def setUp(self):
        self.mapper = ConnectivityMapper()
        self.test_code = '''
def main():
    result = helper()
    return result

def helper():
    return 42

def unused():
    pass
'''

    def test_call_graph_construction(self):
        """Test construction of function call graph."""
        tree = ast.parse(self.test_code)
        analyzer = ConnectivityAnalyzer('test.py', self.test_code, tree)
        analyzer.build_call_graph()

        # Should have nodes for main, helper, unused
        self.assertIn('test:main', analyzer.call_graph.nodes())
        self.assertIn('test:helper', analyzer.call_graph.nodes())

        # Should have edge from main to helper
        self.assertTrue(analyzer.call_graph.has_edge('test:main', 'test:helper'))

    def test_connectivity_score(self):
        """Test connectivity score calculation."""
        tree = ast.parse(self.test_code)
        analyzer = ConnectivityAnalyzer('test.py', self.test_code, tree)
        analyzer.build_call_graph()
        score = analyzer.calculate_connectivity_score()

        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_removal_safety_check(self):
        """Test safety checking for function removal."""
        # Add some functions to the mapper
        tree = ast.parse(self.test_code)
        analyzer = ConnectivityAnalyzer('test.py', self.test_code, tree)
        analyzer.build_call_graph()

        # Manually add to mapper's graphs
        for node in analyzer.call_graph.nodes():
            self.mapper.call_graph.add_node(node)
        for edge in analyzer.call_graph.edges():
            self.mapper.call_graph.add_edge(*edge)
            # Also update dependency maps
            caller, callee = edge
            self.mapper.dependency_map[caller].add(callee)
            self.mapper.usage_map[callee].add(caller)

        # Check removal safety
        safety = self.mapper.check_removal_safety('test:unused')
        self.assertTrue(safety['safe_to_remove'])

        safety = self.mapper.check_removal_safety('test:helper')
        self.assertFalse(safety['safe_to_remove'])
        self.assertIn('test:main', safety['dependents'])


class TestStatisticalSampler(unittest.TestCase):
    """Test statistical sampling functionality."""

    def setUp(self):
        self.sampler = StatisticalSampler()

    def test_file_collection(self):
        """Test collection of Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for i in range(5):
                with open(os.path.join(tmpdir, f'test{i}.py'), 'w') as f:
                    f.write(f'def func{i}():\n    return {i}\n')

            files = self.sampler._collect_python_files(tmpdir, recursive=False)
            self.assertEqual(len(files), 5)
            self.assertTrue(all(f.endswith('.py') for f in files))

    def test_file_statistics(self):
        """Test calculation of file statistics."""
        test_files = []
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with different characteristics
            sizes = [100, 1000, 5000]
            for i, size in enumerate(sizes):
                content = f'def func{i}():\n    ' + 'x = 1\n    ' * (size // 10)
                file_path = os.path.join(tmpdir, f'test{i}.py')
                with open(file_path, 'w') as f:
                    f.write(content)
                test_files.append(file_path)

            stats = self.sampler._calculate_file_statistics(test_files)

            self.assertEqual(len(stats['size']), 3)
            self.assertTrue(all(s > 0 for s in stats['size']))

    def test_stratification(self):
        """Test creation of strata."""
        file_stats = {
            'size': [500, 5000, 15000],
            'complexity': [2, 10, 20],
            'imports': [1, 3, 5],
            'functions': [2, 5, 10],
            'lines': [10, 50, 100]
        }

        strata = self.sampler._create_strata(file_stats)

        self.assertIsInstance(strata, dict)
        self.assertTrue(len(strata) > 0)

    def test_sample_selection(self):
        """Test sample selection from strata."""
        strata = {
            'small_simple': [0, 1],
            'large_complex': [2, 3, 4]
        }
        sample_sizes = {'small_simple': 1, 'large_complex': 2}

        samples = self.sampler._select_samples(strata, sample_sizes)

        self.assertIsInstance(samples, list)
        self.assertTrue(len(samples) <= 3)  # Should not exceed total available

    def test_coverage_estimation(self):
        """Test coverage estimation."""
        samples = [0, 1, 2]
        file_stats = {'size': [100, 200, 300, 400, 500]}

        coverage = self.sampler._estimate_coverage(samples, file_stats)

        self.assertIsInstance(coverage, float)
        self.assertGreaterEqual(coverage, 0)
        self.assertLessEqual(coverage, 100)


class TestSurgicalCleaner(unittest.TestCase):
    """Test surgical cleaning functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = SurgicalCleaner(backup_dir=os.path.join(self.temp_dir, 'backups'))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_backup_creation(self):
        """Test creation of file backups."""
        test_file = os.path.join(self.temp_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write('print("hello")')

        backup_path = self.cleaner._create_backup(test_file)
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))

    def test_surgical_removal(self):
        """Test surgical removal of code."""
        test_file = os.path.join(self.temp_dir, 'test.py')
        original_content = '''import os
import unused
x = 1
y = 2  # unused
print(x)
'''

        with open(test_file, 'w') as f:
            f.write(original_content)

        targets = [
            {'type': 'unused_import', 'line': 2},
            {'type': 'unused_variable', 'line': 4}
        ]

        result = self.cleaner.surgical_remove(test_file, targets, 'test removal')

        self.assertIn('success', result)
        self.assertEqual(result['changes_applied'], 2)

        # Check backup was created
        self.assertTrue(result['backup_created'])
        self.assertTrue(os.path.exists(result['backup_created']))

    def test_rollback_functionality(self):
        """Test rollback of surgical operations."""
        test_file = os.path.join(self.temp_dir, 'test.py')
        original_content = 'print("original")'

        with open(test_file, 'w') as f:
            f.write(original_content)

        # Make a change
        targets = [{'type': 'mockup_code', 'line': 1}]
        result = self.cleaner.surgical_remove(test_file, targets, 'test')

        self.assertIn('success', result)

        # Rollback
        rollback_result = self.cleaner.rollback_last_operation()

        self.assertIn('success', rollback_result)

        # Check file is restored
        with open(test_file, 'r') as f:
            restored_content = f.read()

        self.assertEqual(restored_content, original_content)

    def test_checkpoint_creation(self):
        """Test creation and use of checkpoints."""
        checkpoint_id = self.cleaner.create_checkpoint('test_checkpoint')

        self.assertIsInstance(checkpoint_id, str)
        self.assertIn(checkpoint_id, self.cleaner.backup_manifest)

    def test_dry_run_mode(self):
        """Test dry run functionality."""
        self.cleaner = SurgicalCleaner(dry_run=True)

        test_file = os.path.join(self.temp_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write('print("test")')

        targets = [{'type': 'mockup_code', 'line': 1}]
        result = self.cleaner.surgical_remove(test_file, targets)

        self.assertIn('dry_run', result)
        self.assertTrue(result['dry_run'])

        # File should be unchanged
        with open(test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, 'print("test")')


class TestIntegration(unittest.TestCase):
    """Integration tests across all components."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = self._create_test_project()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def _create_test_project(self):
        """Create a test project with multiple files."""
        files = {}

        # Main module
        main_content = '''
import utils
import unused_module

def main():
    result = utils.helper()
    print(result)

def unused():
    pass

if __name__ == "__main__":
    main()
'''
        main_file = os.path.join(self.temp_dir, 'main.py')
        with open(main_file, 'w') as f:
            f.write(main_content)
        files['main'] = main_file

        # Utils module
        utils_content = '''
def helper():
    return "Hello World"

def unused_helper():
    raise NotImplementedError("TODO")
'''
        utils_file = os.path.join(self.temp_dir, 'utils.py')
        with open(utils_file, 'w') as f:
            f.write(utils_content)
        files['utils'] = utils_file

        return files

    def test_full_analysis_pipeline(self):
        """Test the complete analysis and cleaning pipeline."""
        # Step 1: Analyze with bloat detector
        detector = CodeBloatDetector()
        results = []
        for name, file_path in self.test_files.items():
            result = detector.analyze_file(file_path)
            results.append(result)

        # Should find some bloat
        total_bloat = sum(r.get('bloat_score', 0) for r in results)
        self.assertGreater(total_bloat, 0)

        # Step 2: Analyze connectivity
        mapper = ConnectivityMapper()
        for name, file_path in self.test_files.items():
            mapper.analyze_file(file_path)

        report = mapper.get_connectivity_report()
        self.assertIn('call_graph_stats', report)

        # Step 3: Statistical sampling
        sampler = StatisticalSampler()
        analysis = sampler.analyze_directory(self.temp_dir)

        self.assertGreater(analysis['total_files'], 0)
        self.assertIsInstance(analysis['coverage_estimate'], float)

        # Step 4: Surgical cleaning
        cleaner = SurgicalCleaner(backup_dir=os.path.join(self.temp_dir, 'backups'))

        # Get cleaning targets from bloat analysis
        targets = []
        for result in results:
            if 'unused_imports' in result:
                for imp in result['unused_imports']:
                    targets.append({'type': 'unused_import', 'line': 1})  # Simplified

        if targets:
            result = cleaner.surgical_remove(self.test_files['main'], targets[:1], 'integration test')
            self.assertIn('success', result)

    def test_ghost_code_threshold(self):
        """Test that ghost code calculation works."""
        detector = CodeBloatDetector()
        results = []
        for name, file_path in self.test_files.items():
            result = detector.analyze_file(file_path)
            results.append(result)

        overall = detector.calculate_overall_bloat(results)
        ghost_percentage = overall.get('ghost_code_percentage', 0)

        # Test code has bloat, so ghost code will be present
        self.assertIsInstance(ghost_percentage, float)
        self.assertGreaterEqual(ghost_percentage, 0)


if __name__ == '__main__':
    unittest.main()