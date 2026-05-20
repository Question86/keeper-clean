# CONTRACTS: Machine-Enforced Validation System

"""
Machine-enforced contracts replacing narrative validation.

This module implements a contract-based validation system that replaces
human-readable narrative descriptions with executable, machine-verifiable
contracts. Inspired by depth-first connectivity analysis for comprehensive
validation coverage.

Contracts are defined as executable predicates with evidence collection,
enabling automated validation of system invariants.
"""

import json
import os
import re
from typing import Dict, List, Callable, Any, Tuple
from dataclasses import dataclass

@dataclass
class ContractResult:
    """Result of contract validation."""
    contract_name: str
    passed: bool
    evidence: List[str]
    violations: List[str]

class ContractSystem:
    """Machine-enforced contract validation system."""

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.contracts: Dict[str, Callable[[], ContractResult]] = {}
        self.register_core_contracts()

    def register_contract(self, name: str, validator: Callable[[], ContractResult]):
        """Register a contract validator."""
        self.contracts[name] = validator

    def validate_all(self) -> Dict[str, ContractResult]:
        """Execute all registered contracts."""
        results = {}
        for name, validator in self.contracts.items():
            try:
                results[name] = validator()
            except Exception as e:
                results[name] = ContractResult(
                    contract_name=name,
                    passed=False,
                    evidence=[],
                    violations=[f"Contract execution failed: {str(e)}"]
                )
        return results

    def register_core_contracts(self):
        """Register core system contracts."""

        # Contract: REPORT-FIRST Law Enforcement
        def report_first_contract() -> ContractResult:
            violations = []
            evidence = []

            # Check that active tasks have reports
            neu_path = os.path.join(self.workspace_root, "NEU.md")
            if os.path.exists(neu_path):
                with open(neu_path, 'r') as f:
                    content = f.read()
                    # Extract task references
                    import re
                    task_refs = re.findall(r'\[ref:tasks/task_(TASK_\d+)\.md', content)
                    for task in task_refs:
                        report_path = os.path.join(self.workspace_root, "reports", f"report_{task}_L71_v01.md")
                        if not os.path.exists(report_path):
                            violations.append(f"Missing report for active task {task}")
                        else:
                            evidence.append(f"Report exists for {task}")

            return ContractResult(
                contract_name="REPORT_FIRST_ENFORCEMENT",
                passed=len(violations) == 0,
                evidence=evidence,
                violations=violations
            )

        # Contract: State Consistency
        def state_consistency_contract() -> ContractResult:
            violations = []
            evidence = []

            current_path = os.path.join(self.workspace_root, "current.json")
            if os.path.exists(current_path):
                with open(current_path, 'r') as f:
                    state = json.load(f)

                loop = state.get('STATE', {}).get('loop')
                status = state.get('STATE', {}).get('status')

                # Validate loop number is reasonable
                if not isinstance(loop, int) or loop < 1:
                    violations.append(f"Invalid loop number: {loop}")
                else:
                    evidence.append(f"Valid loop number: {loop}")

                # Validate status is known
                valid_statuses = ['READY_FOR_RESET', 'ACTIVE', 'FINALIZED']
                if status not in valid_statuses:
                    violations.append(f"Invalid status: {status}")
                else:
                    evidence.append(f"Valid status: {status}")

            return ContractResult(
                contract_name="STATE_CONSISTENCY",
                passed=len(violations) == 0,
                evidence=evidence,
                violations=violations
            )

        # Contract: Archive Integrity
        def archive_integrity_contract() -> ContractResult:
            violations = []
            evidence = []

            archive_dir = os.path.join(self.workspace_root, "archive")
            if os.path.exists(archive_dir):
                archives = [f for f in os.listdir(archive_dir) if f.startswith("ARCHIV_") and f.endswith(".md")]
                evidence.append(f"Found {len(archives)} archives")

                # Check archive naming consistency
                for archive in archives:
                    if not re.match(r'ARCHIV_\d+\.md', archive):
                        violations.append(f"Malformed archive name: {archive}")
                    else:
                        evidence.append(f"Valid archive: {archive}")

            return ContractResult(
                contract_name="ARCHIVE_INTEGRITY",
                passed=len(violations) == 0,
                evidence=evidence,
                violations=violations
            )

        # Contract: Depth-First Connectivity (inspired by depth_vs_breathe.md)
        def depth_first_connectivity_contract() -> ContractResult:
            violations = []
            evidence = []

            # Analyze reference depth in key documents
            cortex_path = os.path.join(self.workspace_root, "NEURAL_CORTEX.md")
            if os.path.exists(cortex_path):
                with open(cortex_path, 'r') as f:
                    content = f.read()

                # Count reference chain depth
                import re
                refs = re.findall(r'\[ref:([^]]+)\]', content)
                max_depth = 0
                for ref in refs:
                    depth = ref.count('/') + 1  # Approximate depth by path separators
                    max_depth = max(max_depth, depth)

                if max_depth >= 3:  # Require minimum depth for connectivity
                    evidence.append(f"Reference depth: {max_depth} (sufficient for connectivity)")
                else:
                    violations.append(f"Insufficient reference depth: {max_depth} < 3")

            return ContractResult(
                contract_name="DEPTH_FIRST_CONNECTIVITY",
                passed=len(violations) == 0,
                evidence=evidence,
                violations=violations
            )

        # Register all contracts
        self.register_contract("REPORT_FIRST_ENFORCEMENT", report_first_contract)
        self.register_contract("STATE_CONSISTENCY", state_consistency_contract)
        self.register_contract("ARCHIVE_INTEGRITY", archive_integrity_contract)
        self.register_contract("DEPTH_FIRST_CONNECTIVITY", depth_first_connectivity_contract)

def validate_contracts(workspace_root: str) -> Dict[str, ContractResult]:
    """Validate all machine-enforced contracts."""
    system = ContractSystem(workspace_root)
    return system.validate_all()

if __name__ == "__main__":
    import sys
    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
    results = validate_contracts(workspace)

    print("CONTRACT VALIDATION RESULTS")
    print("=" * 50)

    all_passed = True
    for name, result in results.items():
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"{name}: {status}")

        if result.evidence:
            print("  Evidence:")
            for ev in result.evidence:
                print(f"    + {ev}")

        if result.violations:
            all_passed = False
            print("  Violations:")
            for v in result.violations:
                print(f"    - {v}")

        print()

    print(f"OVERALL: {'ALL CONTRACTS PASSED' if all_passed else 'CONTRACT VIOLATIONS DETECTED'}")