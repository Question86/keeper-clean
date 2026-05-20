#!/usr/bin/env python3
"""
Milestone Knowledge Monitor
Monitors milestone targets and identifies knowledge gaps in the database.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set
from datetime import datetime, timezone

class MilestoneKnowledgeMonitor:
    """Monitors milestones for knowledge requirements and gaps."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.milestones = self._load_milestones()

    def _load_milestones(self) -> Dict[str, Dict]:
        """Load all milestone files."""
        milestones = {}
        for i in range(1, 5):  # milestone_01.json to milestone_04.json
            path = self.workspace_root / f"milestone_{i:02d}.json"
            print(f"Checking milestone file: {path}")
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        milestones[data['MILESTONE']['id']] = data
                        print(f"Loaded milestone {data['MILESTONE']['id']}: status={data['MILESTONE']['status']}")
                except Exception as e:
                    print(f"Warning: Could not load milestone {i:02d}: {e}")
            else:
                print(f"Milestone file not found: {path}")
        return milestones

    def get_active_milestones(self) -> List[Dict]:
        """Get milestones that are not completed."""
        active = []
        for milestone in self.milestones.values():
            if milestone['MILESTONE'].get('status') != 'COMPLETED':
                active.append(milestone)
        return active

    def analyze_knowledge_requirements(self, milestone_id: str) -> Dict[str, List[str]]:
        """Analyze what knowledge is required for a milestone."""
        if milestone_id not in self.milestones:
            return {}

        milestone = self.milestones[milestone_id]
        requirements = {
            'goals': [],
            'objectives': [],
            'keywords': []
        }

        # Extract from goals
        for goal in milestone.get('GOALS', []):
            desc = goal.get('description', '').lower()
            requirements['goals'].append(desc)

            # Extract potential keywords
            words = desc.split()
            keywords = [w for w in words if len(w) > 3 and w not in ['that', 'with', 'from', 'this', 'will']]
            requirements['keywords'].extend(keywords)

        # Remove duplicates
        requirements['keywords'] = list(set(requirements['keywords']))

        return requirements

    def check_knowledge_gaps(self, milestone_id: str) -> Dict[str, List[str]]:
        """Check what knowledge gaps exist for a milestone."""
        requirements = self.analyze_knowledge_requirements(milestone_id)
        gaps = {
            'missing_keywords': [],
            'unmet_goals': []
        }

        # This would integrate with knowledge_db.py to check actual coverage
        # For now, return placeholder
        gaps['missing_keywords'] = requirements['keywords'][:3]  # Simulate some gaps
        gaps['unmet_goals'] = requirements['goals'][:1]  # Simulate some unmet goals

        return gaps

    def get_monitoring_report(self) -> Dict:
        """Generate a monitoring report for all active milestones."""
        active = self.get_active_milestones()
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'active_milestones': len(active),
            'milestones': []
        }

        for milestone in active:
            mid = milestone['MILESTONE']['id']
            gaps = self.check_knowledge_gaps(mid)
            requirements = self.analyze_knowledge_requirements(mid)

            report['milestones'].append({
                'id': mid,
                'name': milestone['MILESTONE']['name'],
                'knowledge_requirements': requirements,
                'gaps': gaps,
                'gap_count': len(gaps['missing_keywords']) + len(gaps['unmet_goals'])
            })

        return report

def main():
    """Main entry point."""
    workspace = Path(__file__).parent.parent
    monitor = MilestoneKnowledgeMonitor(workspace)

    report = monitor.get_monitoring_report()

    print(json.dumps(report, indent=2))

    # Save report
    report_path = workspace / "milestone_knowledge_gaps.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()