# SPDX-License-Identifier: PROPRIETARY
"""Comprehensive tests for new indices (Crime, Misinformation, Social Cohesion)."""

import numpy as np
import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer
from app.core.prediction import BehavioralForecaster
from app.services.ingestion.crime import CrimeSafetyStressFetcher
from app.services.ingestion.misinformation import MisinformationStressFetcher
from app.services.ingestion.social_cohesion import SocialCohesionStressFetcher


class TestCrimeStressIndex:
    """Test Crime & Public Safety Stress Index (CPSSI)."""

    def test_fetcher_initialization(self):
        """Test that fetcher initializes correctly."""
        fetcher = CrimeSafetyStressFetcher()
        assert fetcher is not None
        assert fetcher.cache_duration_minutes == 1440

    def test_calculate_crime_stress(self):
        """Test crime stress calculation."""
        fetcher = CrimeSafetyStressFetcher()
        result = fetcher.calculate_crime_stress(
            "Minnesota", days_back=30, use_cache=False
        )

        assert not result.empty
        assert "timestamp" in result.columns
        assert "crime_stress" in result.columns
        assert "confidence_level" in result.columns

        # Validate values are in range [0, 1]
        assert result["crime_stress"].min() >= 0.0
        assert result["crime_stress"].max() <= 1.0

        # Validate no NaN values
        assert not result["crime_stress"].isna().any()

    def test_crime_stress_components(self):
        """Test that crime stress components are calculated."""
        fetcher = CrimeSafetyStressFetcher()
        sources = fetcher.fetch_primary_sources(
            "Minnesota", days_back=30, use_cache=False
        )

        assert "merged" in sources
        merged = sources["merged"]

        # Check for component columns
        expected_components = [
            "violent_crime_volatility",
            "property_crime_rate",
            "public_disturbance",
            "seasonal_deviation",
            "gun_violence_pressure",
        ]

        # At least some components should be present
        component_count = sum(
            1 for comp in expected_components if comp in merged.columns
        )
        assert component_count > 0


class TestMisinformationStressIndex:
    """Test Information Integrity & Misinformation Index (IIMI)."""

    def test_fetcher_initialization(self):
        """Test that fetcher initializes correctly."""
        fetcher = MisinformationStressFetcher()
        assert fetcher is not None

    def test_calculate_misinformation_stress(self):
        """Test misinformation stress calculation."""
        fetcher = MisinformationStressFetcher()
        result = fetcher.calculate_misinformation_stress(
            "Minnesota", days_back=30, use_cache=False
        )

        assert not result.empty
        assert "timestamp" in result.columns
        assert "misinformation_stress" in result.columns
        assert "confidence_level" in result.columns

        # Validate values are in range [0, 1]
        assert result["misinformation_stress"].min() >= 0.0
        assert result["misinformation_stress"].max() <= 1.0

        # Validate no NaN values
        assert not result["misinformation_stress"].isna().any()

    def test_misinformation_stress_components(self):
        """Test that misinformation stress components are calculated."""
        fetcher = MisinformationStressFetcher()
        sources = fetcher.fetch_primary_sources(
            "Minnesota", days_back=30, use_cache=False
        )

        assert "merged" in sources
        merged = sources["merged"]

        # Check for component columns
        expected_components = [
            "rumor_amplification",
            "sentiment_volatility",
            "narrative_fragmentation",
            "fact_check_volume",
            "content_authenticity",
        ]

        component_count = sum(
            1 for comp in expected_components if comp in merged.columns
        )
        assert component_count > 0


class TestSocialCohesionStressIndex:
    """Test Social Cohesion & Civil Stability Index (SCCSI)."""

    def test_fetcher_initialization(self):
        """Test that fetcher initializes correctly."""
        fetcher = SocialCohesionStressFetcher()
        assert fetcher is not None

    def test_calculate_social_cohesion_stress(self):
        """Test social cohesion stress calculation."""
        fetcher = SocialCohesionStressFetcher()
        result = fetcher.calculate_social_cohesion_stress(
            "Minnesota", days_back=30, use_cache=False
        )

        assert not result.empty
        assert "timestamp" in result.columns
        assert "social_cohesion_stress" in result.columns
        assert "confidence_level" in result.columns

        # Validate values are in range [0, 1]
        assert result["social_cohesion_stress"].min() >= 0.0
        assert result["social_cohesion_stress"].max() <= 1.0

        # Validate no NaN values
        assert not result["social_cohesion_stress"].isna().any()

    def test_social_cohesion_stress_components(self):
        """Test that social cohesion stress components are calculated."""
        fetcher = SocialCohesionStressFetcher()
        sources = fetcher.fetch_primary_sources(
            "Minnesota", days_back=30, use_cache=False
        )

        assert "merged" in sources
        merged = sources["merged"]

        # Check for component columns
        expected_components = [
            "community_trust",
            "mental_health",
            "intergroup_tension",
            "social_capital",
            "civic_participation",
        ]

        component_count = sum(
            1 for comp in expected_components if comp in merged.columns
        )
        assert component_count > 0


