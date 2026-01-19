# SPDX-License-Identifier: PROPRIETARY
"""Policy engine for self-service configuration.

This module provides:
- Policy-driven alert configuration
- RBAC-aware policy control
- Safe defaults & guardrails
- Policy versioning & rollback

All policies are evaluated deterministically and never affect analytics computation.
Zero numerical drift is a HARD invariant.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger("core.policy")


# Policy DSL structure
POLICY_SCHEMA = {
    "alert_thresholds": {
        "type": "object",
        "properties": {
            "factor_id": {"type": "string"},
            "threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "direction": {"type": "string", "enum": ["above", "below"]},
        },
        "required": ["factor_id", "threshold", "direction"],
    },
    "persistence_windows": {
        "type": "object",
        "properties": {
            "alert_type": {"type": "string"},
            "days": {"type": "integer", "minimum": 1, "maximum": 90},
        },
        "required": ["alert_type", "days"],
    },
    "sensitivity_gating": {
        "type": "object",
        "properties": {
            "min_elasticity": {"type": "number", "minimum": 0.0, "maximum": 2.0},
            "require_high_confidence": {"type": "boolean"},
        },
        "required": ["min_elasticity"],
    },
    "early_warning_promotion": {
        "type": "object",
        "properties": {
            "warning_type": {"type": "string"},
            "promotion_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "promotion_persistence_days": {
                "type": "integer",
                "minimum": 1,
                "maximum": 30,
            },
        },
        "required": [
            "warning_type",
            "promotion_confidence",
            "promotion_persistence_days",
        ],
    },
}

# Safe defaults
SAFE_DEFAULTS = {
    "alert_thresholds": {
        "threshold": {"min": 0.1, "max": 0.9},
        "direction": ["above", "below"],
    },
    "persistence_windows": {
        "days": {"min": 1, "max": 30},
    },
    "sensitivity_gating": {
        "min_elasticity": {"min": 0.0, "max": 1.0},
    },
    "early_warning_promotion": {
        "promotion_confidence": {"min": 0.7, "max": 1.0},
        "promotion_persistence_days": {"min": 3, "max": 14},
    },
}

# Rate limit ceilings
RATE_LIMIT_CEILINGS = {
    "alert_generation_per_hour": 100,
    "notification_per_hour": 50,
    "policy_changes_per_day": 10,
}


class PolicyValidator:
    """Validates policy definitions against schema and bounds."""

    @staticmethod
    def validate_policy(policy: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate policy against schema and bounds.

        Args:
            policy: Policy definition

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(policy, dict):
            return False, "Policy must be a dictionary"

        # Validate each policy section
        for section_name, section_schema in POLICY_SCHEMA.items():
            if section_name in policy:
                section_value = policy[section_name]

                # Validate structure
                if not isinstance(section_value, dict):
                    return False, f"{section_name} must be a dictionary"

                # Validate bounds
                bounds_result = PolicyValidator._validate_bounds(
                    section_name, section_value
                )
                if not bounds_result[0]:
                    return bounds_result

        return True, None

    @staticmethod
    def _validate_bounds(
        section_name: str, section_value: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate bounds for a policy section."""
        if section_name not in SAFE_DEFAULTS:
            return True, None

        defaults = SAFE_DEFAULTS[section_name]

        if section_name == "alert_thresholds":
            threshold = section_value.get("threshold")
            if threshold is not None:
                min_threshold = defaults["threshold"]["min"]
                max_threshold = defaults["threshold"]["max"]
                if not (min_threshold <= threshold <= max_threshold):
                    return False, (
                        f"Threshold {threshold} out of bounds "
                        f"[{min_threshold}, {max_threshold}]"
                    )

        elif section_name == "persistence_windows":
            days = section_value.get("days")
            if days is not None:
                min_days = defaults["days"]["min"]
                max_days = defaults["days"]["max"]
                if not (min_days <= days <= max_days):
                    return False, (
                        f"Persistence days {days} out of bounds "
                        f"[{min_days}, {max_days}]"
                    )

        elif section_name == "sensitivity_gating":
            min_elasticity = section_value.get("min_elasticity")
            if min_elasticity is not None:
                min_val = defaults["min_elasticity"]["min"]
                max_val = defaults["min_elasticity"]["max"]
                if not (min_val <= min_elasticity <= max_val):
                    return False, (
                        f"Min elasticity {min_elasticity} out of bounds "
                        f"[{min_val}, {max_val}]"
                    )

        elif section_name == "early_warning_promotion":
            promotion_confidence = section_value.get("promotion_confidence")
            if promotion_confidence is not None:
                min_conf = defaults["promotion_confidence"]["min"]
                max_conf = defaults["promotion_confidence"]["max"]
                if not (min_conf <= promotion_confidence <= max_conf):
                    return False, (
                        f"Promotion confidence {promotion_confidence} out of bounds "
                        f"[{min_conf}, {max_conf}]"
                    )

            promotion_days = section_value.get("promotion_persistence_days")
            if promotion_days is not None:
                min_days = defaults["promotion_persistence_days"]["min"]
                max_days = defaults["promotion_persistence_days"]["max"]
                if not (min_days <= promotion_days <= max_days):
                    return False, (
                        f"Promotion persistence days {promotion_days} out of bounds "
                        f"[{min_days}, {max_days}]"
                    )

        return True, None


