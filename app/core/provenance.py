# SPDX-License-Identifier: PROPRIETARY
"""Provenance and data quality transparency.

This module provides provenance metadata and data quality transparency by tracking:
- Data source attribution per factor/sub-index
- Freshness/latency indicators
- Coverage/completeness metrics
- Known biases & limitations

All provenance metadata is purely derived from existing analytics outputs without
changing any numerical computations.
"""
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger("core.provenance")


# Known data source metadata (derived from codebase analysis)
SOURCE_METADATA = {
    "yfinance": {
        "name": "Yahoo Finance",
        "type": "api",
        "authority": "primary",
        "update_frequency_hours": 1,
        "known_biases": [],
        "geographic_coverage": "global",
    },
    "FRED": {
        "name": "Federal Reserve Economic Data",
        "type": "api",
        "authority": "primary",
        "update_frequency_hours": 24,
        "known_biases": ["US-focused"],
        "geographic_coverage": "US",
    },
    "Open-Meteo": {
        "name": "Open-Meteo Weather API",
        "type": "api",
        "authority": "primary",
        "update_frequency_hours": 1,
        "known_biases": [],
        "geographic_coverage": "global",
    },
    "USGS": {
        "name": "US Geological Survey",
        "type": "api",
        "authority": "primary",
        "update_frequency_hours": 24,
        "known_biases": ["US-focused"],
        "geographic_coverage": "US",
    },
    "search_trends_api": {
        "name": "Search Trends API",
        "type": "api",
        "authority": "proxy",
        "update_frequency_hours": 24,
        "known_biases": ["Urban skew", "Language bias"],
        "geographic_coverage": "global",
    },
    "GDELT": {
        "name": "GDELT Project",
        "type": "api",
        "authority": "proxy",
        "update_frequency_hours": 15,
        "known_biases": ["Media bias", "Language bias"],
        "geographic_coverage": "global",
    },
    "public_health_api": {
        "name": "Public Health API",
        "type": "api",
        "authority": "primary",
        "update_frequency_hours": 24,
        "known_biases": [],
        "geographic_coverage": "varies",
    },
    "OWID": {
        "name": "Our World in Data",
        "type": "api",
        "authority": "primary",
        "update_frequency_hours": 24,
        "known_biases": [],
        "geographic_coverage": "global",
    },
    "political_ingestion": {
        "name": "Political Data Ingestion",
        "type": "proxy",
        "authority": "secondary",
        "update_frequency_hours": 24,
        "known_biases": ["Source-dependent"],
        "geographic_coverage": "varies",
    },
    "crime_ingestion": {
        "name": "Crime Data Ingestion",
        "type": "proxy",
        "authority": "secondary",
        "update_frequency_hours": 24,
        "known_biases": ["Reporting bias", "Geographic bias"],
        "geographic_coverage": "varies",
    },
    "misinformation_ingestion": {
        "name": "Misinformation Data Ingestion",
        "type": "proxy",
        "authority": "secondary",
        "update_frequency_hours": 12,
        "known_biases": ["Detection bias", "Language bias"],
        "geographic_coverage": "varies",
    },
    "social_cohesion_ingestion": {
        "name": "Social Cohesion Data Ingestion",
        "type": "proxy",
        "authority": "secondary",
        "update_frequency_hours": 24,
        "known_biases": ["Sampling bias"],
        "geographic_coverage": "varies",
    },
    "default": {
        "name": "Default Fallback",
        "type": "synthetic",
        "authority": "proxy",
        "update_frequency_hours": None,
        "known_biases": ["No real data"],
        "geographic_coverage": "none",
    },
}


def classify_freshness(
    data_age_hours: Optional[float],
    expected_frequency_hours: Optional[int],
) -> str:
    """
    Classify data freshness based on age and expected update frequency.

    Args:
        data_age_hours: Age of data in hours (None if unknown)
        expected_frequency_hours: Expected update frequency in hours (None if unknown)

    Returns:
        Classification: "fresh", "delayed", or "stale"
    """
    if data_age_hours is None:
        return "unknown"

    if expected_frequency_hours is None:
        # Default thresholds if frequency unknown
        if data_age_hours < 24:
            return "fresh"
        elif data_age_hours < 72:
            return "delayed"
        else:
            return "stale"

    # Classify based on expected frequency
    if data_age_hours <= expected_frequency_hours * 1.5:
        return "fresh"
    elif data_age_hours <= expected_frequency_hours * 3:
        return "delayed"
    else:
        return "stale"


