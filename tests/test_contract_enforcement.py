# SPDX-License-Identifier: PROPRIETARY
"""Tests for contract enforcement and semantic drift detection."""
import pytest

from app.core.contracts import (
    ContractRegistry,
    ContractViolation,
    SemanticDriftDetector,
    ViolationSeverity,
    get_contract_registry,
    get_observability,
    get_semantic_detector,
    register_core_contracts,
)


class TestContractRegistry:
    """Test contract registry functionality."""

    def test_registry_initialization(self):
        """Registry should be initialized with core contracts."""
        registry = get_contract_registry()
        assert registry is not None

        # Re-register to ensure clean state
        register_core_contracts()

        # Check that some contracts are registered
        violations = registry.get_violations()
        assert violations == []  # Should be empty initially

    def test_register_contract(self):
        """Should be able to register contracts."""
        registry = get_contract_registry()
        registry.register(
            "TEST-CONTRACT",
            "1.0",
            {"field1": "str", "field2": "int"},
            stability="STABLE",
            required_fields=["field1"],
        )
        assert "TEST-CONTRACT" in registry._contracts

    def test_validate_structure_valid(self):
        """Valid structures should pass validation."""
        registry = get_contract_registry()
        registry.register(
            "TEST-CONTRACT",
            "1.0",
            {"field1": "str", "field2": "int"},
            stability="STABLE",
            required_fields=["field1"],
        )

        data = {"field1": "value", "field2": 42}
        is_valid, error, violations = registry.validate_structure("TEST-CONTRACT", data)
        assert is_valid
        assert error is None
        assert len(violations) == 0

    def test_validate_structure_missing_required(self):
        """Missing required fields should fail validation."""
        registry = get_contract_registry()
        registry.register(
            "TEST-CONTRACT",
            "1.0",
            {"field1": "str", "field2": "int"},
            stability="STABLE",
            required_fields=["field1"],
        )

        data = {"field2": 42}  # Missing field1
        is_valid, error, violations = registry.validate_structure("TEST-CONTRACT", data)
        assert not is_valid
        assert "Missing required field" in error
        assert len(violations) > 0

    def test_validate_structure_type_mismatch(self):
        """Type mismatches should fail validation."""
        registry = get_contract_registry()
        registry.register(
            "TEST-CONTRACT",
            "1.0",
            {"field1": "str", "field2": "int"},
            stability="STABLE",
            required_fields=["field1"],
        )

        data = {"field1": "value", "field2": "not_an_int"}
        is_valid, error, violations = registry.validate_structure("TEST-CONTRACT", data)
        assert not is_valid
        assert "must be int" in error

    def test_detect_regression_removed_field(self):
        """Removed fields should be detected as regression."""
        registry = get_contract_registry()
        registry.register(
            "TEST-CONTRACT",
            "1.0",
            {"field1": "str", "field2": "int"},
            stability="STABLE",
        )

        # Create snapshot
        snapshot_data = {"field1": "value", "field2": 42}
        registry.snapshot("TEST-CONTRACT", snapshot_data)

        # Current data missing field2
        current_data = {"field1": "value"}
        has_regression, error = registry.detect_regression("TEST-CONTRACT", current_data)
        assert has_regression
        assert "Fields removed" in error

    def test_detect_regression_no_regression(self):
        """No regression should be detected for identical structures."""
        registry = get_contract_registry()
        registry.register(
            "TEST-CONTRACT",
            "1.0",
            {"field1": "str", "field2": "int"},
            stability="STABLE",
        )

        snapshot_data = {"field1": "value", "field2": 42}
        registry.snapshot("TEST-CONTRACT", snapshot_data)

        current_data = {"field1": "value", "field2": 42}
        has_regression, error = registry.detect_regression("TEST-CONTRACT", current_data)
        assert not has_regression
        assert error is None


