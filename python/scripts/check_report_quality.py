#!/usr/bin/env python3
import json
from pathlib import Path
import finalization_validations as fv

report = Path('reports/report_LOOP_61_FINALIZATION_L61_v01.md')

res = fv.validate_report_evidence_based(report)
print(json.dumps({'evidence_based': res}, indent=2))

skept = fv.validate_report_skeptical_verification()
print(json.dumps({'skeptical_verification': skept}, indent=2))
