# MODE: SCRIPT\n\n"""Knowledge Database Usage Verification Tool"""

import os
import re
from pathlib import Path
from knowledge_db import KnowledgeDB

def verify_knowledge_usage_in_reports():
    """Check recent reports for evidence of knowledge database usage."""

    reports_dir = Path('reports')
    if not reports_dir.exists():
        print("❌ Reports directory not found")
        return

    # Get recent reports (last 5)
    reports = sorted(reports_dir.glob('report_*.md'), key=os.path.getmtime, reverse=True)[:5]

    print("🔍 Checking recent reports for knowledge database usage...")
    print("=" * 60)

    usage_found = 0
    total_checked = len(reports)

    for report_path in reports:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        report_name = report_path.name

        # Check for knowledge database references
        knowledge_indicators = [
            'keeper_knowledge.db',
            'knowledge database',
            'semantic search',
            'query_knowledge.py',
            'database query',
            'knowledge findings',
            'similar implementation',
            'historical approach'
        ]

        found_indicators = []
        for indicator in knowledge_indicators:
            if indicator.lower() in content.lower():
                found_indicators.append(indicator)

        if found_indicators:
            usage_found += 1
            print(f"✅ {report_name}")
            print(f"   Found indicators: {', '.join(found_indicators)}")
        else:
            print(f"❌ {report_name}")
            print("   No knowledge database usage detected")

        print()

    print("=" * 60)
    print(f"RESULTS: {usage_found}/{total_checked} recent reports show knowledge database usage")

    if usage_found < total_checked * 0.8:  # Less than 80% usage
        print("⚠️  WARNING: Knowledge database usage below expected threshold")
        print("   Consider enforcing KNOWLEDGE DATABASE LAW more strictly")
    else:
        print("✅ Knowledge database integration appears healthy")

def test_knowledge_query_tool():
    """Test that the knowledge query tool works."""
    print("\n🧪 Testing knowledge query tool...")

    try:
        db = KnowledgeDB(Path('.'))
        results = db.search('test query', limit=2)

        if results:
            print(f"✅ Knowledge database accessible: {len(results)} results found")
            print(f"   Sample relevance: {results[0].relevance:.1f}")
        else:
            print("⚠️  Knowledge database accessible but no results for test query")

    except Exception as e:
        print(f"❌ Knowledge database error: {e}")

if __name__ == "__main__":
    verify_knowledge_usage_in_reports()
    test_knowledge_query_tool()