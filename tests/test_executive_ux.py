# SPDX-License-Identifier: PROPRIETARY
"""Tests for executive UX and decision consumption (N+34)."""
import pytest

from app.core.executive_summary import (
    compose_action_recommendation,
    compose_brief_export,
    compose_change_summary,
    compose_current_status,
    compose_executive_summary,
    compose_primary_drivers_summary,
    compose_risk_confidence_posture,
    compose_why_should_i_care,
)
from app.core.invariants import get_registry


class TestCurrentStatus:
    """Tests for current status composition."""

    def test_current_status_low(self):
        """Test current status for low behavior index."""
        status = compose_current_status(0.25, "stable", "Minnesota")
        assert "low" in status.lower() or "moderate" in status.lower()
        assert "Minnesota" in status
        assert "0.25" in status or "0.2" in status

    def test_current_status_high(self):
        """Test current status for high behavior index."""
        status = compose_current_status(0.85, "high", "California")
        assert "high" in status.lower() or "elevated" in status.lower()
        assert "California" in status

    def test_current_status_deterministic(self):
        """Test that current status is deterministic."""
        status1 = compose_current_status(0.5, "elevated", "Texas")
        status2 = compose_current_status(0.5, "elevated", "Texas")
        assert status1 == status2


class TestPrimaryDriversSummary:
    """Tests for primary drivers summary."""

    def test_primary_drivers_summary(self):
        """Test primary drivers summary composition."""
        drivers = [
            {
                "factor_id": "market_volatility",
                "factor_label": "Market Volatility",
                "sub_index": "economic_stress",
                "contribution": 0.15,
                "signal_strength": 0.8,
                "confidence": 0.9,
            },
            {
                "factor_id": "weather_discomfort",
                "factor_label": "Weather Discomfort",
                "sub_index": "environmental_stress",
                "contribution": 0.12,
                "signal_strength": 0.6,
                "confidence": 0.7,
            },
        ]

        summary = compose_primary_drivers_summary(drivers, max_drivers=3)
        assert len(summary) == 2
        assert summary[0]["factor_label"] == "Market Volatility"
        assert summary[0]["signal_strength"] == "strong"
        assert summary[1]["signal_strength"] == "moderate"

    def test_primary_drivers_limit(self):
        """Test that primary drivers are limited."""
        drivers = [
            {"factor_id": f"factor_{i}", "contribution": 0.1, "signal_strength": 0.5}
            for i in range(5)
        ]

        summary = compose_primary_drivers_summary(drivers, max_drivers=3)
        assert len(summary) == 3


class TestChangeSummary:
    """Tests for change summary composition."""

    def test_change_summary_increasing(self):
        """Test change summary for increasing trend."""
        temporal_attribution = {
            "global_delta": {
                "delta_value": 0.15,
                "direction": "increasing",
            },
            "primary_drivers": [
                {"factor_id": "market_volatility", "delta": 0.1}
            ],
        }

        summary = compose_change_summary(temporal_attribution, 0.65)
        assert summary["direction"] == "increasing"
        assert summary["magnitude"] == 0.15
        assert summary["magnitude_label"] == "significant"

    def test_change_summary_stable(self):
        """Test change summary for stable trend."""
        summary = compose_change_summary(None, 0.5, previous_behavior_index=0.5001)
        assert summary["direction"] == "stable"
        assert abs(summary["magnitude"]) < 0.01

    def test_change_summary_with_previous(self):
        """Test change summary with previous behavior index."""
        summary = compose_change_summary(None, 0.6, previous_behavior_index=0.5)
        assert summary["direction"] == "increasing"
        assert summary["magnitude"] == pytest.approx(0.1)


class TestRiskConfidencePosture:
    """Tests for risk/confidence posture composition."""

    def test_risk_confidence_high(self):
        """Test risk/confidence posture with high confidence."""
        posture = compose_risk_confidence_posture("elevated", 0.85)
        assert posture["confidence_level"] == "high"
        assert posture["confidence_score"] == 0.85
        assert posture["risk_tier"] == "elevated"

    def test_risk_confidence_low(self):
        """Test risk/confidence posture with low confidence."""
        posture = compose_risk_confidence_posture("high", 0.3)
        assert posture["confidence_level"] == "low"
        assert posture["confidence_score"] == 0.3

    def test_risk_confidence_with_provenance(self):
        """Test risk/confidence posture with provenance."""
        provenance = {
            "aggregate_provenance": {
                "aggregate_coverage_classification": "high",
            }
        }

        posture = compose_risk_confidence_posture("elevated", 0.7, provenance)
        assert posture["data_quality"] == "high"