class TestBehaviorIndexIntegration:
    """Test integration of new indices into behavior index calculation."""

    def test_behavior_index_with_all_indices(self):
        """Test behavior index calculation with all 9 indices."""
        computer = BehaviorIndexComputer(
            political_weight=0.15,
            crime_weight=0.15,
            misinformation_weight=0.10,
            social_cohesion_weight=0.15,
        )

        # Create test data
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "economic_stress": np.random.uniform(0.2, 0.8, 30),
                "environmental_stress": np.random.uniform(0.2, 0.8, 30),
                "mobility_activity": np.random.uniform(0.2, 0.8, 30),
                "digital_attention": np.random.uniform(0.2, 0.8, 30),
                "public_health_stress": np.random.uniform(0.2, 0.8, 30),
                "political_stress": np.random.uniform(0.2, 0.8, 30),
                "crime_stress": np.random.uniform(0.2, 0.8, 30),
                "misinformation_stress": np.random.uniform(0.2, 0.8, 30),
                "social_cohesion_stress": np.random.uniform(0.2, 0.8, 30),
            }
        )

        result = computer.compute_behavior_index(test_data)

        # Validate all sub-indices are present
        expected_indices = [
            "economic_stress",
            "environmental_stress",
            "mobility_activity",
            "digital_attention",
            "public_health_stress",
            "political_stress",
            "crime_stress",
            "misinformation_stress",
            "social_cohesion_stress",
        ]

        for idx in expected_indices:
            assert idx in result.columns, f"Missing index: {idx}"
            assert not result[idx].isna().all(), f"All NaN values for {idx}"

        # Validate behavior index
        assert "behavior_index" in result.columns
        assert result["behavior_index"].min() >= 0.0
        assert result["behavior_index"].max() <= 1.0

    def test_contribution_analysis(self):
        """Test contribution analysis includes all indices."""
        computer = BehaviorIndexComputer(
            political_weight=0.15,
            crime_weight=0.15,
            misinformation_weight=0.10,
            social_cohesion_weight=0.15,
        )

        # Create a test row
        row = pd.Series(
            {
                "economic_stress": 0.5,
                "environmental_stress": 0.5,
                "mobility_activity": 0.5,
                "digital_attention": 0.5,
                "public_health_stress": 0.5,
                "political_stress": 0.5,
                "crime_stress": 0.5,
                "misinformation_stress": 0.5,
                "social_cohesion_stress": 0.5,
            }
        )

        contrib = computer.get_contribution_analysis(row)

        # All indices should have contributions
        expected_keys = [
            "economic_stress",
            "environmental_stress",
            "mobility_activity",
            "digital_attention",
            "public_health_stress",
            "political_stress",
            "crime_stress",
            "misinformation_stress",
            "social_cohesion_stress",
        ]

        for key in expected_keys:
            assert key in contrib, f"Missing contribution for {key}"
            assert contrib[key] is not None, f"None contribution for {key}"
            assert (
                "contribution" in contrib[key]
            ), f"Missing contribution value for {key}"
            assert "weight" in contrib[key], f"Missing weight for {key}"


class TestForecastingIntegration:
    """Test forecasting with new indices."""

    def test_forecast_with_new_indices(self):
        """Test that forecast includes new indices."""
        forecaster = BehavioralForecaster()

        result = forecaster.forecast(
            latitude=46.7296,
            longitude=-94.6859,
            region_name="Minnesota",
            days_back=30,
            forecast_horizon=7,
        )

        # Validate structure
        assert "history" in result
        assert "forecast" in result
        assert "sources" in result

        # Check history includes new indices
        if result.get("history"):
            latest = result["history"][-1]
            if "sub_indices" in latest:
                sub = latest["sub_indices"]

                # Check for new indices
                new_indices = [
                    "political_stress",
                    "crime_stress",
                    "misinformation_stress",
                    "social_cohesion_stress",
                ]

                for idx in new_indices:
                    # At least one should be present (they're optional)
                    if idx in sub:
                        val = sub[idx]
                        if val is not None:
                            assert 0.0 <= val <= 1.0, f"Invalid value for {idx}: {val}"

        # Check sources include new ingestion modules
        sources = result.get("sources", [])
        new_sources = [
            "political_ingestion",
            "crime_ingestion",
            "misinformation_ingestion",
            "social_cohesion_ingestion",
        ]

        # At least some new sources should be present
        found_sources = [
            s for s in sources if any(ns in s.lower() for ns in new_sources)
        ]
        assert len(found_sources) > 0, "No new ingestion sources found"


class TestBackwardCompatibility:
    """Test backward compatibility with existing indices."""

    def test_behavior_index_without_new_indices(self):
        """Test behavior index works without new indices."""
        computer = BehaviorIndexComputer()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "economic_stress": np.random.uniform(0.2, 0.8, 30),
                "environmental_stress": np.random.uniform(0.2, 0.8, 30),
                "mobility_activity": np.random.uniform(0.2, 0.8, 30),
                "digital_attention": np.random.uniform(0.2, 0.8, 30),
                "public_health_stress": np.random.uniform(0.2, 0.8, 30),
            }
        )

        result = computer.compute_behavior_index(test_data)

        # Original indices should still work
        original_indices = [
            "economic_stress",
            "environmental_stress",
            "mobility_activity",
            "digital_attention",
            "public_health_stress",
        ]

        for idx in original_indices:
            assert idx in result.columns

        # Behavior index should be calculated
        assert "behavior_index" in result.columns
        assert not result["behavior_index"].isna().any()
