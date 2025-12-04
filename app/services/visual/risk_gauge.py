# SPDX-License-Identifier: PROPRIETARY
"""Risk Gauge Engine for dial/meter visualization."""
from typing import Dict, Optional

import structlog

logger = structlog.get_logger("visual.risk_gauge")


class RiskGaugeEngine:
    """Generates risk gauge data for dial/meter visualization."""

    # Risk tier boundaries
    TIER_BOUNDARIES = {
        "stable": {"min": 0.0, "max": 0.3, "color": "#00ff00", "label": "Stable"},
        "watchlist": {"min": 0.3, "max": 0.5, "color": "#ffff00", "label": "Watchlist"},
        "elevated": {"min": 0.5, "max": 0.7, "color": "#ff8800", "label": "Elevated"},
        "high": {"min": 0.7, "max": 0.85, "color": "#ff0000", "label": "High"},
        "critical": {"min": 0.85, "max": 1.0, "color": "#8800ff", "label": "Critical"},
    }

    def __init__(self):
        """Initialize risk gauge engine."""
        pass

    def generate_gauge_data(
        self,
        risk_score: float,
        risk_tier: Optional[str] = None,
    ) -> Dict:
        """
        Generate gauge data for risk visualization.

        Args:
            risk_score: Risk score (0.0-1.0)
            risk_tier: Optional risk tier string (auto-determined if not provided)

        Returns:
            Dictionary with gauge visualization data
        """
        # Ensure risk_score is in valid range
        risk_score = max(0.0, min(1.0, risk_score))

        # Determine tier if not provided
        if risk_tier is None:
            risk_tier = self._determine_tier(risk_score)

        # Get tier metadata
        tier_meta = self.TIER_BOUNDARIES.get(risk_tier, self.TIER_BOUNDARIES["stable"])

        # Calculate pointer angle (0-180 degrees for half-circle gauge)
        # 0 = left (low risk), 180 = right (high risk)
        pointer_angle = risk_score * 180.0

        # Calculate pointer position (normalized 0-1)
        pointer_position = risk_score

        # Generate color zones for the gauge
        zones = []
        for tier_name, tier_data in self.TIER_BOUNDARIES.items():
            zone_start = tier_data["min"] * 180.0
            zone_end = tier_data["max"] * 180.0
            zones.append(
                {
                    "tier": tier_name,
                    "label": tier_data["label"],
                    "color": tier_data["color"],
                    "start_angle": zone_start,
                    "end_angle": zone_end,
                    "start_position": tier_data["min"],
                    "end_position": tier_data["max"],
                }
            )

        return {
            "risk_score": float(risk_score),
            "risk_tier": risk_tier,
            "pointer_angle": float(pointer_angle),
            "pointer_position": float(pointer_position),
            "current_color": tier_meta["color"],
            "zones": zones,
            "max_value": 1.0,
            "min_value": 0.0,
        }

    def _determine_tier(self, risk_score: float) -> str:
        """Determine risk tier from score."""
        if risk_score >= 0.85:
            return "critical"
        elif risk_score >= 0.7:
            return "high"
        elif risk_score >= 0.5:
            return "elevated"
        elif risk_score >= 0.3:
            return "watchlist"
        else:
            return "stable"