def compute_source_provenance(
    source_name: str,
    data_age_hours: Optional[float] = None,
    coverage_ratio: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute provenance metadata for a data source.

    Args:
        source_name: Source identifier (e.g., "yfinance", "FRED")
        data_age_hours: Age of data in hours (None if unknown)
        coverage_ratio: Coverage ratio (actual / expected, None if unknown)

    Returns:
        Dictionary with provenance metadata
    """
    source_meta = SOURCE_METADATA.get(
        source_name,
        {
            "name": source_name,
            "type": "unknown",
            "authority": "unknown",
            "update_frequency_hours": None,
            "known_biases": [],
            "geographic_coverage": "unknown",
        },
    )

    freshness_classification = classify_freshness(
        data_age_hours,
        source_meta.get("update_frequency_hours"),
    )

    provenance = {
        "source_name": source_name,
        "source_display_name": source_meta["name"],
        "source_type": source_meta["type"],
        "authority_level": source_meta["authority"],
        "geographic_coverage": source_meta["geographic_coverage"],
        "known_biases": source_meta["known_biases"],
    }

    if data_age_hours is not None:
        provenance["data_age_hours"] = float(data_age_hours)
        provenance["freshness_classification"] = freshness_classification
        if source_meta.get("update_frequency_hours"):
            provenance["expected_update_frequency_hours"] = source_meta[
                "update_frequency_hours"
            ]

    if coverage_ratio is not None:
        provenance["coverage_ratio"] = float(coverage_ratio)
        if coverage_ratio < 0.5:
            provenance["coverage_classification"] = "low"
        elif coverage_ratio < 0.8:
            provenance["coverage_classification"] = "moderate"
        else:
            provenance["coverage_classification"] = "high"

    return provenance


def compute_factor_provenance(
    factor_id: str,
    source: str,
    has_data: bool,
    data_age_hours: Optional[float] = None,
    coverage_ratio: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute provenance metadata for a factor.

    Args:
        factor_id: Factor identifier
        source: Data source name
        has_data: Whether factor has real data (vs default/fallback)
        data_age_hours: Age of data in hours (None if unknown)
        coverage_ratio: Coverage ratio (None if unknown)

    Returns:
        Dictionary with factor provenance metadata
    """
    source_provenance = compute_source_provenance(
        source, data_age_hours, coverage_ratio
    )

    factor_provenance = {
        "factor_id": factor_id,
        "source_provenance": source_provenance,
        "has_real_data": has_data,
    }

    # Add data quality flags
    if not has_data:
        factor_provenance["data_quality_flags"] = ["no_real_data"]
    elif source_provenance.get("freshness_classification") == "stale":
        factor_provenance["data_quality_flags"] = ["stale_data"]
    elif source_provenance.get("coverage_classification") == "low":
        factor_provenance["data_quality_flags"] = ["low_coverage"]
    else:
        factor_provenance["data_quality_flags"] = []

    return factor_provenance


def compute_sub_index_provenance(
    sub_index_name: str,
    component_sources: List[str],
    component_has_data: List[bool],
    data_age_hours: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute provenance metadata for a sub-index.

    Args:
        sub_index_name: Sub-index name
        component_sources: List of source names for components
        component_has_data: List of booleans indicating if components have real data
        data_age_hours: Age of data in hours (None if unknown)

    Returns:
        Dictionary with sub-index provenance metadata
    """
    # Aggregate source information
    unique_sources = list(set(component_sources))
    source_provenances = [
        compute_source_provenance(source, data_age_hours) for source in unique_sources
    ]

    # Compute coverage
    real_data_count = sum(component_has_data)
    total_components = len(component_has_data)
    coverage_ratio = real_data_count / total_components if total_components > 0 else 0.0

    # Determine primary source (most authoritative)
    primary_source = None
    for prov in source_provenances:
        if prov["authority_level"] == "primary":
            primary_source = prov["source_name"]
            break
    if not primary_source and source_provenances:
        primary_source = source_provenances[0]["source_name"]

    # Aggregate known biases
    all_biases = []
    for prov in source_provenances:
        all_biases.extend(prov.get("known_biases", []))
    unique_biases = list(set(all_biases))

    return {
        "sub_index_name": sub_index_name,
        "sources": unique_sources,
        "source_provenances": source_provenances,
        "primary_source": primary_source,
        "coverage_ratio": float(coverage_ratio),
        "coverage_classification": (
            "high"
            if coverage_ratio >= 0.8
            else "moderate" if coverage_ratio >= 0.5 else "low"
        ),
        "known_biases": unique_biases,
        "component_count": total_components,
        "real_data_count": real_data_count,
    }


def compute_aggregate_provenance(
    sub_index_provenances: Dict[str, Dict[str, Any]],
    factor_provenances: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Compute aggregate provenance metadata across all sub-indices.

    Args:
        sub_index_provenances: Dictionary mapping sub_index_name -> provenance
        factor_provenances: Optional dictionary mapping factor_id -> provenance

    Returns:
        Dictionary with aggregate provenance metadata
    """
    # Aggregate all sources
    all_sources = set()
    all_biases = set()
    coverage_ratios = []

    for prov in sub_index_provenances.values():
        all_sources.update(prov.get("sources", []))
        all_biases.update(prov.get("known_biases", []))
        coverage_ratios.append(prov.get("coverage_ratio", 0.0))

    avg_coverage = (
        sum(coverage_ratios) / len(coverage_ratios) if coverage_ratios else 0.0
    )

    # Count source types
    source_type_counts = {}
    authority_counts = {}
    for prov in sub_index_provenances.values():
        for source_prov in prov.get("source_provenances", []):
            source_type = source_prov.get("source_type", "unknown")
            authority = source_prov.get("authority_level", "unknown")
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
            authority_counts[authority] = authority_counts.get(authority, 0) + 1

    return {
        "total_sources": len(all_sources),
        "unique_sources": list(all_sources),
        "source_type_distribution": source_type_counts,
        "authority_distribution": authority_counts,
        "average_coverage_ratio": float(avg_coverage),
        "aggregate_coverage_classification": (
            "high"
            if avg_coverage >= 0.8
            else "moderate" if avg_coverage >= 0.5 else "low"
        ),
        "known_biases": list(all_biases),
        "sub_index_count": len(sub_index_provenances),
    }


def compose_provenance(
    subindex_details: Dict[str, Dict[str, Any]],
    data_timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Compose complete provenance analysis from sub-index details.

    This function is purely derived - it does not change any numerical outputs.

    Args:
        subindex_details: Sub-index details dictionary (from get_subindex_details)
        data_timestamp: Timestamp of data (None if unknown)

    Returns:
        Dictionary with:
        - sub_index_provenances: Provenance per sub-index
        - factor_provenances: Provenance per factor (if available)
        - aggregate_provenance: Aggregate provenance metadata
        - metadata: Provenance generation metadata
    """
    # Compute data age if timestamp provided
    data_age_hours = None
    if data_timestamp:
        now = datetime.now(timezone.utc)
        if isinstance(data_timestamp, str):
            # Parse ISO format
            try:
                data_timestamp = datetime.fromisoformat(
                    data_timestamp.replace("Z", "+00:00")
                )
            except Exception:
                logger.warning(
                    "Failed to parse data timestamp", timestamp=data_timestamp
                )
                data_timestamp = None

        if isinstance(data_timestamp, datetime):
            if data_timestamp.tzinfo is None:
                data_timestamp = data_timestamp.replace(tzinfo=timezone.utc)
            delta = now - data_timestamp
            data_age_hours = delta.total_seconds() / 3600.0

    sub_index_provenances = {}
    factor_provenances = {}

    for sub_index_name, sub_index_data in subindex_details.items():
        components = sub_index_data.get("components", [])
        if not components:
            continue

        # Extract source information from components
        component_sources = []
        component_has_data = []

        for component in components:
            source = component.get("source", "default")
            component_sources.append(source)

            # Determine if component has real data
            has_data = (
                component.get("value") is not None
                and math.isfinite(component.get("value", 0))
                and component.get("value", 0.5) != 0.5  # 0.5 is often default fallback
            )
            component_has_data.append(has_data)

            # Compute factor provenance
            factor_id = component.get("id")
            if factor_id:
                factor_provenances[f"{sub_index_name}:{factor_id}"] = (
                    compute_factor_provenance(
                        factor_id=factor_id,
                        source=source,
                        has_data=has_data,
                        data_age_hours=data_age_hours,
                    )
                )

        # Compute sub-index provenance
        sub_index_provenances[sub_index_name] = compute_sub_index_provenance(
            sub_index_name=sub_index_name,
            component_sources=component_sources,
            component_has_data=component_has_data,
            data_age_hours=data_age_hours,
        )

    # Compute aggregate provenance
    aggregate_provenance = compute_aggregate_provenance(
        sub_index_provenances,
        factor_provenances if factor_provenances else None,
    )

    return {
        "sub_index_provenances": sub_index_provenances,
        "factor_provenances": factor_provenances,
        "aggregate_provenance": aggregate_provenance,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_timestamp": (
                data_timestamp.isoformat()
                if isinstance(data_timestamp, datetime)
                else None
            ),
            "data_age_hours": data_age_hours,
            "sub_indices_analyzed": len(sub_index_provenances),
            "factors_analyzed": len(factor_provenances),
        },
    }
