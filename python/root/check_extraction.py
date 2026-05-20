#!/usr/bin/env python3
from context_dreamer import ContextDreamer

dreamer = ContextDreamer()
# Check what references are extracted for a file that mentions FEATURE_VALIDATION
test_file = 'report_TASK_0129_L71_v01.md'
if test_file in dreamer.network_graph:
    analysis = dreamer.network_graph[test_file]
    print(f'File: {test_file}')
    print(f'References: {analysis.get("references", [])}')
    print(f'Mentions: {analysis.get("mentions", [])}')
    print(f'Content preview length: {len(analysis.get("content_preview", ""))}')
else:
    print(f'File {test_file} not in network graph')