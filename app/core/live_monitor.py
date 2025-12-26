# SPDX-License-Identifier: PROPRIETARY
"""Live monitoring module for near real-time behavior index tracking.

This module maintains a rolling window of behavior index snapshots per region
and detects major events that could impact human behavior scores.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import structlog

from app.core.explanations import generate_explanation
from app.core.prediction import BehavioralForecaster
from app.core.regions import get_all_regions, get_region_by_id
from app.services.risk.classifier import RiskClassifier
from app.services.shocks.detector import ShockDetector

logger = structlog.get_logger("core.live_monitor")


class LiveSnapshot:
    """Represents a single snapshot of behavior index data for a region."""

    def __init__(
        self,
        region_id: str,
        timestamp: datetime,
        behavior_index: float,
        sub_indices: Dict[str, float],
        sources: List[str],
        explanation_summary: Optional[str] = None,
        event_flags: Optional[Dict[str, bool]] = None,
    ):
        """
        Initialize a live snapshot.

        Args:
            region_id: Region identifier
            timestamp: When this snapshot was taken
            behavior_index: Current behavior index value
            sub_indices: Dictionary of sub-index values
            sources: List of data sources used
            explanation_summary: Optional human-readable summary
            event_flags: Optional flags for major events detected
        """
        self.region_id = region_id
        self.timestamp = timestamp
        self.behavior_index = behavior_index
        self.sub_indices = sub_indices
        self.sources = sources
        self.explanation_summary = explanation_summary
        self.event_flags = event_flags or {}

    def to_dict(self) -> Dict:
        """Convert snapshot to dictionary for API responses."""
        return {
            "region_id": self.region_id,
            "timestamp": self.timestamp.isoformat(),
            "behavior_index": self.behavior_index,
            "sub_indices": self.sub_indices,
            "sources": self.sources,
            "explanation_summary": self.explanation_summary,
            "event_flags": self.event_flags,
        }


class LiveMonitor:
    """
    Maintains live snapshots of behavior index data per region.

    This class provides:
    - In-memory storage of recent snapshots (rolling window)
    - Background refresh mechanism
    - Major event detection
    - Query interface for live data
    """

    def __init__(
        self,
        max_snapshots_per_region: int = 100,
        refresh_interval_minutes: int = 30,
        historical_days: int = 30,
    ):
        """
        Initialize the live monitor.

        Args:
            max_snapshots_per_region: Maximum number of snapshots to keep per region
            refresh_interval_minutes: How often to refresh data (in minutes)
            historical_days: Number of historical days to use for forecasts
        """
        self.max_snapshots_per_region = max_snapshots_per_region
        self.refresh_interval_minutes = refresh_interval_minutes
        self.historical_days = historical_days

        # In-memory storage: region_id -> list of LiveSnapshot (most recent first)
        self._snapshots: Dict[str, List[LiveSnapshot]] = {}

        # Event detection thresholds
        self._event_thresholds = {
            "digital_attention_spike": 0.15,  # Increase of 0.15 in digital_attention
            "health_stress_elevated": 0.7,  # public_health_stress >= 0.7
            "environmental_shock": 0.8,  # environmental_stress >= 0.8
            "economic_volatility": 0.75,  # economic_stress >= 0.75
        }

        self._forecaster = BehavioralForecaster()
        self._risk_classifier = RiskClassifier()
        self._shock_detector = ShockDetector()

    def refresh_region(self, region_id: str) -> Optional[LiveSnapshot]:
        """
        Refresh data for a single region and create a new snapshot.

        Args:
            region_id: Region to refresh

        Returns:
            New LiveSnapshot if successful, None otherwise
        """
        try:
            region = get_region_by_id(region_id)
            if region is None:
                logger.warning("Region not found for live refresh", region_id=region_id)
                return None

            # Generate forecast using existing pipeline
            forecast_result = self._forecaster.forecast(
                latitude=region.latitude,
                longitude=region.longitude,
                region_name=region.name,
                days_back=self.historical_days,
                forecast_horizon=7,  # Use 7 days for live monitoring
            )

            # Extract latest data from history
            if (
                not forecast_result.get("history")
                or len(forecast_result["history"]) == 0
            ):
                logger.warning(
                    "No history data in forecast result", region_id=region_id
                )
                return None

            latest_history = forecast_result["history"][-1]
            behavior_index = latest_history.get("behavior_index", 0.5)
            sub_indices = latest_history.get("sub_indices", {})

            # Convert sub_indices to SubIndices-like dict for explanation generation
            sub_indices_dict = {
                "economic_stress": sub_indices.get("economic_stress", 0.5),
                "environmental_stress": sub_indices.get("environmental_stress", 0.5),
                "mobility_activity": sub_indices.get("mobility_activity", 0.5),
                "digital_attention": sub_indices.get("digital_attention", 0.5),
                "public_health_stress": sub_indices.get("public_health_stress", 0.5),
            }

            # Generate explanation summary
            explanation_summary = None
            try:
                explanation_dict = generate_explanation(
                    behavior_index=behavior_index,
                    sub_indices=sub_indices_dict,
                    subindex_details=None,  # No component details in live monitoring
                    region_name=region.name,
                )
                # Extract summary from the explanation dict
                if isinstance(explanation_dict, dict) and "summary" in explanation_dict:
                    explanation_summary = explanation_dict["summary"]
                elif isinstance(explanation_dict, str):
                    explanation_summary = explanation_dict
            except Exception as e:
                logger.debug(
                    "Failed to generate explanation summary",
                    error=str(e),
                    region_id=region_id,
                )
                # Continue without explanation summary

            # Detect major events
            event_flags = self._detect_events(sub_indices, region_id)

            # Create snapshot
            snapshot = LiveSnapshot(
                region_id=region_id,
                timestamp=datetime.now(),
                behavior_index=behavior_index,
                sub_indices=sub_indices,
                sources=forecast_result.get("sources", []),
                explanation_summary=explanation_summary,
                event_flags=event_flags,
            )

            # Store snapshot (most recent first)
            if region_id not in self._snapshots:
                self._snapshots[region_id] = []
            self._snapshots[region_id].insert(0, snapshot)

            # Trim old snapshots
            if len(self._snapshots[region_id]) > self.max_snapshots_per_region:
                self._snapshots[region_id] = self._snapshots[region_id][
                    : self.max_snapshots_per_region
                ]

            logger.info(
                "Refreshed live snapshot",
                region_id=region_id,
                behavior_index=behavior_index,
                events=event_flags,
            )

            return snapshot

        except Exception as e:
            logger.error(
                "Failed to refresh region",
                region_id=region_id,
                error=str(e),
                exc_info=True,
            )
            return None

    def refresh_all_regions(self) -> Dict[str, bool]:
        """
        Refresh data for all known regions.

        Returns:
            Dictionary mapping region_id to success status
        """
        regions = get_all_regions()
        results = {}

        for region in regions:
            snapshot = self.refresh_region(region.id)
            results[region.id] = snapshot is not None

        logger.info(
            "Refreshed all regions",
            total=len(regions),
            successful=sum(results.values()),
        )
        return results

    def _detect_events(
        self, sub_indices: Dict[str, float], region_id: str
    ) -> Dict[str, bool]:
        """
        Detect major events based on sub-index values and thresholds.

        Args:
            sub_indices: Current sub-index values
            region_id: Region identifier (for comparing with previous snapshots)

        Returns:
            Dictionary of event flags (event_name -> bool)
        """
        event_flags = {}

        # Check thresholds
        if sub_indices.get("digital_attention", 0.0) >= 0.7:
            # Check if this is a spike (increase from previous)
            previous = self.get_latest_snapshot(region_id)
            if previous:
                prev_digital = previous.sub_indices.get("digital_attention", 0.0)
                current_digital = sub_indices.get("digital_attention", 0.0)
                if (
                    current_digital - prev_digital
                    >= self._event_thresholds["digital_attention_spike"]
                ):
                    event_flags["digital_attention_spike"] = True

        if (
            sub_indices.get("public_health_stress", 0.0)
            >= self._event_thresholds["health_stress_elevated"]
        ):
            event_flags["health_stress_elevated"] = True

        if (
            sub_indices.get("environmental_stress", 0.0)
            >= self._event_thresholds["environmental_shock"]
        ):
            event_flags["environmental_shock"] = True

        if (
            sub_indices.get("economic_stress", 0.0)
            >= self._event_thresholds["economic_volatility"]
        ):
            event_flags["economic_volatility"] = True

        return event_flags

    def get_latest_snapshot(self, region_id: str) -> Optional[LiveSnapshot]:
        """
        Get the most recent snapshot for a region.

        Args:
            region_id: Region identifier

        Returns:
            Latest LiveSnapshot or None if not available
        """
        if region_id not in self._snapshots or len(self._snapshots[region_id]) == 0:
            return None
        return self._snapshots[region_id][0]

    def get_snapshots(
        self,
        region_id: str,
        time_window_minutes: Optional[int] = None,
        max_count: Optional[int] = None,
    ) -> List[LiveSnapshot]:
        """
        Get snapshots for a region within a time window.

        Args:
            region_id: Region identifier
            time_window_minutes: Optional time window in minutes (from now)
            max_count: Optional maximum number of snapshots to return

        Returns:
            List of LiveSnapshot objects (most recent first)
        """
        if region_id not in self._snapshots:
            return []

        snapshots = self._snapshots[region_id]

        # Filter by time window if specified
        if time_window_minutes:
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            snapshots = [s for s in snapshots if s.timestamp >= cutoff_time]

        # Limit count if specified
        if max_count:
            snapshots = snapshots[:max_count]

        return snapshots

    def get_summary(
        self,
        region_ids: Optional[List[str]] = None,
        time_window_minutes: Optional[int] = 60,
    ) -> Dict:
        """
        Get a summary of live data for specified regions.

        Args:
            region_ids: Optional list of region IDs (if None, returns all)
            time_window_minutes: Time window for historical snapshots

        Returns:
            Dictionary with summary data per region, including intelligence fields
        """
        if region_ids is None:
            # Get all regions with data
            region_ids = list(self._snapshots.keys())

        summary = {
            "timestamp": datetime.now().isoformat(),
            "regions": {},
        }

        for region_id in region_ids:
            latest = self.get_latest_snapshot(region_id)
            if latest:
                snapshots = self.get_snapshots(
                    region_id, time_window_minutes=time_window_minutes
                )

                # Compute intelligence data
                intelligence = self._compute_intelligence(latest, snapshots)

                summary["regions"][region_id] = {
                    "latest": latest.to_dict(),
                    "history": [s.to_dict() for s in snapshots],
                    "snapshot_count": len(snapshots),
                    "intelligence": intelligence,
                }
            else:
                summary["regions"][region_id] = {
                    "status": "no_data",
                    "message": "No live data available for this region",
                }

        return summary

    def _compute_intelligence(
        self, latest: LiveSnapshot, snapshots: List[LiveSnapshot]
    ) -> Dict:
        """
        Compute intelligence summary for a region.

        Args:
            latest: Latest snapshot
            snapshots: Historical snapshots for shock detection

        Returns:
            Dictionary with risk_tier, top_contributing_indices, and shock_status
        """
        import pandas as pd

        # Calculate risk tier
        risk_result = self._risk_classifier.classify_risk(
            behavior_index=latest.behavior_index,
            shock_events=None,  # Will be computed from snapshots
            convergence_score=None,
            trend_direction=None,
        )
        risk_tier = risk_result["tier"].capitalize()

        # Calculate top contributing indices from sub_indices
        # Contribution score = absolute value of sub_index (higher = more contribution)
        top_indices = []
        if latest.sub_indices:
            index_contributions = [
                {
                    "name": name.replace("_", " ").title(),
                    "contribution_score": abs(value),
                }
                for name, value in latest.sub_indices.items()
                if isinstance(value, (int, float))
            ]
            # Sort by contribution score descending, take top 3
            index_contributions.sort(
                key=lambda x: x["contribution_score"], reverse=True
            )
            top_indices = index_contributions[:3]

        # Detect shocks from history
        shock_status = "None"
        if len(snapshots) >= 7:  # Need enough history for shock detection
            try:
                # Convert snapshots to DataFrame for shock detection
                history_data = []
                for snapshot in snapshots:
                    row = {
                        "timestamp": snapshot.timestamp,
                        "behavior_index": snapshot.behavior_index,
                    }
                    row.update(snapshot.sub_indices)
                    history_data.append(row)

                history_df = pd.DataFrame(history_data)
                history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
                history_df = history_df.set_index("timestamp").sort_index()

                # Detect shocks
                shocks = self._shock_detector.detect_shocks(history_df)

                if shocks:
                    # Check if there are recent shocks (within last 7 days)
                    recent_cutoff = datetime.now() - timedelta(days=7)
                    recent_shocks = [
                        s
                        for s in shocks
                        if pd.to_datetime(s["timestamp"]) >= recent_cutoff
                    ]

                    if recent_shocks:
                        # Check if any shock is ongoing (within last 24 hours)
                        ongoing_cutoff = datetime.now() - timedelta(days=1)
                        ongoing_shocks = [
                            s
                            for s in recent_shocks
                            if pd.to_datetime(s["timestamp"]) >= ongoing_cutoff
                        ]

                        if ongoing_shocks:
                            shock_status = "OngoingShock"
                        else:
                            shock_status = "RecentShock"
            except Exception as e:
                logger.debug(
                    "Failed to detect shocks for intelligence summary",
                    error=str(e),
                    region_id=latest.region_id,
                )
                # Default to None on error

        return {
            "risk_tier": risk_tier,
            "top_contributing_indices": top_indices,
            "shock_status": shock_status,
        }


# Global instance (singleton pattern)
_live_monitor_instance: Optional[LiveMonitor] = None


def get_live_monitor() -> LiveMonitor:
    """Get or create the global LiveMonitor instance."""
    global _live_monitor_instance
    if _live_monitor_instance is None:
        _live_monitor_instance = LiveMonitor()
    return _live_monitor_instance
