# SPDX-License-Identifier: PROPRIETARY
"""Shock Timeline Engine for chronological shock visualization."""
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import structlog

logger = structlog.get_logger("visual.shock_timeline")


class ShockTimelineEngine:
    """Generates timeline data for shock event visualization."""

    def __init__(self):
        """Initialize shock timeline engine."""
        self.severity_colors = {
            "mild": "#ffff00",  # Yellow
            "moderate": "#ff8800",  # Orange
            "high": "#ff0000",  # Red
            "severe": "#880000",  # Dark Red
        }

    def generate_timeline(
        self,
        shock_events: List[Dict],
        group_by_severity: bool = True,
    ) -> Dict:
        """
        Generate timeline data from shock events.

        Args:
            shock_events: List of shock event dictionaries
            group_by_severity: Whether to group events by severity

        Returns:
            Dictionary with timeline data
        """
        if not shock_events:
            return {"events": [], "grouped": {}, "total_events": 0}

        # Sort events by timestamp
        sorted_events = sorted(
            shock_events, key=lambda x: x.get("timestamp", ""), reverse=False
        )

        # Format events for timeline
        timeline_events = []
        for event in sorted_events:
            severity = event.get("severity", "mild")
            timeline_events.append(
                {
                    "timestamp": event.get("timestamp"),
                    "index": event.get("index"),
                    "severity": severity,
                    "delta": event.get("delta", 0.0),
                    "value": event.get("value"),
                    "color": self.severity_colors.get(severity, "#cccccc"),
                    "intensity": self._get_intensity(severity),
                }
            )

        # Group by severity if requested
        grouped = {}
        if group_by_severity:
            for severity in ["mild", "moderate", "high", "severe"]:
                grouped[severity] = [
                    e for e in timeline_events if e["severity"] == severity
                ]

        # Group by index
        by_index = {}
        for event in timeline_events:
            index_name = event["index"]
            if index_name not in by_index:
                by_index[index_name] = []
            by_index[index_name].append(event)

        return {
            "events": timeline_events,
            "grouped_by_severity": grouped,
            "grouped_by_index": by_index,
            "total_events": len(timeline_events),
            "date_range": {
                "start": timeline_events[0]["timestamp"] if timeline_events else None,
                "end": timeline_events[-1]["timestamp"] if timeline_events else None,
            },
        }

    def _get_intensity(self, severity: str) -> float:
        """Get intensity value for severity (0-1)."""
        intensity_map = {
            "mild": 0.25,
            "moderate": 0.5,
            "high": 0.75,
            "severe": 1.0,
        }
        return intensity_map.get(severity, 0.5)