class TestActionRecommendation:
    """Tests for action recommendation composition."""

    def test_action_recommendation_immediate(self):
        """Test action recommendation for immediate action."""
        alerts = {
            "alert_count": 2,
            "alerts": [
                {"id": "alert1", "severity": "high"},
                {"id": "alert2", "severity": "medium"},
            ],
        }

        recommendation = compose_action_recommendation(alerts, "high", 0.8)
        assert recommendation["recommendation"] == "immediate_action"
        assert recommendation["urgency"] == "high"
        assert recommendation["high_severity_alerts"] == 1

    def test_action_recommendation_watch(self):
        """Test action recommendation for watch."""
        alerts = {
            "alert_count": 1,
            "alerts": [{"id": "alert1", "severity": "medium"}],
        }

        recommendation = compose_action_recommendation(alerts, "elevated", 0.6)
        assert recommendation["recommendation"] == "watch"
        assert recommendation["urgency"] == "medium"

    def test_action_recommendation_monitor(self):
        """Test action recommendation for monitor."""
        recommendation = compose_action_recommendation(None, "stable", 0.4)
        assert recommendation["recommendation"] == "monitor"
        assert recommendation["urgency"] == "low"


class TestWhyShouldICare:
    """Tests for 'Why Should I Care?' panel."""

    def test_why_should_i_care_with_alerts(self):
        """Test 'Why Should I Care?' with alerts."""
        alerts = {
            "alert_count": 2,
            "alerts": [{"id": "alert1", "severity": "high"}],
        }

        panel = compose_why_should_i_care(0.75, None, None, alerts)
        assert "alert" in panel["why_matters"].lower()
        assert panel["urgency_assessment"] in ["urgent", "watch"]

    def test_why_should_i_care_with_benchmarks(self):
        """Test 'Why Should I Care?' with benchmarks."""
        benchmarks = {
            "baseline_deviation": {
                "classification": "anomalous",
            }
        }

        panel = compose_why_should_i_care(0.5, benchmarks, None, None)
        assert "anomalous" in panel["unusual_vs_baseline"].lower()

    def test_why_should_i_care_with_temporal(self):
        """Test 'Why Should I Care?' with temporal attribution."""
        temporal_attribution = {
            "signal_vs_noise": {
                "global_classification": "signal",
            }
        }

        panel = compose_why_should_i_care(0.5, None, temporal_attribution, None)
        assert "signal" in panel["persistent_vs_noise"].lower()


class TestComposeExecutiveSummary:
    """Tests for complete executive summary composition."""

    def test_compose_executive_summary_basic(self):
        """Test basic executive summary composition."""
        summary = compose_executive_summary(
            behavior_index=0.6,
            risk_tier="elevated",
            region_name="Minnesota",
            forecast_confidence=0.75,
        )

        assert "current_status" in summary
        assert "primary_drivers" in summary
        assert "change_summary" in summary
        assert "risk_confidence_posture" in summary
        assert "action_recommendation" in summary
        assert "why_should_i_care" in summary
        assert "metadata" in summary

    def test_compose_executive_summary_with_narrative(self):
        """Test executive summary with narrative."""
        narrative = {
            "primary_drivers": [
                {
                    "factor_id": "market_volatility",
                    "factor_label": "Market Volatility",
                    "sub_index": "economic_stress",
                    "contribution": 0.15,
                    "signal_strength": 0.8,
                    "confidence": 0.9,
                }
            ]
        }

        summary = compose_executive_summary(
            behavior_index=0.6,
            risk_tier="elevated",
            region_name="Minnesota",
            narrative=narrative,
        )

        assert len(summary["primary_drivers"]) > 0

    def test_compose_executive_summary_deterministic(self):
        """Test that executive summary is deterministic."""
        summary1 = compose_executive_summary(
            behavior_index=0.6,
            risk_tier="elevated",
            region_name="Minnesota",
            forecast_confidence=0.75,
        )

        summary2 = compose_executive_summary(
            behavior_index=0.6,
            risk_tier="elevated",
            region_name="Minnesota",
            forecast_confidence=0.75,
        )

        assert summary1["current_status"] == summary2["current_status"]
        assert summary1["action_recommendation"]["recommendation"] == summary2["action_recommendation"]["recommendation"]


class TestBriefExport:
    """Tests for brief export composition."""

    def test_compose_brief_export(self):
        """Test brief export composition."""
        executive_summary = {
            "current_status": "Test status",
            "action_recommendation": {"recommendation": "monitor"},
        }

        export = compose_brief_export(
            executive_summary=executive_summary,
            region_name="Minnesota",
            data_timestamp="2024-01-01T00:00:00Z",
            data_window_days=30,
        )

        assert export["region_name"] == "Minnesota"
        assert export["data_timestamp"] == "2024-01-01T00:00:00Z"
        assert export["data_window_days"] == 30
        assert export["export_format"] == "brief"
        assert export["executive_summary"] == executive_summary