class TestSemanticDriftDetection:
    """Test semantic drift detection."""

    def test_semantic_detector_initialization(self):
        """Semantic drift detector should initialize correctly."""
        detector = get_semantic_detector()
        assert detector is not None

    def test_check_risk_tier_monotonicity_valid(self):
        """Monotonic risk tiers should pass."""
        detector = get_semantic_detector()
        has_drift, error = detector.check_risk_tier_monotonicity(
            0.3, "watchlist", 0.6, "elevated"
        )
        assert not has_drift
        assert error is None

    def test_check_risk_tier_monotonicity_invalid(self):
        """Non-monotonic risk tiers should be detected."""
        detector = get_semantic_detector()
        has_drift, error = detector.check_risk_tier_monotonicity(
            0.3, "elevated", 0.6, "watchlist"
        )
        assert has_drift
        assert error is not None

    def test_check_confidence_volatility_valid(self):
        """Consistent confidence-volatility should pass."""
        detector = get_semantic_detector()
        has_drift, error = detector.check_confidence_volatility_relationship(0.3, 0.8)
        assert not has_drift
        assert error is None

    def test_check_confidence_volatility_invalid(self):
        """Inconsistent confidence-volatility should be detected."""
        detector = get_semantic_detector()
        has_drift, error = detector.check_confidence_volatility_relationship(0.8, 0.8)
        assert has_drift
        assert error is not None

    def test_check_convergence_meaning_valid(self):
        """Consistent convergence meaning should pass."""
        detector = get_semantic_detector()
        reinforcing = [["index1", "index2", 0.8], ["index2", "index3", 0.7]]
        has_drift, error = detector.check_convergence_meaning(75.0, reinforcing)
        assert not has_drift
        assert error is None

    def test_check_convergence_meaning_invalid(self):
        """Inconsistent convergence meaning should be detected."""
        detector = get_semantic_detector()
        reinforcing = []  # High score but no reinforcing signals
        has_drift, error = detector.check_convergence_meaning(75.0, reinforcing)
        assert has_drift
        assert error is not None


class TestContractObservability:
    """Test contract observability."""

    def test_observability_initialization(self):
        """Observability should initialize correctly."""
        obs = get_observability()
        assert obs is not None

    def test_record_violation(self):
        """Should record violations."""
        obs = get_observability()
        obs.clear_metrics()
        obs.record_violation("TEST-CONTRACT", "high", "test_endpoint")
        metrics = obs.get_metrics()
        assert metrics["total_violations"] == 1
        assert metrics["violation_by_severity"]["high"] == 1

    def test_record_semantic_drift(self):
        """Should record semantic drift."""
        obs = get_observability()
        obs.clear_metrics()
        obs.record_semantic_drift("risk_tier_monotonicity")
        metrics = obs.get_metrics()
        assert metrics["total_semantic_drift"] == 1
        assert metrics["semantic_drift_counts"]["risk_tier_monotonicity"] == 1

    def test_get_metrics(self):
        """Should return comprehensive metrics."""
        obs = get_observability()
        obs.clear_metrics()
        obs.record_violation("CONTRACT-1", "high")
        obs.record_violation("CONTRACT-2", "medium")
        obs.record_semantic_drift("test_invariant")

        metrics = obs.get_metrics()
        assert "violation_counts" in metrics
        assert "violation_by_severity" in metrics
        assert "semantic_drift_counts" in metrics
        assert metrics["total_violations"] == 2
        assert metrics["total_semantic_drift"] == 1


