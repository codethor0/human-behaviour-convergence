# SPDX-License-Identifier: PROPRIETARY
"""Version evolution, deprecation, and partial upgrade detection.

This module provides version tracking, deprecation warnings, and detection
of unsafe partial upgrades.
"""
import os
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger("core.versioning")


class DeprecationStatus(Enum):
    """Deprecation status levels."""

    ACTIVE = "active"  # Field is active
    DEPRECATED = "deprecated"  # Field is deprecated, will be removed
    REMOVED = "removed"  # Field has been removed


class VersionMismatch(Exception):
    """Exception raised when version mismatch is detected."""

    def __init__(self, component: str, expected: str, actual: str, message: str):
        super().__init__(
            f"Version mismatch in {component}: expected {expected}, got {actual} - {message}"
        )
        self.component = component
        self.expected = expected
        self.actual = actual
        self.message = message


class DeprecationRegistry:
    """Registry of deprecated fields and their migration paths."""

    def __init__(self):
        """Initialize deprecation registry."""
        self._deprecations: Dict[str, Dict[str, Any]] = {}
        self._warnings_logged: Set[str] = set()

    def register_deprecation(
        self,
        contract_name: str,
        field_name: str,
        deprecated_in_version: str,
        removal_version: str,
        migration_path: str,
        replacement_field: Optional[str] = None,
    ) -> None:
        """
        Register a deprecated field.

        Args:
            contract_name: Contract name (e.g., "API-FORECAST-RESULT")
            field_name: Field name being deprecated
            deprecated_in_version: Version when field was deprecated
            removal_version: Version when field will be removed
            migration_path: Description of migration path
            replacement_field: Optional replacement field name
        """
        key = f"{contract_name}:{field_name}"
        self._deprecations[key] = {
            "contract": contract_name,
            "field": field_name,
            "deprecated_in": deprecated_in_version,
            "removal_version": removal_version,
            "migration_path": migration_path,
            "replacement": replacement_field,
            "status": DeprecationStatus.DEPRECATED.value,
        }

    def check_deprecation(
        self, contract_name: str, field_name: str, data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check if a field is deprecated and log warning if used.

        Args:
            contract_name: Contract name
            field_name: Field name to check
            data: Data dictionary containing the field

        Returns:
            Warning message if deprecated, None otherwise
        """
        key = f"{contract_name}:{field_name}"
        if key not in self._deprecations:
            return None

        deprecation = self._deprecations[key]
        if field_name in data and data[field_name] is not None:
            warning_key = f"{key}:{id(data)}"
            if warning_key not in self._warnings_logged:
                self._warnings_logged.add(warning_key)
                warning_msg = (
                    f"Field '{field_name}' in contract '{contract_name}' is deprecated "
                    f"(deprecated in {deprecation['deprecated_in']}, "
                    f"will be removed in {deprecation['removal_version']}). "
                    f"Migration: {deprecation['migration_path']}"
                )
                if deprecation["replacement"]:
                    warning_msg += f" Use '{deprecation['replacement']}' instead."
                # Log without duplicating contract/field keys
                log_data = {
                    k: v
                    for k, v in deprecation.items()
                    if k not in ["contract", "field"]
                }
                logger.warning(
                    "Deprecated field used",
                    contract=contract_name,
                    field=field_name,
                    **log_data,
                )
                return warning_msg

        return None

    def get_deprecations(self) -> List[Dict[str, Any]]:
        """Get all registered deprecations."""
        return list(self._deprecations.values())

    def is_deprecated(self, contract_name: str, field_name: str) -> bool:
        """Check if a field is deprecated."""
        key = f"{contract_name}:{field_name}"
        return key in self._deprecations


# Global deprecation registry
_deprecation_registry = DeprecationRegistry()


def get_deprecation_registry() -> DeprecationRegistry:
    """Get the global deprecation registry."""
    return _deprecation_registry


class VersionChecker:
    """Checks version compatibility and detects partial upgrades."""

    def __init__(self):
        """Initialize version checker."""
        self._backend_version = os.getenv("APP_VERSION", "0.1.0")
        self._frontend_version = os.getenv("FRONTEND_VERSION", "0.1.0")
        self._mismatches_detected: List[Dict[str, Any]] = []

    def get_backend_version(self) -> str:
        """Get backend version."""
        # Read dynamically to allow test monkeypatching
        return os.getenv("APP_VERSION", self._backend_version)

    def get_frontend_version(self) -> str:
        """Get frontend version."""
        return self._frontend_version

    def check_version_compatibility(
        self, expected_version: str, actual_version: str, component: str = "unknown"
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if two versions are compatible.

        Args:
            expected_version: Expected version (e.g., "0.1.0")
            actual_version: Actual version (e.g., "0.1.0")
            component: Component name for error messages

        Returns:
            Tuple of (is_compatible, error_message)
        """
        if expected_version == actual_version:
            return True, None

        # Parse semantic versions
        try:
            expected_parts = [int(x) for x in expected_version.split(".")]
            actual_parts = [int(x) for x in actual_version.split(".")]
        except (ValueError, AttributeError):
            return (
                False,
                f"Invalid version format: {expected_version} vs {actual_version}",
            )

        # Major version mismatch = incompatible
        if expected_parts[0] != actual_parts[0]:
            mismatch_info = {
                "component": component,
                "expected": expected_version,
                "actual": actual_version,
                "reason": "major_version_mismatch",
            }
            self._mismatches_detected.append(mismatch_info)
            logger.error("Major version mismatch detected", **mismatch_info)
            return (
                False,
                f"Major version mismatch: expected {expected_version}, got {actual_version}",
            )

        # Minor version mismatch = may be incompatible
        if expected_parts[1] != actual_parts[1]:
            mismatch_info = {
                "component": component,
                "expected": expected_version,
                "actual": actual_version,
                "reason": "minor_version_mismatch",
            }
            self._mismatches_detected.append(mismatch_info)
            logger.warning("Minor version mismatch detected", **mismatch_info)
            return (
                True,
                f"Minor version mismatch: expected {expected_version}, got {actual_version} (may cause issues)",
            )

        # Patch version mismatch = compatible
        return True, None

    def check_partial_upgrade(
        self, frontend_version: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for partial upgrade scenarios.

        Args:
            frontend_version: Optional frontend version to check

        Returns:
            Tuple of (has_partial_upgrade, error_message)
        """
        if frontend_version is None:
            frontend_version = self._frontend_version

        is_compatible, error = self.check_version_compatibility(
            frontend_version, self._backend_version, "frontend-backend"
        )

        if not is_compatible:
            return (
                True,
                f"Partial upgrade detected: frontend {frontend_version} vs backend {self._backend_version} - {error}",
            )

        return False, None

    def get_mismatches(self) -> List[Dict[str, Any]]:
        """Get all detected version mismatches."""
        return self._mismatches_detected.copy()

    def clear_mismatches(self) -> None:
        """Clear detected mismatches."""
        self._mismatches_detected.clear()


# Global version checker
_version_checker = VersionChecker()


def get_version_checker() -> VersionChecker:
    """Get the global version checker."""
    return _version_checker


class MisuseDetector:
    """Detects human misuse scenarios."""

    def __init__(self):
        """Initialize misuse detector."""
        self._misuse_detected: List[Dict[str, Any]] = []

    def check_configuration_combination(
        self, days_back: int, forecast_horizon: int, data_points: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for invalid configuration combinations.

        Args:
            days_back: Number of historical days
            forecast_horizon: Number of days to forecast
            data_points: Optional actual data points available

        Returns:
            Tuple of (has_misuse, warning_message)
        """
        # Check: forecast_horizon should not exceed days_back significantly
        if forecast_horizon > days_back * 0.5:
            warning = (
                f"Forecast horizon ({forecast_horizon}) is more than 50% of historical "
                f"data window ({days_back}). This may lead to unreliable forecasts."
            )
            self._record_misuse("configuration_combination", warning)
            logger.warning("Configuration misuse detected", warning=warning)
            return True, warning

        # Check: insufficient data for forecast
        if data_points is not None and data_points < forecast_horizon * 2:
            warning = (
                f"Insufficient data points ({data_points}) for forecast horizon "
                f"({forecast_horizon}). Need at least {forecast_horizon * 2} data points."
            )
            self._record_misuse("insufficient_data", warning)
            logger.warning("Configuration misuse detected", warning=warning)
            return True, warning

        return False, None

    def check_dangerous_parameters(
        self, scenario_config: Optional[Dict[str, float]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for dangerous parameter combinations.

        Args:
            scenario_config: Optional scenario configuration dictionary

        Returns:
            Tuple of (has_misuse, warning_message)
        """
        if scenario_config is None:
            return False, None

        # Check for extreme offset values
        extreme_values = []
        for key, value in scenario_config.items():
            if isinstance(value, (int, float)) and abs(value) > 0.8:
                extreme_values.append((key, value))

        if extreme_values:
            warning = (
                f"Extreme parameter values detected: {extreme_values}. "
                f"Values > 0.8 may create unrealistic scenarios."
            )
            self._record_misuse("extreme_parameters", warning)
            logger.warning("Parameter misuse detected", warning=warning)
            return True, warning

        return False, None

    def check_misleading_defaults(
        self, region_name: str, region_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for misleading default values.

        Args:
            region_name: Region name
            region_id: Optional region ID

        Returns:
            Tuple of (has_misuse, warning_message)
        """
        if region_name == "Unknown" and region_id is None:
            warning = "Region name is 'Unknown' without region_id. This may indicate invalid configuration."
            self._record_misuse("misleading_defaults", warning)
            logger.warning("Default misuse detected", warning=warning)
            return True, warning

        return False, None

    def _record_misuse(self, category: str, message: str) -> None:
        """Record a misuse detection."""
        self._misuse_detected.append(
            {"category": category, "message": message, "timestamp": None}
        )

    def get_misuse_detected(self) -> List[Dict[str, Any]]:
        """Get all detected misuse."""
        return self._misuse_detected.copy()

    def clear_misuse(self) -> None:
        """Clear detected misuse."""
        self._misuse_detected.clear()


# Global misuse detector
_misuse_detector = MisuseDetector()


def get_misuse_detector() -> MisuseDetector:
    """Get the global misuse detector."""
    return _misuse_detector


# Initialize deprecations (currently none, but structure ready)
def register_deprecations() -> None:
    """Register known deprecations."""
    # No deprecations currently, but structure is ready for future use
    # Example:
    # registry = get_deprecation_registry()
    # registry.register_deprecation(
    #     "API-FORECAST-RESULT",
    #     "explanation",
    #     deprecated_in_version="0.2.0",
    #     removal_version="1.0.0",
    #     migration_path="Use 'explanations' field instead",
    #     replacement_field="explanations",
    # )


# Initialize on import
register_deprecations()
