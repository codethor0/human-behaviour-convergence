# SPDX-License-Identifier: PROPRIETARY
"""Economic data ingestion using yfinance for market sentiment analysis."""
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import structlog
import yfinance as yf

logger = structlog.get_logger("ingestion.finance")


class MarketSentimentFetcher:
    """
    Fetch and normalize market sentiment indicators from public financial data.

    Uses VIX (Volatility Index) and SPY (S&P 500) to calculate a normalized
    stress index (0.0-1.0) where high VIX = high market stress.
    """

    def __init__(self, cache_duration_minutes: int = 5):
        """
        Initialize the market sentiment fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses (default: 5 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: Optional[pd.DataFrame] = None
        self._cache_timestamp: Optional[datetime] = None

    def fetch_stress_index(
        self, days_back: int = 30, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch and normalize market stress index from VIX and SPY.

        Args:
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'vix', 'spy', 'stress_index']
            stress_index is normalized to 0.0-1.0 where 1.0 = maximum stress
        """
        # Check cache validity
        if use_cache and self._cache is not None and self._cache_timestamp is not None:
            age_minutes = (datetime.now() - self._cache_timestamp).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info(
                    "Using cached market sentiment data", age_minutes=age_minutes
                )
                return self._cache.copy()

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(
                days=days_back + 5
            )  # Extra days for weekends

            logger.info(
                "Fetching market sentiment data",
                start_date=start_date.date().isoformat(),
                end_date=end_date.date().isoformat(),
            )

            # Fetch VIX (Volatility Index) - higher VIX = higher stress
            vix_ticker = yf.Ticker("^VIX")
            vix_data = vix_ticker.history(start=start_date, end=end_date, interval="1d")

            # Fetch SPY (S&P 500 ETF) - lower SPY = higher stress (inverse correlation)
            spy_ticker = yf.Ticker("SPY")
            spy_data = spy_ticker.history(start=start_date, end=end_date, interval="1d")

            if vix_data.empty or spy_data.empty:
                logger.warning(
                    "Empty data returned from yfinance",
                    vix_empty=vix_data.empty,
                    spy_empty=spy_data.empty,
                )
                # Return empty DataFrame with correct structure
                return pd.DataFrame(
                    columns=["timestamp", "vix", "spy", "stress_index"],
                    dtype=float,
                )

            # Normalize timestamps to date only (remove time component)
            vix_data.index = pd.to_datetime(vix_data.index).normalize()
            spy_data.index = pd.to_datetime(spy_data.index).normalize()

            # Extract Close prices
            vix_close = vix_data["Close"].rename("vix")
            spy_close = spy_data["Close"].rename("spy")

            # Merge on date index using outer join to preserve all dates
            # Then forward-fill missing values within a small window (2 days)
            merged = pd.DataFrame({"vix": vix_close, "spy": spy_close})

            # Sort by date
            merged = merged.sort_index()

            # Forward fill missing values within 2 days (to handle minor date misalignments)
            merged = merged.ffill(limit=2)

            # Drop rows where both are still NaN (no data available)
            merged = merged.dropna(how="all")

            # For rows with only one value, use a default for the missing one
            # This allows us to still compute stress index even if one ticker is missing
            if not merged.empty:
                # If VIX is missing but SPY exists, use median VIX value
                if merged["vix"].isna().any():
                    vix_median = merged["vix"].median()
                    if pd.isna(vix_median):
                        vix_median = 20.0  # Default VIX value
                    merged["vix"] = merged["vix"].fillna(vix_median)

                # If SPY is missing but VIX exists, use median SPY value
                if merged["spy"].isna().any():
                    spy_median = merged["spy"].median()
                    if pd.isna(spy_median):
                        spy_median = 400.0  # Default SPY value
                    merged["spy"] = merged["spy"].fillna(spy_median)

            if merged.empty:
                logger.warning(
                    "No market data available after merge",
                    vix_rows=len(vix_close),
                    spy_rows=len(spy_close),
                )
                return pd.DataFrame(
                    columns=["timestamp", "vix", "spy", "stress_index"],
                    dtype=float,
                )

            # Calculate stress index
            # VIX normalization: Use absolute thresholds based on historical VIX ranges
            # VIX typically ranges 10-80, with:
            #   < 15: Very low stress (0.0-0.2)
            #   15-20: Low stress (0.2-0.4)
            #   20-30: Moderate stress (0.4-0.6)
            #   30-40: High stress (0.6-0.8)
            #   > 40: Very high stress (0.8-1.0)
            # Use a sigmoid-like function for smooth transitions
            def normalize_vix(vix_value):
                # Clamp to reasonable range (10-80)
                vix_clamped = max(10.0, min(80.0, vix_value))
                # Normalize: 10 -> 0.0, 20 -> 0.4, 30 -> 0.6, 40 -> 0.8, 80 -> 1.0
                if vix_clamped <= 15:
                    return 0.1 + (vix_clamped - 10) / 5 * 0.1  # 10->0.1, 15->0.2
                elif vix_clamped <= 20:
                    return 0.2 + (vix_clamped - 15) / 5 * 0.2  # 15->0.2, 20->0.4
                elif vix_clamped <= 30:
                    return 0.4 + (vix_clamped - 20) / 10 * 0.2  # 20->0.4, 30->0.6
                elif vix_clamped <= 40:
                    return 0.6 + (vix_clamped - 30) / 10 * 0.2  # 30->0.6, 40->0.8
                else:
                    return 0.8 + min(
                        0.2, (vix_clamped - 40) / 40 * 0.2
                    )  # 40->0.8, 80->1.0

            vix_norm = merged["vix"].apply(normalize_vix)

            # SPY normalization: Use percentile-based approach with absolute context
            # SPY has been in range ~300-700 in recent years
            # Use rolling percentile but with absolute floor/ceiling
            spy_min_window = merged["spy"].min()
            spy_max_window = merged["spy"].max()
            spy_range = spy_max_window - spy_min_window

            # If window range is too small, use absolute range (300-700)
            if spy_range < 50:
                spy_min_abs = 300.0
                spy_max_abs = 700.0
                spy_range_abs = 400.0
            else:
                # Use window range but expand slightly for stability
                spy_min_abs = spy_min_window - 20
                spy_max_abs = spy_max_window + 20
                spy_range_abs = spy_max_abs - spy_min_abs

            # Inverse relationship: lower SPY = higher stress
            spy_norm_inv = 1.0 - ((merged["spy"] - spy_min_abs) / spy_range_abs).clip(
                0.0, 1.0
            )

            # Combined stress index: weighted average (VIX weighted more heavily)
            stress_index = (vix_norm * 0.6) + (spy_norm_inv * 0.4)

            # Create result DataFrame
            result = pd.DataFrame(
                {
                    "timestamp": merged.index,
                    "vix": merged["vix"].values,
                    "spy": merged["spy"].values,
                    "stress_index": stress_index.values,
                }
            )

            # Sort by timestamp and reset index
            result = result.sort_values("timestamp").reset_index(drop=True)

            # Clip stress_index to valid range [0.0, 1.0]
            result["stress_index"] = result["stress_index"].clip(0.0, 1.0)

            # Update cache
            self._cache = result.copy()
            self._cache_timestamp = datetime.now()

            logger.info(
                "Market sentiment data fetched successfully",
                rows=len(result),
                stress_index_range=(
                    result["stress_index"].min(),
                    result["stress_index"].max(),
                ),
            )

            return result

        except Exception as e:
            logger.error(
                "Error fetching market sentiment data", error=str(e), exc_info=True
            )
            # Return empty DataFrame with correct structure on error
            return pd.DataFrame(
                columns=["timestamp", "vix", "spy", "stress_index"],
                dtype=float,
            )
