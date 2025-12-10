# SPDX-License-Identifier: PROPRIETARY
"""Correlation Matrix Engine for heatmap visualization."""
from typing import Dict

import structlog

logger = structlog.get_logger("visual.correlation_matrix")


class CorrelationMatrixEngine:
    """Generates correlation matrix data for heatmap visualization."""

    def __init__(self):
        """Initialize correlation matrix engine."""
        self.index_order = [
            "economic_stress",
            "environmental_stress",
            "mobility_activity",
            "digital_attention",
            "public_health_stress",
            "political_stress",
            "crime_stress",
            "misinformation_stress",
            "social_cohesion_stress",
        ]

    def generate_matrix(
        self,
        correlation_data: Dict[str, Dict[str, float]],
        method: str = "pearson",
    ) -> Dict:
        """
        Generate correlation matrix in heatmap-friendly format.

        Args:
            correlation_data: Nested dictionary of correlations
            method: Correlation method used (for metadata)

        Returns:
            Dictionary with matrix data and metadata
        """
        # Build matrix
        matrix = []
        labels = []

        # Use index order if available, otherwise use keys from correlation_data
        available_indices = [
            idx for idx in self.index_order if idx in correlation_data
        ] or list(correlation_data.keys())

        for index1 in available_indices:
            row = []
            for index2 in available_indices:
                if index1 == index2:
                    row.append(1.0)  # Self-correlation
                elif index2 in correlation_data.get(index1, {}):
                    row.append(float(correlation_data[index1][index2]))
                elif index1 in correlation_data.get(index2, {}):
                    row.append(float(correlation_data[index2][index1]))
                else:
                    row.append(0.0)  # No correlation data
            matrix.append(row)
            labels.append(index1.replace("_", " ").title())

        # Generate color mapping metadata
        color_scheme = {
            "strong_positive": {"min": 0.7, "max": 1.0, "color": "#8b0000"},  # Dark red
            "moderate_positive": {
                "min": 0.3,
                "max": 0.7,
                "color": "#ff6b6b",
            },  # Light red
            "weak_positive": {
                "min": 0.0,
                "max": 0.3,
                "color": "#ffcccc",
            },  # Very light red
            "neutral": {"min": -0.1, "max": 0.1, "color": "#ffffff"},  # White
            "weak_negative": {
                "min": -0.3,
                "max": 0.0,
                "color": "#cce5ff",
            },  # Very light blue
            "moderate_negative": {
                "min": -0.7,
                "max": -0.3,
                "color": "#6b9fff",
            },  # Light blue
            "strong_negative": {
                "min": -1.0,
                "max": -0.7,
                "color": "#00008b",
            },  # Dark blue
        }

        return {
            "matrix": matrix,
            "labels": labels,
            "method": method,
            "color_scheme": color_scheme,
            "min_value": -1.0,
            "max_value": 1.0,
            "size": len(available_indices),
        }
