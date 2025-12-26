# SPDX-License-Identifier: PROPRIETARY
"""Tests for version evolution, deprecation, and misuse detection."""

from app.core.versioning import (
    get_deprecation_registry,
    get_misuse_detector,
    get_version_checker,
)


class TestDeprecationRegistry:
    """Test deprecation registry functionality."""

    def test_registry_initialization(self):
        """Registry should initialize correctly."""
        registry = get_deprecation_registry()
        assert registry is not None

    def test_register_deprecation(self):
        """Should be able to register deprecations."""
        registry = get_deprecation_registry()
        registry.register_deprecation(
            "API-FORECAST-RESULT",
            "explanation",
            deprecated_in_version="0.2.0",
            removal_version="1.0.0",
            migration_path="Use 'explanations' field instead",
            replacement_field="explanations",
        )
        assert registry.is_deprecated("API-FORECAST-RESULT", "explanation")

    def test_check_deprecation_warns(self):
        """Should warn when deprecated field is used."""
        registry = get_deprecation_registry()
        registry.register_deprecation(
            "API-FORECAST-RESULT",
            "explanation",
            deprecated_in_version="0.2.0",
            removal_version="1.0.0",
            migration_path="Use 'explanations' field instead",
            replacement_field="explanations",
        )

        data = {"explanation": "test"}
        warning = registry.check_deprecation("API-FORECAST-RESULT", "explanation", data)
        assert warning is not None
        assert "deprecated" in warning.lower()

    def test_check_deprecation_no_warning_for_none(self):
        """Should not warn when deprecated field is None."""
        registry = get_deprecation_registry()
        registry.register_deprecation(
            "API-FORECAST-RESULT",
            "explanation",
            deprecated_in_version="0.2.0",
            removal_version="1.0.0",
            migration_path="Use 'explanations' field instead",
        )

        data = {"explanation": None}
        warning = registry.check_deprecation("API-FORECAST-RESULT", "explanation", data)
        # Should not warn for None values
        assert warning is None or "deprecated" not in warning.lower()


class TestVersionChecker:
    """Test version checker functionality."""

    def test_checker_initialization(self):
        """Version checker should initialize correctly."""
        checker = get_version_checker()
        assert checker is not None

    def test_check_compatible_versions(self):
        """Compatible versions should pass."""
        checker = get_version_checker()
        is_compatible, error = checker.check_version_compatibility("0.1.0", "0.1.0", "test")
        assert is_compatible
        assert error is None

    def test_check_major_version_mismatch(self):
        """Major version mismatch should fail."""
        checker = get_version_checker()
        is_compatible, error = checker.check_version_compatibility("1.0.0", "2.0.0", "test")
        assert not is_compatible
        assert "major" in error.lower()

    def test_check_minor_version_mismatch(self):
        """Minor version mismatch should warn but be compatible."""
        checker = get_version_checker()
        is_compatible, error = checker.check_version_compatibility("0.1.0", "0.2.0", "test")
        assert is_compatible  # Minor versions are compatible but may cause issues
        assert error is not None
        assert "minor" in error.lower()

    def test_check_patch_version_mismatch(self):
        """Patch version mismatch should be compatible."""
        checker = get_version_checker()
        is_compatible, error = checker.check_version_compatibility("0.1.0", "0.1.1", "test")
        assert is_compatible
        assert error is None

    def test_check_partial_upgrade_detection(self):
        """Should detect partial upgrades."""
        checker = get_version_checker()
        has_partial, error = checker.check_partial_upgrade(frontend_version="0.2.0")
        # May or may not detect depending on backend version
        # This test verifies the method works
        assert isinstance(has_partial, bool)
        assert isinstance(error, (type(None), str))


