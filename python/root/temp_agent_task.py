from local_mistral_agent import LocalMistralAgent
agent = LocalMistralAgent()
search_fix_task = '''
I need you to FIX the database search system. The current query_db.py is shit - it only does keyword matching, no context, no metadata, no semantic search.

CURRENT PROBLEMS:
- Only FTS keyword search, no semantic understanding
- No contextual snippets from files
- Missing metadata (file dates, sizes, tags, versions)
- Truncated summaries without full content
- No relevance ranking beyond basic FTS scores
- Search results lack actionable development context

EXISTING CODE (query_db.py):
```python
import sys
import sqlite3
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print('Usage: python query_db.py <query terms...>')
        sys.exit(1)

    query = ' '.join(sys.argv[1:])

    workspace_root = Path(__file__).parent
    db_path = workspace_root / 'keeper_knowledge.db'

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        fts_tables = ['reports_fts', 'archives_fts', 'docs_fts']
        all_results = []

        for fts_table in fts_tables:
            try:
                base_table = fts_table.replace('_fts', '')

                if fts_table == 'reports_fts':
                    fts_query = '''
SELECT d.id as title, d.path as file_path, 'report' as type,
d.task_id, d.loop_num as loop_number, d.goal as summary,
highlight(reports_fts, 0, '<mark>', '</mark>') as highlighted_content,
rank
FROM reports_fts
JOIN reports d ON reports_fts.id = d.id
WHERE reports_fts MATCH ?
ORDER BY rank
LIMIT 5
'''
                elif fts_table == 'docs_fts':
                    fts_query = '''
SELECT d.id as title, d.path as file_path, 'doc' as type,
'' as task_id, 0 as loop_number, d.title as summary,
highlight(docs_fts, 0, '<mark>', '</mark>') as highlighted_content,
rank
FROM docs_fts
JOIN docs d ON docs_fts.id = d.id
WHERE docs_fts MATCH ?
ORDER BY rank
LIMIT 5
'''
                else:
                    continue

                cursor.execute(fts_query, (query,))
                results = cursor.fetchall()
                all_results.extend(results)
            except Exception as e:
                continue

        all_results.sort(key=lambda x: x[7])
        results = all_results[:10]

        print(f'Search results for: "{query}"')
        print(f'Found {len(results)} results:')
        print('-' * 50)

        for i, (title, file_path, doc_type, task_id, loop_number, summary, highlighted, rank) in enumerate(results, 1):
            print(f'{i}. {title}')
            print(f'   Type: {doc_type}')
            print(f'   File: {file_path}')
            if task_id:
                print(f'   Task: {task_id}')
            if loop_number:
                print(f'   Loop: {loop_number}')
            print(f'   Relevance: {rank:.3f}')
            print(f'   Summary: {summary[:200]}...')
            print()

    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()
```

REQUIRED IMPROVEMENTS:
1. Add semantic search using local embeddings (Ollama Mistral for zero-cost)
2. Include full metadata (file paths, timestamps, sizes, tags, versions, authors)
3. Provide contextual snippets (3-5 lines before/after matches from actual files)
4. Implement relevance scoring combining keyword + semantic similarity
5. Add search result caching and performance optimization
6. Support advanced queries (boolean, fuzzy, date ranges)
7. Integrate with existing rate limit framework

TASK: Generate the COMPLETE improved query_db.py with all these features. Include:
- Semantic search using local Ollama embeddings
- Full metadata extraction
- Contextual file content extraction
- Better relevance ranking
- Caching mechanisms
- Error handling and fallbacks
- Performance optimizations

Make it production-ready with proper error handling, logging, and documentation.
'''
print(agent.generate(search_fix_task))