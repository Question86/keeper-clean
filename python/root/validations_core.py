from pathlib import Path
import re

WORKSPACE_ROOT = Path("D:/Keeper-Clean-Loop1").resolve()


def validate_report_evidence_based(report_path: Path) -> dict:
    """Evidence-based validation: require positive artifacts and structured sections.

    Returns dict: {'passed': bool, 'score': int, 'missing': list[str], 'evidence': dict}
    """
    content = report_path.read_text(encoding='utf-8')
    evidence = {
        'files_modified': [],
        'files_created': [],
        'api_endpoints': [],
        'code_snippets': [],
        'test_results': [],
        'before_after': []
    }
    missing = []
    score = 0

    # 1. FILE EVIDENCE - filenames with extensions
    file_pattern = r'`([a-zA-Z0-9_/\\\.-]+\.(py|js|html|md|json|css))`'
    file_matches = re.findall(file_pattern, content)
    evidence['files_modified'] = [m[0] for m in file_matches]
    if evidence['files_modified']:
        verified = []
        for f in evidence['files_modified']:
            if (WORKSPACE_ROOT / f).exists():
                verified.append(f)
        if verified:
            score += 2
            evidence['verified_files'] = verified
        else:
            missing.append('Referenced files not found on disk')
    else:
        missing.append('No specific files referenced (expected `filename.ext`)')

    # 2. CODE EVIDENCE - code blocks
    code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', content, re.DOTALL)
    evidence['code_snippets'] = [b.strip() for b in code_blocks if len(b.strip()) > 20]
    if evidence['code_snippets']:
        score += 1
    else:
        missing.append('No code examples provided in ``` blocks')

    # 3. API EVIDENCE
    api_pattern = r"(/api/[\w/-]+)|@app\.route\([\'\"].*?[\'\"]\)"
    api_matches = re.findall(api_pattern, content)
    evidence['api_endpoints'] = [m[0] or m[1] for m in api_matches if m]
    if evidence['api_endpoints']:
        score += 1

    # 4. TEST EVIDENCE
    test_patterns = [r'(PASSED|FAILED|SUCCESS|ERROR):\s*\d+', r'test.*?:\s*(pass|fail|ok)', r'\d+/\d+\s*(tests?|checks?)']
    for pattern in test_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            evidence['test_results'].extend(matches)
    if evidence['test_results']:
        score += 2

    # 5. BEFORE/AFTER EVIDENCE
    ba_pattern = r'(before|previous|old|was):\s*.*?\n.*(after|new|now|is):\s*'
    if re.search(ba_pattern, content, re.IGNORECASE):
        evidence['before_after'] = True
        score += 1

    # Structural sections requirement
    required_sections = ['OBJECTIVE', 'IMPLEMENTATION', 'VALIDATION']
    content_upper = content.upper()
    for section in required_sections:
        if section not in content_upper:
            # allow VALIDATION synonyms
            if section == 'VALIDATION' and any(s in content_upper for s in ['VALIDATION', 'VERIFICATION', 'CONCRETE EVIDENCE']):
                pass
            else:
                missing.append(f'Missing required section: {section}')

    # FILES MODIFIED: allow several synonyms (reports use varied headings)
    file_section_tokens = ['FILES MODIFIED', 'FILE MOD', 'MODIFICATIONS', 'FILE MODIFICATION', 'FILE MODIFICATIONS', 'FILE MOD CONFIRM', 'KEY FILE DIFFS', 'FILE MODIFICATION CONFIRMATIONS', 'FILE MODIFICATION CONFIRMATION', 'FILE MOD CONFIRMATIONS']
    if not any(tok in content_upper for tok in file_section_tokens):
        missing.append('Missing required section: FILES MODIFIED (or equivalent)')

    # Length checks
    word_count = len(content.split())
    if word_count < 200:
        missing.append('Report too brief (< 200 words)')
    elif word_count > 2000:
        missing.append('Report excessively long (> 2000 words) - be concise')

    # Anti-gaming repetition checks (lighter penalties)
    checkmark_count = content.count('✅')
    successfully_count = content.lower().count('successfully')
    penalty = 0
    if checkmark_count > 8:
        penalty += (checkmark_count - 8) * 2
        missing.append(f'Excessive checkmarks ({checkmark_count}) - focus on evidence')
    if successfully_count > 6:
        penalty += (successfully_count - 6)
        missing.append(f'Excessive "successfully" mentions ({successfully_count})')

    final_score = max(0, score - penalty)
    categories = sum([
        int(len(evidence['files_modified']) > 0),
        int(len(evidence['code_snippets']) > 0),
        int(len(evidence['api_endpoints']) > 0 or len(evidence['test_results']) > 0),
        int(bool(evidence.get('before_after'))),
    ])
    passed = (categories >= 2) and penalty < 10 and not any(s.startswith('Missing required section') for s in missing)

    return {'passed': passed, 'score': final_score, 'missing': missing, 'evidence': evidence}
