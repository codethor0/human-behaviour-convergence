# SPDX-License-Identifier: PROPRIETARY
"""Calibration configuration constants for behavioral forecasting.

This module centralizes all tunable parameters. Values are extracted from
the current implementation to enable easy tuning without code changes.

CALIBRATION GUIDELINES:
- All values are generic and data-driven, not region-specific.
- Modify these constants to tune the model, then verify:
  - Determinism: Same input → same output across runs
  - Numeric integrity: All indices remain in [0.0, 1.0]
  - Observability: Source status and metadata remain accurate

CURRENT VALUES (extracted from existing code):
- BehaviorIndexComputer default weights
- GDELT enforcement normalization K=5.0
- GDELT legislative normalization K=10.0
"""

# Behavior Index Dimension Weights
# These weights determine how much each dimension contributes to the overall behavior_index.
# Weights should sum to approximately 1.0 (they are normalized if needed).
BEHAVIOR_INDEX_WEIGHTS = {
    "economic_weight": 0.25,
    "environmental_weight": 0.25,
    "mobility_weight": 0.20,
    "digital_attention_weight": 0.15,
    "health_weight": 0.15,
    "political_weight": 0.15,
    "crime_weight": 0.15,
    "misinformation_weight": 0.10,
    "social_cohesion_weight": 0.15,
}

# GDELT Enforcement Event Normalization
# Formula: enforcement_attention = min(1.0, log1p(event_count) / log1p(K))
# K controls the saturation point. Lower K = more sensitive to small event counts.
ENFORCEMENT_NORMALIZATION = {
    "K": 5.0,  # Saturation constant for enforcement events
    # Expected scaling:
    # - 0 events → ~0.0
    # - 5 events → ~0.54
    # - 10 events → ~0.65
    # - 20 events → ~0.77
    # - 50+ events → 0.85-1.0 (saturates)
}

# GDELT Legislative Event Normalization
# Formula: legislative_attention = min(1.0, log1p(event_count) / log1p(K))
# Legislative events typically occur at higher volume than enforcement, hence higher K.
LEGISLATIVE_NORMALIZATION = {
    "K": 10.0,  # Saturation constant for legislative events
    # Expected scaling:
    # - 0 events → ~0.0
    # - 10 events → ~0.47
    # - 25 events → ~0.61
    # - 50 events → ~0.71
    # - 100+ events → 0.80-1.0 (saturates)
}

# Synthetic Baseline Defaults
# These are fallback values used when real-time data is unavailable.
# They should be treated as neutral/moderate baselines and flagged in metadata.
SYNTHETIC_DEFAULTS = {
    "political_stress_baseline": 0.35,  # Moderate baseline for political stress
    "crime_stress_baseline": 0.35,  # Moderate baseline for crime stress
    "social_cohesion_stress_baseline": 0.35,  # Moderate baseline for social cohesion
    "misinformation_stress_baseline": 0.35,  # Moderate baseline for misinformation
}

# Reality Blend Weights
# Controls how much real-time signals vs synthetic baselines contribute to each dimension.
# TARGET: 20% Synthetic / 80% Real-Time Signal (inverted from previous 70/30).
# Real-time signals MUST dominate when available to reflect reality.
REALITY_BLEND_WEIGHTS = {
    # Political stress blending: GDELT tone + enforcement + legislative vs synthetic baseline
    "political_base_weight": 0.20,  # Synthetic baseline weight (reduced to 20%)
    "political_realtime_weight": 0.80,  # Real-time signals weight (GDELT tone, enforcement, legislative) - DOMINATES
    # Crime stress: Currently all synthetic, so base_weight=1.0 (no real-time signals yet)
    "crime_base_weight": 1.0,  # All synthetic until real-time signals are added
    "crime_realtime_weight": 0.0,  # No real-time signals available yet
    # Social cohesion: GDELT tone + enforcement + other signals vs synthetic baseline
    "social_cohesion_base_weight": 0.20,  # Synthetic baseline weight (reduced to 20%)
    "social_cohesion_realtime_weight": 0.80,  # Real-time signals (GDELT tone, enforcement, etc.) - DOMINATES
    # Misinformation: Currently all synthetic
    "misinformation_base_weight": 1.0,  # All synthetic until real-time signals are added
    "misinformation_realtime_weight": 0.0,  # No real-time signals available yet
}

# Enforcement Signal Adjustment Weights
# These control how enforcement_attention adjusts political and social cohesion stress.
# Applied as bounded additive adjustments to real-time blended signals.
ENFORCEMENT_ADJUSTMENT = {
    "political_alpha": 0.15,  # Adjustment coefficient for political_stress
    "political_max_adjustment": 0.25,  # Maximum additive adjustment
    "social_cohesion_beta": 0.10,  # Adjustment coefficient for social_cohesion_stress
    "social_cohesion_max_adjustment": 0.20,  # Maximum additive adjustment
}

# Shock Multiplier Configuration
# Applied to behavior_index when shock event count exceeds threshold.
# CRITICAL: This ensures high shock events (e.g., 55 in MN) produce high risk scores.
SHOCK_MULTIPLIER = {
    "threshold": 15,  # Minimum shock events to trigger multiplier
    "base_multiplier": 1.0,  # Base multiplier
    "multiplier_per_shock": 0.01,  # Additional multiplier per shock event (e.g., 55 events = +0.55 = 1.55x total)
    "max_behavior_index": 0.99,  # Maximum behavior_index after multiplier (cap at 0.99 to allow headroom)
    # Formula: multiplier = base_multiplier + (shock_count / 100) * multiplier_per_shock * 100
    # Example: 55 shocks = 1.0 + (55/100) * 0.01 * 100 = 1.0 + 0.55 = 1.55x
}

# Reality Mismatch Integrity Check
# Flags conditions where high event volume doesn't match low behavior_index.
REALITY_MISMATCH_CHECK = {
    "shock_threshold": 20,  # Minimum shock events to trigger check
    "behavior_index_threshold": 0.5,  # Maximum behavior_index to trigger flag
    "enabled": True,  # Whether to perform this check
}
