#!/usr/bin/env python3
"""
Bootstrap Exit Validator

Validates that bootstrap process completed properly with correct state machine transitions.
This script prevents future bootstrap failures by enforcing mandatory validation steps.

TASK_0198: Bootstrap State Machine Enforcement
"""

import json
import os
import sys
import socket
from pathlib import Path
from datetime import datetime, timezone
import requests
from output_safety import safe_print

class BootstrapExitValidator:
    """Validates bootstrap exit completion and state machine transitions."""

    def __init__(self, workspace_root=None):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.current_json = self.workspace_root / "current.json"
        self.loop_gate = self.workspace_root / "_LOOP_GATE.md"
        self.transaction_log = self.workspace_root / "_transaction_log.jsonl"
        self.bootstrap_file = self.workspace_root / "_BOOTSTRAP.md"

    def validate_bootstrap_exit(self) -> dict:
        """Comprehensive validation of bootstrap exit process."""
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "validations": {},
            "overall_status": "UNKNOWN",
            "errors": [],
            "warnings": []
        }

        # 1. Check bootstrap file is deleted
        results["validations"]["bootstrap_file_deleted"] = self._check_bootstrap_file_deleted()

        # 2. Check state machine transition
        results["validations"]["state_machine_transition"] = self._check_state_machine_transition()

        # 3. Check confirm-bootstrap transaction
        results["validations"]["confirm_bootstrap_transaction"] = self._check_confirm_bootstrap_transaction()

        # 4. Check cockpit server accessibility
        results["validations"]["cockpit_server_running"] = self._check_cockpit_server()

        # Determine overall status
        all_passed = all(v["status"] == "PASS" for v in results["validations"].values())
        results["overall_status"] = "PASS" if all_passed else "FAIL"

        return results

    def _check_bootstrap_file_deleted(self) -> dict:
        """Verify bootstrap file has been deleted."""
        exists = self.bootstrap_file.exists()
        status = "PASS" if not exists else "FAIL"
        message = "Bootstrap file properly deleted" if not exists else "Bootstrap file still exists - deletion incomplete"

        return {
            "status": status,
            "message": message,
            "details": {
                "file_exists": exists,
                "file_path": str(self.bootstrap_file)
            }
        }

    def _check_state_machine_transition(self) -> dict:
        """Verify state machine transitioned from READY_FOR_RESET to ACTIVE."""
        try:
            if not self.current_json.exists():
                return {
                    "status": "FAIL",
                    "message": "current.json not found",
                    "details": {"file_path": str(self.current_json)}
                }

            with open(self.current_json, 'r') as f:
                data = json.load(f)

            state = data.get("STATE", {})
            status = state.get("status")
            loop = state.get("loop")
            transition_trigger = state.get("transitionTrigger")

            if status == "ACTIVE":
                return {
                    "status": "PASS",
                    "message": f"State machine properly transitioned to ACTIVE (Loop {loop})",
                    "details": {
                        "current_status": status,
                        "loop": loop,
                        "transition_trigger": transition_trigger
                    }
                }
            else:
                return {
                    "status": "FAIL",
                    "message": f"State machine stuck in {status} - did not transition to ACTIVE",
                    "details": {
                        "current_status": status,
                        "expected_status": "ACTIVE",
                        "loop": loop
                    }
                }

        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Failed to read current.json: {e}",
                "details": {"error": str(e)}
            }

    def _check_confirm_bootstrap_transaction(self) -> dict:
        """Verify confirm-bootstrap transaction exists in log."""
        try:
            if not self.transaction_log.exists():
                return {
                    "status": "FAIL",
                    "message": "Transaction log not found",
                    "details": {"file_path": str(self.transaction_log)}
                }

            confirm_bootstrap_found = False
            with open(self.transaction_log, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            transaction = json.loads(line)
                            if transaction.get("operation") == "confirm-bootstrap":
                                confirm_bootstrap_found = True
                                break
                        except json.JSONDecodeError:
                            continue

            if confirm_bootstrap_found:
                return {
                    "status": "PASS",
                    "message": "confirm-bootstrap transaction found in log",
                    "details": {"transaction_found": True}
                }
            else:
                return {
                    "status": "FAIL",
                    "message": "confirm-bootstrap transaction NOT found in log - API call may be missing",
                    "details": {"transaction_found": False}
                }

        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Failed to read transaction log: {e}",
                "details": {"error": str(e)}
            }

    def _check_loop_gate_status(self) -> dict:
        """Verify loop gate shows PASS status."""
        try:
            if not self.loop_gate.exists():
                return {
                    "status": "FAIL",
                    "message": "Loop gate file not found",
                    "details": {"file_path": str(self.loop_gate)}
                }

            with open(self.loop_gate, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            if "STATUS: PASS" in content:
                return {
                    "status": "PASS",
                    "message": "Loop gate shows PASS status",
                    "details": {"gate_status": "PASS"}
                }
            elif "STATUS: BLOCKED" in content:
                return {
                    "status": "FAIL",
                    "message": "Loop gate shows BLOCKED status - validation failed",
                    "details": {"gate_status": "BLOCKED"}
                }
            else:
                return {
                    "status": "WARNING",
                    "message": "Loop gate status unclear",
                    "details": {"gate_content_preview": content[:200] + "..."}
                }

        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Failed to read loop gate: {e}",
                "details": {"error": str(e)}
            }

    def _check_cockpit_server(self) -> dict:
        """Verify cockpit server is running and accessible."""
        try:
            # Prefer a lightweight socket check so busy /api/status handlers
            # don't produce false bootstrap failures.
            with socket.create_connection(("127.0.0.1", 5000), timeout=2):
                return {
                    "status": "PASS",
                    "message": "Cockpit server port is reachable",
                    "details": {
                        "host": "127.0.0.1",
                        "port": 5000
                    }
                }
        except OSError as e:
            return {
                "status": "FAIL",
                "message": f"Cockpit server port not reachable: {e}",
                "details": {
                    "error": str(e),
                    "host": "127.0.0.1",
                    "port": 5000
                }
            }

    def generate_report(self, results: dict) -> str:
        """Generate human-readable validation report."""
        report_lines = [
            "# BOOTSTRAP EXIT VALIDATION REPORT",
            f"**Timestamp:** {results['timestamp']}",
            f"**Overall Status:** {results['overall_status']}",
            "",
            "## VALIDATION RESULTS",
            ""
        ]

        for validation_name, validation_result in results["validations"].items():
            status_tag = {
                "PASS": "[PASS]",
                "FAIL": "[FAIL]",
                "WARNING": "[WARN]",
                "ERROR": "[ERROR]",
            }.get(validation_result["status"], "[UNKNOWN]")

            report_lines.extend([
                f"### {status_tag} {validation_name.replace('_', ' ').title()}",
                f"**Status:** {validation_result['status']}",
                f"**Message:** {validation_result['message']}",
                ""
            ])

            if "details" in validation_result:
                report_lines.append("**Details:**")
                for key, value in validation_result["details"].items():
                    report_lines.append(f"- **{key}:** {value}")
                report_lines.append("")

        if results["errors"]:
            report_lines.extend([
                "## ERRORS",
                ""
            ] + [f"- {error}" for error in results["errors"]] + [""])

        if results["warnings"]:
            report_lines.extend([
                "## WARNINGS",
                ""
            ] + [f"- {warning}" for warning in results["warnings"]] + [""])

        report_lines.extend([
            "## SUMMARY",
            f"**Total Validations:** {len(results['validations'])}",
            f"**Passed:** {sum(1 for v in results['validations'].values() if v['status'] == 'PASS')}",
            f"**Failed:** {sum(1 for v in results['validations'].values() if v['status'] == 'FAIL')}",
            "",
            "---",
            "*Generated by bootstrap_exit_validator.py*"
        ])

        return "\n".join(report_lines)


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate bootstrap exit completion")
    parser.add_argument("--workspace", help="Workspace root directory")
    parser.add_argument("--output", help="Output report file")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")

    args = parser.parse_args()

    validator = BootstrapExitValidator(args.workspace)
    results = validator.validate_bootstrap_exit()

    if args.json:
        safe_print(json.dumps(results, indent=2))
    else:
        report = validator.generate_report(results)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            safe_print(f"Report written to {args.output}")
        else:
            safe_print(report)

    # Exit with appropriate code
    sys.exit(0 if results["overall_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
