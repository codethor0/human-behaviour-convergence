# SPDX-License-Identifier: PROPRIETARY
"""Tests for Visualization Layer components."""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from app.services.comparison.state_compare import StateComparisonEngine
from app.services.visual.convergence_graph import ConvergenceGraphEngine
from app.services.visual.correlation_matrix import CorrelationMatrixEngine
from app.services.visual.heatmap_engine import HeatmapEngine
from app.services.visual.radar_engine import RadarEngine
from app.services.visual.risk_gauge import RiskGaugeEngine
from app.services.visual.shock_timeline import ShockTimelineEngine
from app.services.visual.trend_engine import TrendEngine


class TestHeatmapEngine:
    """Tests for Heatmap Engine."""

    def test_heatmap_engine_initialization(self):
        """Test heatmap engine can be initialized."""
        engine = HeatmapEngine()
        assert engine is not None

    def test_generate_heatmap(self):
        """Test heatmap generation."""
        engine = HeatmapEngine()

        state_data = {
            "Minnesota": {
                "political_stress": 0.44,
                "crime_stress": 0.39,
                "economic_stress": 0.18,
            },
            "California": {
                "political_stress": 0.52,
                "crime_stress": 0.45,
                "economic_stress": 0.22,
            },
        }

        heatmap = engine.generate_heatmap(state_data)

        assert "political_stress" in heatmap
        assert "crime_stress" in heatmap
        assert "_metadata" in heatmap
        assert "Minnesota" in heatmap["political_stress"]
        assert heatmap["political_stress"]["Minnesota"] == 0.44


class TestTrendEngine:
    """Tests for Trend Engine."""

    def test_trend_engine_initialization(self):
        """Test trend engine can be initialized."""
        engine = TrendEngine()
        assert engine.short_window == 7
        assert engine.long_window == 30

    def test_calculate_trends(self):
        """Test trend calculation."""
        engine = TrendEngine()

        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "political_stress": np.linspace(0.3, 0.7, 30),  # Increasing trend
            }
        )

        trends = engine.calculate_trends(df)

        assert "political_stress" in trends
        assert trends["political_stress"]["direction"] == "increasing"
        assert trends["political_stress"]["slope_7d"] > 0


class TestRadarEngine:
    """Tests for Radar Engine."""

    def test_radar_engine_initialization(self):
        """Test radar engine can be initialized."""
        engine = RadarEngine()
        assert len(engine.index_order) == 9

    def test_generate_radar_data(self):
        """Test radar data generation."""
        engine = RadarEngine()

        state_indices = {
            "political_stress": 0.44,
            "crime_stress": 0.39,
            "economic_stress": 0.18,
        }

        radar = engine.generate_radar_data(state_indices)

        assert "values" in radar
        assert "indices" in radar
        assert "coordinates" in radar
        assert len(radar["values"]) == 9


class TestConvergenceGraphEngine:
    """Tests for Convergence Graph Engine."""

    def test_convergence_graph_initialization(self):
        """Test convergence graph engine can be initialized."""
        engine = ConvergenceGraphEngine()
        assert engine.correlation_threshold == 0.3

    def test_generate_graph(self):
        """Test graph generation."""
        engine = ConvergenceGraphEngine()

        correlation_matrix = {
            "political_stress": {
                "misinformation_stress": 0.85,
                "social_cohesion_stress": -0.72,
            },
            "misinformation_stress": {
                "political_stress": 0.85,
            },
        }

        graph = engine.generate_graph(correlation_matrix)

        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) > 0
        assert len(graph["edges"]) > 0


class TestRiskGaugeEngine:
    """Tests for Risk Gauge Engine."""

    def test_risk_gauge_initialization(self):
        """Test risk gauge engine can be initialized."""
        engine = RiskGaugeEngine()
        assert engine is not None

    def test_generate_gauge_data(self):
        """Test gauge data generation."""
        engine = RiskGaugeEngine()

        gauge = engine.generate_gauge_data(0.65, "elevated")

        assert "risk_score" in gauge
        assert "risk_tier" in gauge
        assert "pointer_angle" in gauge
        assert "zones" in gauge
        assert gauge["risk_tier"] == "elevated"
        assert 0 <= gauge["pointer_angle"] <= 180


class TestShockTimelineEngine:
    """Tests for Shock Timeline Engine."""

    def test_shock_timeline_initialization(self):
        """Test shock timeline engine can be initialized."""
        engine = ShockTimelineEngine()
        assert engine is not None

    def test_generate_timeline(self):
        """Test timeline generation."""
        engine = ShockTimelineEngine()

        shock_events = [
            {
                "index": "political_stress",
                "severity": "high",
                "delta": 0.23,
                "timestamp": "2025-12-01T00:00:00",
            },
            {
                "index": "crime_stress",
                "severity": "moderate",
                "delta": 0.15,
                "timestamp": "2025-12-02T00:00:00",
            },
        ]

        timeline = engine.generate_timeline(shock_events)

        assert "events" in timeline
        assert "grouped_by_severity" in timeline
        assert len(timeline["events"]) == 2


class TestCorrelationMatrixEngine:
    """Tests for Correlation Matrix Engine."""

    def test_correlation_matrix_initialization(self):
        """Test correlation matrix engine can be initialized."""
        engine = CorrelationMatrixEngine()
        assert len(engine.index_order) == 9

    def test_generate_matrix(self):
        """Test matrix generation."""
        engine = CorrelationMatrixEngine()

        correlation_data = {
            "political_stress": {
                "misinformation_stress": 0.85,
            },
            "misinformation_stress": {
                "political_stress": 0.85,
            },
        }

        matrix = engine.generate_matrix(correlation_data)

        assert "matrix" in matrix
        assert "labels" in matrix
        assert "color_scheme" in matrix
        assert len(matrix["matrix"]) > 0


class TestStateComparisonEngine:
    """Tests for State Comparison Engine."""

    def test_state_comparison_initialization(self):
        """Test state comparison engine can be initialized."""
        engine = StateComparisonEngine()
        assert engine is not None

    def test_compare_states(self):
        """Test state comparison."""
        engine = StateComparisonEngine()

        state_a_data = {
            "political_stress": 0.44,
            "crime_stress": 0.39,
            "behavior_index": 0.41,
        }

        state_b_data = {
            "political_stress": 0.52,
            "crime_stress": 0.45,
            "behavior_index": 0.48,
        }

        comparison = engine.compare_states(
            state_a_data=state_a_data,
            state_b_data=state_b_data,
            state_a_name="Minnesota",
            state_b_name="California",
        )

        assert "differences" in comparison
        assert "winners" in comparison
        assert "overall_winner" in comparison
        assert comparison["state_a"] == "Minnesota"
        assert comparison["state_b"] == "California"
