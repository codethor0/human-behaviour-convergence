# SPDX-License-Identifier: PROPRIETARY
"""Tests for Intelligence Layer components."""

import numpy as np
import pandas as pd

from app.services.analytics.correlation import CorrelationEngine
from app.services.convergence.engine import ConvergenceEngine
from app.services.forecast.monitor import ForecastMonitor
from app.services.risk.classifier import RiskClassifier
from app.services.shocks.detector import ShockDetector
from app.services.simulation.engine import SimulationEngine


class TestShockDetector:
    """Tests for Real-Time Event Shock Detection Layer."""

    def test_shock_detector_initialization(self):
        """Test shock detector can be initialized."""
        detector = ShockDetector()
        assert detector.z_score_threshold == 2.5
        assert detector.delta_threshold == 0.15
        assert detector.window_size == 7

    def test_detect_shocks_with_spike(self):
        """Test shock detection with a clear spike."""
        detector = ShockDetector()

        # Create data with a spike
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        values = np.random.uniform(0.3, 0.5, 30)
        values[15] = 0.9  # Add a spike

        df = pd.DataFrame({"timestamp": dates, "economic_stress": values})
        df = df.set_index("timestamp")

        shocks = detector.detect_shocks(df)
        assert isinstance(shocks, list)
        assert len(shocks) > 0
        assert shocks[0]["index"] == "economic_stress"

    def test_detect_shocks_empty_data(self):
        """Test shock detection with empty data."""
        detector = ShockDetector()
        df = pd.DataFrame()
        shocks = detector.detect_shocks(df)
        assert shocks == []


class TestConvergenceEngine:
    """Tests for Cross-Index Convergence Engine."""

    def test_convergence_engine_initialization(self):
        """Test convergence engine can be initialized."""
        engine = ConvergenceEngine()
        assert engine.convergence_threshold == 0.6

    def test_analyze_convergence(self):
        """Test convergence analysis."""
        engine = ConvergenceEngine()

        # Create correlated data
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        base = np.random.uniform(0.3, 0.7, 30)

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "political_stress": base,
                "misinformation_stress": base + np.random.normal(0, 0.1, 30),
                "social_cohesion_stress": 1.0 - base + np.random.normal(0, 0.1, 30),
            }
        )

        result = engine.analyze_convergence(df)
        assert "score" in result
        assert "reinforcing_signals" in result
        assert "conflicting_signals" in result
        assert isinstance(result["score"], (int, float))


class TestRiskClassifier:
    """Tests for Risk Tier Classification System."""

    def test_risk_classifier_initialization(self):
        """Test risk classifier can be initialized."""
        classifier = RiskClassifier()
        assert classifier is not None

    def test_classify_risk_stable(self):
        """Test risk classification for stable tier."""
        classifier = RiskClassifier()
        result = classifier.classify_risk(
            behavior_index=0.2,
            shock_events=[],
            convergence_score=20.0,
            trend_direction="stable",
        )
        assert result["tier"] == "stable"
        assert result["risk_score"] < 0.3

    def test_classify_risk_critical(self):
        """Test risk classification for critical tier."""
        classifier = RiskClassifier()
        result = classifier.classify_risk(
            behavior_index=0.9,
            shock_events=[{"severity": "severe", "delta": 0.3}],
            convergence_score=90.0,
            trend_direction="increasing",
        )
        assert result["tier"] in ["high", "critical"]
        assert result["risk_score"] > 0.7


class TestForecastMonitor:
    """Tests for Forecast Confidence Monitoring."""

    def test_forecast_monitor_initialization(self):
        """Test forecast monitor can be initialized."""
        monitor = ForecastMonitor()
        assert monitor.drift_threshold == 0.15

    def test_calculate_confidence(self):
        """Test confidence score calculation."""
        monitor = ForecastMonitor()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "economic_stress": np.random.uniform(0.3, 0.7, 30),
            }
        )

        confidence = monitor.calculate_confidence(df)
        assert isinstance(confidence, dict)
        assert "economic_stress" in confidence
        assert 0.0 <= confidence["economic_stress"] <= 1.0

    def test_detect_drift(self):
        """Test drift detection."""
        monitor = ForecastMonitor()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        # Create data with drift
        values = np.concatenate(
            [np.random.uniform(0.3, 0.4, 15), np.random.uniform(0.7, 0.8, 15)]
        )

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "economic_stress": values,
            }
        )

        drift = monitor.detect_drift(df)
        assert isinstance(drift, dict)
        assert "economic_stress" in drift


class TestCorrelationEngine:
    """Tests for Correlation Analytics Engine."""

    def test_correlation_engine_initialization(self):
        """Test correlation engine can be initialized."""
        engine = CorrelationEngine()
        assert engine is not None

    def test_calculate_correlations(self):
        """Test correlation calculation."""
        engine = CorrelationEngine()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        base = np.random.uniform(0.3, 0.7, 30)

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "political_stress": base,
                "misinformation_stress": base + np.random.normal(0, 0.1, 30),
            }
        )

        result = engine.calculate_correlations(df)
        assert "correlations" in result
        assert "relationships" in result
        assert "indices_analyzed" in result


class TestSimulationEngine:
    """Tests for Scenario Simulation Engine."""

    def test_simulation_engine_initialization(self):
        """Test simulation engine can be initialized."""
        engine = SimulationEngine()
        assert engine is not None

    def test_simulate_scenario(self):
        """Test scenario simulation."""
        engine = SimulationEngine()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "economic_stress": np.random.uniform(0.3, 0.7, 30),
                "political_stress": np.random.uniform(0.3, 0.7, 30),
                "behavior_index": np.random.uniform(0.3, 0.7, 30),
            }
        )

        result = engine.simulate_scenario(
            base_history_df=df,
            index_modifiers={"political_stress": 1.2},  # 20% increase
            region_name="Minnesota",
        )

        assert "projected_behavior_index" in result
        assert "modified_indices" in result
        assert result["region_name"] == "Minnesota"


class TestIntelligenceLayerIntegration:
    """Integration tests for intelligence layer."""

    def test_intelligence_layer_in_forecast(self):
        """Test intelligence layer is included in forecast results."""
        from app.core.prediction import BehavioralForecaster

        forecaster = BehavioralForecaster()
        result = forecaster.forecast(
            latitude=46.7296,
            longitude=-94.6859,
            region_name="Minnesota",
            days_back=30,
            forecast_horizon=7,
        )

        # Check all intelligence fields are present
        assert "shock_events" in result
        assert "convergence" in result
        assert "risk_tier" in result
        assert "forecast_confidence" in result
        assert "model_drift" in result
        assert "correlations" in result

        # Check convergence structure
        convergence = result["convergence"]
        assert "score" in convergence
        assert "reinforcing_signals" in convergence
        assert "conflicting_signals" in convergence

        # Check risk tier structure
        risk_tier = result["risk_tier"]
        assert "tier" in risk_tier
        assert "risk_score" in risk_tier
