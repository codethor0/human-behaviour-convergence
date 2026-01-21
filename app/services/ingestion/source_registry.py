# SPDX-License-Identifier: PROPRIETARY
"""Single source of truth registry for data sources."""
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger("ingestion.source_registry")

# Optional: SQLite-backed storage (if available)
try:
    from app.storage import SourceRegistryDB

    _registry_db: Optional[SourceRegistryDB] = None

    def _get_registry_db() -> Optional[SourceRegistryDB]:
        """Get or initialize the registry database."""
        global _registry_db
        if _registry_db is None:
            try:
                _registry_db = SourceRegistryDB()
                logger.info("SourceRegistryDB initialized")
            except Exception as e:
                logger.warning("Failed to initialize SourceRegistryDB", error=str(e))
                _registry_db = None
        return _registry_db

except ImportError:
    SourceRegistryDB = None  # type: ignore[assignment, misc]

    def _get_registry_db() -> Optional[Any]:
        return None


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


# Registry: single source of truth (in-memory cache)
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

    # Optional connector - only import if available
    try:
        from app.services.ingestion.openstates_legislative import (
            OpenStatesLegislativeFetcher,
        )
    except ImportError:
        OpenStatesLegislativeFetcher = None  # type: ignore[assignment]
    from app.services.ingestion.public_health import PublicHealthFetcher
    from app.services.ingestion.search_trends import SearchTrendsFetcher
    from app.services.ingestion.weather import EnvironmentalImpactFetcher

    result = {
        "MarketSentimentFetcher": MarketSentimentFetcher,
        "EnvironmentalImpactFetcher": EnvironmentalImpactFetcher,
        "SearchTrendsFetcher": SearchTrendsFetcher,
        "PublicHealthFetcher": PublicHealthFetcher,
        "MobilityFetcher": MobilityFetcher,
        "GDELTEventsFetcher": GDELTEventsFetcher,
        "OpenFEMAEmergencyManagementFetcher": OpenFEMAEmergencyManagementFetcher,
    }
    # Only include optional connectors if available
    if OpenStatesLegislativeFetcher is not None:
        result["OpenStatesLegislativeFetcher"] = OpenStatesLegislativeFetcher
    return result


def _check_missing_env_vars(required_vars: List[str]) -> List[str]:
    """Check which required environment variables are missing."""
    return [var for var in required_vars if not os.getenv(var)]


def _sync_source_to_db(source: SourceDefinition) -> None:
    """Sync a source definition to SQLite database (if available)."""
    db = _get_registry_db()
    if db is None:
        return

    try:
        db.upsert_source(
            source_id=source.id,
            name=source.display_name,
            category=source.category,
            description=source.description,
            geographic_resolution=None,  # Can be enhanced later
            temporal_resolution=None,  # Can be enhanced later
            update_cadence=None,  # Can be enhanced later
            requires_key=source.requires_key,
            config_env_vars=(
                source.required_env_vars if source.required_env_vars else None
            ),
            endpoint_template=None,  # Can be enhanced later
            license_tag=None,  # Can be enhanced later
            license_note=None,  # Can be enhanced later
        )
    except Exception as e:
        logger.warning(
            "Failed to sync source to database",
            source_id=source.id,
            error=str(e),
        )


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

    # FRED is always treated as active (public data source, no key UX)
    if source.id == "fred_economic":
        return status_result

    # Handle sources that require a key
    if source.requires_key:
        missing = _check_missing_env_vars(source.required_env_vars)
        if missing:
            if source.can_run_without_key:
                # Optional source: mark as inactive (not needs_key) so UI can show it gracefully
                status_result["status"] = "inactive"
                status_result["ok"] = False  # Still not OK, but graceful
                status_result["error_type"] = "missing_key"
                missing_vars_str = ", ".join(missing)
                status_result["details"] = (
                    f"{source.display_name} API not configured; using baseline indicators only."
                )
            else:
                # Required source: mark as needs_key (blocking)
                status_result["status"] = "needs_key"
                status_result["ok"] = False
                status_result["error_type"] = "missing_key"
                missing_vars_str = ", ".join(missing)
                status_result["details"] = (
                    f"Set {missing_vars_str} to enable {source.display_name}. See .env.example and docs."
                )
            return status_result

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

    # Try to enrich with DB health data if available
    db = _get_registry_db()
    if db is not None:
        try:
            db_health = db.get_source_health(source.id)
            if db_health:
                # Merge DB health status if available
                db_status = db_health.get("status")
                if db_status and db_status != "Active":
                    # Prefer DB status if it indicates a problem
                    status_result["status"] = db_status.lower()
                    if db_status in ["Degraded", "Disabled", "NotConfigured"]:
                        status_result["ok"] = False
                # Add freshness/coverage if available
                if db_health.get("freshness_seconds") is not None:
                    status_result["freshness_seconds"] = db_health["freshness_seconds"]
                if db_health.get("coverage_pct") is not None:
                    status_result["coverage_pct"] = db_health["coverage_pct"]
        except Exception as e:
            logger.debug(
                "Failed to get DB health for source", source_id=source.id, error=str(e)
            )

    return status_result


def register_source(source: SourceDefinition) -> None:
    """Register a source in the registry."""
    SOURCE_REGISTRY[source.id] = source
    # Sync to database if available
    _sync_source_to_db(source)


def get_all_sources() -> Dict[str, SourceDefinition]:
    """Get all registered sources."""
    # Try to load from DB first (read-through), then fall back to in-memory
    db = _get_registry_db()
    if db is not None:
        try:
            db.get_all_sources()  # currently unused; kept for potential future merge logic
            # If DB has sources, we could merge them, but for now we keep
            # in-memory as primary and DB as persistence layer
            # This maintains backward compatibility
        except Exception as e:
            logger.debug("Failed to load sources from DB", error=str(e))

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

    # FRED economic data (public data, no key required - same as other public data sources)
    register_source(
        SourceDefinition(
            id="fred_economic",
            display_name="FRED Economic Data",
            category="economic",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Federal Reserve Economic Data (FRED): GDP growth, unemployment rate, consumer sentiment, CPI inflation, jobless claims. Public data, no API key required.",
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

    # Air quality (OpenAQ - no key required)
    register_source(
        SourceDefinition(
            id="openaq_air_quality",
            display_name="OpenAQ Air Quality",
            category="environmental",
            requires_key=False,
            required_env_vars=[],
            can_run_without_key=True,
            description="Air quality measurements (PM2.5, PM10, AQI) from OpenAQ global monitoring network. Public data, no API key required.",
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
