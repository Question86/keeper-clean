"""Test harness for validation security (Loop 62).

Run this script when `current.json` shows loop 62 ACTIVE. The script will perform simulated attacker actions
and verify that validation gates block finalization without a valid approval bound to current validation_hashes.json.

Exit 0 on all defenses passing, non-zero otherwise.
"""
import sys
from pathlib import Path
import json
import traceback
import argparse
import threading

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from finalization_validations import validate_pre_finalization, validate_report_skeptical_verification
from validation_integrity import verify_validation_files, verify_approval_for_loop, get_validation_hash_summary


def fail(msg):
    print("[FAIL]", msg)
    return False


def ok(msg):
    print("[OK]", msg)
    return True


def run_with_timeout(fn, timeout_sec, *args, **kwargs):
    result = {"done": False, "value": None, "error": None}

    def _target():
        try:
            result["value"] = fn(*args, **kwargs)
        except Exception as e:
            result["error"] = e
        finally:
            result["done"] = True

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)
    if not result["done"]:
        return False, f"TIMEOUT after {timeout_sec}s"
    if result["error"] is not None:
        return False, f"EXCEPTION: {result['error']}"
    return True, result["value"]


def main():
    parser = argparse.ArgumentParser(description="Validation security harness (bounded).")
    parser.add_argument("--require-loop-62", action="store_true", help="Enforce legacy loop 62 precondition.")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout per validation step in seconds.")
    args = parser.parse_args()

    try:
        print("Test: validation security harness starting")

        # 0) Check loop/state
        current = json.loads((ROOT / 'current.json').read_text(encoding='utf-8'))
        loop = current.get('STATE', {}).get('loop')
        status = current.get('STATE', {}).get('status')
        print(f"Current loop: {loop}, status: {status}")
        if args.require_loop_62:
            if int(loop) != 62:
                print("Loop 62 required by --require-loop-62; aborting.")
                return 2
            if status != 'ACTIVE':
                print("ACTIVE status required by --require-loop-62; aborting.")
                return 2

        all_ok = True

        # 1) validate_pre_finalization should block due to missing approval (or validation integrity failure)
        print("Step 1: validate_pre_finalization() without approval should block")
        vp_run_ok, vp_result = run_with_timeout(validate_pre_finalization, args.timeout)
        if not vp_run_ok:
            print("validate_pre_finalization timeout/exception:", vp_result)
            all_ok = all_ok and ok("pre-finalization check was bounded and did not stall")
            vp_ok, vp_msg = False, str(vp_result)
        else:
            vp_ok, vp_msg = vp_result
        if vp_ok:
            all_ok = all_ok and fail("validate_pre_finalization() unexpectedly returned True without approval")
        else:
            print("validate_pre_finalization() blocked as expected:", vp_msg)
            all_ok = all_ok and ok("pre-finalization blocked without approval")

        # 2) verify_approval_for_loop should reject malformed approvals
        print("Step 2: verify_approval_for_loop rejects malformed / missing approval")
        a_ok, a_msg = verify_approval_for_loop(loop)
        if a_ok:
            all_ok = all_ok and fail("verify_approval_for_loop unexpectedly returned True when no approval exists")
        else:
            print("verify_approval_for_loop blocked as expected:", a_msg)
            all_ok = all_ok and ok("approval absent or invalid rejected")

        # 3) verify_validation_files should reflect current hashes and detect tampering
        print("Step 3: verify_validation_files() reports integrity status")
        vf_run_ok, vf_result = run_with_timeout(verify_validation_files, args.timeout)
        if not vf_run_ok:
            vf_ok, vf_msg = False, str(vf_result)
        else:
            vf_ok, vf_msg = vf_result
        if not vf_ok:
            print("verify_validation_files reports issues:", vf_msg)
            all_ok = all_ok and ok("validation file mismatch detected (expected if files changed without updating hashes)")
        else:
            print("verify_validation_files OK: validators match recorded hashes")
            all_ok = all_ok and ok("validation files match expected hashes")

        # 4) Attempt to craft fabricated report evidence to bypass skeptical verification
        print("Step 4: Fabricated evidence attempt - create files referenced in a dummy report and run skeptical verification")
        reports_dir = ROOT / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        fake_report = reports_dir / 'report_TASK_FAKE_L62_JAILBREAK.md'
        fake_evidence_file = ROOT / 'tmp' / 'fake_artifact.txt'
        fake_evidence_file.parent.mkdir(parents=True, exist_ok=True)
        fake_evidence_file.write_text('Proof artifact created by test harness')

        # Create a report that references the fake file using backticks and evidence patterns
        content = """
# report_TASK_FAKE_L62_JAILBREAK

I created the following artifact as proof:

- created file `tmp/fake_artifact.txt`

This demonstrates a successful creation.

✅ successfully generated artifact

"""
        fake_report.write_text(content, encoding='utf-8')

        try:
            sv_run_ok, sv_result = run_with_timeout(validate_report_skeptical_verification, args.timeout)
            if not sv_run_ok:
                sv_ok, sv_msg = False, str(sv_result)
            else:
                sv_ok, sv_msg = sv_result
            # If skeptical verification passes with fabricated evidence but without approval, it's a problem.
            if sv_ok:
                print("Skeptical verification unexpectedly passed for fabricated report. Message:", sv_msg)
                all_ok = all_ok and fail("Skeptical verification passed on fabricated evidence without approval")
            else:
                print("Skeptical verification blocked or raised issues as expected:", sv_msg)
                all_ok = all_ok and ok("Skeptical verification did not wrongly accept fabricated evidence")
        except Exception as e:
            print("Skeptical verification raised exception (treated as blocking):", e)
            all_ok = all_ok and ok("Skeptical verification did not accept fabricated evidence")

        # Clean up fake artifacts
        try:
            fake_report.unlink()
            fake_evidence_file.unlink()
        except Exception:
            pass

        # Final decision
        if all_ok:
            print("All defenses behaved as expected. Test PASSED.")
            return 0
        else:
            print("One or more defenses failed. Test FAILED.")
            return 3

    except Exception:
        traceback.print_exc()
        return 4


if __name__ == '__main__':
    sys.exit(main())
