from knowledge_db import KnowledgeDB

db = KnowledgeDB('.')

# Test the exact extraction process
line = "Discovered that manual token tracking leads to errors when handling complex workflows"

print(f"Original line: {line}")

# Simulate what _analyze_line_for_high_quality_lessons does
line_lower = line.lower()
for indicator in ["learned that", "learned how", "discovered that", "found that", "realized that", "key insight:", "critical insight:", "important insight:", "key finding:", "critical finding:", "important finding:", "major lesson:", "key lesson:", "critical lesson:", "best practice:", "key practice:", "recommended practice:", "avoid:", "never:", "don't:", "always:", "consistently:", "must:", "going forward:", "in the future:", "next time:", "recommend:", "suggest:", "advise:", "tip:", "pro tip:", "important tip:", "remember:", "note:", "important note:", "lesson learned:", "lessons learned:"]:
    if indicator in line_lower:
        idx = line_lower.find(indicator)
        lesson_text = line[idx + len(indicator):].strip()
        print(f"Found indicator '{indicator}' -> extracted text: '{lesson_text}'")
        break

db.close()