from pathlib import Path
from loop_cockpit import KnowledgeDBEventHandler

report_path = Path('reports') / 'report_TASK_0081_L60_v01.md'
print('Report exists:', report_path.exists())
KnowledgeDBEventHandler.on_report_created(report_path)
print('Indexed report:', report_path)
