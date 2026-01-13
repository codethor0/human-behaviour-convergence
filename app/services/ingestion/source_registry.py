# SPDX-License-Identifier: PROPRIETARY
"""Single source of truth registry for data sources."""
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SourceDefinition:
    """Definition of a data source in the registry."""

    id: str  # snake_case identifier
    display_name: str  # Human-readable name
    category: str  # e.g., "economic", "environmental", "social"
    requires_key: bool  # Whether an API key is required
    required_env_vars: List[str] = field(
        default_factory=list
    )  # Environment variables needed
    can_run_without_key: bool = False  # Can operate without key (fallback mode)
    description: str = ""
    fetcher_class: Optional[Any] = None  # The fetcher class (not instantiated)
    healthcheck: Optional[Callable[[], Dict[str, Any]]] = (
        None  # Optional healthcheck function
    )


# Registry: single source of truth
SOURCE_REGISTRY: Dict[str, SourceDefinition] = {}


# Import fetchers (lazy to avoid circular imports)
def _get_fetcher_classes():
    """Get fetcher classes dynamically to avoid circular imports."""
    from app.services.ingestion.finance import MarketSentimentFetcher
    from app.services.ingestion.gdelt_events import GDELTEventsFetcher
    from app.services.ingestion.mobility import MobilityFetcher
    from app.services.ingestion.openfema_emergency_management import (
        OpenFEMAEmergencyManagementFetcher,
    )
    from app.services.ingestion.openstates_legislative import (
        OpenStatesLegislativeFetcher,
    )
    from app.services.ingestion.public_health import PublicHealthFetcher
    from app.services.ingestion.search_trends import SearchTrendsFetcher
    from app.services.ingestion.weather import EnvironmentalImpactFetcher

    return {
        "MarketSentimentFetcher": MarketSentimentFetcher,
        "EnvironmentalImpactFetcher": EnvironmentalImpactFetcher,
        "SearchTrendsFetcher": SearchTrendsFetcher,
        "PublicHealthFetcher": PublicHealthFetcher,
        "MobilityFetcher": MobilityFetcher,
        "GDELTEventsFetcher": GDELTEventsFetcher,
        "OpenFEMAEmergencyManagementFetcher": OpenFEMAEmergencyManagementFetcher,
        "OpenStatesLegislativeFetcher": OpenStatesLegislativeFetcher,
    }


def _check_missing_env_vars(required_vars: List[str]) -> List[str]:
    """Check which required environment variables are missing."""
    return [var for var in required_vars if not os.getenv(var)]


def _compute_source_status(source: SourceDefinition) -> Dict[str, Any]:
    """
    Compute current status for a source.

    Returns:
        Dict with: status, ok, error_type, required_env_vars, details, last_checked
    """
    from datetime import datetime

    status_result = {
        "status": "active",
        "ok": True,
        "error_type": None,
        "required_env_vars": source.required_env_vars,
        "details": source.description,
        "last_checked": datetime.now().isoformat(),
    }

    # Only mark as "needs_key" if the source requires a key AND cannot run without it
    if source.requires_key and not source.can_run_without_key:
        missing = _check_missing_env_vars(source.required_env_vars)
        if missing:
            status_result["status"] = "needs_key"
            status_result["ok"] = False
            status_result["error_type"] = "missing_key"
            missing_vars_str = ", ".join(missing)
            status_result["details"] = (
                f"Set {missing_vars_str} to enable {source.display_name}. See .env.example and docs."
            )
            return status_result
    # If source.can_run_without_key is True, it can operate without the key (optional enhancement)

    # If we have a healthcheck, run it (never throw)
    if source.healthcheck:
        try:
            health_result = source.healthcheck()
            if health_result.get("ok", True):
                status_result["status"] = "active"
                status_result["ok"] = True
            else:
                status_result["status"] = health_result.get("status", "error")
                status_result["ok"] = False
                status_result["error_type"] = health_result.get("error_type")
                status_result["details"] = health_result.get(
                    "details", source.description
                )
        except Exception as e:
            status_result["status"] = "error"
            status_result["ok"] = False
            status_result["error_type"] = "exception"
            status_result["details"] = f"Healthcheck failed: {str(e)[:100]}"

    return status_result


