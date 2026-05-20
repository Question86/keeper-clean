from knowledge_db import KnowledgeDB
from pathlib import Path
import sqlite3
import json
import os
from collections import defaultdict, Counter
import re

def analyze_file_db_mapping():
    """Analyze the mapping between files and database entries using mega.md methodology."""

    print("🔍 DEPTH-FIRST METADATA NETWORK ANALYSIS")
    print("=" * 60)

    db = KnowledgeDB(Path('.'))
    conn = db.conn

    # 1. FILE EXISTENCE VALIDATION
    print("\n📁 PHASE 1: FILE EXISTENCE VALIDATION")
    print("-" * 40)

    file_existence_stats = {
        'total_db_entries': 0,
        'files_found': 0,
        'files_missing': 0,
        'orphaned_entries': [],
        'path_mismatches': []
    }

    # Check reports
    reports = conn.execute('SELECT id, path FROM reports').fetchall()
    for report in reports:
        file_existence_stats['total_db_entries'] += 1
        full_path = Path('.') / report[1]
        if full_path.exists():
            file_existence_stats['files_found'] += 1
        else:
            file_existence_stats['files_missing'] += 1
            file_existence_stats['orphaned_entries'].append(f"REPORT: {report[0]} -> {report[1]}")

    # Check tasks
    tasks = conn.execute('SELECT id, path FROM tasks').fetchall()
    for task in tasks:
        file_existence_stats['total_db_entries'] += 1
        full_path = Path('.') / 'tasks' / task[1]
        if full_path.exists():
            file_existence_stats['files_found'] += 1
        else:
            file_existence_stats['files_missing'] += 1
            file_existence_stats['orphaned_entries'].append(f"TASK: {task[0]} -> tasks/{task[1]}")

    # Check archives
    archives = conn.execute('SELECT id, path FROM archives').fetchall()
    for archive in archives:
        file_existence_stats['total_db_entries'] += 1
        full_path = Path('.') / 'archive' / archive[1]
        if full_path.exists():
            file_existence_stats['files_found'] += 1
        else:
            file_existence_stats['files_missing'] += 1
            file_existence_stats['orphaned_entries'].append(f"ARCHIVE: {archive[0]} -> archive/{archive[1]}")

    print(f"Total DB entries with file paths: {file_existence_stats['total_db_entries']}")
    print(f"Files found: {file_existence_stats['files_found']}")
    print(f"Files missing: {file_existence_stats['files_missing']}")
    print(".1f")

    if file_existence_stats['orphaned_entries']:
        print(f"\n❌ ORPHANED ENTRIES ({len(file_existence_stats['orphaned_entries'])}):")
        for entry in file_existence_stats['orphaned_entries'][:10]:  # Show first 10
            print(f"  {entry}")
        if len(file_existence_stats['orphaned_entries']) > 10:
            print(f"  ... and {len(file_existence_stats['orphaned_entries']) - 10} more")

    # 2. REFERENCE RELATIONSHIP ANALYSIS
    print("\n🔗 PHASE 2: REFERENCE RELATIONSHIP ANALYSIS")
    print("-" * 40)

    ref_stats = conn.execute('''
        SELECT source_type, target_type, relationship_type, COUNT(*) as count
        FROM reference_relationships
        GROUP BY source_type, target_type, relationship_type
        ORDER BY count DESC
    ''').fetchall()

    print("Reference relationship types:")
    for stat in ref_stats:
        print(f"  {stat[0]} -> {stat[1]} ({stat[2]}): {stat[3]} relationships")

    # 3. MILESTONE INDEXING ANALYSIS
    print("\n🎯 PHASE 3: MILESTONE INDEXING ANALYSIS")
    print("-" * 40)

    milestone_stats = conn.execute('''
        SELECT milestone_id, goal_id, entity_type, COUNT(*) as count,
               AVG(relevance_score) as avg_relevance
        FROM milestone_index
        GROUP BY milestone_id, goal_id, entity_type
        ORDER BY milestone_id, goal_id
    ''').fetchall()

    print("Milestone indexing coverage:")
    current_milestone = None
    for stat in milestone_stats:
        milestone, goal, entity_type, count, avg_rel = stat
        if milestone != current_milestone:
            print(f"\n📌 MILESTONE {milestone}:")
            current_milestone = milestone
        goal_desc = f"Goal {goal}" if goal else "General"
        print(f"  {goal_desc} - {entity_type}: {count} entities (avg relevance: {avg_rel:.2f})")

    # 4. QUALITY SCORING ANALYSIS
    print("\n⭐ PHASE 4: QUALITY SCORING ANALYSIS")
    print("-" * 40)

    quality_stats = conn.execute('''
        SELECT entity_type, COUNT(*) as count,
               AVG(overall_score) as avg_overall,
               AVG(relevance_score) as avg_relevance,
               AVG(recency_score) as avg_recency,
               AVG(validation_score) as avg_validation,
               AVG(impact_score) as avg_impact
        FROM quality_scores
        GROUP BY entity_type
    ''').fetchall()

    print("Quality scores by entity type:")
    for stat in quality_stats:
        etype, count, overall, rel, recency, val, impact = stat
        print(f"  {etype.upper()}: {count} entities")
        print(f"    Overall: {overall:.2f}, Relevance: {rel:.2f}, Recency: {recency:.2f}")
        print(f"    Validation: {val:.2f}, Impact: {impact:.2f}")

    # 5. CONTEXTUAL LOCATION MAPPING
    print("\n🗺️  PHASE 5: CONTEXTUAL LOCATION MAPPING")
    print("-" * 40)

    # Analyze file distribution
    file_locations = defaultdict(int)

    # Get all files in workspace
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv', '.vscode']]

        for file in files:
            if file.endswith('.md'):
                rel_path = os.path.relpath(os.path.join(root, file))
                category = categorize_file_location(rel_path)
                file_locations[category] += 1

    print("File distribution by location:")
    for category, count in sorted(file_locations.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count} files")

    # 6. FAILURE RATE ANALYSIS
    print("\n❌ PHASE 6: FAILURE RATE ANALYSIS")
    print("-" * 40)

    # Analyze references in content vs actual files
    reference_failures = analyze_reference_failures(db)
    print(f"Reference validation: {len(reference_failures)} failures found")

    if reference_failures:
        print("\nTop reference failures:")
        for failure in reference_failures[:10]:
            print(f"  {failure}")

    # 7. DEPTH-FIRST CONNECTIVITY ANALYSIS
    print("\n🌐 PHASE 7: DEPTH-FIRST CONNECTIVITY ANALYSIS")
    print("-" * 40)

    # Analyze connectivity following mega.md methodology
    connectivity = analyze_connectivity(db)
    print(f"Network connectivity metrics:")
    print(f"  Total nodes: {connectivity['total_nodes']}")
    print(f"  Connected components: {connectivity['components']}")
    print(f"  Average branching factor: {connectivity['avg_branching']:.2f}")
    print(f"  Isolated nodes: {connectivity['isolated_nodes']}")

    # 8. RECOMMENDATIONS
    print("\n💡 PHASE 8: RECOMMENDATIONS")
    print("-" * 40)

    recommendations = generate_recommendations(file_existence_stats, reference_failures, connectivity)
    for rec in recommendations:
        print(f"  • {rec}")

    db.close()

