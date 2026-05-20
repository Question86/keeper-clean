#!/usr/bin/env python3
"""
Knowledge Dependency Analyzer

Analyzes knowledge requirements and dependencies for strategic task planning.
"""

import json
import sqlite3
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
import networkx as nx
from datetime import datetime, timedelta

class KnowledgeDependencyAnalyzer:
    """
    Analyzes knowledge dependencies and requirements for task planning.
    """

    def __init__(self, db_path: str = "keeper_knowledge.db", max_items: int = 300):
        self.db_path = db_path
        self.max_items = max_items
        self.knowledge_graph = nx.DiGraph()
        self.task_dependencies = defaultdict(list)
        self.knowledge_requirements = defaultdict(set)

    def analyze_knowledge_landscape(self) -> Dict:
        """
        Perform comprehensive analysis of the knowledge landscape.
        """
        # Get all knowledge items
        knowledge_items = self._get_knowledge_items()

        # Analyze categories and tags
        category_analysis = self._analyze_categories(knowledge_items)
        tag_analysis = self._analyze_tags(knowledge_items)

        # Build knowledge graph
        self._build_knowledge_graph(knowledge_items)

        # Identify knowledge gaps
        gaps = self._identify_knowledge_gaps(knowledge_items)

        # Calculate knowledge readiness scores
        readiness_scores = self._calculate_readiness_scores(knowledge_items)

        return {
            'total_items': len(knowledge_items),
            'categories': category_analysis,
            'tags': tag_analysis,
            'knowledge_graph': self._graph_summary(),
            'gaps': gaps,
            'readiness_scores': readiness_scores,
            'analysis_timestamp': datetime.now().isoformat()
        }

    def _get_knowledge_items(self) -> List[Dict]:
        """Retrieve all knowledge items from database across all tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Query all knowledge tables with their specific column structures
            all_items = []

            # DOCS table
            try:
                cursor.execute("""
                    SELECT id, path, title, category, tags, substr(content_full, 1, 2000), indexed_at
                    FROM docs
                    ORDER BY indexed_at DESC
                """)
                for row in cursor.fetchall():
                    all_items.append({
                        'id': row[0],
                        'path': row[1],
                        'title': row[2] or row[1],
                        'category': row[3] or 'documentation',
                        'tags': row[4].split(',') if row[4] else [],
                        'content': row[5] or '',
                        'indexed_at': row[6],
                        'source_table': 'docs'
                    })
            except Exception as e:
                print(f"Warning: Could not query docs table: {e}")

            # REPORTS table
            try:
                cursor.execute("""
                    SELECT id, path, goal, tags, substr(content_full, 1, 2000), indexed_at, task_id
                    FROM reports
                    ORDER BY indexed_at DESC
                """)
                for row in cursor.fetchall():
                    all_items.append({
                        'id': row[0],
                        'path': row[1],
                        'title': f"Report: {row[6]}" if row[6] else row[1],  # Use task_id as title
                        'category': 'reports',
                        'tags': row[3].split(',') if row[3] else [],
                        'content': row[4] or '',
                        'indexed_at': row[5],
                        'source_table': 'reports'
                    })
            except Exception as e:
                print(f"Warning: Could not query reports table: {e}")

            # TASKS table
            try:
                cursor.execute("""
                    SELECT id, path, objective, tags, indexed_at, status
                    FROM tasks
                    ORDER BY indexed_at DESC
                """)
                for row in cursor.fetchall():
                    all_items.append({
                        'id': row[0],
                        'path': row[1],
                        'title': row[2] or row[1],  # Use objective as title
                        'category': 'tasks',
                        'tags': row[3].split(',') if row[3] else [],
                        'content': row[2] or '',  # Use objective as content
                        'indexed_at': row[4],
                        'source_table': 'tasks'
                    })
            except Exception as e:
                print(f"Warning: Could not query tasks table: {e}")

            # CODE table
            try:
                cursor.execute("""
                    SELECT id, path, title, category, tags, substr(content_full, 1, 2000), indexed_at
                    FROM code
                    ORDER BY indexed_at DESC
                """)
                for row in cursor.fetchall():
                    all_items.append({
                        'id': row[0],
                        'path': row[1],
                        'title': row[2] or row[1],
                        'category': row[3] or 'code',
                        'tags': row[4].split(',') if row[4] else [],
                        'content': row[5] or '',
                        'indexed_at': row[6],
                        'source_table': 'code'
                    })
            except Exception as e:
                print(f"Warning: Could not query code table: {e}")

            # BUGS table
            try:
                cursor.execute("""
                    SELECT id, path, title, severity, tags, substr(content_full, 1, 2000), indexed_at
                    FROM bugs
                    ORDER BY indexed_at DESC
                """)
                for row in cursor.fetchall():
                    all_items.append({
                        'id': row[0],
                        'path': row[1],
                        'title': row[2] or row[1],
                        'category': 'bugs',
                        'tags': ([row[3]] if row[3] else []) + (row[4].split(',') if row[4] else []),
                        'content': row[5] or '',
                        'indexed_at': row[6],
                        'source_table': 'bugs'
                    })
            except Exception as e:
                print(f"Warning: Could not query bugs table: {e}")

            # ARCHIVES table
            try:
                cursor.execute("""
                    SELECT id, path, summary, lessons_learned, substr(content_full, 1, 2000), indexed_at, loop_num
                    FROM archives
                    ORDER BY indexed_at DESC
                """)
                for row in cursor.fetchall():
                    all_items.append({
                        'id': row[0],
                        'path': row[1],
                        'title': f"Archive L{row[6]}" if row[6] else row[1],
                        'category': 'archives',
                        'tags': [],
                        'content': row[4] or row[2] or row[3] or '',
                        'indexed_at': row[5],
                        'source_table': 'archives'
                    })
            except Exception as e:
                print(f"Warning: Could not query archives table: {e}")

            # LESSONS table
            try:
                cursor.execute("""
                    SELECT id, source_type, source_id, lesson_text, category, indexed_at, loop_num
                    FROM lessons
                    ORDER BY indexed_at DESC
                """)
                for row in cursor.fetchall():
                    all_items.append({
                        'id': f"lesson_{row[0]}",
                        'path': f"lessons/lesson_{row[0]}.md",
                        'title': f"Lesson L{row[6]}: {row[2]}" if row[2] else f"Lesson {row[0]}",
                        'category': row[4] or 'lessons',
                        'tags': [row[1]] if row[1] else [],  # source_type as tag
                        'content': row[3] or '',
                        'indexed_at': row[5],
                        'source_table': 'lessons'
                    })
            except Exception as e:
                print(f"Warning: Could not query lessons table: {e}")

            conn.close()
            if self.max_items and len(all_items) > self.max_items:
                return all_items[: self.max_items]
            return all_items

        except Exception as e:
            print(f"Error retrieving knowledge items: {e}")
            return []

    def _analyze_categories(self, items: List[Dict]) -> Dict:
        """Analyze knowledge distribution across categories."""
        categories = defaultdict(lambda: {'count': 0, 'tags': set(), 'avg_length': 0, 'freshness': []})

        for item in items:
            cat = item.get('category') or 'uncategorized'
            categories[cat]['count'] += 1
            categories[cat]['tags'].update(item['tags'])
            categories[cat]['avg_length'] += len(item['content'])
            categories[cat]['freshness'].append(item['indexed_at'])

        # Calculate averages and freshness scores
        for cat_data in categories.values():
            if cat_data['count'] > 0:
                cat_data['avg_length'] = cat_data['avg_length'] / cat_data['count']
                cat_data['freshness_score'] = self._calculate_category_freshness(cat_data['freshness'])
                cat_data['tags'] = list(cat_data['tags'])

        return dict(categories)

    def _analyze_tags(self, items: List[Dict]) -> Dict:
        """Analyze knowledge distribution across tags."""
        tags = defaultdict(lambda: {'count': 0, 'categories': set(), 'items': []})

        for item in items:
            for tag in item['tags']:
                tags[tag]['count'] += 1
                tags[tag]['categories'].add(item.get('category') or 'uncategorized')
                tags[tag]['items'].append(item['id'])

        # Convert sets to lists
        for tag_data in tags.values():
            tag_data['categories'] = list(tag_data['categories'])

        return dict(tags)

    def _build_knowledge_graph(self, items: List[Dict]):
        """Build a graph representing knowledge relationships."""
        # Add nodes
        for item in items:
            self.knowledge_graph.add_node(item['id'],
                                        title=item['title'],
                                        category=item.get('category'),
                                        tags=item['tags'])

        # Add edges based on content references and semantic relationships
        for item in items:
            content = item['content'].lower()

            # Find references to other items
            for other_item in items:
                if item['id'] != other_item['id']:
                    # Check for title mentions
                    if other_item['title'].lower() in content:
                        self.knowledge_graph.add_edge(item['id'], other_item['id'],
                                                    type='reference', weight=1)

                    # Check for tag overlaps (semantic connections)
                    common_tags = set(item['tags']) & set(other_item['tags'])
                    if common_tags:
                        self.knowledge_graph.add_edge(item['id'], other_item['id'],
                                                    type='semantic',
                                                    weight=len(common_tags) * 0.5)

    def _graph_summary(self) -> Dict:
        """Generate summary of knowledge graph."""
        # Calculate clustering coefficient with timeout protection
        clustering = 0.0

        def calculate_clustering():
            nonlocal clustering
            try:
                clustering = nx.average_clustering(self.knowledge_graph)
            except Exception:
                clustering = 0.0

        # Use threading for cross-platform timeout
        import threading

        clustering_thread = threading.Thread(target=calculate_clustering)
        clustering_thread.daemon = True
        clustering_thread.start()
        clustering_thread.join(timeout=3.0)  # 3 second timeout

        # If thread is still alive, calculation timed out
        if clustering_thread.is_alive():
            print("Warning: Graph clustering calculation timed out, using default value")
            clustering = 0.0

        return {
            'nodes': self.knowledge_graph.number_of_nodes(),
            'edges': self.knowledge_graph.number_of_edges(),
            'density': nx.density(self.knowledge_graph),
            'connected_components': nx.number_connected_components(self.knowledge_graph.to_undirected()),
            'average_clustering': clustering
        }

    def _identify_knowledge_gaps(self, items: List[Dict]) -> List[Dict]:
        """Identify gaps in knowledge coverage."""
        gaps = []

        # Category balance analysis
        categories = defaultdict(int)
        for item in items:
            categories[item.get('category') or 'uncategorized'] += 1

        total_items = len(items)
        avg_per_category = total_items / len(categories) if categories else 0

        for cat, count in categories.items():
            if count < avg_per_category * 0.5:  # Less than 50% of average
                gaps.append({
                    'type': 'category_underrepresentation',
                    'category': cat,
                    'current_count': count,
                    'expected_count': avg_per_category,
                    'severity': 'medium'
                })

        # Tag connectivity gaps
        isolated_tags = []
        for tag, data in self._analyze_tags(items).items():
            if data['count'] == 1:  # Only one item with this tag
                isolated_tags.append(tag)

        if isolated_tags:
            gaps.append({
                'type': 'isolated_knowledge',
                'tags': isolated_tags,
                'description': f"{len(isolated_tags)} tags have only one associated item",
                'severity': 'low'
            })

        # Graph connectivity gaps
        undirected_graph = self.knowledge_graph.to_undirected()
        if not nx.is_connected(undirected_graph):
            components = list(nx.connected_components(undirected_graph))
            small_components = [comp for comp in components if len(comp) < 3]
            if small_components:
                gaps.append({
                    'type': 'connectivity_gaps',
                    'small_components': len(small_components),
                    'description': f"{len(small_components)} small disconnected knowledge clusters",
                    'severity': 'medium'
                })

        return gaps

    def _calculate_readiness_scores(self, items: List[Dict]) -> Dict:
        """Calculate knowledge readiness scores for different domains."""
        readiness = {}

        # Category readiness
        for cat, data in self._analyze_categories(items).items():
            # Factors: count, freshness, connectivity
            count_score = min(data['count'] / 10, 1.0)  # Scale to 10+ items
            freshness_score = data.get('freshness_score', 0.5)

            # Connectivity score (based on graph centrality)
            cat_nodes = [node for node, attrs in self.knowledge_graph.nodes(data=True)
                        if attrs.get('category') == cat]
            if cat_nodes:
                subgraph = self.knowledge_graph.subgraph(cat_nodes)
                connectivity_score = nx.density(subgraph) if subgraph.number_of_nodes() > 1 else 0
            else:
                connectivity_score = 0

            readiness[cat] = {
                'overall_score': (count_score + freshness_score + connectivity_score) / 3,
                'count_score': count_score,
                'freshness_score': freshness_score,
                'connectivity_score': connectivity_score
            }

        return readiness

    def _calculate_category_freshness(self, timestamps: List[str]) -> float:
        """Calculate freshness score for a category."""
        if not timestamps:
            return 0.0

        now = datetime.now()
        scores = []

        for ts in timestamps:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                days_old = (now - dt).days

                # Freshness score: 1.0 for < 30 days, decreasing to 0.0 for > 365 days
                if days_old < 30:
                    score = 1.0
                elif days_old < 90:
                    score = 0.8
                elif days_old < 180:
                    score = 0.6
                elif days_old < 365:
                    score = 0.4
                else:
                    score = 0.2

                scores.append(score)
            except:
                scores.append(0.5)  # Default for parsing errors

        return sum(scores) / len(scores) if scores else 0.0

    def analyze_task_requirements(self, task_description: str) -> Dict:
        """
        Analyze knowledge requirements for a potential task.
        """
        requirements = {
            'required_categories': set(),
            'required_tags': set(),
            'estimated_complexity': 'unknown',
            'knowledge_gaps': [],
            'readiness_score': 0.0
        }

        # Simple keyword-based analysis (could be enhanced with ML)
        desc_lower = task_description.lower()

        # Category detection
        category_keywords = {
            'implementation': ['implement', 'code', 'develop', 'build', 'create'],
            'analysis': ['analyze', 'assess', 'evaluate', 'review', 'study'],
            'documentation': ['document', 'write', 'describe', 'explain'],
            'planning': ['plan', 'strategy', 'design', 'architect'],
            'testing': ['test', 'validate', 'verify', 'check'],
            'optimization': ['optimize', 'improve', 'enhance', 'performance']
        }

        for cat, keywords in category_keywords.items():
            if any(keyword in desc_lower for keyword in keywords):
                requirements['required_categories'].add(cat)

        # Tag detection
        tag_keywords = {
            'python': ['python', 'script', 'module'],
            'database': ['database', 'sql', 'query', 'table'],
            'api': ['api', 'endpoint', 'rest', 'http'],
            'ui': ['ui', 'interface', 'dashboard', 'frontend'],
            'ai': ['ai', 'machine learning', 'ml', 'model'],
            'testing': ['test', 'unittest', 'pytest']
        }

        for tag, keywords in tag_keywords.items():
            if any(keyword in desc_lower for keyword in keywords):
                requirements['required_tags'].add(tag)

        # Estimate complexity
        complexity_indicators = {
            'high': ['complex', 'advanced', 'sophisticated', 'multi-system'],
            'medium': ['moderate', 'standard', 'typical', 'integration'],
            'low': ['simple', 'basic', 'straightforward', 'single']
        }

        for level, indicators in complexity_indicators.items():
            if any(ind in desc_lower for ind in indicators):
                requirements['estimated_complexity'] = level
                break

        # Calculate readiness score based on available knowledge
        landscape = self.analyze_knowledge_landscape()

        cat_readiness = sum(landscape['readiness_scores'].get(cat, {'overall_score': 0})['overall_score']
                          for cat in requirements['required_categories']) / max(len(requirements['required_categories']), 1)

        tag_coverage = len([tag for tag in requirements['required_tags']
                          if tag in landscape['tags']]) / max(len(requirements['required_tags']), 1)

        requirements['readiness_score'] = (cat_readiness + tag_coverage) / 2

        # Identify gaps
        missing_cats = requirements['required_categories'] - set(landscape['readiness_scores'].keys())
        missing_tags = requirements['required_tags'] - set(landscape['tags'].keys())

        if missing_cats:
            requirements['knowledge_gaps'].append(f"Missing categories: {', '.join(missing_cats)}")
        if missing_tags:
            requirements['knowledge_gaps'].append(f"Missing tags: {', '.join(missing_tags)}")

        return requirements

    def generate_planning_recommendations(self) -> List[Dict]:
        """
        Generate strategic planning recommendations based on analysis.
        """
        landscape = self.analyze_knowledge_landscape()
        recommendations = []

        # Category balancing recommendations
        categories = landscape['categories']
        avg_count = sum(cat['count'] for cat in categories.values()) / len(categories)

        for cat_name, cat_data in categories.items():
            if cat_data['count'] < avg_count * 0.7:
                recommendations.append({
                    'type': 'knowledge_expansion',
                    'category': cat_name,
                    'description': f"Expand knowledge in '{cat_name}' category (currently {cat_data['count']} items, below average)",
                    'priority': 'medium',
                    'estimated_effort': 'high'
                })

        # Connectivity improvement recommendations
        graph_data = landscape['knowledge_graph']
        if graph_data['density'] < 0.1:
            recommendations.append({
                'type': 'connectivity_improvement',
                'description': f"Improve knowledge connectivity (current density: {graph_data['density']:.3f})",
                'priority': 'low',
                'estimated_effort': 'medium'
            })

        # Freshness maintenance recommendations
        stale_categories = [cat for cat, data in categories.items()
                          if data.get('freshness_score', 1.0) < 0.6]
        if stale_categories:
            recommendations.append({
                'type': 'freshness_update',
                'categories': stale_categories,
                'description': f"Update stale knowledge in categories: {', '.join(stale_categories)}",
                'priority': 'high',
                'estimated_effort': 'medium'
            })

        return recommendations


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze knowledge dependencies with bounded workload.")
    parser.add_argument("--max-items", type=int, default=300, help="Maximum items sampled for analysis.")
    args = parser.parse_args()

    analyzer = KnowledgeDependencyAnalyzer(max_items=args.max_items)
    landscape = analyzer.analyze_knowledge_landscape()

    print("Knowledge Landscape Analysis:")
    print(f"Total items: {landscape['total_items']}")
    print(f"Categories: {len(landscape['categories'])}")
    print(f"Knowledge gaps: {len(landscape['gaps'])}")
    print(f"Graph density: {landscape['knowledge_graph']['density']:.3f}")

    # Test task requirements analysis
    test_task = "Implement a machine learning model for user behavior prediction"
    requirements = analyzer.analyze_task_requirements(test_task)
    print(f"\nTask Requirements Analysis for: {test_task}")
    print(f"Required categories: {requirements['required_categories']}")
    print(f"Required tags: {requirements['required_tags']}")
    print(f"Readiness score: {requirements['readiness_score']:.2f}")
    print(f"Knowledge gaps: {requirements['knowledge_gaps']}")

    recommendations = analyzer.generate_planning_recommendations()
    print(f"\nPlanning Recommendations: {len(recommendations)}")
    for rec in recommendations[:3]:  # Show first 3
        print(f"- {rec['type']}: {rec['description']}")
