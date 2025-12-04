# SPDX-License-Identifier: PROPRIETARY
"""Scenario Simulation Engine.

Allows hypothetical scenario testing by modifying index values.
"""
from typing import Dict, Optional

import pandas as pd
import structlog

from app.core.behavior_index import BehaviorIndexComputer

logger = structlog.get_logger("simulation.engine")


class SimulationEngine:
    """Simulates scenarios with modified index values."""

    def __init__(self):
        """Initialize simulation engine."""
        pass

    def simulate_scenario(
        self,
        base_history_df: pd.DataFrame,
        index_modifiers: Dict[str, float],
        region_name: str,
    ) -> Dict:
        """
        Simulate a scenario with modified index values.

        Args:
            base_history_df: Base historical data
            index_modifiers: Dictionary mapping index names to modification factors
                            (e.g., 1.2 = 20% increase, 0.8 = 20% decrease)
            region_name: Region name for the simulation

        Returns:
            Dictionary with simulation results
        """
        # Create modified DataFrame
        modified_df = base_history_df.copy()

        # Apply modifiers to latest values
        for index_name, modifier in index_modifiers.items():
            if index_name in modified_df.columns:
                # Apply modifier to latest value
                if len(modified_df) > 0:
                    latest_idx = modified_df.index[-1]
                    current_value = modified_df.loc[latest_idx, index_name]
                    if not pd.isna(current_value):
                        new_value = current_value * modifier
                        # Clip to valid range
                        new_value = max(0.0, min(1.0, new_value))
                        modified_df.loc[latest_idx, index_name] = new_value

        # Recalculate behavior index with modified values
        index_computer = BehaviorIndexComputer()
        result_df = index_computer.compute_behavior_index(modified_df)

        # Get projected behavior index
        if len(result_df) > 0:
            projected_behavior_index = float(result_df["behavior_index"].iloc[-1])
        else:
            projected_behavior_index = 0.5

        # Calculate changes
        if len(base_history_df) > 0 and len(result_df) > 0:
            base_behavior_index = float(
                base_history_df.get("behavior_index", pd.Series([0.5])).iloc[-1]
            )
            behavior_index_change = projected_behavior_index - base_behavior_index
        else:
            base_behavior_index = 0.5
            behavior_index_change = 0.0

        result = {
            "region_name": region_name,
            "modified_indices": index_modifiers,
            "base_behavior_index": float(base_behavior_index),
            "projected_behavior_index": float(projected_behavior_index),
            "behavior_index_change": float(behavior_index_change),
            "modified_values": {
                idx: float(modified_df[idx].iloc[-1])
                for idx in index_modifiers.keys()
                if idx in modified_df.columns
            },
        }

        logger.info(
            "Scenario simulation completed",
            region=region_name,
            modifiers=index_modifiers,
            projected_bi=projected_behavior_index,
        )

        return result