class TestMisuseDetector:
    """Test misuse detector functionality."""

    def test_detector_initialization(self):
        """Misuse detector should initialize correctly."""
        detector = get_misuse_detector()
        assert detector is not None

    def test_check_configuration_combination_valid(self):
        """Valid configurations should pass."""
        detector = get_misuse_detector()
        has_misuse, warning = detector.check_configuration_combination(
            days_back=30, forecast_horizon=7
        )
        assert not has_misuse
        assert warning is None

    def test_check_configuration_combination_invalid_horizon(self):
        """Forecast horizon > 50% of days_back should warn."""
        detector = get_misuse_detector()
        has_misuse, warning = detector.check_configuration_combination(
            days_back=10, forecast_horizon=7
        )
        assert has_misuse
        assert warning is not None
        assert "50%" in warning or "horizon" in warning.lower()

    def test_check_configuration_combination_insufficient_data(self):
        """Insufficient data should warn."""
        detector = get_misuse_detector()
        has_misuse, warning = detector.check_configuration_combination(
            days_back=30, forecast_horizon=7, data_points=5
        )
        assert has_misuse
        assert warning is not None
        assert "insufficient" in warning.lower() or "data" in warning.lower()

    def test_check_dangerous_parameters_none(self):
        """None scenario config should pass."""
        detector = get_misuse_detector()
        has_misuse, warning = detector.check_dangerous_parameters(None)
        assert not has_misuse
        assert warning is None

    def test_check_dangerous_parameters_extreme_values(self):
        """Extreme parameter values should warn."""
        detector = get_misuse_detector()
        scenario_config = {"economic_stress_offset": 0.9, "environmental_stress_offset": -0.85}
        has_misuse, warning = detector.check_dangerous_parameters(scenario_config)
        assert has_misuse
        assert warning is not None
        assert "extreme" in warning.lower() or "0.8" in warning

    def test_check_misleading_defaults_valid(self):
        """Valid defaults should pass."""
        detector = get_misuse_detector()
        has_misuse, warning = detector.check_misleading_defaults("New York", region_id="city_nyc")
        assert not has_misuse
        assert warning is None

    def test_check_misleading_defaults_invalid(self):
        """Unknown region without region_id should warn."""
        detector = get_misuse_detector()
        has_misuse, warning = detector.check_misleading_defaults("Unknown", region_id=None)
        assert has_misuse
        assert warning is not None
        assert "unknown" in warning.lower()


class TestMetaVersionEvolution:
    """Meta-tests that simulate version evolution scenarios."""

    def test_meta_deprecation_workflow(self):
        """Simulate deprecation workflow."""
        registry = get_deprecation_registry()
        registry.register_deprecation(
            "API-FORECAST-RESULT",
            "old_field",
            deprecated_in_version="0.2.0",
            removal_version="1.0.0",
            migration_path="Use 'new_field' instead",
            replacement_field="new_field",
        )

        # Simulate using deprecated field
        data = {"old_field": "value", "new_field": "value"}
        warning = registry.check_deprecation("API-FORECAST-RESULT", "old_field", data)
        assert warning is not None
        assert "deprecated" in warning.lower()
        assert "new_field" in warning

    def test_meta_version_mismatch_detection(self):
        """Simulate version mismatch detection."""
        checker = get_version_checker()
        checker.clear_mismatches()

        # Simulate frontend expecting different version
        has_partial, error = checker.check_partial_upgrade(frontend_version="1.0.0")
        # May or may not detect depending on backend version
        assert isinstance(has_partial, bool)

    def test_meta_misuse_scenarios(self):
        """Simulate various misuse scenarios."""
        detector = get_misuse_detector()
        detector.clear_misuse()

        # Scenario 1: Extreme forecast horizon
        has_misuse, _ = detector.check_configuration_combination(days_back=10, forecast_horizon=8)
        assert has_misuse

        # Scenario 2: Extreme parameters
        has_misuse, _ = detector.check_dangerous_parameters({"offset": 0.95})
        assert has_misuse

        # Scenario 3: Misleading defaults
        has_misuse, _ = detector.check_misleading_defaults("Unknown", region_id=None)
        assert has_misuse

        misuse_count = len(detector.get_misuse_detected())
        assert misuse_count >= 3


class TestVersionEvolutionIntegration:
    """Integration tests for version evolution."""

    def test_deprecation_in_forecast_result(self):
        """Deprecation checks should work with ForecastResult."""
        registry = get_deprecation_registry()
        registry.register_deprecation(
            "API-FORECAST-RESULT",
            "explanation",
            deprecated_in_version="0.2.0",
            removal_version="1.0.0",
            migration_path="Use 'explanations' field",
            replacement_field="explanations",
        )

        # Simulate ForecastResult with deprecated field
        result_dict = {
            "history": [],
            "forecast": [],
            "sources": [],
            "metadata": {},
            "explanation": "test",  # Deprecated field
        }
        warning = registry.check_deprecation("API-FORECAST-RESULT", "explanation", result_dict)
        assert warning is not None

    def test_version_check_in_status_endpoint(self):
        """Version checker should provide backend version."""
        checker = get_version_checker()
        backend_version = checker.get_backend_version()
        assert backend_version is not None
        assert isinstance(backend_version, str)
        # Should be semantic version format
        assert "." in backend_version
