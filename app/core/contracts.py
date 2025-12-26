# SPDX-License-Identifier: PROPRIETARY
"""Contract enforcement and regression guards.

This module provides contract validation, schema regression detection,
and semantic drift detection for API and trace contracts.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger("core.contracts")


class ContractViolation(Exception):
    """Exception raised when a contract is violated."""

    def __init__(self, contract_name: str, message: str, details: Optional[Dict] = None):
        super().__init__(f"Contract violation: {contract_name} - {message}")
        self.contract_name = contract_name
        self.message = message
        self.details = details or {}


class ViolationSeverity(Enum):
    """Severity levels for contract violations."""

    CRITICAL = "critical"  # Breaking change
    HIGH = "high"  # Significant change
    MEDIUM = "medium"  # Minor change
    LOW = "low"  # Informational


class ContractRegistry:
    """Registry of all system contracts."""

    def __init__(self):
        """Initialize contract registry."""
        self._contracts: Dict[str, Dict[str, Any]] = {}
        self._violations: List[Dict[str, Any]] = []
        self._snapshots: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        version: str,
        schema: Dict[str, Any],
        stability: str = "STABLE",
        required_fields: Optional[List[str]] = None,
    ) -> None:
        """
        Register a contract.

        Args:
            name: Contract name (e.g., "API-001")
            version: Contract version (e.g., "1.0")
            schema: JSON schema or structure definition
            stability: Stability level ("STABLE", "EXPERIMENTAL")
            required_fields: List of required field names
        """
        self._contracts[name] = {
            "name": name,
            "version": version,
            "schema": schema,
            "stability": stability,
            "required_fields": required_fields or [],
        }

    def snapshot(self, name: str, data: Dict[str, Any]) -> None:
        """
        Create a snapshot of contract data for regression detection.

        Args:
            name: Contract name
            data: Contract data to snapshot
        """
        self._snapshots[name] = {
            "data": data,
            "fields": set(data.keys()) if isinstance(data, dict) else set(),
        }

    def validate_structure(
        self, name: str, data: Dict[str, Any], strict: bool = False
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate data structure against contract.

        Args:
            name: Contract name
            data: Data to validate
            strict: If True, fail on extra fields

        Returns:
            Tuple of (is_valid, error_message, violations)
        """
        if name not in self._contracts:
            return False, f"Unknown contract: {name}", []

        contract = self._contracts[name]
        schema = contract["schema"]
        required_fields = contract["required_fields"]
        violations = []

        if not isinstance(data, dict):
            return False, f"Data must be a dictionary, got {type(data)}", []

        # Check required fields
        for field in required_fields:
            if field not in data:
                violations.append(f"Missing required field: {field}")

        # Check field types (basic validation)
        for field, expected_type in schema.items():
            if field in data:
                actual_value = data[field]
                if expected_type == "float" and not isinstance(actual_value, (int, float)):
                    violations.append(f"Field {field} must be float, got {type(actual_value)}")
                elif expected_type == "int" and not isinstance(actual_value, int):
                    violations.append(f"Field {field} must be int, got {type(actual_value)}")
                elif expected_type == "str" and not isinstance(actual_value, str):
                    violations.append(f"Field {field} must be str, got {type(actual_value)}")
                elif expected_type == "bool" and not isinstance(actual_value, bool):
                    violations.append(f"Field {field} must be bool, got {type(actual_value)}")
                elif expected_type == "list" and not isinstance(actual_value, list):
                    violations.append(f"Field {field} must be list, got {type(actual_value)}")
                elif expected_type == "dict" and not isinstance(actual_value, dict):
                    violations.append(f"Field {field} must be dict, got {type(actual_value)}")

        # Check for removed fields (regression detection)
        if name in self._snapshots:
            snapshot_fields = self._snapshots[name]["fields"]
            current_fields = set(data.keys())
            removed_fields = snapshot_fields - current_fields
            if removed_fields:
                violations.append(f"Removed fields detected: {removed_fields}")

        # Check for unexpected fields (if strict)
        if strict:
            schema_fields = set(schema.keys())
            extra_fields = set(data.keys()) - schema_fields - set(required_fields)
            if extra_fields:
                violations.append(f"Unexpected fields: {extra_fields}")

        is_valid = len(violations) == 0
        error_msg = "; ".join(violations) if violations else None

        if not is_valid:
            violation = {
                "contract": name,
                "version": contract["version"],
                "violations": violations,
                "severity": self._classify_severity(violations),
            }
            self._violations.append(violation)
            logger.warning(
                "Contract violation detected",
                contract=name,
                violations=violations,
                severity=violation["severity"],
            )

        return is_valid, error_msg, violations

    def detect_regression(self, name: str, current_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Detect regression by comparing current data to snapshot.

        Args:
            name: Contract name
            current_data: Current contract data

        Returns:
            Tuple of (has_regression, error_message)
        """
        if name not in self._snapshots:
            self.snapshot(name, current_data)
            return False, None

        snapshot = self._snapshots[name]
        snapshot_fields = snapshot["fields"]
        current_fields = set(current_data.keys())

        # Detect removed fields
        removed_fields = snapshot_fields - current_fields
        if removed_fields:
            return True, f"Fields removed: {removed_fields}"

        # Detect renamed fields (heuristic: same count, different names)
        if len(snapshot_fields) == len(current_fields) and snapshot_fields != current_fields:
            return True, f"Field structure changed: {snapshot_fields} -> {current_fields}"

        return False, None

    def _classify_severity(self, violations: List[str]) -> str:
        """Classify violation severity."""
        if any("Missing required field" in v for v in violations):
            return ViolationSeverity.CRITICAL.value
        elif any("Removed fields" in v for v in violations):
            return ViolationSeverity.CRITICAL.value
        elif any("must be" in v for v in violations):
            return ViolationSeverity.HIGH.value
        else:
            return ViolationSeverity.MEDIUM.value

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all recorded violations."""
        return self._violations.copy()

    def clear_violations(self) -> None:
        """Clear recorded violations."""
        self._violations.clear()


# Global contract registry instance
_registry = ContractRegistry()


def get_contract_registry() -> ContractRegistry:
    """Get the global contract registry."""
    return _registry


class SemanticDriftDetector:
    """Detects semantic drift in contract meanings."""

    def __init__(self):
        """Initialize semantic drift detector."""
        self._baselines: Dict[str, Dict[str, Any]] = {}
        self._drift_detected: List[Dict[str, Any]] = []

    def set_baseline(self, key: str, data: Dict[str, Any]) -> None:
        """
        Set baseline for semantic comparison.

        Args:
            key: Semantic invariant key
            data: Baseline data
        """
        self._baselines[key] = data

    def check_risk_tier_monotonicity(
        self, risk_score1: float, tier1: str, risk_score2: float, tier2: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check semantic invariant: Risk tier monotonicity.

        Args:
            risk_score1: First risk score
            tier1: First risk tier
            risk_score2: Second risk score
            tier2: Second risk tier

        Returns:
            Tuple of (has_drift, error_message)
        """
        tier_order = {"stable": 0, "watchlist": 1, "elevated": 2, "high": 3, "critical": 4}
        order1 = tier_order.get(tier1, -1)
        order2 = tier_order.get(tier2, -1)

        if order1 == -1 or order2 == -1:
            return True, f"Unknown tier: {tier1} or {tier2}"

        # Semantic drift: score1 < score2 but tier1 > tier2
        if risk_score1 < risk_score2 and order1 > order2:
            drift_info = {
                "invariant": "risk_tier_monotonicity",
                "score1": risk_score1,
                "tier1": tier1,
                "score2": risk_score2,
                "tier2": tier2,
            }
            self._drift_detected.append(drift_info)
            logger.warning("Semantic drift detected: risk tier monotonicity", **drift_info)
            return True, f"Risk score {risk_score1} ({tier1}) < {risk_score2} ({tier2}) but tier order violated"

        return False, None

    def check_confidence_volatility_relationship(
        self, volatility: float, confidence: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check semantic invariant: Confidence decreases with volatility.

        Args:
            volatility: Volatility value (0.0-1.0)
            confidence: Confidence value (0.0-1.0)

        Returns:
            Tuple of (has_drift, error_message)
        """
        # Semantic drift: high volatility but high confidence
        if volatility > 0.7 and confidence > 0.7:
            drift_info = {
                "invariant": "confidence_volatility_relationship",
                "volatility": volatility,
                "confidence": confidence,
            }
            self._drift_detected.append(drift_info)
            logger.warning(
                "Semantic drift detected: confidence-volatility relationship", **drift_info
            )
            return True, f"High volatility ({volatility}) but high confidence ({confidence})"

        return False, None

    def check_convergence_meaning(
        self, score: float, reinforcing_signals: List[List]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check semantic invariant: Convergence score meaning.

        Args:
            score: Convergence score (0-100)
            reinforcing_signals: List of reinforcing signal pairs

        Returns:
            Tuple of (has_drift, error_message)
        """
        # Semantic drift: high score but few reinforcing signals
        if score > 70 and len(reinforcing_signals) < 2:
            drift_info = {
                "invariant": "convergence_meaning",
                "score": score,
                "reinforcing_count": len(reinforcing_signals),
            }
            self._drift_detected.append(drift_info)
            logger.warning("Semantic drift detected: convergence meaning", **drift_info)
            return True, f"High convergence score ({score}) but few reinforcing signals ({len(reinforcing_signals)})"

        return False, None

    def get_drift_detected(self) -> List[Dict[str, Any]]:
        """Get all detected semantic drift."""
        return self._drift_detected.copy()

    def clear_drift(self) -> None:
        """Clear detected drift."""
        self._drift_detected.clear()


# Global semantic drift detector instance
_semantic_detector = SemanticDriftDetector()


def get_semantic_detector() -> SemanticDriftDetector:
    """Get the global semantic drift detector."""
    return _semantic_detector


class ContractObservability:
    """Exposes contract violations and semantic drift to operators."""

    def __init__(self):
        """Initialize observability system."""
        self._violation_counts: Dict[str, int] = {}
        self._violation_by_severity: Dict[str, int] = {}
        self._semantic_drift_counts: Dict[str, int] = {}

    def record_violation(
        self, contract_name: str, severity: str, endpoint: Optional[str] = None
    ) -> None:
        """
        Record a contract violation.

        Args:
            contract_name: Contract name
            severity: Violation severity
            endpoint: Optional endpoint name
        """
        key = f"{contract_name}:{severity}"
        self._violation_counts[key] = self._violation_counts.get(key, 0) + 1
        self._violation_by_severity[severity] = self._violation_by_severity.get(severity, 0) + 1

        logger.warning(
            "Contract violation recorded",
            contract=contract_name,
            severity=severity,
            endpoint=endpoint,
            count=self._violation_counts[key],
        )

    def record_semantic_drift(self, invariant_name: str) -> None:
        """
        Record semantic drift detection.

        Args:
            invariant_name: Semantic invariant name
        """
        self._semantic_drift_counts[invariant_name] = (
            self._semantic_drift_counts.get(invariant_name, 0) + 1
        )

        logger.warning(
            "Semantic drift recorded",
            invariant=invariant_name,
            count=self._semantic_drift_counts[invariant_name],
        )

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get observability metrics.

        Returns:
            Dictionary with violation and drift metrics
        """
        return {
            "violation_counts": self._violation_counts.copy(),
            "violation_by_severity": self._violation_by_severity.copy(),
            "semantic_drift_counts": self._semantic_drift_counts.copy(),
            "total_violations": sum(self._violation_counts.values()),
            "total_semantic_drift": sum(self._semantic_drift_counts.values()),
        }

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self._violation_counts.clear()
        self._violation_by_severity.clear()
        self._semantic_drift_counts.clear()


# Global observability instance
_observability = ContractObservability()


def get_observability() -> ContractObservability:
    """Get the global observability system."""
    return _observability


# Register core contracts
def register_core_contracts() -> None:
    """Register core system contracts."""
    registry = get_contract_registry()

    # RiskTrace contract
    registry.register(
        "TRACE-001",
        "1.0",
        {
            "output": "dict",
            "components": "dict",
            "reconciliation": "dict",
            "metadata": "dict",
        },
        stability="STABLE",
        required_fields=["output", "components", "reconciliation", "metadata"],
    )

    # ConfidenceTrace contract
    registry.register(
        "TRACE-002",
        "1.0",
        {
            "output": "dict",
            "components": "dict",
            "reconciliation": "dict",
            "metadata": "dict",
        },
        stability="STABLE",
        required_fields=["output", "components", "reconciliation", "metadata"],
    )

    # RiskClassification contract
    registry.register(
        "API-RISK-CLASSIFICATION",
        "1.0",
        {
            "tier": "str",
            "risk_score": "float",
            "base_risk": "float",
            "shock_adjustment": "float",
            "convergence_adjustment": "float",
            "trend_adjustment": "float",
            "contributing_factors": "list",
        },
        stability="STABLE",
        required_fields=[
            "tier",
            "risk_score",
            "base_risk",
            "shock_adjustment",
            "convergence_adjustment",
            "trend_adjustment",
            "contributing_factors",
        ],
    )

    # ForecastResult contract
    registry.register(
        "API-FORECAST-RESULT",
        "1.0",
        {
            "history": "list",
            "forecast": "list",
            "sources": "list",
            "metadata": "dict",
        },
        stability="STABLE",
        required_fields=["history", "forecast", "sources", "metadata"],
    )


# Initialize contracts on import
register_core_contracts()