class TestExecutiveUXInvariants:
    """Tests for executive UX invariants."""

    def test_inv_ux01_executive_summary_determinism(self):
        """Test INV-UX01: Executive summary determinism."""
        registry = get_registry()

        summary1 = {
            "current_status": "Test status",
            "action_recommendation": {"recommendation": "monitor"},
        }
        summary2 = {
            "current_status": "Test status",
            "action_recommendation": {"recommendation": "monitor"},
        }

        is_valid, error = registry.check("INV-UX01", summary1, summary2)
        assert is_valid is True

    def test_inv_ux01_determinism_violation(self):
        """Test INV-UX01 violation: Non-deterministic summary."""
        registry = get_registry()

        summary1 = {
            "current_status": "Status A",
            "action_recommendation": {"recommendation": "monitor"},
        }
        summary2 = {
            "current_status": "Status B",
            "action_recommendation": {"recommendation": "monitor"},
        }

        is_valid, error = registry.check("INV-UX01", summary1, summary2)
        assert is_valid is False
        assert "status" in error.lower()

    def test_inv_ux02_summary_derivability(self):
        """Test INV-UX02: Summary derivability."""
        registry = get_registry()

        summary = {
            "current_status": "Test",
            "metadata": {"behavior_index": 0.6},
        }
        source_data = {
            "behavior_index": 0.6,
            "risk_tier": "elevated",
        }

        is_valid, error = registry.check("INV-UX02", summary, source_data)
        assert is_valid is True

    def test_inv_ux02_derivability_violation(self):
        """Test INV-UX02 violation: Missing source data."""
        registry = get_registry()

        summary = {
            "current_status": "Test",
            "metadata": {"behavior_index": 0.6},
        }
        source_data = {
            "risk_tier": "elevated",
            # Missing behavior_index
        }

        is_valid, error = registry.check("INV-UX02", summary, source_data)
        assert is_valid is False
        assert "behavior_index" in error.lower()

    def test_inv_ux03_no_hidden_analytics(self):
        """Test INV-UX03: No hidden analytics."""
        registry = get_registry()

        summary = {
            "metadata": {"behavior_index": 0.6},
        }
        backend_outputs = {
            "behavior_index": 0.6,
        }

        is_valid, error = registry.check("INV-UX03", summary, backend_outputs)
        assert is_valid is True

    def test_inv_ux03_hidden_analytics_violation(self):
        """Test INV-UX03 violation: Summary doesn't match backend."""
        registry = get_registry()

        summary = {
            "metadata": {"behavior_index": 0.7},  # Different from backend
        }
        backend_outputs = {
            "behavior_index": 0.6,
        }

        is_valid, error = registry.check("INV-UX03", summary, backend_outputs)
        assert is_valid is False
        assert "match" in error.lower()

    def test_inv_ux04_zero_numerical_drift(self):
        """Test INV-UX04: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check("INV-UX04", behavior_index_before, behavior_index_after)
        assert is_valid is True

    def test_inv_ux04_zero_numerical_drift_violation(self):
        """Test INV-UX04 violation: Numerical drift."""
        from app.core.invariants import InvariantViolation

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550  # Changed

        # INV-UX04 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-UX04", behavior_index_before, behavior_index_after)

        assert "drift" in str(exc_info.value).lower() or "changed" in str(exc_info.value).lower()


class TestNoSemanticDrift:
    """Tests to ensure executive UX doesn't cause semantic drift."""

    def test_executive_summary_purely_derived(self):
        """Test that executive summary is purely derived."""
        # Executive summary should not change alert generation or analytics
        from app.core.alerting import compose_alerts

        alerts_dict = compose_alerts(
            behavior_index=0.8,
            behavior_index_history=[0.8] * 10,
            alert_definitions=[
                {
                    "id": "test",
                    "type": "threshold",
                    "threshold": 0.7,
                    "comparison": "greater_than",
                    "persistence_days": 0,
                    "severity": "high",
                }
            ],
        )

        # Generate executive summary
        summary = compose_executive_summary(
            behavior_index=0.8,
            risk_tier="high",
            region_name="Test Region",
            alerts=alerts_dict,
        )

        # Alerts should be unchanged
        assert alerts_dict["alert_count"] > 0
        # Summary should reference alerts
        assert summary["action_recommendation"]["alert_count"] == alerts_dict["alert_count"]

    def test_executive_summary_deterministic(self):
        """Test that executive summary is deterministic."""
        summary1 = compose_executive_summary(
            behavior_index=0.6,
            risk_tier="elevated",
            region_name="Minnesota",
            forecast_confidence=0.75,
        )

        summary2 = compose_executive_summary(
            behavior_index=0.6,
            risk_tier="elevated",
            region_name="Minnesota",
            forecast_confidence=0.75,
        )

        # Key fields should be identical
        assert summary1["current_status"] == summary2["current_status"]
        assert summary1["action_recommendation"]["recommendation"] == summary2["action_recommendation"]["recommendation"]


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_executive_summary_optional_in_api(self):
        """Test that executive summary is optional in API responses."""
        # API should work even if executive summary generation fails
        summary = compose_executive_summary(
            behavior_index=0.6,
            risk_tier="elevated",
            region_name="Minnesota",
        )

        assert isinstance(summary, dict)
        assert "current_status" in summary

    def test_executive_summary_minimal_inputs(self):
        """Test executive summary with minimal inputs."""
        summary = compose_executive_summary(
            behavior_index=0.5,
            risk_tier="stable",
            region_name="Test Region",
        )

        assert isinstance(summary, dict)
        assert len(summary["primary_drivers"]) == 0  # No narrative provided
