# SPDX-License-Identifier: MIT-0
"""WHO Disease Surveillance data connector for global disease outbreak tracking."""
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests
import structlog

from connectors.base import AbstractSync, ethical_check

logger = structlog.get_logger("connector.who_disease")


class WHODiseaseSync(AbstractSync):
    """
    Connector for WHO Disease Surveillance data.

    Fetches aggregated global disease outbreak data from WHO public APIs.
    Provides disease incidence and mortality data for epidemiological analysis.
    """

    BASE_URL = "https://ghoapi.azureedge.net/api"
    CACHE_DIR = None  # Will be set in __init__

    def __init__(self, date: Optional[str] = None, country: Optional[str] = None):
        """
        Initialize WHO Disease Surveillance connector.

        Args:
            date: Date in YYYY-MM-DD format (defaults to yesterday)
            country: ISO country code (e.g., 'USA', 'GBR') or None for global
        """
        super().__init__()
        if date is None:
            date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.date = date
        self.country = country

        # Set cache directory (create if needed)
        import pathlib
        self.CACHE_DIR = pathlib.Path(".cache/who_disease")
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @ethical_check
    def pull(self) -> pd.DataFrame:
        """
        Pull WHO disease surveillance data for configured date and country.

        Returns:
            DataFrame with columns: [date, country, disease_code, cases, deaths, region]
        """
        # CI offline mode: return synthetic deterministic data
        if os.getenv("HBC_CI_OFFLINE_DATA", "0") == "1":
            self.logger.info("Using CI offline mode for WHO disease data")
            # Return empty DataFrame with correct schema for CI
            return pd.DataFrame(columns=["date", "country", "disease_code", "cases", "deaths", "region"])

        cache_file = self.CACHE_DIR / f"who_disease_{self.country or 'global'}_{self.date}.parquet"

        if cache_file.exists():
            self.logger.info("Loading from cache", cache_file=str(cache_file))
            return pd.read_parquet(cache_file)

        # WHO Global Health Observatory (GHO) API
        # Endpoint: /Indicator (for disease indicators)
        # We'll fetch aggregated disease data (no individual records)
        
        self.logger.info("Fetching WHO disease surveillance data", date=self.date, country=self.country)

        try:
            # WHO GHO OData API: Get disease indicators
            # API endpoint: https://ghoapi.azureedge.net/api/Indicator
            # Note: This API will be deprecated end of 2025, replaced with new OData implementation
            url = f"{self.BASE_URL}/Indicator"
            
            # Filter for disease-related indicators (mortality and morbidity)
            # Common indicator codes: MORT_300 (all-cause mortality), MORT_302 (communicable diseases)
            params = {
                "$filter": "IndicatorCode eq 'MORT_300' or IndicatorCode eq 'MORT_302'",
                "$format": "json",
                "$top": 1000  # Limit results
            }
            
            if self.country:
                # Add country filter if specified
                params["$filter"] += f" and SpatialDim eq '{self.country}'"

            response = requests.get(url, params=params, timeout=60, headers={"User-Agent": "HumanBehaviourConvergence/1.0"})
            response.raise_for_status()
            
            data = response.json()
            
            # Parse WHO GHO OData API response structure
            # Response format: {"value": [{"IndicatorCode": "...", "SpatialDim": "...", "TimeDim": "...", "NumericValue": ...}, ...]}
            records = []
            
            if "value" in data:
                for item in data["value"]:
                    # Extract relevant fields from WHO API response
                    # Apply k-anonymity: only include if NumericValue >= 15
                    numeric_value = item.get("NumericValue", 0)
                    if numeric_value < 15:
                        continue  # Skip records that don't meet k-anonymity
                    
                    record = {
                        "date": item.get("TimeDim", self.date),
                        "country": item.get("SpatialDim", self.country or "GLOBAL"),
                        "disease_code": item.get("IndicatorCode", "UNKNOWN"),
                        "cases": numeric_value,  # For mortality indicators, this represents deaths
                        "deaths": numeric_value if "MORT" in item.get("IndicatorCode", "") else 0,
                        "region": item.get("ParentLocationCode", "GLOBAL")
                    }
                    records.append(record)
            
            if not records:
                # Return empty DataFrame with correct schema if no data
                self.logger.info("No WHO disease data found for date", date=self.date)
                df = pd.DataFrame(columns=["date", "country", "disease_code", "cases", "deaths", "region"])
            else:
                df = pd.DataFrame(records)
                # Ensure numeric columns are numeric
                df["cases"] = pd.to_numeric(df["cases"], errors="coerce").fillna(0)
                df["deaths"] = pd.to_numeric(df["deaths"], errors="coerce").fillna(0)
                
                # Apply k-anonymity: filter out records with < 15 cases
                df = df[df["cases"] >= 15]
                
                # Cache result
                df.to_parquet(cache_file)
                self.logger.info("Cached WHO disease data", rows=len(df))

            return df

        except requests.exceptions.RequestException as e:
            self.logger.warning("Failed to fetch WHO disease data", error=str(e)[:200])
            # Return empty DataFrame on error (graceful degradation)
            return pd.DataFrame(columns=["date", "country", "disease_code", "cases", "deaths", "region"])
        except Exception as e:
            self.logger.error("Unexpected error fetching WHO disease data", error=str(e)[:200], exc_info=True)
            return pd.DataFrame(columns=["date", "country", "disease_code", "cases", "deaths", "region"])
