import pytest
from pathlib import Path
from finalization_validations import validate_report_evidence_based

ROOT = Path(__file__).parent.parent


def test_bypass_reports_fail():
    # Known bad report (empty claims) should fail evidence-based validation
    rpt = ROOT / "tests" / "guardrail_bypass_reports" / "test_case_01_empty_claims.md"
    assert rpt.exists()
    res = validate_report_evidence_based(rpt)
    assert not res['passed'], f"Expected fail but passed: {res}"


def test_real_report_passes():
    # TASK_0076 report contains concrete evidence (file references, test details)
    rpt = ROOT / "reports" / "report_TASK_0077_L57_v01.md"
    assert rpt.exists()
    res = validate_report_evidence_based(rpt)
    assert res['passed'], f"Expected pass but failed: {res}"
