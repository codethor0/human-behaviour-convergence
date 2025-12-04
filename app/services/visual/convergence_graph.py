# SPDX-License-Identifier: PROPRIETARY
"""Convergence Graph Engine for network visualization."""
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger("visual.convergence_graph")


class ConvergenceGraphEngine:
    """Generates network graph data for index convergence visualization."""

    def __init__(self, correlation_threshold: float = 0.3):
        """
        Initialize convergence graph engine.

        Args:
            correlation_threshold: Minimum correlation to include an edge (default: 0.3)
        """
        self.correlation_threshold = correlation_threshold

    def generate_graph(
        self,
        correlation_matrix: Dict[str, Dict[str, float]],
        convergence_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate network graph structure from correlations.

        Args:
            correlation_matrix: Nested dictionary of correlations
                {index1: {index2: corr}}
            convergence_data: Optional convergence analysis data

        Returns:
            Dictionary with nodes and edges for graph visualization
        """
        # Extract all unique indices (nodes)
        nodes = set()
        for index1 in correlation_matrix.keys():
            nodes.add(index1)
            for index2 in correlation_matrix[index1].keys():
                nodes.add(index2)

        nodes = sorted(list(nodes))

        # Create node list with metadata
        node_list = []
        for node in nodes:
            node_data = {
                "id": node,
                "label": node.replace("_", " ").title(),
                "group": self._get_index_group(node),
            }
            node_list.append(node_data)

        # Create edge list from correlations (deduplicate)
        edges = []
        edge_pairs = set()  # Track (source, target) pairs to avoid duplicates
        for index1 in correlation_matrix.keys():
            for index2, correlation in correlation_matrix[index1].items():
                if index1 != index2 and abs(correlation) >= self.correlation_threshold:
                    # Use sorted pair to ensure uniqueness
                    pair = tuple(sorted([index1, index2]))
                    if pair not in edge_pairs:
                        edge_pairs.add(pair)
                        edge = {
                            "source": index1,
                            "target": index2,
                            "weight": float(abs(correlation)),
                            "correlation": float(correlation),
                            "direction": "positive" if correlation > 0 else "negative",
                            "strength": (
                                "strong"
                                if abs(correlation) > 0.7
                                else "moderate" if abs(correlation) > 0.5 else "weak"
                            ),
                        }
                        edges.append(edge)

        # Sort edges by weight (strongest first)
        edges.sort(key=lambda x: x["weight"], reverse=True)

        # Add convergence metadata if available
        metadata = {}
        if convergence_data:
            metadata["convergence_score"] = convergence_data.get("score", 0.0)
            metadata["reinforcing_count"] = len(
                convergence_data.get("reinforcing_signals", [])
            )
            metadata["conflicting_count"] = len(
                convergence_data.get("conflicting_signals", [])
            )

        return {
            "nodes": node_list,
            "edges": edges,
            "metadata": metadata,
            "total_nodes": len(node_list),
            "total_edges": len(edges),
        }

    def _get_index_group(self, index_name: str) -> str:
        """Categorize index into a group for visualization."""
        if "economic" in index_name or "mobility" in index_name:
            return "economic"
        elif "environmental" in index_name:
            return "environmental"
        elif "health" in index_name:
            return "health"
        elif "political" in index_name or "crime" in index_name:
            return "social"
        elif "misinformation" in index_name or "digital" in index_name:
            return "information"
        elif "social" in index_name or "cohesion" in index_name:
            return "social"
        else:
            return "other"
