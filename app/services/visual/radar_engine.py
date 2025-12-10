# SPDX-License-Identifier: PROPRIETARY
"""Radar/Spider Chart Engine for behavioral fingerprints."""
from typing import Dict

import numpy as np
import structlog

logger = structlog.get_logger("visual.radar")


class RadarEngine:
    """Generates radar/spider chart data for behavioral fingerprints."""

    def __init__(self):
        """Initialize radar engine."""
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

    def generate_radar_data(
        self,
        state_indices: Dict[str, float],
        normalize: bool = True,
    ) -> Dict:
        """
        Generate radar chart data for a state.

        Args:
            state_indices: Dictionary mapping index names to values
            normalize: Whether to normalize values to 0-1 range

        Returns:
            Dictionary with radar chart data including values and metadata
        """
        values = []

        for index_name in self.index_order:
            if index_name in state_indices:
                value = state_indices[index_name]
                if value is not None:
                    if normalize:
                        # Already should be 0-1, but ensure it
                        value = float(np.clip(value, 0.0, 1.0))
                    values.append(value)
                else:
                    values.append(0.0)  # Default to 0 if missing
            else:
                values.append(0.0)  # Default to 0 if missing

        # Invariant: Radar vector length must equal number of indices (9)
        # Ensure values array has exactly 9 elements (one per index)
        if len(values) != len(self.index_order):
            logger.warning(
                "Radar values length mismatch",
                values_length=len(values),
                expected_length=len(self.index_order),
            )
            # Pad with zeros or truncate to match expected length
            while len(values) < len(self.index_order):
                values.append(0.0)
            values = values[: len(self.index_order)]

        # Calculate polygon coordinates (for frontend rendering)
        # This is a simplified version - frontend will handle actual rendering
        num_indices = len(self.index_order)
        angle_step = 2 * np.pi / num_indices

        coordinates = []
        for i, value in enumerate(values):
            angle = i * angle_step - np.pi / 2  # Start at top
            x = value * np.cos(angle)
            y = value * np.sin(angle)
            coordinates.append({"x": float(x), "y": float(y), "value": value})

        return {
            "values": values,
            "indices": self.index_order,
            "coordinates": coordinates,
            "max_value": 1.0,
            "min_value": 0.0,
        }

    def generate_multi_state_radar(
        self, states_data: Dict[str, Dict[str, float]]
    ) -> Dict:
        """
        Generate radar data for multiple states.

        Args:
            states_data: Dictionary mapping state names to their index values

        Returns:
            Dictionary with radar data for each state
        """
        radar_data = {}

        for state_name, state_indices in states_data.items():
            radar_data[state_name] = self.generate_radar_data(state_indices)

        logger.info("Multi-state radar data generated", states=len(radar_data))

        return radar_data
