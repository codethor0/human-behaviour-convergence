# SPDX-License-Identifier: PROPRIETARY
"""Tests for live monitoring functionality."""
from datetime import datetime, timedelta

from app.core.live_monitor import LiveMonitor, LiveSnapshot


class TestLiveSnapshot:
    """Test LiveSnapshot class."""

    def test_snapshot_creation(self):
        """Test creating a live snapshot."""
        snapshot = LiveSnapshot(
            region_id="us_dc",
            timestamp=datetime.now(),
            behavior_index=0.5,
            sub_indices={"economic_stress": 0.4, "environmental_stress": 0.3},
            sources=["weather", "market"],
        )
        assert snapshot.region_id == "us_dc"
        assert snapshot.behavior_index == 0.5
        assert len(snapshot.sub_indices) == 2

    def test_snapshot_to_dict(self):
        """Test converting snapshot to dictionary."""
        snapshot = LiveSnapshot(
            region_id="us_dc",
            timestamp=datetime.now(),
            behavior_index=0.5,
            sub_indices={"economic_stress": 0.4},
            sources=["weather"],
        )
        data = snapshot.to_dict()
        assert data["region_id"] == "us_dc"
        assert data["behavior_index"] == 0.5
        assert "timestamp" in data


class TestLiveMonitor:
    """Test LiveMonitor class."""

    def test_monitor_initialization(self):
        """Test LiveMonitor initialization."""
        monitor = LiveMonitor(
            max_snapshots_per_region=50,
            refresh_interval_minutes=15,
            historical_days=30,
        )
        assert monitor.max_snapshots_per_region == 50
        assert monitor.refresh_interval_minutes == 15
        assert monitor.historical_days == 30

    def test_get_latest_snapshot_no_data(self):
        """Test getting latest snapshot when no data exists."""
        monitor = LiveMonitor()
        snapshot = monitor.get_latest_snapshot("us_dc")
        assert snapshot is None

    def test_get_snapshots_no_data(self):
        """Test getting snapshots when no data exists."""
        monitor = LiveMonitor()
        snapshots = monitor.get_snapshots("us_dc")
        assert len(snapshots) == 0

    def test_get_snapshots_time_window(self):
        """Test getting snapshots within a time window."""
        monitor = LiveMonitor()

        # Create test snapshots
        now = datetime.now()
        old_snapshot = LiveSnapshot(
            region_id="us_dc",
            timestamp=now - timedelta(hours=2),
            behavior_index=0.5,
            sub_indices={},
            sources=[],
        )
        recent_snapshot = LiveSnapshot(
            region_id="us_dc",
            timestamp=now - timedelta(minutes=30),
            behavior_index=0.6,
            sub_indices={},
            sources=[],
        )

        monitor._snapshots["us_dc"] = [recent_snapshot, old_snapshot]

        # Get snapshots within last 60 minutes
        snapshots = monitor.get_snapshots("us_dc", time_window_minutes=60)
        assert len(snapshots) == 1
        assert snapshots[0].behavior_index == 0.6

    def test_get_snapshots_max_count(self):
        """Test limiting snapshot count."""
        monitor = LiveMonitor()

        # Create multiple snapshots
        snapshots = []
        for i in range(10):
            snapshots.append(
                LiveSnapshot(
                    region_id="us_dc",
                    timestamp=datetime.now() - timedelta(minutes=i),
                    behavior_index=0.5 + i * 0.01,
                    sub_indices={},
                    sources=[],
                )
            )

        monitor._snapshots["us_dc"] = snapshots

        # Get only 5 most recent
        result = monitor.get_snapshots("us_dc", max_count=5)
        assert len(result) == 5

    def test_detect_events_health_stress(self):
        """Test event detection for health stress elevation."""
        monitor = LiveMonitor()

        sub_indices = {
            "public_health_stress": 0.75,  # Above threshold of 0.7
        }

        event_flags = monitor._detect_events(sub_indices, "us_dc")
        assert event_flags.get("health_stress_elevated") is True

    def test_detect_events_environmental_shock(self):
        """Test event detection for environmental shock."""
        monitor = LiveMonitor()

        sub_indices = {
            "environmental_stress": 0.85,  # Above threshold of 0.8
        }

        event_flags = monitor._detect_events(sub_indices, "us_dc")
        assert event_flags.get("environmental_shock") is True

    def test_detect_events_economic_volatility(self):
        """Test event detection for economic volatility."""
        monitor = LiveMonitor()

        sub_indices = {
            "economic_stress": 0.80,  # Above threshold of 0.75
        }

        event_flags = monitor._detect_events(sub_indices, "us_dc")
        assert event_flags.get("economic_volatility") is True

    def test_detect_events_digital_attention_spike(self):
        """Test event detection for digital attention spike."""
        monitor = LiveMonitor()

        # Create previous snapshot with lower digital attention
        previous = LiveSnapshot(
            region_id="us_dc",
            timestamp=datetime.now() - timedelta(minutes=30),
            behavior_index=0.5,
            sub_indices={"digital_attention": 0.5},
            sources=[],
        )
        monitor._snapshots["us_dc"] = [previous]

        # Current snapshot with higher digital attention (spike of 0.2)
        sub_indices = {
            "digital_attention": 0.7,  # 0.7 - 0.5 = 0.2 > 0.15 threshold
        }

        event_flags = monitor._detect_events(sub_indices, "us_dc")
        assert event_flags.get("digital_attention_spike") is True

    def test_get_summary_no_regions(self):
        """Test getting summary with no regions specified."""
        monitor = LiveMonitor()
        summary = monitor.get_summary()
        assert "timestamp" in summary
        assert "regions" in summary

    def test_get_summary_with_regions(self):
        """Test getting summary for specific regions."""
        monitor = LiveMonitor()

        # Create test snapshot
        snapshot = LiveSnapshot(
            region_id="us_dc",
            timestamp=datetime.now(),
            behavior_index=0.5,
            sub_indices={"economic_stress": 0.4},
            sources=["weather"],
        )
        monitor._snapshots["us_dc"] = [snapshot]

        summary = monitor.get_summary(region_ids=["us_dc"])
        assert "us_dc" in summary["regions"]
        assert summary["regions"]["us_dc"]["latest"]["region_id"] == "us_dc"

    def test_get_summary_region_no_data(self):
        """Test getting summary for region with no data."""
        monitor = LiveMonitor()
        summary = monitor.get_summary(region_ids=["us_dc"])
        assert "us_dc" in summary["regions"]
        assert summary["regions"]["us_dc"]["status"] == "no_data"
