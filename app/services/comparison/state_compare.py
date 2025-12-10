# SPDX-License-Identifier: PROPRIETARY
"""State Comparison Engine for side-by-side analysis."""
from typing import Dict, Optional

import pandas as pd
import structlog

from app.services.visual.radar_engine import RadarEngine
from app.services.visual.trend_engine import TrendEngine

logger = structlog.get_logger("comparison.state_compare")


class StateComparisonEngine:
    """Compares two states across all metrics."""

    def __init__(self):
        """Initialize state comparison engine."""
        self.radar_engine = RadarEngine()
        self.trend_engine = TrendEngine()

    def compare_states(
        self,
        state_a_data: Dict,
        state_b_data: Dict,
        state_a_name: str,
        state_b_name: str,
        state_a_history: Optional[pd.DataFrame] = None,
        state_b_history: Optional[pd.DataFrame] = None,
    ) -> Dict:
        """
        Compare two states across all metrics.

        Args:
            state_a_data: Latest index values for state A
            state_b_data: Latest index values for state B
            state_a_name: Name of state A
            state_b_name: Name of state B
            state_a_history: Historical data for state A (optional)
            state_b_history: Historical data for state B (optional)

        Returns:
            Dictionary with comprehensive comparison data
        """
        indices = [
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

        # Extract index values
        state_a_indices = {idx: state_a_data.get(idx, 0.0) for idx in indices}
        state_b_indices = {idx: state_b_data.get(idx, 0.0) for idx in indices}

        # Calculate differences
        differences = {}
        winners = {}
        for idx in indices:
            val_a = state_a_indices.get(idx, 0.0)
            val_b = state_b_indices.get(idx, 0.0)
            diff = val_a - val_b
            differences[idx] = {
                "state_a_value": float(val_a),
                "state_b_value": float(val_b),
                "difference": float(diff),
                "absolute_difference": float(abs(diff)),
                "percent_difference": float((diff / val_b * 100) if val_b > 0 else 0.0),
            }

            # Determine winner (for stress indices, lower is better;
            # for activity, higher is better)
            if "activity" in idx or "attention" in idx:
                # Higher is better
                winners[idx] = state_a_name if val_a > val_b else state_b_name
            else:
                # Lower is better (stress indices)
                winners[idx] = state_a_name if val_a < val_b else state_b_name

        # Generate radar data
        radar_a = self.radar_engine.generate_radar_data(state_a_indices)
        radar_b = self.radar_engine.generate_radar_data(state_b_indices)

        # Calculate trends if history available
        trends_a = {}
        trends_b = {}
        if state_a_history is not None and not state_a_history.empty:
            trends_a = self.trend_engine.calculate_trends(state_a_history)
        if state_b_history is not None and not state_b_history.empty:
            trends_b = self.trend_engine.calculate_trends(state_b_history)

        # Compare risk tiers
        risk_a = state_a_data.get("risk_tier", {})
        risk_b = state_b_data.get("risk_tier", {})

        risk_comparison = {
            "state_a": {
                "tier": (
                    risk_a.get("tier", "stable")
                    if isinstance(risk_a, dict)
                    else "stable"
                ),
                "risk_score": (
                    risk_a.get("risk_score", 0.5) if isinstance(risk_a, dict) else 0.5
                ),
            },
            "state_b": {
                "tier": (
                    risk_b.get("tier", "stable")
                    if isinstance(risk_b, dict)
                    else "stable"
                ),
                "risk_score": (
                    risk_b.get("risk_score", 0.5) if isinstance(risk_b, dict) else 0.5
                ),
            },
        }

        # Compare behavior index
        behavior_index_a = state_a_data.get("behavior_index", 0.5)
        behavior_index_b = state_b_data.get("behavior_index", 0.5)
        behavior_index_diff = behavior_index_a - behavior_index_b

        # Overall winner (lower behavior index is better)
        overall_winner = (
            state_a_name if behavior_index_a < behavior_index_b else state_b_name
        )

        return {
            "state_a": state_a_name,
            "state_b": state_b_name,
            "differences": differences,
            "winners": winners,
            "overall_winner": overall_winner,
            "radar_data": {
                "state_a": radar_a,
                "state_b": radar_b,
            },
            "trends": {
                "state_a": trends_a,
                "state_b": trends_b,
            },
            "risk_comparison": risk_comparison,
            "behavior_index": {
                "state_a": float(behavior_index_a),
                "state_b": float(behavior_index_b),
                "difference": float(behavior_index_diff),
            },
            "summary": {
                "indices_compared": len(indices),
                "state_a_better": sum(
                    1 for idx, winner in winners.items() if winner == state_a_name
                ),
                "state_b_better": sum(
                    1 for idx, winner in winners.items() if winner == state_b_name
                ),
            },
        }
