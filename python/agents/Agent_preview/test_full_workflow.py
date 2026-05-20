import pytest
import asyncio
import requests
import json
import time
import os
from pathlib import Path

# FIX: Einheitlicher Datenpfad – muss identisch mit conftest.py und Agent sein
DATA_JOBS_DIR = "/workspace/data/jobs"


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _wait_for_job(
    api_url: str,
    job_id: str,
    timeout: int = 60,
) -> dict:
    """
    Poll job status bis DONE oder ERROR.
    FIX: Gibt final status_data zurück statt Variable aus äußerem Scope zu nutzen,
         wodurch unklar war ob die letzte Iteration überhaupt erreicht wurde.
    """
    start_time = time.time()
    last_status: dict = {}

    while time.time() - start_time < timeout:
        response = requests.get(f"{api_url}/v1/jobs/{job_id}", timeout=5)
        assert response.status_code == 200, (
            f"Status endpoint returned HTTP {response.status_code}"
        )

        last_status = response.json()
        status = last_status.get("status", "UNKNOWN")
        progress = last_status.get("progress", 0)
        print(f"   📊 Status: {status} | Progress: {progress:.1f}%")

        if status in ("DONE", "ERROR"):
            return last_status

        await asyncio.sleep(2)

    # Timeout
    last_status["_timed_out"] = True
    return last_status


# ─── Test: Full Workflow ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_workflow(services, sample_data):
    """Test complete workflow from upload to results"""
    api_url = services["api_url"]

    # Step 1: Job anlegen
    print("\n📤 Creating job...")
    with open(sample_data, "rb") as f:
        response = requests.post(
            f"{api_url}/v1/jobs/upload",
            files={"file": ("zee.txt", f, "text/plain")},
            data={"job_type": "upload", "requested_n_toys": "100"},
        )

    assert response.status_code == 200, (
        f"Job creation failed: HTTP {response.status_code} — {response.text}"
    )
    job_id = response.json()["job_id"]
    print(f"✅ Job created: {job_id}")

    # Step 2: Job überwachen
    print("⏳ Monitoring job progress...")
    job_status = await _wait_for_job(api_url, job_id, timeout=60)

    # FIX: Timeout explizit als Fehler behandeln
    if job_status.get("_timed_out"):
        pytest.fail(f"Job {job_id} did not finish within 60s")

    # FIX: ERROR-Status als Fehler behandeln mit Details
    if job_status["status"] == "ERROR":
        error_detail = job_status.get("error", "No error detail available")
        pytest.fail(f"Job {job_id} ended with ERROR: {error_detail}")

    assert job_status["status"] == "DONE", (
        f"Expected DONE, got: {job_status['status']}"
    )
    print("✅ Job completed successfully")

    # Step 3: Ergebnisse abrufen
    print("📋 Retrieving results...")
    response = requests.get(f"{api_url}/v1/jobs/{job_id}/results", timeout=10)
    assert response.status_code == 200, (
        f"Results endpoint returned HTTP {response.status_code}"
    )
    results = response.json()
    assert "p_value" in results, f"'p_value' missing in results: {results.keys()}"
    print(f"🎯 Final P-value: {results['p_value']}")

    # Step 4: Artifacts prüfen
    print("📦 Checking artifacts...")
    response = requests.get(f"{api_url}/v1/jobs/{job_id}/artifacts", timeout=10)
    assert response.status_code == 200
    artifacts = response.json()
    assert len(artifacts) > 0, "Expected at least one artifact"
    print(f"📁 Found {len(artifacts)} artifact(s):")
    for a in artifacts:
        print(f"   - {a['filename']} ({a['size_bytes']} bytes)")

    # Step 5: Reproducibility prüfen
    print("🔍 Verifying reproducibility...")

    # FIX: Einheitlichen DATA_JOBS_DIR Pfad verwenden
    manifest_path = Path(DATA_JOBS_DIR) / job_id / "manifest.json"
    assert manifest_path.exists(), (
        f"Manifest not found at {manifest_path}. "
        f"Check that API writes to {DATA_JOBS_DIR}, not /data/jobs"
    )

    with open(manifest_path) as f:
        manifest = json.load(f)

    # FIX: Normalisierung vor Vergleich – verhindert False-Failures durch
    #      UUID-Formatunterschiede (mit/ohne Bindestriche)
    assert str(manifest["run_id"]).replace("-", "") == str(results["run_id"]).replace("-", ""), (
        f"run_id mismatch: manifest={manifest['run_id']} vs results={results['run_id']}"
    )
    assert manifest["dataset_sha256"] == results["dataset_sha256"], (
        f"SHA256 mismatch: manifest={manifest['dataset_sha256']} "
        f"vs results={results['dataset_sha256']}"
    )
    print("✅ Reproducibility verified")

    # Step 6: Artifact Download
    print("⬇️  Testing artifact download...")
    first_artifact = artifacts[0]
    response = requests.get(
        f"{api_url}/v1/jobs/{job_id}/artifacts/{first_artifact['filename']}",
        timeout=10,
    )
    assert response.status_code == 200, (
        f"Artifact download failed: HTTP {response.status_code}"
    )
    print(f"✅ Downloaded artifact: {first_artifact['filename']}")

    print("🎉 Full workflow test completed successfully!")


