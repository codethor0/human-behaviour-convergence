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

            # Merge on date index
            merged = pd.DataFrame({"vix": vix_close, "spy": spy_close})
            merged = merged.dropna()

            if merged.empty:
                logger.warning("No overlapping dates between VIX and SPY data")
                return pd.DataFrame(
                    columns=["timestamp", "vix", "spy", "stress_index"],
                    dtype=float,
                )

            # Calculate stress index
            # VIX normalization: historical range roughly 10-80, normalize to 0-1
            vix_min, vix_max = merged["vix"].min(), merged["vix"].max()
            if vix_max > vix_min:
                vix_norm = (merged["vix"] - vix_min) / (vix_max - vix_min)
            else:
                vix_norm = pd.Series([0.5] * len(merged), index=merged.index)

            # SPY normalization: inverse relationship (lower SPY = higher stress)
            spy_min, spy_max = merged["spy"].min(), merged["spy"].max()
            if spy_max > spy_min:
                spy_norm_inv = 1.0 - ((merged["spy"] - spy_min) / (spy_max - spy_min))
            else:
                spy_norm_inv = pd.Series([0.5] * len(merged), index=merged.index)

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
