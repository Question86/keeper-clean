#!/usr/bin/env python3
"""
Analyze the actual lessons in the database to understand content quality
"""

import sqlite3
import sys
from collections import Counter


def safe_print(*parts):
    text = " ".join(str(p) for p in parts)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("ascii", "replace"))


class LessonAnalyzer:
    def __init__(self, db_path: str = "keeper_knowledge.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def analyze_all_lessons(self):
        """Analyze all lessons in the database"""
        cursor = self.conn.execute("""
            SELECT lesson_text, category, confidence_score, context_section, source_id, loop_num
            FROM lessons
            ORDER BY confidence_score DESC, id
        """)

        lessons = cursor.fetchall()

        safe_print(f"LESSON DATABASE ANALYSIS ({len(lessons)} lessons)")
        safe_print("=" * 60)
        if not lessons:
            safe_print("No lessons found.")
            return

        # Confidence distribution
        conf_counts = Counter()
        for lesson in lessons:
            conf = lesson[2]
            if conf >= 0.8:
                conf_counts['high'] += 1
            elif conf >= 0.5:
                conf_counts['medium'] += 1
            else:
                conf_counts['low'] += 1

        safe_print("Confidence Distribution:")
        total = len(lessons)
        for level, count in conf_counts.items():
            pct = (count / total) * 100
            safe_print(f"  {level.upper():6s}: {count:2d} ({pct:5.1f}%)")

        # Category distribution
        categories = Counter(lesson[1] for lesson in lessons)
        safe_print("\nCategory Distribution:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total) * 100
            safe_print(f"  {cat:12s}: {count:2d} ({pct:5.1f}%)")

        # Context sections
        contexts = Counter(lesson[3] for lesson in lessons if lesson[3])
        safe_print("\nTop Context Sections:")
        for context, count in sorted(contexts.items(), key=lambda x: x[1], reverse=True)[:5]:
            pct = (count / total) * 100
            safe_print(f"  {context:20s}: {count:2d} ({pct:5.1f}%)")

        # Loop distribution
        loops = Counter(lesson[5] for lesson in lessons)
        safe_print("\nLessons by Loop:")
        for loop, count in sorted(loops.items(), key=lambda x: x[1], reverse=True)[:10]:
            pct = (count / total) * 100
            safe_print(f"  Loop {loop:2d}: {count:2d} ({pct:5.1f}%)")

        # Sample high-confidence lessons
        safe_print("\nSAMPLE HIGH-CONFIDENCE LESSONS:")
        high_conf = [l for l in lessons if l[2] >= 0.8]
        for i, lesson in enumerate(high_conf[:5], 1):
            safe_print(f"{i}. [{lesson[1]}] {lesson[0][:100]}...")
            safe_print(f"   (confidence: {lesson[2]}, loop: {lesson[5]}, context: {lesson[3] or 'none'})")

        # Sample medium-confidence lessons
        safe_print("\nSAMPLE MEDIUM-CONFIDENCE LESSONS:")
        med_conf = [l for l in lessons if 0.5 <= l[2] < 0.8]
        for i, lesson in enumerate(med_conf[:5], 1):
            safe_print(f"{i}. [{lesson[1]}] {lesson[0][:100]}...")
            safe_print(f"   (confidence: {lesson[2]}, loop: {lesson[5]}, context: {lesson[3] or 'none'})")

        # Content analysis - what themes appear
        safe_print("\nCONTENT THEMES ANALYSIS:")
        all_text = ' '.join(lesson[0].lower() for lesson in lessons)

        # Common themes from project
        themes = {
            'validation': all_text.count('validat'),
            'testing': all_text.count('test'),
            'performance': all_text.count('perform'),
            'error': all_text.count('error'),
            'code': all_text.count('code'),
            'database': all_text.count('databas'),
            'api': all_text.count('api'),
            'file': all_text.count('file'),
            'task': all_text.count('task'),
            'loop': all_text.count('loop'),
            'documentation': all_text.count('doc'),
            'automation': all_text.count('auto'),
            'integration': all_text.count('integrat'),
            'deployment': all_text.count('deploy'),
            'configuration': all_text.count('config'),
            'security': all_text.count('secur'),
            'monitoring': all_text.count('monitor'),
            'logging': all_text.count('log'),
            'caching': all_text.count('cach'),
            'scaling': all_text.count('scal'),
            'optimization': all_text.count('optim'),
            'debugging': all_text.count('debug'),
            'refactoring': all_text.count('refactor'),
            'architecture': all_text.count('architect'),
            'design': all_text.count('design'),
            'pattern': all_text.count('pattern'),
            'quality': all_text.count('qual'),
            'maintenance': all_text.count('maintain'),
            'reliability': all_text.count('reliab'),
            'efficiency': all_text.count('efficien'),
            'communication': all_text.count('communicat'),
            'collaboration': all_text.count('collaborat'),
            'planning': all_text.count('plan'),
            'estimation': all_text.count('estimat'),
            'deadline': all_text.count('deadlin'),
            'scope': all_text.count('scope'),
            'debt': all_text.count('debt'),
            'legacy': all_text.count('legac'),
            'feedback': all_text.count('feedback'),
            'improvement': all_text.count('improv'),
            'learning': all_text.count('learn'),
            'training': all_text.count('train'),
            'mentoring': all_text.count('mentor')
        }

        safe_print("Most Common Themes in Lessons:")
        sorted_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)
        for theme, count in sorted_themes[:15]:
            pct = (count / len(all_text.split())) * 100
            safe_print(f"  {theme:15s}: {count:3d} mentions ({pct:4.1f}%)")

        # Length analysis
        lengths = [len(lesson[0].split()) for lesson in lessons]
        avg_length = sum(lengths) / len(lengths)
        safe_print(f"\nLESSON LENGTH ANALYSIS:")
        safe_print(f"  Average words per lesson: {avg_length:.1f}")
        safe_print(f"  Shortest lesson: {min(lengths)} words")
        safe_print(f"  Longest lesson: {max(lengths)} words")

        # Quality assessment
        safe_print(f"\nOVERALL QUALITY ASSESSMENT:")
        safe_print(f"  Total genuine lessons: {len(lessons)}")
        safe_print(f"  High-quality lessons: {len(high_conf)}")
        safe_print(f"  Well-categorized content: {'Yes' if len(categories) >= 4 else 'Limited'}")
        safe_print(f"  Diverse loop coverage: {'Yes' if len(loops) >= 10 else 'Limited'}")
        safe_print(f"  Focused on project themes: {'Yes' if sorted_themes[0][1] > 10 else 'Limited'}")

def main():
    analyzer = LessonAnalyzer()
    analyzer.analyze_all_lessons()
    analyzer.close()

if __name__ == "__main__":
    main()