class PolicyEngine:
    """
    Policy engine for evaluating and managing policies.

    Policies are evaluated deterministically and never affect analytics computation.
    """

    def __init__(self):
        """Initialize policy engine."""
        self.policies: Dict[str, Dict[str, Any]] = {}
        self.policy_versions: Dict[str, List[Dict[str, Any]]] = {}
        self.policy_audit_log: List[Dict[str, Any]] = []

    def create_policy(
        self,
        policy_id: str,
        policy: Dict[str, Any],
        created_by: str,
        tenant_id: str = "default",
    ) -> Tuple[bool, Optional[str]]:
        """
        Create a new policy.

        Args:
            policy_id: Unique policy identifier
            policy: Policy definition
            created_by: User ID who created the policy
            tenant_id: Tenant identifier

        Returns:
            (success, error_message)
        """
        # Validate policy
        is_valid, error = PolicyValidator.validate_policy(policy)
        if not is_valid:
            return False, error

        # Check if policy already exists
        full_policy_id = f"{tenant_id}:{policy_id}"
        if full_policy_id in self.policies:
            return False, f"Policy {policy_id} already exists"

        # Create policy version
        policy_version = {
            "policy_id": policy_id,
            "tenant_id": tenant_id,
            "policy": policy,
            "version": 1,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": False,  # Must be activated explicitly
        }

        # Store policy
        self.policies[full_policy_id] = policy_version
        self.policy_versions[full_policy_id] = [policy_version]

        # Audit log
        self._audit_log(
            action="create",
            policy_id=policy_id,
            tenant_id=tenant_id,
            user_id=created_by,
        )

        return True, None

    def update_policy(
        self,
        policy_id: str,
        policy: Dict[str, Any],
        updated_by: str,
        tenant_id: str = "default",
    ) -> Tuple[bool, Optional[str]]:
        """
        Update an existing policy (creates new version).

        Args:
            policy_id: Policy identifier
            policy: Updated policy definition
            updated_by: User ID who updated the policy
            tenant_id: Tenant identifier

        Returns:
            (success, error_message)
        """
        # Validate policy
        is_valid, error = PolicyValidator.validate_policy(policy)
        if not is_valid:
            return False, error

        # Check if policy exists
        full_policy_id = f"{tenant_id}:{policy_id}"
        if full_policy_id not in self.policies:
            return False, f"Policy {policy_id} not found"

        # Get current version
        current_version = self.policies[full_policy_id]
        new_version_num = current_version["version"] + 1

        # Create new version
        new_version = {
            "policy_id": policy_id,
            "tenant_id": tenant_id,
            "policy": policy,
            "version": new_version_num,
            "created_by": updated_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": False,  # Must be activated explicitly
        }

        # Store new version
        self.policies[full_policy_id] = new_version
        self.policy_versions[full_policy_id].append(new_version)

        # Audit log
        self._audit_log(
            action="update",
            policy_id=policy_id,
            tenant_id=tenant_id,
            user_id=updated_by,
            version=new_version_num,
        )

        return True, None

    def activate_policy(
        self,
        policy_id: str,
        activated_by: str,
        tenant_id: str = "default",
    ) -> Tuple[bool, Optional[str]]:
        """
        Activate a policy version.

        Args:
            policy_id: Policy identifier
            activated_by: User ID who activated the policy
            tenant_id: Tenant identifier

        Returns:
            (success, error_message)
        """
        full_policy_id = f"{tenant_id}:{policy_id}"
        if full_policy_id not in self.policies:
            return False, f"Policy {policy_id} not found"

        # Activate policy
        self.policies[full_policy_id]["active"] = True

        # Audit log
        self._audit_log(
            action="activate",
            policy_id=policy_id,
            tenant_id=tenant_id,
            user_id=activated_by,
        )

        return True, None

    def deactivate_policy(
        self,
        policy_id: str,
        deactivated_by: str,
        tenant_id: str = "default",
    ) -> Tuple[bool, Optional[str]]:
        """
        Deactivate a policy.

        Args:
            policy_id: Policy identifier
            deactivated_by: User ID who deactivated the policy
            tenant_id: Tenant identifier

        Returns:
            (success, error_message)
        """
        full_policy_id = f"{tenant_id}:{policy_id}"
        if full_policy_id not in self.policies:
            return False, f"Policy {policy_id} not found"

        # Deactivate policy
        self.policies[full_policy_id]["active"] = False

        # Audit log
        self._audit_log(
            action="deactivate",
            policy_id=policy_id,
            tenant_id=tenant_id,
            user_id=deactivated_by,
        )

        return True, None

    def rollback_policy(
        self,
        policy_id: str,
        target_version: int,
        rolled_back_by: str,
        tenant_id: str = "default",
    ) -> Tuple[bool, Optional[str]]:
        """
        Rollback policy to a previous version.

        Args:
            policy_id: Policy identifier
            target_version: Version to rollback to
            rolled_back_by: User ID who rolled back the policy
            tenant_id: Tenant identifier

        Returns:
            (success, error_message)
        """
        full_policy_id = f"{tenant_id}:{policy_id}"
        if full_policy_id not in self.policy_versions:
            return False, f"Policy {policy_id} not found"

        versions = self.policy_versions[full_policy_id]
        target_version_obj = None
        for version in versions:
            if version["version"] == target_version:
                target_version_obj = version
                break

        if target_version_obj is None:
            return False, f"Version {target_version} not found"

        # Rollback to target version
        self.policies[full_policy_id] = target_version_obj.copy()
        self.policies[full_policy_id]["active"] = False  # Must be reactivated

        # Audit log
        self._audit_log(
            action="rollback",
            policy_id=policy_id,
            tenant_id=tenant_id,
            user_id=rolled_back_by,
            version=target_version,
        )

        return True, None

    def get_policy(
        self,
        policy_id: str,
        tenant_id: str = "default",
    ) -> Optional[Dict[str, Any]]:
        """
        Get policy by ID.

        Args:
            policy_id: Policy identifier
            tenant_id: Tenant identifier

        Returns:
            Policy object or None
        """
        full_policy_id = f"{tenant_id}:{policy_id}"
        return self.policies.get(full_policy_id)

    def get_policy_versions(
        self,
        policy_id: str,
        tenant_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """
        Get all versions of a policy.

        Args:
            policy_id: Policy identifier
            tenant_id: Tenant identifier

        Returns:
            List of policy versions
        """
        full_policy_id = f"{tenant_id}:{policy_id}"
        return self.policy_versions.get(full_policy_id, [])

    def evaluate_policy(
        self,
        policy_id: str,
        context: Dict[str, Any],
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Evaluate policy against context.

        This is deterministic and never affects analytics computation.

        Args:
            policy_id: Policy identifier
            context: Evaluation context (factor values, alerts, etc.)
            tenant_id: Tenant identifier

        Returns:
            Evaluation result
        """
        policy = self.get_policy(policy_id, tenant_id)
        if not policy or not policy.get("active"):
            return {"evaluated": False, "reason": "Policy not found or inactive"}

        policy_def = policy["policy"]
        result = {"evaluated": True, "matches": []}

        # Evaluate alert thresholds
        if "alert_thresholds" in policy_def:
            threshold_config = policy_def["alert_thresholds"]
            factor_id = threshold_config.get("factor_id")
            threshold = threshold_config.get("threshold")
            direction = threshold_config.get("direction")

            factor_value = context.get("factor_values", {}).get(factor_id, 0.0)

            if direction == "above" and factor_value > threshold:
                result["matches"].append(
                    {
                        "type": "alert_threshold",
                        "factor_id": factor_id,
                        "value": factor_value,
                        "threshold": threshold,
                    }
                )
            elif direction == "below" and factor_value < threshold:
                result["matches"].append(
                    {
                        "type": "alert_threshold",
                        "factor_id": factor_id,
                        "value": factor_value,
                        "threshold": threshold,
                    }
                )

        return result

    def _audit_log(
        self,
        action: str,
        policy_id: str,
        tenant_id: str,
        user_id: str,
        version: Optional[int] = None,
    ) -> None:
        """Log policy action to audit trail."""
        log_entry = {
            "action": action,
            "policy_id": policy_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if version is not None:
            log_entry["version"] = version

        self.policy_audit_log.append(log_entry)

        logger.info(
            "policy_action",
            action=action,
            policy_id=policy_id,
            tenant_id=tenant_id,
            user_id=user_id,
            version=version,
        )


# Singleton instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get singleton policy engine instance."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine


def reset_policy_engine() -> None:
    """Reset policy engine singleton (for testing)."""
    global _policy_engine
    _policy_engine = None
