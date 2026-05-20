from knowledge_db import KnowledgeDB

db = KnowledgeDB('.')

lesson = "Discovered that manual token tracking leads to errors when handling complex workflows"

print(f"Testing lesson: {lesson}")
print(f"Starts with descriptive prefix: {lesson.lower().startswith(('the ', 'this ', 'these ', 'those ', 'our ', 'project '))}")

# Check the descriptive content logic
words = lesson.split()
first_few_words = ' '.join(words[:4]).lower()
descriptive_words = ['is', 'are', 'was', 'were', 'has', 'have', 'had', 'contains', 'includes']
has_descriptive = any(word in first_few_words for word in descriptive_words)
print(f"First few words: '{first_few_words}'")
print(f"Has descriptive words: {has_descriptive}")

# Test the actual method
result = db._is_genuine_high_quality_lesson(lesson, 'lessons learned', 'test')
print(f"Final result: {result}")

db.close()