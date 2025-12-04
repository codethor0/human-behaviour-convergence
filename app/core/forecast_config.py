# SPDX-License-Identifier: PROPRIETARY
"""Forecast location configuration preparation.

Prepares structured configuration objects for behavioral forecasting,
using LocationNormalizer to resolve locations and providing state-like
labels suitable for dataset fields.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.core.location_normalizer import LocationNormalizer
from app.core.regions import Region, get_region_by_id


@dataclass
class ForecastLocationConfig:
    """Complete location configuration for a forecast."""

    region_id: str
    region_label: str
    state_like_label: str
    state_code: Optional[str]
    admin_level: str
    best_guess: bool
    alternatives: List[str]
    reason: str


@dataclass
class ForecastConfig:
    """Complete forecast configuration object."""

    task: str = "prepare_forecast_location_config"
    input_description: Optional[str] = None
    user_selected_region_id: Optional[str] = None
    normalized_location: Optional[ForecastLocationConfig] = None
    forecast_request: Optional[Dict[str, any]] = None


# State code mapping for US states and DC
STATE_CODE_MAP = {
    "us_al": "AL",
    "us_ak": "AK",
    "us_az": "AZ",
    "us_ar": "AR",
    "us_ca": "CA",
    "us_co": "CO",
    "us_ct": "CT",
    "us_de": "DE",
    "us_dc": "DC",
    "us_fl": "FL",
    "us_ga": "GA",
    "us_hi": "HI",
    "us_id": "ID",
    "us_il": "IL",
    "us_in": "IN",
    "us_ia": "IA",
    "us_ks": "KS",
    "us_ky": "KY",
    "us_la": "LA",
    "us_me": "ME",
    "us_md": "MD",
    "us_ma": "MA",
    "us_mi": "MI",
    "us_mn": "MN",
    "us_ms": "MS",
    "us_mo": "MO",
    "us_mt": "MT",
    "us_ne": "NE",
    "us_nv": "NV",
    "us_nh": "NH",
    "us_nj": "NJ",
    "us_nm": "NM",
    "us_ny": "NY",
    "us_nc": "NC",
    "us_nd": "ND",
    "us_oh": "OH",
    "us_ok": "OK",
    "us_or": "OR",
    "us_pa": "PA",
    "us_ri": "RI",
    "us_sc": "SC",
    "us_sd": "SD",
    "us_tn": "TN",
    "us_tx": "TX",
    "us_ut": "UT",
    "us_vt": "VT",
    "us_va": "VA",
    "us_wa": "WA",
    "us_wv": "WV",
    "us_wi": "WI",
    "us_wy": "WY",
}

# State-like label mapping for cities (what state they're in)
CITY_STATE_MAP = {
    "city_nyc": "New York",
    "city_la": "California",
    # Add more as needed
}


class ForecastConfigBuilder:
    """Builds forecast configuration objects from location descriptions."""

    def __init__(self):
        """Initialize the builder with LocationNormalizer."""
        self.normalizer = LocationNormalizer()

    def prepare_config(
        self,
        description: Optional[str] = None,
        user_selected_region_id: Optional[str] = None,
        historical_days: int = 365,
        forecast_horizon_days: int = 30,
    ) -> ForecastConfig:
        """
        Prepare a forecast configuration from location description or user selection.

        Args:
            description: Natural language description of event/location
            user_selected_region_id: Explicitly selected region_id (takes precedence)
            historical_days: Number of historical days for forecast (default 365)
            forecast_horizon_days: Forecast horizon in days (default 30)

        Returns:
            ForecastConfig with normalized location and forecast request
        """
        # If user explicitly selected a region_id, use it directly
        if user_selected_region_id:
            region = get_region_by_id(user_selected_region_id)
            if region:
                location_config = self._build_location_config_from_region(
                    region,
                    best_guess=False,
                    alternatives=[],
                    reason="User explicitly selected region_id",
                )
            else:
                # Invalid region_id - try to normalize from description
                location_config = self._normalize_from_description(description)
        else:
            # Use LocationNormalizer to resolve from description
            location_config = self._normalize_from_description(description)

        # Build forecast request
        forecast_request = {
            "region_id": location_config.region_id,
            "historical_days": historical_days,
            "forecast_horizon_days": forecast_horizon_days,
        }

        return ForecastConfig(
            task="prepare_forecast_location_config",
            input_description=description,
            user_selected_region_id=user_selected_region_id,
            normalized_location=location_config,
            forecast_request=forecast_request,
        )

    def _normalize_from_description(
        self, description: Optional[str]
    ) -> ForecastLocationConfig:
        """
        Normalize location from description using LocationNormalizer.

        Args:
            description: Natural language description

        Returns:
            ForecastLocationConfig with resolved location
        """
        if not description:
            raise ValueError(
                "Description is required when user_selected_region_id is not provided"
            )

        # Use LocationNormalizer
        result = self.normalizer.normalize(description)

        # Extract region_id and metadata
        if result.normalized_location:
            region_id = result.normalized_location.region_id
            alternatives = result.normalized_location.alternatives
            reason = result.normalized_location.reason
            best_guess = False  # Normalized location is definitive
        elif result.best_guess_region_id:
            region_id = result.best_guess_region_id
            region = get_region_by_id(region_id)
            alternatives = result.alternate_region_ids
            reason = (
                result.ambiguity_reason
                or "LocationNormalizer provided best guess with ambiguity"
            )
            best_guess = True
        else:
            raise ValueError(
                f"Could not resolve location from description: {description}"
            )

        # Get region object to build full config
        region = get_region_by_id(region_id)
        if not region:
            raise ValueError(f"Region not found: {region_id}")

        return self._build_location_config_from_region(
            region, best_guess=best_guess, alternatives=alternatives, reason=reason
        )

    def _build_location_config_from_region(
        self,
        region: Region,
        best_guess: bool = False,
        alternatives: Optional[List[str]] = None,
        reason: str = "",
    ) -> ForecastLocationConfig:
        """
        Build ForecastLocationConfig from a Region object.

        Args:
            region: Region object
            best_guess: Whether this is a best guess (ambiguous)
            alternatives: List of alternative region_ids
            reason: Reason for this configuration

        Returns:
            ForecastLocationConfig with state-like labels
        """
        if alternatives is None:
            alternatives = []

        # Determine state_like_label and state_code
        state_like_label, state_code, admin_level = self._get_state_like_info(region)

        return ForecastLocationConfig(
            region_id=region.id,
            region_label=region.name,
            state_like_label=state_like_label,
            state_code=state_code,
            admin_level=admin_level,
            best_guess=best_guess,
            alternatives=alternatives,
            reason=reason,
        )

    def _get_state_like_info(self, region: Region) -> tuple[str, Optional[str], str]:
        """
        Get state-like label, state code, and admin level for a region.

        Args:
            region: Region object

        Returns:
            Tuple of (state_like_label, state_code, admin_level)
        """
        # US States (including DC)
        if region.region_type == "state" and region.country == "US":
            state_code = STATE_CODE_MAP.get(region.id)
            admin_level = "district" if region.id == "us_dc" else "state"
            return (region.name, state_code, admin_level)

        # Cities
        if region.region_type == "city":
            # For US cities, use the state they're in
            if region.country == "US":
                state_like_label = CITY_STATE_MAP.get(region.id, region.name)
                # Try to get state code from city's state
                state_code = self._get_city_state_code(region)
                admin_level = "city"
                return (state_like_label, state_code, admin_level)
            else:
                # Non-US cities
                admin_level = "city"
                return (region.name, None, admin_level)

        # Countries (if any)
        if region.region_type == "country":
            return (region.name, None, "country")

        # Default
        return (region.name, None, "region")

    def _get_city_state_code(self, region: Region) -> Optional[str]:
        """Get state code for a US city."""
        # Map city to its state's region_id, then get state code
        city_to_state = {
            "city_nyc": "us_ny",
            "city_la": "us_ca",
            # Add more as needed
        }
        state_region_id = city_to_state.get(region.id)
        if state_region_id:
            return STATE_CODE_MAP.get(state_region_id)
        return None


def prepare_forecast_config(
    description: Optional[str] = None,
    user_selected_region_id: Optional[str] = None,
    historical_days: int = 365,
    forecast_horizon_days: int = 30,
) -> Dict:
    """
    Convenience function to prepare forecast configuration.

    Args:
        description: Natural language description of event/location
        user_selected_region_id: Explicitly selected region_id
        historical_days: Number of historical days (default 365)
        forecast_horizon_days: Forecast horizon in days (default 30)

    Returns:
        Dictionary representation of ForecastConfig suitable for JSON serialization

    Example:
        >>> config = prepare_forecast_config(
        ...     "Two West Virginia National Guardsmen were shot near the "
        ...     "White House in Washington, D.C."
        ... )
        >>> config["normalized_location"]["region_id"]
        'us_dc'
    """
    builder = ForecastConfigBuilder()
    config = builder.prepare_config(
        description=description,
        user_selected_region_id=user_selected_region_id,
        historical_days=historical_days,
        forecast_horizon_days=forecast_horizon_days,
    )

    # Convert to dictionary for JSON serialization
    return {
        "task": config.task,
        "input": {
            "description": config.input_description,
            "user_selected_region_id": config.user_selected_region_id,
        },
        "normalized_location": {
            "region_id": config.normalized_location.region_id,
            "region_label": config.normalized_location.region_label,
            "state_like_label": config.normalized_location.state_like_label,
            "state_code": config.normalized_location.state_code,
            "admin_level": config.normalized_location.admin_level,
            "best_guess": config.normalized_location.best_guess,
            "alternatives": config.normalized_location.alternatives,
            "reason": config.normalized_location.reason,
        },
        "forecast_request": config.forecast_request,
    }
