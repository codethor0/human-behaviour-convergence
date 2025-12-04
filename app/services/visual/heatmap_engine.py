# SPDX-License-Identifier: PROPRIETARY
"""Heatmap Engine for generating visualization-ready heatmap data."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger("visual.heatmap")


class HeatmapEngine:
    """Generates heatmap data for all indices across states."""

    def __init__(self):
        """Initialize heatmap engine."""
        pass

    def generate_heatmap(
        self,
        state_data: Dict[str, Dict],
        indices: Optional[List[str]] = None,
    ) -> Dict:
        """
        Generate heatmap data for all states and indices.

        Args:
            state_data: Dictionary mapping state names to their latest index values
                       Format: {"Minnesota": {"political_stress": 0.44, "crime_stress": 0.39, ...}, ...}
            indices: List of index names to include (default: all 9 indices)

        Returns:
            Dictionary with heatmap data for each index
        """
        if indices is None:
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

        heatmap_data = {}

        # Generate heatmap for each index
        for index_name in indices:
            index_map = {}
            for state_name, state_indices in state_data.items():
                if not state_indices or not isinstance(state_indices, dict):
                    continue
                if index_name in state_indices:
                    value = state_indices[index_name]
                    if value is not None:
                        try:
                            # Normalize to 0-1 range and clip
                            value_float = float(value)
                            if not np.isnan(value_float) and np.isfinite(value_float):
                                normalized_value = float(np.clip(value_float, 0.0, 1.0))
                                index_map[state_name] = normalized_value
                        except (TypeError, ValueError, OverflowError):
                            continue

            if index_map:
                heatmap_data[index_name] = index_map

        # Generate overall behavior index heatmap (if behavior_index present)
        behavior_index_map = {}
        for state_name, state_indices in state_data.items():
            if not state_indices or not isinstance(state_indices, dict):
                continue
            if "behavior_index" in state_indices:
                value = state_indices["behavior_index"]
                if value is not None:
                    try:
                        value_float = float(value)
                        if not np.isnan(value_float) and np.isfinite(value_float):
                            behavior_index_map[state_name] = float(
                                np.clip(value_float, 0.0, 1.0)
                            )
                    except (TypeError, ValueError, OverflowError):
                        pass
            # Also try to compute from sub-indices if behavior_index not present
            elif all(idx in state_indices for idx in indices):
                try:
                    # Simple average as fallback (actual behavior index uses weighted sum)
                    values = []
                    for idx in indices:
                        val = state_indices.get(idx)
                        if val is not None:
                            try:
                                val_float = float(val)
                                if not np.isnan(val_float) and np.isfinite(val_float):
                                    values.append(val_float)
                            except (TypeError, ValueError):
                                continue
                    if values:
                        avg_value = np.mean(values)
                        behavior_index_map[state_name] = float(
                            np.clip(avg_value, 0.0, 1.0)
                        )
                except Exception:
                    continue

        if behavior_index_map:
            heatmap_data["overall_behavior"] = behavior_index_map

        # Add color coding metadata
        heatmap_data["_metadata"] = {
            "color_scheme": {
                "low": {"min": 0.0, "max": 0.33, "color": "#00ff00"},  # Green
                "moderate": {"min": 0.33, "max": 0.67, "color": "#ffff00"},  # Yellow
                "high": {"min": 0.67, "max": 1.0, "color": "#ff0000"},  # Red
            },
            "indices": indices,
            "states_count": len(state_data),
        }

        logger.info(
            "Heatmap generated",
            indices=len(heatmap_data),
            states=len(state_data),
        )

        return heatmap_data

    def generate_timeseries_heatmap(
        self,
        timeseries_data: Dict[str, pd.DataFrame],
        indices: Optional[List[str]] = None,
    ) -> Dict:
        """
        Generate time-series heatmap data for animation.

        Args:
            timeseries_data: Dictionary mapping state names to DataFrames with time-series data
            indices: List of index names to include

        Returns:
            Dictionary with time-series heatmap frames
        """
        if indices is None:
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

        frames = []

        # Get all unique timestamps
        all_timestamps = set()
        for state_df in timeseries_data.values():
            if "timestamp" in state_df.columns:
                all_timestamps.update(state_df["timestamp"].unique())

        all_timestamps = sorted(list(all_timestamps))

        # Generate frame for each timestamp
        for timestamp in all_timestamps:
            frame_data = {"timestamp": str(timestamp), "states": {}}

            for state_name, state_df in timeseries_data.items():
                if "timestamp" in state_df.columns:
                    # Get data for this timestamp
                    row = state_df[state_df["timestamp"] == timestamp]
                    if not row.empty:
                        state_values = {}
                        for index_name in indices:
                            if index_name in row.columns:
                                value = row[index_name].iloc[0]
                                if pd.notna(value):
                                    state_values[index_name] = float(
                                        np.clip(value, 0.0, 1.0)
                                    )

                        if state_values:
                            frame_data["states"][state_name] = state_values

            if frame_data["states"]:
                frames.append(frame_data)

        return {"frames": frames, "total_frames": len(frames)}
