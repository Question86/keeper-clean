from knowledge_db import KnowledgeDB

# Test the new ultra-selective extraction method
db = KnowledgeDB('.')

# Test with a report that has both good and bad content
test_content = '''
## Summary
This report covers the implementation of new features.

## Lessons Learned
- Learned that early validation prevents downstream issues and saves significant time
- Discovered that manual token tracking leads to errors when handling complex workflows
- Realized that automated testing frameworks work better when integrated early in development
- Going forward, we should always validate API responses before processing them
- Key insight: Database connection pooling prevents performance bottlenecks during high load
- Critical finding: Memory leaks occur when event listeners aren't properly cleaned up
- Important lesson: Code reviews should focus on both functionality and maintainability
- Best practice: Always implement proper error boundaries in user-facing components

## Features Implemented
- Real-time visualization of project files
- Token budget explanation and guidance
- Multi-agent orchestrator with live telemetry

## Challenges Faced
- The initial approach didn't work well with large datasets
- Discovered that manual token tracking leads to errors

## Generic Observations
- The system is working well
- Good progress was made
- Important work completed
- Best practices were followed
'''

print("Testing new ultra-selective extraction method...")

# Test the extraction
lessons_count = db._extract_lessons_from_content(test_content, 'test', 'selective_test', 100)
print(f'Extracted {lessons_count} lessons from test content')

# Check what was extracted
cursor = db.conn.execute('SELECT lesson_text, category, confidence_score, context_section FROM lessons WHERE source_id = ? ORDER BY id DESC LIMIT 10', ('selective_test',))
extracted = cursor.fetchall()

print('\nExtracted lessons:')
for i, lesson in enumerate(extracted, 1):
    print(f'{i}. [{lesson[1]}] {lesson[0][:100]}...')
    print(f'   (confidence: {lesson[2]}, section: {lesson[3]})')

db.close()