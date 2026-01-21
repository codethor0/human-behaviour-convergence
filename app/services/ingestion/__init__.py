# SPDX-License-Identifier: PROPRIETARY
"""Public data ingestion services."""

# Optional connectors (future features - not required for CI startup)
try:
    from .cisa_kev import CISAKEVFetcher  # type: ignore[attr-defined]
except ImportError:
    CISAKEVFetcher = None  # type: ignore[assignment]

try:
    from .nws_alerts import NWSAlertsFetcher  # type: ignore[attr-defined]
except ImportError:
    NWSAlertsFetcher = None  # type: ignore[assignment]

try:
    from .openstates_legislative import (
        OpenStatesLegislativeFetcher,  # type: ignore[attr-defined]
    )
except ImportError:
    OpenStatesLegislativeFetcher = None  # type: ignore[assignment]

from .crime import CrimeSafetyStressFetcher
from .economic_fred import FREDEconomicFetcher
from .finance import MarketSentimentFetcher
from .gdelt_events import GDELTEventsFetcher
from .health_owid import OWIDHealthFetcher
from .misinformation import MisinformationStressFetcher
from .mobility import MobilityFetcher
from .openaq_air_quality import OpenAQAirQualityFetcher
from .openfema_emergency_management import OpenFEMAEmergencyManagementFetcher
from .political import PoliticalStressFetcher
from .processor import DataHarmonizer
from .public_health import PublicHealthFetcher
from .search_trends import SearchTrendsFetcher
from .social_cohesion import SocialCohesionStressFetcher
from .usgs_earthquakes import USGSEarthquakeFetcher
from .weather import EnvironmentalImpactFetcher

__all__ = [
    "MarketSentimentFetcher",
    "FREDEconomicFetcher",
    "EnvironmentalImpactFetcher",
    "DataHarmonizer",
    "SearchTrendsFetcher",
    "PublicHealthFetcher",
    "MobilityFetcher",
    "GDELTEventsFetcher",
    "OWIDHealthFetcher",
    "USGSEarthquakeFetcher",
    "OpenFEMAEmergencyManagementFetcher",
    "OpenAQAirQualityFetcher",
    "PoliticalStressFetcher",
    "CrimeSafetyStressFetcher",
    "MisinformationStressFetcher",
    "SocialCohesionStressFetcher",
]

# Add optional connectors to __all__ only if they are available
if OpenStatesLegislativeFetcher is not None:
    __all__.append("OpenStatesLegislativeFetcher")
if NWSAlertsFetcher is not None:
    __all__.append("NWSAlertsFetcher")
if CISAKEVFetcher is not None:
    __all__.append("CISAKEVFetcher")
