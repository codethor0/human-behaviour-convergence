# SPDX-License-Identifier: PROPRIETARY
"""Calibration configuration for behavioral forecasting.

This module centralizes all tunable constants used in the forecasting pipeline.
All normalization factors, dimension weights, and scaling parameters should
be defined here to make calibration straightforward.

DO NOT hard-code region-specific values or subjective "reality" assumptions.
All values should be generic and data-driven.
"""

from app.services.calibration.config import (
    BEHAVIOR_INDEX_WEIGHTS,
    ENFORCEMENT_ADJUSTMENT,
    ENFORCEMENT_NORMALIZATION,
    LEGISLATIVE_NORMALIZATION,
    REALITY_BLEND_WEIGHTS,
    REALITY_MISMATCH_CHECK,
    SHOCK_MULTIPLIER,
    SYNTHETIC_DEFAULTS,
)

__all__ = [
    "BEHAVIOR_INDEX_WEIGHTS",
    "ENFORCEMENT_NORMALIZATION",
    "LEGISLATIVE_NORMALIZATION",
    "SYNTHETIC_DEFAULTS",
    "REALITY_BLEND_WEIGHTS",
    "ENFORCEMENT_ADJUSTMENT",
    "SHOCK_MULTIPLIER",
    "REALITY_MISMATCH_CHECK",
]
