# SPDX-License-Identifier: PROPRIETARY
"""Information Integrity & Misinformation Index (IIMI) data ingestion."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import structlog

logger = structlog.get_logger("ingestion.misinformation")


class MisinformationStressFetcher:
    """
    Fetch and compute Information Integrity & Misinformation Index
    from multiple sources.

    Combines signals from:
    - Rumor Amplification Index (RAI)
    - Sentiment Volatility Score (SVS)
    - Narrative Fragmentation Score (NFS)
    - Fact-Check Volume (FCV)
    - Content Authenticity Drift (CAD)

    Returns normalized IIMI (0.0-1.0) per region.
    """

    def __init__(self, cache_duration_minutes: int = 1440):
        """Initialize the misinformation stress fetcher."""
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}

    def fetch_primary_sources(
        self, region_name: str, days_back: int = 30, use_cache: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """Fetch data from primary misinformation data sources."""
        cache_key = f"misinformation_{region_name}_{days_back}"

        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached misinformation data", region=region_name)
                return {"cached": df}

        sources = {}
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        sources["rumor_amplification"] = self._fetch_rumor_amplification(
            region_name, start_date, end_date
        )
        sources["sentiment_volatility"] = self._fetch_sentiment_volatility(
            region_name, start_date, end_date
        )
        sources["narrative_fragmentation"] = self._fetch_narrative_fragmentation(
            region_name, start_date, end_date
        )
        sources["fact_check_volume"] = self._fetch_fact_check_volume(
            region_name, start_date, end_date
        )
        sources["content_authenticity"] = self._fetch_content_authenticity(
            region_name, start_date, end_date
        )

        merged = self._merge_misinformation_sources(sources, start_date, end_date)
        self._cache[cache_key] = (merged.copy(), datetime.now())

        return {"merged": merged, "components": sources}

    def _fetch_rumor_amplification(
        self, region_name: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Fetch rumor amplification indicators."""
        dates = pd.date_range(start=start_date.date(), end=end_date.date(), freq="D")
        base_rai = 0.35
        rai = base_rai + (pd.Series(range(len(dates))) % 14) * 0.05
        return pd.DataFrame(
            {
                "timestamp": dates,
                "rumor_amplification": rai.clip(0.0, 1.0),
                "confidence_level": "medium",
            }
        )

    def _fetch_sentiment_volatility(
        self, region_name: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Fetch sentiment volatility indicators."""
        dates = pd.date_range(start=start_date.date(), end=end_date.date(), freq="D")
        base_svs = 0.40
        svs = base_svs + (pd.Series(range(len(dates))) % 7) * 0.06
        return pd.DataFrame(
            {
                "timestamp": dates,
                "sentiment_volatility": svs.clip(0.0, 1.0),
                "confidence_level": "medium",
            }
        )

    def _fetch_narrative_fragmentation(
        self, region_name: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Fetch narrative fragmentation indicators."""
        dates = pd.date_range(start=start_date.date(), end=end_date.date(), freq="D")
        base_nfs = 0.38
        nfs = base_nfs + (pd.Series(range(len(dates))) % 10) * 0.04
        return pd.DataFrame(
            {
                "timestamp": dates,
                "narrative_fragmentation": nfs.clip(0.0, 1.0),
                "confidence_level": "medium",
            }
        )

    def _fetch_fact_check_volume(
        self, region_name: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Fetch fact-check volume indicators (higher = more misinformation)."""
        dates = pd.date_range(start=start_date.date(), end=end_date.date(), freq="D")
        base_fcv = 0.32
        fcv = base_fcv + (pd.Series(range(len(dates))) % 21) * 0.03
        return pd.DataFrame(
            {
                "timestamp": dates,
                "fact_check_volume": fcv.clip(0.0, 1.0),
                "confidence_level": "medium",
            }
        )

    def _fetch_content_authenticity(
        self, region_name: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Fetch content authenticity drift indicators."""
        dates = pd.date_range(start=start_date.date(), end=end_date.date(), freq="D")
        base_cad = 0.36
        cad = base_cad + (pd.Series(range(len(dates))) % 12) * 0.05
        return pd.DataFrame(
            {
                "timestamp": dates,
                "content_authenticity": cad.clip(0.0, 1.0),
                "confidence_level": "medium",
            }
        )

    def _merge_misinformation_sources(
        self, sources: Dict[str, pd.DataFrame], start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Merge all misinformation data sources."""
        dates = pd.date_range(start=start_date.date(), end=end_date.date(), freq="D")
        merged = pd.DataFrame({"timestamp": dates})

        source_to_col = {
            "rumor_amplification": "rumor_amplification",
            "sentiment_volatility": "sentiment_volatility",
            "narrative_fragmentation": "narrative_fragmentation",
            "fact_check_volume": "fact_check_volume",
            "content_authenticity": "content_authenticity",
        }

        for source_name, df in sources.items():
            if source_name == "merged":
                continue
            if not df.empty and "timestamp" in df.columns:
                col_name = source_to_col.get(source_name, source_name)
                if col_name in df.columns:
                    merged = merged.merge(
                        df[["timestamp", col_name]], on="timestamp", how="left"
                    )

        merged = merged.ffill().bfill()
        return merged

    def calculate_misinformation_stress(
        self, region_name: str, days_back: int = 30, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Calculate Information Integrity & Misinformation Index (IIMI).

        Formula:
        IIMI = 0.25 * RAI + 0.25 * SVS + 0.20 * NFS + 0.15 * FCV + 0.15 * CAD
        """
        sources = self.fetch_primary_sources(region_name, days_back, use_cache)

        if "merged" not in sources:
            return pd.DataFrame(
                columns=["timestamp", "misinformation_stress", "confidence_level"]
            )

        merged = sources["merged"]
        if merged.empty or "timestamp" not in merged.columns:
            return pd.DataFrame(
                columns=["timestamp", "misinformation_stress", "confidence_level"]
            )

        base_index = merged.index if hasattr(merged, "index") else range(len(merged))

        rai = (
            merged["rumor_amplification"].fillna(0.35)
            if "rumor_amplification" in merged.columns
            else pd.Series([0.35] * len(merged), index=base_index)
        )
        svs = (
            merged["sentiment_volatility"].fillna(0.4)
            if "sentiment_volatility" in merged.columns
            else pd.Series([0.4] * len(merged), index=base_index)
        )
        nfs = (
            merged["narrative_fragmentation"].fillna(0.38)
            if "narrative_fragmentation" in merged.columns
            else pd.Series([0.38] * len(merged), index=base_index)
        )
        fcv = (
            merged["fact_check_volume"].fillna(0.32)
            if "fact_check_volume" in merged.columns
            else pd.Series([0.32] * len(merged), index=base_index)
        )
        cad = (
            merged["content_authenticity"].fillna(0.36)
            if "content_authenticity" in merged.columns
            else pd.Series([0.36] * len(merged), index=base_index)
        )

        misinformation_stress = (
            0.25 * rai + 0.25 * svs + 0.20 * nfs + 0.15 * fcv + 0.15 * cad
        )

        misinformation_stress = misinformation_stress.clip(0.0, 1.0)

        timestamps = (
            pd.to_datetime(merged["timestamp"])
            if "timestamp" in merged.columns
            else pd.date_range(
                start=datetime.now() - timedelta(days=days_back),
                end=datetime.now(),
                freq="D",
            )[: len(merged)]
        )

        result = pd.DataFrame(
            {
                "timestamp": timestamps,
                "misinformation_stress": (
                    misinformation_stress.values
                    if hasattr(misinformation_stress, "values")
                    else misinformation_stress
                ),
                "confidence_level": "medium",
            }
        )

        logger.info(
            "Misinformation stress calculated",
            region=region_name,
            rows=len(result),
            stress_range=(
                result["misinformation_stress"].min(),
                result["misinformation_stress"].max(),
            ),
        )

        return result
