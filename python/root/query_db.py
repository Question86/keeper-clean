import sys
import sqlite3
from pathlib import Path
import os
from datetime import datetime
from local_mistral_agent import LocalMistralAgent

def get_file_context(file_path, query_terms, max_context=3):
    """Extract context around query terms from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        context_lines = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(term.lower() in line_lower for term in query_terms):
                # Get context around the match
                start = max(0, i - max_context)
                end = min(len(lines), i + max_context + 1)
                context = lines[start:end]
                context_lines.extend(context)
        
        # Remove duplicates and limit
        unique_context = []
        seen = set()
        for line in context_lines:
            if line.strip() and line.strip() not in seen:
                unique_context.append(line.strip())
                seen.add(line.strip())
        
        return '\n'.join(unique_context[:10])  # Limit to 10 lines
    except Exception:
        return "Could not extract context"

def get_file_metadata(file_path):
    """Get file metadata."""
    try:
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'exists': True
        }
    except Exception:
        return {
            'size': 0,
            'modified': 'Unknown',
            'exists': False
        }

def enhance_query_with_semantic(query):
    """Use local Mistral agent to enhance query with semantic understanding."""
    try:
        agent = LocalMistralAgent()
        prompt = f"Given the search query '{query}', provide 3-5 related search terms. Output format: term1 term2 term3 (space separated, no quotes, no explanations)"
        enhanced = agent.generate(prompt, max_tokens=50)
        if enhanced and not enhanced.startswith("Error"):
            # Clean up the response - split on spaces and filter valid terms
            terms = enhanced.strip().split()
            # Filter out non-word terms and limit to reasonable number
            valid_terms = [t for t in terms if t.isalnum() and len(t) > 2][:5]
            if valid_terms:
                # For FTS, we need OR syntax for multiple terms
                or_terms = ' OR '.join([query] + valid_terms)
                return or_terms
        return query
    except Exception:
        return query
        return query
    except Exception:
        return query

def main():
    if len(sys.argv) < 2:
        print("Usage: python query_db.py <query terms...>")
        sys.exit(1)

    # Join all arguments as the query
    query = " ".join(sys.argv[1:])

    # Enhance query with semantic understanding
    print(f"Original query: '{query}'")
    enhanced_query = enhance_query_with_semantic(query)
    print(f"Enhanced query: '{enhanced_query}'")
    # For context extraction, split on OR and use individual terms
    enhanced_terms = [t.strip() for t in enhanced_query.replace(' OR ', ' ').split() if t.strip()]

    # Connect to the database
    workspace_root = Path(__file__).parent
    db_path = workspace_root / "keeper_knowledge.db"

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Search across all FTS tables
        fts_tables = ['reports_fts', 'archives_fts', 'lessons_fts', 'docs_fts', 'patterns_fts', 'tasks_fts', 'bugs_fts', 'code_fts', 'json_content_fts']
        all_results = []

        for fts_table in fts_tables:
            try:
                # Get table name without _fts suffix
                base_table = fts_table.replace('_fts', '')

                if fts_table == 'reports_fts':
                    fts_query = f"""
                    SELECT d.id as title, d.path as file_path, 'report' as type,
                           d.task_id, d.loop_num as loop_number, d.goal as summary,
                           highlight(reports_fts, 0, '<mark>', '</mark>') as highlighted_content,
                           rank
                    FROM reports_fts
                    JOIN reports d ON reports_fts.id = d.id
                    WHERE reports_fts MATCH ?
                    ORDER BY rank
                    LIMIT 5
                    """
                elif fts_table == 'archives_fts':
                    fts_query = f"""
                    SELECT d.id as title, d.path as file_path, 'archive' as type,
                           '' as task_id, d.loop_num as loop_number, d.summary,
                           highlight(archives_fts, 0, '<mark>', '</mark>') as highlighted_content,
                           rank
                    FROM archives_fts
                    JOIN archives d ON archives_fts.id = d.id
                    WHERE archives_fts MATCH ?
                    ORDER BY rank
                    LIMIT 5
                    """
                elif fts_table == 'docs_fts':
                    fts_query = f"""
                    SELECT d.id as title, d.path as file_path, 'doc' as type,
                           '' as task_id, 0 as loop_number, d.title as summary,
                           highlight(docs_fts, 0, '<mark>', '</mark>') as highlighted_content,
                           rank
                    FROM docs_fts
                    JOIN docs d ON docs_fts.id = d.id
                    WHERE docs_fts MATCH ?
                    ORDER BY rank
                    LIMIT 5
                    """
                elif fts_table == 'tasks_fts':
                    fts_query = f"""
                    SELECT d.id as title, d.path as file_path, 'task' as type,
                           d.id as task_id, 0 as loop_number, d.objective as summary,
                           highlight(tasks_fts, 0, '<mark>', '</mark>') as highlighted_content,
                           rank
                    FROM tasks_fts
                    JOIN tasks d ON tasks_fts.id = d.id
                    WHERE tasks_fts MATCH ?
                    ORDER BY rank
                    LIMIT 5
                    """
                elif fts_table == 'bugs_fts':
                    fts_query = f"""
                    SELECT d.id as title, d.path as file_path, 'bug' as type,
                           d.task_id, d.loop_num as loop_number, d.title as summary,
                           highlight(bugs_fts, 0, '<mark>', '</mark>') as highlighted_content,
                           rank
                    FROM bugs_fts
                    JOIN bugs d ON bugs_fts.id = d.id
                    WHERE bugs_fts MATCH ?
                    ORDER BY rank
                    LIMIT 5
                    """
                elif fts_table == 'code_fts':
                    fts_query = f"""
                    SELECT d.id as title, d.path as file_path, 'code' as type,
                           d.task_id, d.loop_num as loop_number, d.title as summary,
                           highlight(code_fts, 0, '<mark>', '</mark>') as highlighted_content,
                           rank
                    FROM code_fts
                    JOIN code d ON code_fts.id = d.id
                    WHERE code_fts MATCH ?
                    ORDER BY rank
                    LIMIT 5
                    """
                elif fts_table == 'json_content_fts':
                    fts_query = f"""
                    SELECT d.id as title, d.path as file_path, 'json' as type,
                           '' as task_id, 0 as loop_number, d.title as summary,
                           highlight(json_content_fts, 0, '<mark>', '</mark>') as highlighted_content,
                           rank
                    FROM json_content_fts
                    JOIN json_content d ON json_content_fts.id = d.id
                    WHERE json_content_fts MATCH ?
                    ORDER BY rank
                    LIMIT 5
                    """
                else:
                    # Skip tables without proper id columns or different structure
                    continue

                cursor.execute(fts_query, (enhanced_query,))
                results = cursor.fetchall()
                all_results.extend(results)
            except Exception as e:
                # Skip tables that don't exist or have issues
                continue

        # Sort by rank and limit to top 10
        all_results.sort(key=lambda x: x[7])  # rank is at index 7
        results = all_results[:10]

        print(f"Search results for: '{enhanced_query}'")
        print(f"Found {len(results)} results:")
        print("-" * 80)

        for i, (title, file_path, doc_type, task_id, loop_number, summary, highlighted, rank) in enumerate(results, 1):
            # Get full file path - handle different directory structures
            if doc_type == 'report':
                full_path = workspace_root / 'reports' / file_path
            elif doc_type == 'archive':
                full_path = workspace_root / 'archive' / file_path
            elif doc_type == 'doc':
                full_path = workspace_root / 'docs' / file_path
            elif doc_type == 'task':
                full_path = workspace_root / 'tasks' / file_path
            elif doc_type == 'bug':
                full_path = workspace_root / 'bugs' / file_path
            elif doc_type == 'code':
                full_path = workspace_root / 'code' / file_path
            elif doc_type == 'json':
                full_path = workspace_root / file_path
            else:
                full_path = workspace_root / file_path
            
            # If not found, try direct path
            if not full_path.exists():
                full_path = workspace_root / file_path
            
            # Get metadata
            metadata = get_file_metadata(full_path)
            
            # Get context
            context = get_file_context(full_path, enhanced_terms)
            
            print(f"{i}. {title}")
            print(f"   Type: {doc_type}")
            print(f"   File: {file_path}")
            if task_id:
                print(f"   Task: {task_id}")
            if loop_number:
                print(f"   Loop: {loop_number}")
            print(f"   Relevance: {rank:.3f}")
            print(f"   Modified: {metadata['modified']}")
            print(f"   Size: {metadata['size']} bytes")
            print(f"   Summary: {summary}")
            if highlighted:
                print(f"   Highlighted: {highlighted[:200]}...")
            if context:
                print(f"   Context:")
                for line in context.split('\n')[:5]:  # Show first 5 context lines
                    print(f"     {line}")
            print()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()