# TASK_0087: Smart Report Templates

MODE: IMPLEMENTATION
STATUS: COMPLETED
CREATED: 2026-01-11T03:20:32Z
COMPLETED: 2026-01-11T04:35:32Z
SOURCE: TASK_0071 EPIC - Phase 3 (Workflow Polish)

---

## OBJECTIVE

Create smart report template generator that pre-fills reports from task spec data, reducing boilerplate and ensuring consistency.

## CONTEXT

Report creation requires copying OBJECTIVE, listing expected files, creating acceptance checklists - all available in task spec. Automate this.

## SCOPE

1. Create `/api/generate-report-template` endpoint
2. Parse task spec for: OBJECTIVE, SCOPE, ACCEPTANCE CRITERIA
3. Generate report skeleton with pre-filled sections
4. Include acceptance criteria as checkboxes
5. Add "Generate Report" button in cockpit UI

## ACCEPTANCE CRITERIA

- [ ] API generates valid report template
- [ ] Template includes task objective
- [ ] Template includes acceptance criteria as checkboxes
- [ ] Template passes lint validation
- [ ] Button copies template to clipboard
- [ ] Generated reports reduce creation time 50%

## TESTING

```python
def test_report_template():
    template = generate_report_template("TASK_0001", loop=45, version=1)
    assert "TASK_0001" in template
    assert "## OBJECTIVE" in template
    assert "[ ]" in template  # Checkboxes
    assert lint_report(template)["errors"] == []
```

## DEPENDENCIES

- Phase 2 complete (needs context index)

---

END OF DOCUMENT
