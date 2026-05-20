from knowledge_db import KnowledgeDB

db = KnowledgeDB('.')

lesson = "Discovered that manual token tracking leads to errors when handling complex workflows"

print(f"Testing lesson: {lesson}")

# Check exclude patterns
exclude_patterns = [
    "provides", "supports", "includes", "contains", "offers", "enables",
    "allows", "gives", "creates", "generates", "displays", "shows",
    "visualization", "interface", "dashboard", "panel", "control",
    "management", "monitoring", "tracking", "analysis", "processing",
    "automation", "integration", "connection", "communication",
    "feature", "functionality", "capability", "system", "component",
    "module", "service", "endpoint", "api", "database", "file",
    "configuration", "setting", "parameter", "option", "choice"
]

lesson_lower = lesson.lower()
feature_words = sum(1 for pattern in exclude_patterns if pattern in lesson_lower)
print(f"Feature words found: {feature_words}")
if feature_words >= 2:
    print("REJECTED: Too many feature-like words")

# Check length
words = lesson.split()
print(f"Word count: {len(words)}")
if len(words) < 6:
    print("REJECTED: Too short")

# Check include indicators
include_indicators = [
    "learned", "found", "discovered", "realized", "improved",
    "better", "worse", "avoid", "should", "will", "going forward",
    "next time", "recommend", "suggest", "tip", "must", "always",
    "never", "don't", "critical", "key", "important", "major",
    "significant", "valuable", "essential", "crucial"
]

has_learning_indicator = any(word in lesson_lower for word in include_indicators)
print(f"Has learning indicator: {has_learning_indicator}")

db.close()