def register_source(source: SourceDefinition) -> None:
    """Register a source in the registry."""
    SOURCE_REGISTRY[source.id] = source


def get_all_sources() -> Dict[str, SourceDefinition]:
    """Get all registered sources."""
    return SOURCE_REGISTRY.copy()


def get_source_statuses() -> Dict[str, Dict[str, Any]]:
    """Get computed status for all sources."""
    return {
        source_id: _compute_source_status(source)
        for source_id, source in SOURCE_REGISTRY.items()
    }


def initialize_registry() -> None:
    """Initialize the source registry with all known sources."""
    # Economic indicators (market sentiment - no key required)
    register_source(
        SourceDefinition(
            id="economic_indicators",
            display_name="Economic Indicators",
            category="economic",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Market sentiment indicators from public financial data (volatility index, market indices)",
        )
    )

    # Weather patterns (no key required)
    register_source(
        SourceDefinition(
            id="weather_patterns",
            display_name="Weather Patterns",
            category="environmental",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Environmental data including temperature, precipitation, and wind patterns",
        )
    )

    # Search trends (Wikipedia Pageviews - no key required)
    register_source(
        SourceDefinition(
            id="search_trends",
            display_name="Search Trends",
            category="digital",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Digital attention signals from Wikipedia Pageviews API (public, no key required)",
        )
    )

    # Public health (key required, but can run without key in fallback mode)
    register_source(
        SourceDefinition(
            id="public_health",
            display_name="Public Health",
            category="health",
            requires_key=False,  # Can run without key (fallback mode)
            required_env_vars=["PUBLIC_HEALTH_API_ENDPOINT"],
            can_run_without_key=True,
            description="Public health indicators from aggregated health statistics (requires API configuration for full functionality)",
        )
    )

    # Mobility patterns (TSA passenger throughput - no key required)
    register_source(
        SourceDefinition(
            id="mobility_patterns",
            display_name="Mobility Patterns",
            category="mobility",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Mobility and activity patterns from TSA daily passenger throughput (public dataset, no key required)",
        )
    )

    # Emergency management (OpenFEMA - no key required)
    register_source(
        SourceDefinition(
            id="emergency_management",
            display_name="Emergency Management",
            category="government",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Disaster declarations and emergency management data from OpenFEMA (official disaster declarations, emergency events, FEMA program activity)",
        )
    )

    # Legislative activity (GDELT no-key fallback + optional OpenStates enhancement)
    register_source(
        SourceDefinition(
            id="legislative_activity",
            display_name="Legislative Activity",
            category="government",
            requires_key=False,
            required_env_vars=["OPENSTATES_API_KEY"],  # Optional for enhanced data
            can_run_without_key=True,
            description="Legislative/governance events from GDELT (no key required). Optional OpenStates enhancement when OPENSTATES_API_KEY is set.",
        )
    )

    # GDELT events (no key required)
    register_source(
        SourceDefinition(
            id="gdelt_events",
            display_name="GDELT Events",
            category="digital",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Global event and crisis signals from GDELT (Global Database of Events, Language, and Tone)",
        )
    )

    # GDELT enforcement events (no key required)
    register_source(
        SourceDefinition(
            id="gdelt_enforcement",
            display_name="GDELT Enforcement Events",
            category="digital",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Enforcement/ICE/policing-related events from GDELT (normalized attention signal for political/social stress adjustment)",
        )
    )

    # Weather alerts (NWS - no key required)
    register_source(
        SourceDefinition(
            id="weather_alerts",
            display_name="Weather Alerts",
            category="environmental",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Active weather alerts from NWS (National Weather Service) - warnings, watches, and advisories",
        )
    )

    # Cyber risk (CISA KEV - no key required)
    register_source(
        SourceDefinition(
            id="cyber_risk",
            display_name="Cyber Risk",
            category="digital",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Known Exploited Vulnerabilities from CISA (Cybersecurity and Infrastructure Security Agency)",
        )
    )


# Initialize on module import
initialize_registry()
