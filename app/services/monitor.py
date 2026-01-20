# SPDX-License-Identifier: PROPRIETARY
"""Source Health Monitoring and Connectivity Checks.

This module implements pre-flight connectivity checks and health monitoring
for external data sources to prevent silent failures and ensure reliability.
"""
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import requests
import structlog

logger = structlog.get_logger("services.monitor")

# Health check endpoints for external APIs
SOURCE_HEALTH_ENDPOINTS = {
    "gdelt": "https://api.gdeltproject.org/api/v2/doc/doc?mode=timelinetone&format=json&query=sourcelang:english&TIMESPAN=1days",
    "fred": "https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&api_key=test&file_type=json&limit=1",
    "nws": "https://api.weather.gov/",
    "openfema": "https://www.fema.gov/api/open/v1/DisasterDeclarationsSummaries?$top=1",
    "tsa": "https://www.tsa.gov/covid-19/passenger-throughput",
    "wikimedia": "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2024/01/01",
}


@dataclass
class SourceHealthStatus:
    """Health status for a data source."""

    source_id: str
    is_healthy: bool
    response_time_ms: Optional[float] = None
    http_status: Optional[int] = None
    error_message: Optional[str] = None
    checked_at: Optional[str] = None


class SourceHealthMonitor:
    """
    Monitor health and connectivity of external data sources.

    Implements pre-flight connectivity checks to fail fast and prevent
    silent failures when sources are unreachable.
    """

    def __init__(self, timeout_seconds: float = 5.0):
        """
        Initialize the health monitor.

        Args:
            timeout_seconds: Timeout for health check requests (default: 5.0)
        """
        self.timeout_seconds = timeout_seconds
        self.health_cache: Dict[str, SourceHealthStatus] = {}
        self.cache_duration_seconds = 60  # Cache health checks for 1 minute

    def check_source_health(
        self, source_id: str, endpoint: Optional[str] = None
    ) -> SourceHealthStatus:
        """
        Check health of a specific data source.

        Args:
            source_id: Identifier for the source (e.g., "gdelt", "fred")
            endpoint: Optional custom endpoint URL (default: uses SOURCE_HEALTH_ENDPOINTS)

        Returns:
            SourceHealthStatus with health information
        """
        # Check cache first
        if source_id in self.health_cache:
            cached_status = self.health_cache[source_id]
            if cached_status.checked_at:
                checked_time = datetime.fromisoformat(cached_status.checked_at)
                age_seconds = (datetime.now() - checked_time).total_seconds()
                if age_seconds < self.cache_duration_seconds:
                    logger.debug(
                        "Using cached health check",
                        source_id=source_id,
                        age_seconds=age_seconds,
                    )
                    return cached_status

        # Determine endpoint URL
        if endpoint is None:
            endpoint = SOURCE_HEALTH_ENDPOINTS.get(source_id)
            if endpoint is None:
                status = SourceHealthStatus(
                    source_id=source_id,
                    is_healthy=False,
                    error_message=f"No health endpoint configured for {source_id}",
                    checked_at=datetime.now().isoformat(),
                )
                self.health_cache[source_id] = status
                return status

        # Perform health check
        start_time = time.time()
        try:
            response = requests.get(
                endpoint, timeout=self.timeout_seconds, allow_redirects=True
            )
            response_time_ms = (time.time() - start_time) * 1000

            # Consider healthy if we get any response (even 4xx/5xx means service is reachable)
            # For strict checks, you could require 2xx status
            is_healthy = response.status_code is not None

            status = SourceHealthStatus(
                source_id=source_id,
                is_healthy=is_healthy,
                response_time_ms=response_time_ms,
                http_status=response.status_code,
                checked_at=datetime.now().isoformat(),
            )

            if not is_healthy:
                status.error_message = f"HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            status = SourceHealthStatus(
                source_id=source_id,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Request timeout",
                checked_at=datetime.now().isoformat(),
            )
        except requests.exceptions.ConnectionError as e:
            status = SourceHealthStatus(
                source_id=source_id,
                is_healthy=False,
                error_message=f"Connection error: {str(e)[:100]}",
                checked_at=datetime.now().isoformat(),
            )
        except Exception as e:
            status = SourceHealthStatus(
                source_id=source_id,
                is_healthy=False,
                error_message=f"Unexpected error: {str(e)[:100]}",
                checked_at=datetime.now().isoformat(),
            )

        # Cache result
        self.health_cache[source_id] = status

        logger.info(
            "Source health check completed",
            source_id=source_id,
            is_healthy=status.is_healthy,
            response_time_ms=status.response_time_ms,
            error_message=status.error_message,
        )

        return status

    def check_all_sources(
        self, source_ids: Optional[List[str]] = None
    ) -> Dict[str, SourceHealthStatus]:
        """
        Check health of multiple sources.

        Args:
            source_ids: List of source IDs to check (default: all configured sources)

        Returns:
            Dictionary mapping source_id to SourceHealthStatus
        """
        if source_ids is None:
            source_ids = list(SOURCE_HEALTH_ENDPOINTS.keys())

        results = {}
        for source_id in source_ids:
            results[source_id] = self.check_source_health(source_id)

        return results

    def get_unhealthy_sources(
        self, source_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get list of unhealthy sources.

        Args:
            source_ids: List of source IDs to check (default: all configured sources)

        Returns:
            List of source IDs that are unhealthy
        """
        health_results = self.check_all_sources(source_ids)
        return [
            source_id
            for source_id, status in health_results.items()
            if not status.is_healthy
        ]
