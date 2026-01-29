"""Air Quality Data Fetcher - PurpleAir and EPA AirNow APIs.

This module fetches air quality data from multiple sources:
- PurpleAir API: Community sensor network
- EPA AirNow API: Official government air quality data

Both sources provide AQI (Air Quality Index) which is normalized to a stress index.
"""

import os
import time
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import requests
import structlog

logger = structlog.get_logger("ingestion.air_quality")

# Cache for API responses (5 minute TTL)
_cache: Dict[str, tuple[float, pd.DataFrame]] = {}
_cache_ttl = 300  # 5 minutes


class AirQualityFetcher:
    """Fetches air quality data from PurpleAir and EPA AirNow APIs."""

    def __init__(self):
        self.purpleair_api_key = os.getenv("PURPLEAIR_API_KEY")
        self.airnow_api_key = os.getenv("AIRNOW_API_KEY")
        self.use_cache = True

    def _get_cache_key(self, source: str, region: str) -> str:
        """Generate cache key."""
        return f"air_quality_{source}_{region}"

    def _get_cached_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get data from cache if valid."""
        if not self.use_cache or cache_key not in _cache:
            return None

        timestamp, data = _cache[cache_key]
        if time.time() - timestamp > _cache_ttl:
            del _cache[cache_key]
            return None

        return data.copy()

    def _set_cached_data(self, cache_key: str, data: pd.DataFrame):
        """Store data in cache."""
        _cache[cache_key] = (time.time(), data.copy())

    def _fetch_purpleair(self, region: str) -> pd.DataFrame:
        """Fetch data from PurpleAir API."""
        cache_key = self._get_cache_key("purpleair", region)
        cached = self._get_cached_data(cache_key)
        if cached is not None:
            return cached

        # CI offline mode
        if os.getenv("CI") == "true" or not self.purpleair_api_key:
            logger.info("Using CI offline mode for PurpleAir")
            return self._get_ci_offline_data(region, "purpleair")

        try:
            # PurpleAir API endpoint (simplified - actual API may vary)
            # Note: PurpleAir API structure may require sensor-specific queries
            url = "https://api.purpleair.com/v1/sensors"
            headers = {"X-API-Key": self.purpleair_api_key}
            params = {
                "fields": "pm2.5,pm10.0,humidity,temperature",
                "location_type": 0,  # Outdoor sensors
                "max_age": 3600,  # Max 1 hour old
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Process PurpleAir data
            records = []
            for sensor in data.get("data", []):
                pm25 = sensor.get("pm2.5", 0)
                pm10 = sensor.get("pm10.0", 0)
                aqi = self._calculate_aqi_from_pm25(pm25)

                records.append(
                    {
                        "timestamp": datetime.now(),
                        "source": "purpleair",
                        "aqi": aqi,
                        "pm25": pm25,
                        "pm10": pm10,
                        "sensor_id": sensor.get("sensor_index"),
                    }
                )

            df = pd.DataFrame(records)
            if not df.empty:
                df = (
                    df.groupby("timestamp")
                    .agg(
                        {
                            "aqi": "mean",
                            "pm25": "mean",
                            "pm10": "mean",
                        }
                    )
                    .reset_index()
                )

            self._set_cached_data(cache_key, df)
            return df

        except Exception as e:
            logger.error("Failed to fetch PurpleAir data", error=str(e), exc_info=True)
            return self._get_fallback_data(region, "purpleair")

    def _fetch_airnow(self, region: str) -> pd.DataFrame:
        """Fetch data from EPA AirNow API."""
        cache_key = self._get_cache_key("airnow", region)
        cached = self._get_cached_data(cache_key)
        if cached is not None:
            return cached

        # CI offline mode
        if os.getenv("CI") == "true" or not self.airnow_api_key:
            logger.info("Using CI offline mode for AirNow")
            return self._get_ci_offline_data(region, "airnow")

        try:
            # EPA AirNow API
            url = "https://www.airnowapi.org/aq/observation/zipCode/current"
            params = {
                "format": "application/json",
                "zipCode": self._get_zipcode_for_region(region),
                "API_KEY": self.airnow_api_key,
                "distance": 25,  # 25 miles radius
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Process AirNow data
            records = []
            for observation in data:
                aqi = observation.get("AQI", 0)
                parameter = observation.get("ParameterName", "")
                category = observation.get("Category", {}).get("Name", "")

                records.append(
                    {
                        "timestamp": datetime.fromisoformat(
                            observation.get("DateObserved", datetime.now().isoformat())
                        ),
                        "source": "airnow",
                        "aqi": aqi,
                        "parameter": parameter,
                        "category": category,
                    }
                )

            df = pd.DataFrame(records)
            if not df.empty:
                # Aggregate by timestamp
                df = (
                    df.groupby("timestamp")
                    .agg(
                        {
                            "aqi": "mean",
                        }
                    )
                    .reset_index()
                )

            self._set_cached_data(cache_key, df)
            return df

        except Exception as e:
            logger.error("Failed to fetch AirNow data", error=str(e), exc_info=True)
            return self._get_fallback_data(region, "airnow")

    def _calculate_aqi_from_pm25(self, pm25: float) -> float:
        """Calculate AQI from PM2.5 concentration."""
        # Simplified AQI calculation (EPA formula)
        if pm25 <= 12.0:
            return (pm25 / 12.0) * 50
        elif pm25 <= 35.4:
            return ((pm25 - 12.1) / (35.4 - 12.1)) * (100 - 51) + 51
        elif pm25 <= 55.4:
            return ((pm25 - 35.5) / (55.4 - 35.5)) * (150 - 101) + 101
        elif pm25 <= 150.4:
            return ((pm25 - 55.5) / (150.4 - 55.5)) * (200 - 151) + 151
        elif pm25 <= 250.4:
            return ((pm25 - 150.5) / (250.4 - 150.5)) * (300 - 201) + 201
        else:
            return min(500, ((pm25 - 250.5) / (350.4 - 250.5)) * (400 - 301) + 301)

    def _get_zipcode_for_region(self, region: str) -> str:
        """Map region to zipcode for AirNow API."""
        # Simplified mapping - would need actual region-to-zipcode mapping
        region_zipcodes = {
            "city_nyc": "10001",
            "us_ny": "10001",
            "us_ca": "90001",
            "us_il": "60601",
            "us_tx": "75201",
            "us_fl": "33101",
        }
        return region_zipcodes.get(region, "10001")

    def _normalize_to_stress_index(self, aqi: float) -> float:
        """Normalize AQI (0-500) to stress index (0-1)."""
        # AQI > 100 is unhealthy, > 150 is unhealthy for sensitive groups
        # Normalize: 0-50 (good) = 0-0.2, 50-100 (moderate) = 0.2-0.4,
        # 100-150 (unhealthy for sensitive) = 0.4-0.6, 150+ (unhealthy) = 0.6-1.0
        if aqi <= 50:
            return (aqi / 50) * 0.2
        elif aqi <= 100:
            return 0.2 + ((aqi - 50) / 50) * 0.2
        elif aqi <= 150:
            return 0.4 + ((aqi - 100) / 50) * 0.2
        else:
            return min(1.0, 0.6 + ((aqi - 150) / 350) * 0.4)

    def _get_ci_offline_data(self, region: str, source: str) -> pd.DataFrame:
        """Generate deterministic CI offline data."""
        base_aqi = 45.0 if source == "purpleair" else 50.0
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        data = {
            "timestamp": dates,
            "aqi": [base_aqi + (i % 10) * 2 for i in range(30)],
            "air_quality_stress_index": [
                self._normalize_to_stress_index(base_aqi + (i % 10) * 2)
                for i in range(30)
            ],
        }
        return pd.DataFrame(data)

    def _get_fallback_data(self, region: str, source: str) -> pd.DataFrame:
        """Return fallback data when API fails."""
        logger.warning(f"Using fallback data for {source} in {region}")
        return self._get_ci_offline_data(region, source)

    def fetch_air_quality(self, region: str) -> pd.DataFrame:
        """Fetch and combine air quality data from all sources."""
        try:
            # Fetch from both sources
            purpleair_df = self._fetch_purpleair(region)
            airnow_df = self._fetch_airnow(region)

            # Combine data (prefer AirNow for official data, PurpleAir for coverage)
            if not purpleair_df.empty and not airnow_df.empty:
                # Merge on timestamp, average AQI values
                combined = pd.merge(
                    purpleair_df[["timestamp", "aqi"]],
                    airnow_df[["timestamp", "aqi"]],
                    on="timestamp",
                    how="outer",
                    suffixes=("_purpleair", "_airnow"),
                )
                combined["aqi"] = combined[["aqi_purpleair", "aqi_airnow"]].mean(axis=1)
                combined = combined[["timestamp", "aqi"]].copy()
            elif not airnow_df.empty:
                combined = airnow_df[["timestamp", "aqi"]].copy()
            elif not purpleair_df.empty:
                combined = purpleair_df[["timestamp", "aqi"]].copy()
            else:
                return self._get_fallback_data(region, "combined")

            # Calculate stress index
            combined["air_quality_stress_index"] = combined["aqi"].apply(
                self._normalize_to_stress_index
            )

            # Ensure timestamp is datetime
            combined["timestamp"] = pd.to_datetime(combined["timestamp"])

            return combined.sort_values("timestamp").reset_index(drop=True)

        except Exception as e:
            logger.error(
                "Failed to fetch air quality data", error=str(e), exc_info=True
            )
            return self._get_fallback_data(region, "combined")


def fetch_air_quality_data(region: str) -> pd.DataFrame:
    """Convenience function to fetch air quality data."""
    fetcher = AirQualityFetcher()
    return fetcher.fetch_air_quality(region)
