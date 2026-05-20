from knowledge_db import KnowledgeDB

# Debug the full selective extraction pipeline
db = KnowledgeDB('.')

test_content = '''
## Lessons Learned
- Learned that early validation prevents downstream issues and saves significant time
- Discovered that manual token tracking leads to errors when handling complex workflows
- Realized that automated testing frameworks work better when integrated early in development
'''

print("Testing full extraction pipeline...")

# Simulate the extraction process
sections = test_content.split('## ')
for section in sections:
    section_lines = section.strip().split('\n')
    if not section_lines:
        continue

    section_header = section_lines[0].strip().lower() if section_lines else ""

    print(f"\nSection: {section_header}")

    for i, line in enumerate(section_lines):
        line = line.strip()
        if not line or line.startswith('#') or len(line) < 15:
            continue

        # Strip bullet points
        clean_line = line
        if clean_line.startswith(('- ', '* ', '• ')):
            clean_line = clean_line[2:].strip()

        print(f"\n  Line: {clean_line}")

        # Test extraction
        lesson_data = db._analyze_line_for_high_quality_lessons(clean_line, section_header, section_lines, i)
        print(f"  Lesson data: {lesson_data is not None}")

        if lesson_data:
            genuine = db._is_genuine_high_quality_lesson(lesson_data['text'], section_header, 'test')
            actionable = db._has_actionable_insight(lesson_data['text'])
            not_generic = not db._is_generic_or_documentation(lesson_data['text'])

            print(f"  Genuine: {genuine}, Actionable: {actionable}, Not generic: {not_generic}")

            if genuine and actionable and not_generic:
                print("  ✅ WOULD BE EXTRACTED")
            else:
                print("  ❌ WOULD BE REJECTED")

db.close()