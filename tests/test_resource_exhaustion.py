# SPDX-License-Identifier: PROPRIETARY
"""Tests for resource exhaustion protection (memory, cache, connections)."""
import os
from unittest.mock import patch


from app.core.live_monitor import LiveMonitor
from app.core.prediction import BehavioralForecaster


class TestBehavioralForecasterCacheBounds:
    """Test that BehavioralForecaster cache has hard bounds."""

    def test_cache_enforces_max_size(self):
        """Cache must not exceed max_cache_size entries."""
        forecaster = BehavioralForecaster()
        forecaster._max_cache_size = 3  # Small limit for testing

        # Generate forecasts to fill cache
        for i in range(5):
            forecaster.forecast(
                latitude=40.0 + i * 0.1,
                longitude=-74.0,
                region_name=f"Test Region {i}",
                days_back=30,
                forecast_horizon=7,
            )

        # Cache should not exceed max size
        assert len(forecaster._cache) <= forecaster._max_cache_size

    def test_cache_evicts_oldest_entry(self):
        """Cache must evict oldest entry when at capacity."""
        forecaster = BehavioralForecaster()
        forecaster._max_cache_size = 2

        # Generate two forecasts
        forecaster.forecast(
            latitude=40.0, longitude=-74.0, region_name="Region A", days_back=30
        )
        forecaster.forecast(
            latitude=41.0, longitude=-75.0, region_name="Region B", days_back=30
        )

        # First two keys should be in cache
        keys = list(forecaster._cache.keys())
        assert len(keys) == 2

        # Add third forecast - should evict oldest
        forecaster.forecast(
            latitude=42.0, longitude=-76.0, region_name="Region C", days_back=30
        )

        # Cache should still be at max size
        assert len(forecaster._cache) == forecaster._max_cache_size
        # Oldest key should be gone
        assert keys[0] not in forecaster._cache

    def test_cache_lru_ordering(self):
        """Cache must maintain LRU ordering."""
        forecaster = BehavioralForecaster()
        forecaster._max_cache_size = 3

        # Generate three forecasts
        forecaster.forecast(
            latitude=40.0, longitude=-74.0, region_name="Region A", days_back=30
        )
        forecaster.forecast(
            latitude=41.0, longitude=-75.0, region_name="Region B", days_back=30
        )
        forecaster.forecast(
            latitude=42.0, longitude=-76.0, region_name="Region C", days_back=30
        )

        first_key = list(forecaster._cache.keys())[0]

        # Access first entry - should move to end
        forecaster.forecast(
            latitude=40.0, longitude=-74.0, region_name="Region A", days_back=30
        )

        # First key should now be at end (most recently used)
        last_key = list(forecaster._cache.keys())[-1]
        assert first_key == last_key

    def test_cache_thread_safety(self):
        """Cache operations must be thread-safe."""
        import threading

        forecaster = BehavioralForecaster()
        forecaster._max_cache_size = 10

        def generate_forecast(i):
            forecaster.forecast(
                latitude=40.0 + i * 0.01,
                longitude=-74.0,
                region_name=f"Region {i}",
                days_back=30,
            )

        # Generate forecasts concurrently
        threads = [threading.Thread(target=generate_forecast, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Cache should not exceed max size
        assert len(forecaster._cache) <= forecaster._max_cache_size


class TestLiveMonitorBounds:
    """Test that LiveMonitor has hard bounds on regions and snapshots."""

    def test_max_regions_enforced(self):
        """LiveMonitor must not exceed max_regions."""
        monitor = LiveMonitor(max_regions=3)

        # Add snapshots for more than max_regions
        for i in range(5):
            monitor.refresh_region(f"region_{i}")

        # Should not exceed max_regions
        assert len(monitor._snapshots) <= monitor.max_regions

    def test_region_eviction_when_at_capacity(self):
        """LiveMonitor must evict oldest region when at capacity."""
        monitor = LiveMonitor(max_regions=2)

        # Add two regions
        monitor.refresh_region("region_a")
        monitor.refresh_region("region_b")

        assert len(monitor._snapshots) == 2
        first_region = list(monitor._snapshots.keys())[0]

        # Add third region - should evict oldest
        monitor.refresh_region("region_c")

        assert len(monitor._snapshots) == monitor.max_regions
        assert first_region not in monitor._snapshots

    def test_max_snapshots_per_region_enforced(self):
        """LiveMonitor must not exceed max_snapshots_per_region per region."""
        monitor = LiveMonitor(max_snapshots_per_region=3)

        # Generate more snapshots than limit
        for _ in range(5):
            monitor.refresh_region("test_region")

        # Should not exceed max_snapshots_per_region
        assert len(monitor._snapshots["test_region"]) <= monitor.max_snapshots_per_region

    def test_snapshots_trimmed_when_over_limit(self):
        """LiveMonitor must trim snapshots when over limit."""
        monitor = LiveMonitor(max_snapshots_per_region=2)

        # Generate three snapshots
        monitor.refresh_region("test_region")
        monitor.refresh_region("test_region")
        monitor.refresh_region("test_region")

        # Should be trimmed to max_snapshots_per_region
        assert len(monitor._snapshots["test_region"]) == monitor.max_snapshots_per_region

    def test_region_lru_ordering(self):
        """LiveMonitor must maintain LRU ordering for regions."""
        monitor = LiveMonitor(max_regions=3)

        # Add three regions
        monitor.refresh_region("region_a")
        monitor.refresh_region("region_b")
        monitor.refresh_region("region_c")

        first_region = list(monitor._snapshots.keys())[0]

        # Access first region - should move to end
        monitor.get_latest_snapshot("region_a")

        # First region should now be at end (most recently used)
        last_region = list(monitor._snapshots.keys())[-1]
        assert first_region == last_region

    def test_thread_safety(self):
        """LiveMonitor operations must be thread-safe."""
        import threading

        monitor = LiveMonitor(max_regions=10)

        def refresh_region(i):
            monitor.refresh_region(f"region_{i}")

        # Refresh regions concurrently
        threads = [threading.Thread(target=refresh_region, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not exceed max_regions
        assert len(monitor._snapshots) <= monitor.max_regions


class TestRepeatedRequests:
    """Test that repeated requests do not cause unbounded growth."""

    def test_repeated_forecast_requests(self):
        """Repeated forecast requests must not cause unbounded cache growth."""
        forecaster = BehavioralForecaster()
        forecaster._max_cache_size = 5

        # Make many requests with same parameters
        for _ in range(100):
            forecaster.forecast(
                latitude=40.0, longitude=-74.0, region_name="NYC", days_back=30
            )

        # Cache should still be bounded
        assert len(forecaster._cache) <= forecaster._max_cache_size

    def test_repeated_live_monitor_requests(self):
        """Repeated live monitor requests must not cause unbounded growth."""
        monitor = LiveMonitor(max_regions=5, max_snapshots_per_region=10)

        # Make many refresh requests
        for i in range(100):
            monitor.refresh_region(f"region_{i % 10}")

        # Should not exceed bounds
        assert len(monitor._snapshots) <= monitor.max_regions
        for region_id in monitor._snapshots:
            assert len(monitor._snapshots[region_id]) <= monitor.max_snapshots_per_region

    def test_cache_size_from_env(self):
        """Forecaster cache size should be configurable via env var."""
        with patch.dict(os.environ, {"FORECASTER_CACHE_MAX_SIZE": "25"}):
            forecaster = BehavioralForecaster()
            assert forecaster._max_cache_size == 25

    def test_monitor_max_regions_from_env(self):
        """LiveMonitor max_regions should be configurable via env var."""
        with patch.dict(os.environ, {"LIVE_MONITOR_MAX_REGIONS": "150"}):
            monitor = LiveMonitor()
            assert monitor.max_regions == 150
