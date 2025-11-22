# SPDX-License-Identifier: MIT-0
"""Base classes and utilities for public data connectors."""
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable

import h3
import pandas as pd
import structlog

logger = structlog.get_logger("connector")

# PII detection regex (basic patterns)
PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # email
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    r"\b\d{16}\b",  # credit card
]


def ethical_check(func: Callable) -> Callable:
    """
    Decorator to enforce ethical data practices:
    - k-anonymity ≥ 15 (no individual count < 15)
    - geo-precision ≤ H3-9 (≈ 0.1 km²)
    - drop any text containing PII regex
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> pd.DataFrame:
        df = func(*args, **kwargs)

        # Drop PII from text columns
        for col in df.select_dtypes(include=["object"]).columns:
            for pattern in PII_PATTERNS:
                df[col] = (
                    df[col].astype(str).str.replace(pattern, "[REDACTED]", regex=True)
                )

        # K-anonymity check (if count column exists)
        if "count" in df.columns:
            rows_before = len(df)
            df = df[df["count"] >= 15]
            rows_dropped = rows_before - len(df)
            logger.info("k-anonymity filter applied", rows_dropped=rows_dropped)

        # Geo-precision check (if h3 column exists)
        if "h3_9" in df.columns:
            # Ensure all H3 indices are at resolution 9 or coarser
            df["h3_res"] = df["h3_9"].apply(lambda x: h3.h3_get_resolution(x))
            df = df[df["h3_res"] <= 9]
            df = df.drop(columns=["h3_res"])

        return df

    return wrapper


class AbstractSync(ABC):
    """Abstract base class for public data connectors."""

    def __init__(self) -> None:
        self.logger = logger.bind(connector=self.__class__.__name__)

    @abstractmethod
    def pull(self) -> pd.DataFrame:
        """
        Pull data from the public source.
        Returns a DataFrame with source-specific schema.
        """
        pass

    def h3_index(
        self, df: pd.DataFrame, lat_col: str, lon_col: str, res: int = 9
    ) -> pd.DataFrame:
        """
        Add H3 index column to a DataFrame with lat/lon columns.

        Args:
            df: Input DataFrame with geographic coordinates
            lat_col: Name of latitude column
            lon_col: Name of longitude column
            res: H3 resolution (default 9, ≈ 0.1 km²)

        Returns:
            DataFrame with added h3_{res} column
        """
        df[f"h3_{res}"] = df.apply(
            lambda row: h3.geo_to_h3(row[lat_col], row[lon_col], res), axis=1
        )
        return df
