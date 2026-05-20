# test_performance.py - Performance benchmarks for API endpoints

import pytest
import json
from pathlib import Path


class TestPerformanceBenchmarks:
    """Performance benchmarks for critical API endpoints."""

    @pytest.mark.benchmark
    def test_api_status_performance(self, benchmark, client, sample_current_json, temp_workspace):
        """Benchmark GET /api/status endpoint performance."""
        # Setup current.json
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        def run_status_request():
            response = client.get('/api/status')
            assert response.status_code == 200
            return response

        result = benchmark(run_status_request)
        assert result is not None

    @pytest.mark.benchmark
    def test_api_tasks_performance(self, benchmark, client, temp_workspace):
        """Benchmark GET /api/tasks endpoint performance."""
        # Create sample NEU.md
        neu_content = """# NEU

MODE: POINTER-ONLY

---

## TASK QUEUE (PRIORITY ORDER)

[ref:tasks/task_TASK_0230.md|v:1|tags:testing|src:test]
[ref:tasks/task_TASK_0191.md|v:1|tags:api|src:user]
[ref:tasks/task_TASK_0229.md|v:1|tags:gap|src:strategic]
"""

        neu_path = Path("NEU.md")
        neu_path.write_text(neu_content, encoding="utf-8")

        def run_tasks_request():
            response = client.get('/api/tasks')
            assert response.status_code == 200
            return response

        result = benchmark(run_tasks_request)
        assert result is not None

    @pytest.mark.benchmark
    def test_health_endpoint_performance(self, benchmark, client):
        """Benchmark GET /health endpoint performance."""
        def run_health_request():
            response = client.get('/health')
            assert response.status_code == 200
            return response

        result = benchmark(run_health_request)
        assert result is not None


class TestLoadTests:
    """Load testing for API endpoints."""

    def test_concurrent_status_requests(self, client, sample_current_json, temp_workspace):
        """Test multiple concurrent requests to /api/status."""
        import threading
        import time

        # Setup current.json
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        results = []
        errors = []

        def make_request():
            try:
                response = client.get('/api/status')
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create 10 concurrent threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify results
        assert len(results) == 10
        assert all(code == 200 for code in results)
        assert len(errors) == 0

    def test_memory_usage_status_endpoint(self, client, sample_current_json, temp_workspace):
        """Test memory usage for /api/status endpoint."""
        import psutil
        import os

        # Setup current.json
        current_path = Path("current.json")
        current_path.write_text(json.dumps(sample_current_json), encoding="utf-8")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Make multiple requests
        for _ in range(100):
            response = client.get('/api/status')
            assert response.status_code == 200

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 50MB)
        assert memory_increase < 50 * 1024 * 1024, f"Memory increase: {memory_increase} bytes"


class TestStressTests:
    """Stress tests for API endpoints."""

    def test_large_task_list_performance(self, client, temp_workspace):
        """Test performance with large number of tasks."""
        # Create NEU.md with many tasks
        tasks = []
        for i in range(100):
            tasks.append(f"[ref:tasks/task_TASK_{i:04d}.md|v:1|tags:test|src:auto]")

        neu_content = f"""# NEU

MODE: POINTER-ONLY

---

## TASK QUEUE (PRIORITY ORDER)

{"\n".join(tasks)}
"""

        neu_path = Path("NEU.md")
        neu_path.write_text(neu_content, encoding="utf-8")

        import time
        start_time = time.time()

        response = client.get('/api/tasks')
        end_time = time.time()

        assert response.status_code == 200

        duration = end_time - start_time
        # Should complete within reasonable time (< 1 second)
        assert duration < 1.0, f"Request took {duration} seconds"

        data = json.loads(response.data)
        assert "active" in data  # Should have active content
        assert "closed" in data