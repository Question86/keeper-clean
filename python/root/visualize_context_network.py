#!/usr/bin/env python3
"""
Context Network Visualization

Visualizes the neural network of context dreaming connectivity patterns.
Shows document relationships, connectivity strength, and dreaming evolution.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import networkx as nx
from datetime import datetime
import numpy as np

class ContextNetworkVisualizer:
    """
    Visualizes context dreaming network connectivity patterns.
    """

    def __init__(self, workspace_root: str = "."):
        self.workspace = Path(workspace_root)
        self.context_profiles = self._load_context_profiles()
        self.graph = self._build_network_graph()

        # Visualization settings
        self.node_colors = plt.cm.viridis
        self.edge_colors = plt.cm.plasma
        self.fig_size = (12, 8)

    def _load_context_profiles(self) -> Dict:
        """
        Load context profiles from JSON file.
        """
        profile_file = self.workspace / "context_profiles.json"
        if profile_file.exists():
            with open(profile_file, 'r') as f:
                return json.load(f)
        return {}

    def _build_network_graph(self) -> nx.Graph:
        """
        Build NetworkX graph from context profiles.
        """
        G = nx.Graph()

        # Add nodes
        for file_path, profile in self.context_profiles.items():
            node_attrs = {
                'stickiness': profile.get('A_stickiness', 0),
                'significance': profile.get('B_significance', 0),
                'complexity': profile.get('C_complexity', 0),
                'connections': profile.get('connections', 0),
                'last_updated': profile.get('last_updated', ''),
                'file_type': self._get_file_type(file_path)
            }
            G.add_node(file_path, **node_attrs)

        # Add edges based on connectivity
        # This is a simplified version - in practice, you'd use actual connectivity data
        nodes = list(G.nodes())
        for i, node1 in enumerate(nodes):
            for node2 in nodes[i+1:]:
                # Calculate edge weight based on profile similarity
                weight = self._calculate_connectivity_weight(G.nodes[node1], G.nodes[node2])
                if weight > 0.1:  # Threshold for visualization
                    G.add_edge(node1, node2, weight=weight)

        return G

    def _get_file_type(self, file_path: str) -> str:
        """
        Determine file type from path.
        """
        if file_path.endswith('.py'):
            return 'python'
        elif file_path.endswith('.md'):
            return 'markdown'
        elif file_path.endswith('.json'):
            return 'json'
        else:
            return 'other'

    def _calculate_connectivity_weight(self, node1_attrs: Dict, node2_attrs: Dict) -> float:
        """
        Calculate connectivity weight between two nodes.
        """
        # Simple similarity-based weight
        stickiness_diff = abs(node1_attrs['stickiness'] - node2_attrs['stickiness'])
        significance_diff = abs(node1_attrs['significance'] - node2_attrs['significance'])
        complexity_diff = abs(node1_attrs['complexity'] - node2_attrs['complexity'])

        # Normalize and combine
        weight = 1.0 / (1.0 + stickiness_diff + significance_diff + complexity_diff)
        return weight

    def visualize_network(self, save_path: Optional[str] = None, show_plot: bool = True):
        """
        Create static network visualization.

        Args:
            save_path: Path to save the visualization
            show_plot: Whether to display the plot
        """
        if not self.graph.nodes():
            print("No network data available for visualization")
            return

        plt.figure(figsize=self.fig_size)

        # Calculate node sizes based on significance
        node_sizes = [self.graph.nodes[node]['significance'] * 100 + 50 for node in self.graph.nodes()]

        # Calculate node colors based on connectivity
        node_colors = [self.graph.nodes[node]['connections'] for node in self.graph.nodes()]

        # Calculate edge weights
        edges = self.graph.edges()
        edge_weights = [self.graph[u][v]['weight'] * 2 for u, v in edges]

        # Create layout
        pos = nx.spring_layout(self.graph, k=1, iterations=50, seed=42)

        # Draw nodes
        nodes = nx.draw_networkx_nodes(
            self.graph, pos,
            node_size=node_sizes,
            node_color=node_colors,
            cmap=self.node_colors,
            alpha=0.7
        )

        # Draw edges
        edges = nx.draw_networkx_edges(
            self.graph, pos,
            width=edge_weights,
            edge_color=edge_weights,
            edge_cmap=self.edge_colors,
            alpha=0.5
        )

        # Draw labels for important nodes
        important_nodes = sorted(
            self.graph.nodes(),
            key=lambda x: self.graph.nodes[x]['significance'],
            reverse=True
        )[:10]  # Top 10 nodes

        labels = {node: Path(node).name for node in important_nodes}
        nx.draw_networkx_labels(self.graph, pos, labels, font_size=8, font_weight='bold')

        plt.title("Context Dreaming Network Visualization\n" +
                 f"Nodes: {len(self.graph.nodes())}, Edges: {len(self.graph.edges())}",
                 fontsize=14, pad=20)
        plt.axis('off')

        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=self.node_colors)
        sm.set_array(node_colors)
        cbar = plt.colorbar(sm, ax=plt.gca(), shrink=0.8)
        cbar.set_label('Connectivity Strength')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to: {save_path}")

        if show_plot:
            plt.show()
        else:
            plt.close()

    def visualize_evolution(self, iterations_data: List[Dict], save_path: Optional[str] = None):
        """
        Create evolution timeline visualization.

        Args:
            iterations_data: List of iteration data
            save_path: Path to save animation
        """
        if not iterations_data:
            print("No evolution data available")
            return

        fig, ax = plt.subplots(figsize=self.fig_size)

        def animate(frame):
            ax.clear()
            iteration = iterations_data[frame]

            # Update graph with iteration data
            # This would need actual iteration tracking data
            # For now, show static with iteration info

            pos = nx.spring_layout(self.graph, seed=42)
            nx.draw(self.graph, pos, with_labels=False, node_size=50,
                   node_color='lightblue', ax=ax)

            ax.set_title(f"Context Dreaming Evolution - Iteration {frame + 1}")
            ax.axis('off')

        anim = animation.FuncAnimation(
            fig, animate, frames=len(iterations_data),
            interval=1000, repeat=True
        )

        if save_path:
            anim.save(save_path, writer='pillow', fps=1)
            print(f"Evolution animation saved to: {save_path}")

        plt.show()

    def generate_connectivity_report(self) -> Dict:
        """
        Generate connectivity analysis report.
        """
        if not self.graph.nodes():
            return {"error": "No network data available"}

        # Calculate network metrics
        metrics = {
            'total_nodes': len(self.graph.nodes()),
            'total_edges': len(self.graph.edges()),
            'average_degree': sum(dict(self.graph.degree()).values()) / len(self.graph.nodes()),
            'connected_components': nx.number_connected_components(self.graph),
            'average_clustering': nx.average_clustering(self.graph),
            'network_density': nx.density(self.graph)
        }

        # Node analysis
        node_analysis = {}
        for node in self.graph.nodes():
            node_analysis[node] = {
                'degree': self.graph.degree(node),
                'clustering': nx.clustering(self.graph, node),
                'significance': self.graph.nodes[node]['significance'],
                'connections': self.graph.nodes[node]['connections']
            }

        # Top nodes by different metrics
        top_by_degree = sorted(node_analysis.items(),
                             key=lambda x: x[1]['degree'], reverse=True)[:5]
        top_by_significance = sorted(node_analysis.items(),
                                   key=lambda x: x[1]['significance'], reverse=True)[:5]

        return {
            'metrics': metrics,
            'node_analysis': node_analysis,
            'top_by_degree': top_by_degree,
            'top_by_significance': top_by_significance,
            'timestamp': datetime.now().isoformat()
        }

def main():
    """
    Main visualization execution.
    """
    print("Context Network Visualizer")
    print("=" * 40)

    visualizer = ContextNetworkVisualizer()

    # Generate static visualization
    print("Generating network visualization...")
    visualizer.visualize_network(
        save_path="context_network_visualization.png",
        show_plot=False
    )

    # Generate connectivity report
    print("Generating connectivity report...")
    report = visualizer.generate_connectivity_report()

    # Save report
    report_file = "connectivity_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Connectivity report saved to: {report_file}")

    # Print summary
    if 'metrics' in report:
        metrics = report['metrics']
        print("\nNetwork Summary:")
        print(f"  • Nodes: {metrics['total_nodes']}")
        print(f"  • Edges: {metrics['total_edges']}")
        print(f"  • Average Degree: {metrics['average_degree']:.2f}")
        print(f"  • Connected Components: {metrics['connected_components']}")
        print(f"  • Network Density: {metrics['network_density']:.4f}")

    print("\n✅ Visualization complete!")

if __name__ == "__main__":
    main()