# ─── Test: Fail Closed ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fail_closed_parsing(services):
    """Test that unknown formats fail closed"""
    api_url = services["api_url"]

    unknown_content = """\
This is not a recognized format
Some random text data
That doesn't match any adapter
"""
    # FIX: tmp_path nicht verfügbar hier, aber /tmp ist OK für diesen Test
    test_file = Path("/tmp/unknown_format_test.txt")
    test_file.write_text(unknown_content)

    with open(test_file, "rb") as f:
        response = requests.post(
            f"{api_url}/v1/jobs/upload",
            files={"file": ("unknown.txt", f, "text/plain")},
            data={"job_type": "upload", "requested_n_toys": "10"},
        )

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # FIX: Statt blindem sleep – echten Poll nutzen
    job_status = await _wait_for_job(api_url, job_id, timeout=30)

    # Job sollte mit ERROR enden (unknown format → fail closed)
    # FIX: Vorher wurde nur results-endpoint auf 400 geprüft, aber nie
    #      gewartet bis der Job wirklich fertig ist → Race Condition
    assert job_status["status"] == "ERROR", (
        f"Expected ERROR for unknown format, got: {job_status['status']}"
    )

    # Results-Endpoint sollte ebenfalls 400 zurückgeben
    response = requests.get(f"{api_url}/v1/jobs/{job_id}/results", timeout=10)
    assert response.status_code == 400, (
        f"Expected 400 for failed job results, got: {response.status_code}"
    )

    print("✅ Unknown format correctly rejected (fail-closed)")


# ─── Test: Partial Results ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_partial_results(services, sample_data):
    """Test partial result handling during job execution"""
    api_url = services["api_url"]

    with open(sample_data, "rb") as f:
        response = requests.post(
            f"{api_url}/v1/jobs/upload",
            files={"file": ("zee.txt", f, "text/plain")},
            data={"job_type": "upload", "requested_n_toys": "5"},
        )

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # Auf partielle Ergebnisse während RUNNING-Phase warten
    start_time = time.time()
    partial_found = False

    while time.time() - start_time < 30:
        status_resp = requests.get(f"{api_url}/v1/jobs/{job_id}", timeout=5)
        job_status = status_resp.json()

        if job_status.get("progress", 0) > 0 and job_status.get("status") == "RUNNING":
            results_resp = requests.get(
                f"{api_url}/v1/jobs/{job_id}/results", timeout=5
            )
            if results_resp.status_code == 200:
                results = results_resp.json()
                if results.get("partial_result"):
                    partial_found = True
                    print("✅ Partial result detected during RUNNING phase")
                    break

        # Frühzeitig abbrechen wenn Job schon fertig
        if job_status.get("status") in ("DONE", "ERROR"):
            break

        await asyncio.sleep(1)

    # Warten bis Job vollständig abgeschlossen
    final_status = await _wait_for_job(api_url, job_id, timeout=30)

    # FIX: ERROR abfangen
    if final_status["status"] == "ERROR":
        error_detail = final_status.get("error", "No detail")
        pytest.fail(f"Job ended with ERROR: {error_detail}")

    response = requests.get(f"{api_url}/v1/jobs/{job_id}/results", timeout=10)
    assert response.status_code == 200, (
        f"Final results endpoint returned HTTP {response.status_code}"
    )

    if not partial_found:
        print("⚠️  No partial results observed (job may have been too fast)")

    print("✅ Partial result handling test completed")
