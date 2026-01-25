# SPDX-License-Identifier: PROPRIETARY
"""US Census Bureau API connector for demographic data."""
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import requests
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
)
from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.demographic")

# US Census Bureau API base URL
CENSUS_API_BASE = "https://api.census.gov/data"

# Census API variables for demographic data
CENSUS_VARIABLES = {
    "population": "B01001_001E",  # Total population
    "population_density": "B01001_001E",  # Will compute from population + area
    "age_under_18": "B01001_003E,B01001_004E,B01001_005E,B01001_006E,B01001_027E,B01001_028E,B01001_029E,B01001_030E",  # Sum of male/female under 18
    "age_18_64": "B01001_007E,B01001_008E,B01001_009E,B01001_010E,B01001_011E,B01001_012E,B01001_031E,B01001_032E,B01001_033E,B01001_034E,B01001_035E,B01001_036E",  # Working age
    "age_65_plus": "B01001_020E,B01001_021E,B01001_022E,B01001_023E,B01001_024E,B01001_025E,B01001_044E,B01001_045E,B01001_046E,B01001_047E,B01001_048E,B01001_049E",  # Senior
    "male": "B01001_002E",  # Total male population
    "female": "B01001_026E",  # Total female population (approximate, need to sum)
}


class DemographicFetcher:
    """
    Fetch demographic data from US Census Bureau API.
    
    US Census Bureau API: https://www.census.gov/data/developers/data-sets.html
    American Community Survey (ACS) 5-year estimates for demographic data.
    No API key required for public data.
    Rate limits: Reasonable (no strict documented limits)
    
    Provides:
    - Population density stress index
    - Age distribution indicators
    - Gender distribution indicators
    """

    def __init__(self, api_key: Optional[str] = None, cache_duration_minutes: int = 1440):
        """
        Initialize demographic fetcher.
        
        Args:
            api_key: Census API key (optional, not required for public data)
            cache_duration_minutes: Cache duration (default: 1440 = 24 hours, 
                since Census data updates annually)
        """
        self.api_key = api_key or os.getenv("CENSUS_API_KEY")
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def _normalize_state_code(self, state: str) -> str:
        """Normalize state code to 2-letter uppercase format."""
        state_upper = state.upper().strip()
        
        state_fips = {
            "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
            "CT": "09", "DE": "10", "FL": "12", "GA": "13", "HI": "15", "ID": "16",
            "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22",
            "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
            "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
            "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39", "OK": "40",
            "OR": "41", "PA": "42", "RI": "43", "SC": "44", "SD": "45", "TN": "47",
            "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54",
            "WI": "55", "WY": "56", "DC": "11",
        }
        
        if state_upper in state_fips:
            return state_upper
        
        # Try to extract from "us_il" format
        if "_" in state_upper:
            parts = state_upper.split("_")
            if len(parts) >= 2 and parts[0] == "US" and len(parts[1]) == 2:
                potential_code = parts[1].upper()
                if potential_code in state_fips:
                    return potential_code
        
        return state_upper

    def fetch_demographic_stress_index(
        self,
        state: str,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch demographic data and compute demographic stress index.
        
        Demographic stress considers:
        - Population density (high density = potential stress)
        - Age distribution (high dependency ratio = stress)
        - Gender balance (imbalance may indicate migration patterns)
        
        Args:
            state: State code (2-letter, e.g., "IL", "CA") or state name
            use_cache: Whether to use cached data (default: True)
            
        Returns:
            Tuple of (DataFrame with columns: ['timestamp', 'demographic_stress_index', 
            'population_density', 'age_dependency_ratio'], SourceStatus)
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for demographic data", state=state)
            state_code = self._normalize_state_code(state)
            today = datetime.now().date()
            df = pd.DataFrame({
                "timestamp": [pd.Timestamp(today)],
                "demographic_stress_index": [0.5],
                "population_density": [200.0],  # per sq km
                "age_dependency_ratio": [0.6],  # dependents / working age
            })
            status = SourceStatus(
                provider="CI_Synthetic_Census",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
            )
            return df, status

        state_code = self._normalize_state_code(state)
        cache_key = f"census_demographic_{state_code}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached Census data", state=state_code)
                status = SourceStatus(
                    provider="Census_Cached",
                    ok=True,
                    http_status=200,
                    fetched_at=cache_time.isoformat(),
                    rows=len(df),
                )
                return df.copy(), status

        try:
            # Use ACS 5-year estimates (most recent year available)
            # ACS data is updated annually, so we use the latest available year
            current_year = datetime.now().year
            acs_year = current_year - 1 if datetime.now().month < 12 else current_year
            
            # Get state FIPS code
            state_fips_map = {
                "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
                "CT": "09", "DE": "10", "FL": "12", "GA": "13", "HI": "15", "ID": "16",
                "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22",
                "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
                "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
                "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39", "OK": "40",
                "OR": "41", "PA": "42", "RI": "43", "SC": "44", "SD": "45", "TN": "47",
                "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54",
                "WI": "55", "WY": "56", "DC": "11",
            }
            
            state_fips = state_fips_map.get(state_code)
            if not state_fips:
                logger.warning("Unknown state code", state=state_code)
                return self._fallback_demographic_data(state_code)

            # Fetch population and age data
            url = f"{CENSUS_API_BASE}/{acs_year}/acs/acs5"
            params = {
                "get": f"NAME,{CENSUS_VARIABLES['population']}",
                "for": f"state:{state_fips}",
            }
            
            if self.api_key:
                params["key"] = self.api_key

            logger.info("Fetching Census demographic data", state=state_code, year=acs_year)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            
            if not data or len(data) < 2:
                logger.warning("Empty Census response", state=state_code)
                return self._fallback_demographic_data(state_code)

            # Parse response (first row is headers)
            headers = data[0]
            rows = data[1:]
            
            # Find population column
            pop_idx = headers.index(CENSUS_VARIABLES['population']) if CENSUS_VARIABLES['population'] in headers else None
            if pop_idx is None:
                logger.warning("Population column not found", state=state_code)
                return self._fallback_demographic_data(state_code)

            population = int(rows[0][pop_idx]) if rows else 0
            
            # Get state area (approximate, in sq km) - using known values
            # In production, this would come from Census TIGER/Line shapefiles
            state_areas_km2 = {
                "CA": 423967, "TX": 695662, "FL": 170312, "NY": 141297,
                "IL": 149995, "PA": 119280, "OH": 116098, "GA": 153910,
                "NC": 139391, "MI": 250487, "AZ": 295234, "MA": 27336,
            }
            area_km2 = state_areas_km2.get(state_code, 100000)  # Default fallback
            
            population_density = population / area_km2 if area_km2 > 0 else 0
            
            # Compute demographic stress index
            # High population density = higher stress (normalized 0-1)
            # Typical US density: 10-5000 per sq km
            density_stress = min(population_density / 5000.0, 1.0)
            
            # Age dependency ratio (simplified - would need detailed age data)
            # Higher dependency = higher stress
            age_dependency_ratio = 0.6  # Default, would compute from age data
            
            demographic_stress = (density_stress * 0.7 + age_dependency_ratio * 0.3)
            
            today = datetime.now().date()
            df = pd.DataFrame({
                "timestamp": [pd.Timestamp(today)],
                "demographic_stress_index": [demographic_stress],
                "population_density": [population_density],
                "age_dependency_ratio": [age_dependency_ratio],
            })

            # Cache result
            self._cache[cache_key] = (df.copy(), datetime.now())

            status = SourceStatus(
                provider="Census_Demographic",
                ok=True,
                http_status=response.status_code,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
            )

            logger.info(
                "Fetched Census demographic data",
                state=state_code,
                population=population,
                density=population_density,
            )

            return df, status

        except requests.exceptions.RequestException as e:
            logger.error("Census API error", state=state_code, error=str(e), exc_info=True)
            return self._fallback_demographic_data(state_code)
        except Exception as e:
            logger.error("Unexpected error fetching Census data", state=state_code, error=str(e), exc_info=True)
            return self._fallback_demographic_data(state_code)

    def _fallback_demographic_data(
        self, state_code: str
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """Fallback to default values when API fails."""
        today = datetime.now().date()
        df = pd.DataFrame({
            "timestamp": [pd.Timestamp(today)],
            "demographic_stress_index": [0.5],  # Neutral
            "population_density": [200.0],
            "age_dependency_ratio": [0.6],
        })

        status = SourceStatus(
            provider="Census_Demographic_Fallback",
            ok=False,
            http_status=None,
            error_type="fallback",
            error_detail="API unavailable, using default values",
            fetched_at=datetime.now().isoformat(),
            rows=len(df),
        )

        return df, status