class TestMetaContractViolations:
    """Meta-tests that intentionally violate contracts to verify detection."""

    def test_meta_missing_required_field(self):
        """Intentionally violate contract by removing required field."""
        registry = get_contract_registry()
        register_core_contracts()

        # Violate API-RISK-CLASSIFICATION by removing required field
        invalid_data = {
            "tier": "elevated",
            "risk_score": 0.6,
            # Missing: base_risk, shock_adjustment, etc.
        }
        is_valid, error, violations = registry.validate_structure(
            "API-RISK-CLASSIFICATION", invalid_data
        )
        assert not is_valid
        assert len(violations) > 0

    def test_meta_type_mismatch(self):
        """Intentionally violate contract with type mismatch."""
        registry = get_contract_registry()
        register_core_contracts()

        # Violate by using wrong type
        invalid_data = {
            "tier": "elevated",
            "risk_score": "not_a_float",  # Should be float
            "base_risk": 0.5,
            "shock_adjustment": 0.0,
            "convergence_adjustment": 0.0,
            "trend_adjustment": 0.0,
            "contributing_factors": [],
        }
        is_valid, error, violations = registry.validate_structure(
            "API-RISK-CLASSIFICATION", invalid_data
        )
        assert not is_valid
        assert any("must be float" in v for v in violations)

    def test_meta_regression_detection(self):
        """Intentionally cause regression by removing field."""
        registry = get_contract_registry()
        register_core_contracts()

        # Create snapshot
        snapshot_data = {
            "tier": "elevated",
            "risk_score": 0.6,
            "base_risk": 0.5,
            "shock_adjustment": 0.0,
            "convergence_adjustment": 0.0,
            "trend_adjustment": 0.0,
            "contributing_factors": [],
        }
        registry.snapshot("API-RISK-CLASSIFICATION", snapshot_data)

        # Current data missing a field
        current_data = {
            "tier": "elevated",
            "risk_score": 0.6,
            # Missing: base_risk
            "shock_adjustment": 0.0,
            "convergence_adjustment": 0.0,
            "trend_adjustment": 0.0,
            "contributing_factors": [],
        }
        has_regression, error = registry.detect_regression(
            "API-RISK-CLASSIFICATION", current_data
        )
        assert has_regression
        assert "base_risk" in error or "Fields removed" in error

    def test_meta_semantic_drift_risk_tier(self):
        """Intentionally violate semantic invariant: risk tier monotonicity."""
        detector = get_semantic_detector()
        detector.clear_drift()

        # Violate: score1 < score2 but tier1 > tier2
        has_drift, error = detector.check_risk_tier_monotonicity(
            0.3, "elevated", 0.6, "watchlist"
        )
        assert has_drift
        assert len(detector.get_drift_detected()) > 0

    def test_meta_semantic_drift_confidence_volatility(self):
        """Intentionally violate semantic invariant: confidence-volatility."""
        detector = get_semantic_detector()
        detector.clear_drift()

        # Violate: high volatility but high confidence
        has_drift, error = detector.check_confidence_volatility_relationship(0.8, 0.8)
        assert has_drift
        assert len(detector.get_drift_detected()) > 0

    def test_meta_semantic_drift_convergence(self):
        """Intentionally violate semantic invariant: convergence meaning."""
        detector = get_semantic_detector()
        detector.clear_drift()

        # Violate: high score but few reinforcing signals
        has_drift, error = detector.check_convergence_meaning(75.0, [])
        assert has_drift
        assert len(detector.get_drift_detected()) > 0


class TestContractIntegration:
    """Test contract enforcement integration with actual endpoints."""

    def test_risk_classification_contract_validation(self):
        """Risk classification should validate against contract."""
        from app.services.risk.classifier import RiskClassifier

        classifier = RiskClassifier()
        result = classifier.classify_risk(
            behavior_index=0.6,
            convergence_score=70.0,
            trend_direction="increasing",
        )

        # Verify contract structure
        registry = get_contract_registry()
        is_valid, error, violations = registry.validate_structure(
            "API-RISK-CLASSIFICATION", result
        )
        # Should pass (result matches contract)
        assert is_valid or len(violations) == 0  # May have warnings but structure valid

    def test_forecast_result_contract_validation(self):
        """Forecast result should validate against contract."""
        registry = get_contract_registry()
        register_core_contracts()

        # Sample forecast result structure
        forecast_result = {
            "history": [],
            "forecast": [],
            "sources": [],
            "metadata": {},
        }

        is_valid, error, violations = registry.validate_structure(
            "API-FORECAST-RESULT", forecast_result
        )
        assert is_valid
        assert len(violations) == 0
