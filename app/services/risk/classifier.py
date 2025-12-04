# SPDX-License-Identifier: PROPRIETARY
"""State Risk Tier Classification System.

Classifies regions into risk tiers based on behavioral indices.
"""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger("risk.classifier")


class RiskClassifier:
    """Classifies regions into risk tiers."""

    # Risk tier thresholds
    TIER_THRESHOLDS = {
        "stable": 0.0,
        "watchlist": 0.3,
        "elevated": 0.5,
        "high": 0.7,
        "critical": 0.85,
    }

    def __init__(self):
        """Initialize risk classifier."""
        pass

    def classify_risk(
        self,
        behavior_index: float,
        shock_events: Optional[List[Dict]] = None,
        convergence_score: Optional[float] = None,
        trend_direction: Optional[str] = None,
    ) -> Dict:
        """
        Classify risk tier based on multiple factors.

        Args:
            behavior_index: Current behavior index value (0.0-1.0)
            shock_events: List of recent shock events
            convergence_score: Convergence score from CICE (0-100)
            trend_direction: Trend direction ('increasing', 'decreasing', 'stable')

        Returns:
            Dictionary with risk classification
        """
        if shock_events is None:
            shock_events = []
        if convergence_score is None:
            convergence_score = 0.0

        # Validate and sanitize inputs
        try:
            behavior_index = float(behavior_index)
            if pd.isna(behavior_index) or not (0.0 <= behavior_index <= 1.0):
                behavior_index = 0.5
            behavior_index = max(0.0, min(1.0, behavior_index))
        except (TypeError, ValueError):
            behavior_index = 0.5

        try:
            convergence_score = float(convergence_score)
            if pd.isna(convergence_score):
                convergence_score = 0.0
            convergence_score = max(0.0, min(100.0, convergence_score))
        except (TypeError, ValueError):
            convergence_score = 0.0

        # Base risk from behavior index
        base_risk = behavior_index

        # Adjust for shock events
        shock_adjustment = self._calculate_shock_adjustment(shock_events)

        # Adjust for convergence
        convergence_adjustment = self._calculate_convergence_adjustment(
            convergence_score
        )

        # Adjust for trend
        trend_adjustment = self._calculate_trend_adjustment(trend_direction)

        # Calculate final risk score
        final_risk = (
            base_risk + shock_adjustment + convergence_adjustment + trend_adjustment
        )
        final_risk = max(0.0, min(1.0, final_risk))  # Clip to [0, 1]

        # Determine tier
        tier = self._determine_tier(final_risk)

        # Get contributing factors
        contributing_factors = self._get_contributing_factors(
            behavior_index, shock_events, convergence_score, trend_direction
        )

        result = {
            "tier": tier,
            "risk_score": float(final_risk),
            "base_risk": float(base_risk),
            "shock_adjustment": float(shock_adjustment),
            "convergence_adjustment": float(convergence_adjustment),
            "trend_adjustment": float(trend_adjustment),
            "contributing_factors": contributing_factors,
        }

        logger.info(
            "Risk classification completed",
            tier=tier,
            risk_score=final_risk,
            behavior_index=behavior_index,
        )

        return result

    def _calculate_shock_adjustment(self, shock_events: List[Dict]) -> float:
        """Calculate risk adjustment from shock events."""
        if not shock_events:
            return 0.0

        # Weight shocks by severity
        severity_weights = {
            "mild": 0.05,
            "moderate": 0.10,
            "high": 0.15,
            "severe": 0.25,
        }

        adjustment = 0.0
        for shock in shock_events:
            severity = shock.get("severity", "mild")
            weight = severity_weights.get(severity, 0.05)
            adjustment += weight

        # Cap adjustment at 0.3
        return min(adjustment, 0.3)

    def _calculate_convergence_adjustment(self, convergence_score: float) -> float:
        """Calculate risk adjustment from convergence score."""
        # High convergence (multiple indices moving together) increases risk
        # Normalize convergence score (0-100) to adjustment (-0.1 to +0.2)
        normalized = convergence_score / 100.0
        adjustment = (normalized - 0.5) * 0.4  # Center at 0, scale to ±0.2

        return float(np.clip(adjustment, -0.1, 0.2))

    def _calculate_trend_adjustment(self, trend_direction: Optional[str]) -> float:
        """Calculate risk adjustment from trend direction."""
        if trend_direction == "increasing":
            return 0.1
        elif trend_direction == "decreasing":
            return -0.05
        else:
            return 0.0

    def _determine_tier(self, risk_score: float) -> str:
        """Determine risk tier from risk score."""
        if risk_score >= self.TIER_THRESHOLDS["critical"]:
            return "critical"
        elif risk_score >= self.TIER_THRESHOLDS["high"]:
            return "high"
        elif risk_score >= self.TIER_THRESHOLDS["elevated"]:
            return "elevated"
        elif risk_score >= self.TIER_THRESHOLDS["watchlist"]:
            return "watchlist"
        else:
            return "stable"

    def _get_contributing_factors(
        self,
        behavior_index: float,
        shock_events: List[Dict],
        convergence_score: float,
        trend_direction: Optional[str],
    ) -> List[str]:
        """Get list of contributing factors to risk classification."""
        factors = []

        if behavior_index >= 0.7:
            factors.append("high_behavior_index")
        elif behavior_index >= 0.5:
            factors.append("moderate_behavior_index")

        if shock_events:
            severe_shocks = [
                s for s in shock_events if s.get("severity") in ["high", "severe"]
            ]
            if severe_shocks:
                factors.append(f"{len(severe_shocks)}_severe_shocks")
            else:
                factors.append(f"{len(shock_events)}_shocks")

        if convergence_score >= 70:
            factors.append("high_convergence")

        if trend_direction == "increasing":
            factors.append("increasing_trend")

        return factors