def categorize_file_location(file_path):
    """Categorize file location for analysis."""
    path_parts = Path(file_path).parts

    if 'reports' in path_parts:
        return 'reports/'
    elif 'tasks' in path_parts:
        return 'tasks/'
    elif 'archive' in path_parts:
        return 'archive/'
    elif 'docs' in path_parts:
        return 'docs/'
    elif file_path.startswith('NEU.md') or file_path.startswith('Alt.md'):
        return 'pointers/'
    elif any(x in file_path for x in ['_LOOP_GATE', '_SESSION', '_BOOTSTRAP', '_KNOWLEDGE_TASK']):
        return 'system/'
    else:
        return 'root/'

def analyze_reference_failures(db):
    """Analyze failures where DB claims references to non-existent files."""
    failures = []

    # Check reports for broken refs
    reports = db.conn.execute('SELECT id, refs FROM reports WHERE refs IS NOT NULL').fetchall()
    for report in reports:
        if report[1]:
            refs = json.loads(report[1])
            for ref in refs:
                if not ref.startswith('[ref:'):
                    continue
                ref_path = ref.split('|')[0][5:-1].split('#')[0]  # Extract file path
                if ref_path.startswith('reports/'):
                    full_path = Path('.') / ref_path
                    if not full_path.exists():
                        failures.append(f"REPORT {report[0]} -> {ref_path} (missing)")
                elif ref_path.startswith('tasks/'):
                    full_path = Path('.') / ref_path
                    if not full_path.exists():
                        failures.append(f"REPORT {report[0]} -> {ref_path} (missing)")

    return failures

def analyze_connectivity(db):
    """Analyze network connectivity following mega.md depth-first approach."""
    # This is a simplified connectivity analysis
    # In a full implementation, this would build a graph and analyze components

    connectivity = {
        'total_nodes': 0,
        'components': 1,  # Simplified
        'avg_branching': 0.0,
        'isolated_nodes': 0
    }

    # Count total entities
    tables = ['reports', 'tasks', 'archives', 'docs', 'lessons']
    for table in tables:
        try:
            count = db.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            connectivity['total_nodes'] += count
        except:
            pass

    # Estimate branching factor from reference relationships
    ref_count = db.conn.execute('SELECT COUNT(*) FROM reference_relationships').fetchone()[0]
    if connectivity['total_nodes'] > 0:
        connectivity['avg_branching'] = ref_count / connectivity['total_nodes']

    return connectivity

def generate_recommendations(file_stats, ref_failures, connectivity):
    """Generate recommendations based on analysis."""
    recommendations = []

    failure_rate = file_stats['files_missing'] / file_stats['total_db_entries'] if file_stats['total_db_entries'] > 0 else 0

    if failure_rate > 0.1:
        recommendations.append(f"CRITICAL: {failure_rate:.1%} of DB entries reference missing files - rebuild database")

    if ref_failures:
        recommendations.append(f"Fix {len(ref_failures)} broken references in content")

    if connectivity['avg_branching'] < 5:
        recommendations.append(f"Increase connectivity - current branching factor {connectivity['avg_branching']:.1f} < target 5.0")

    if connectivity['isolated_nodes'] > 0:
        recommendations.append(f"Connect {connectivity['isolated_nodes']} isolated nodes to improve network")

    recommendations.append("Add file_path column to all tables for explicit file tracking")
    recommendations.append("Implement automated reference validation in rebuild process")

    return recommendations

if __name__ == '__main__':
    analyze_file_db_mapping()