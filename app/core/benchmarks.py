# SPDX-License-Identifier: PROPRIETARY
"""Comparative benchmarks and peer analysis.

This module provides comparative benchmarks by comparing regions against:
- Peer groups (e.g., US_STATES, GLOBAL_CITIES)
- Historical baselines
- National/global averages
- Sub-index level comparisons

All benchmarks are purely derived from existing analytics outputs without
changing any numerical computations.
"""
import math
from typing import Any, Dict, List, Optional

import structlog

from app.core.regions import Region, get_all_regions

logger = structlog.get_logger("core.benchmarks")


def compute_peer_group_average(
    current_region: Region,
    behavior_index_values: Dict[str, float],
    sub_index_values: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """
    Compute average behavior index and sub-indices for peer group.

    Args:
        current_region: Current region being analyzed
        behavior_index_values: Dictionary mapping region_id -> behavior_index
        sub_index_values: Optional dictionary mapping region_id -> sub_index_name -> value

    Returns:
        Dictionary with:
        - peer_group: Region group name
        - peer_count: Number of peers in group
        - average_behavior_index: Average behavior index across peers
        - average_sub_indices: Average sub-index values (if provided)
        - current_rank: Rank of current region (1-based, lower is better for stress)
    """
    if current_region.region_group is None:
        return {
            "peer_group": None,
            "peer_count": 0,
            "average_behavior_index": None,
            "average_sub_indices": None,
            "current_rank": None,
        }

    # Get all regions in the same group

    all_regions = get_all_regions()
    peer_regions = [
        r for r in all_regions if r.region_group == current_region.region_group
    ]

    if not peer_regions:
        return {
            "peer_group": current_region.region_group,
            "peer_count": 0,
            "average_behavior_index": None,
            "average_sub_indices": None,
            "current_rank": None,
        }

    # Filter to peers that have behavior index values
    peer_values = []
    for peer in peer_regions:
        if peer.id != current_region.id and peer.id in behavior_index_values:
            peer_values.append(behavior_index_values[peer.id])

    if not peer_values:
        return {
            "peer_group": current_region.region_group,
            "peer_count": 0,
            "average_behavior_index": None,
            "average_sub_indices": None,
            "current_rank": None,
        }

    # Compute average
    average_behavior_index = sum(peer_values) / len(peer_values)

    # Compute average sub-indices if provided
    average_sub_indices = None
    if sub_index_values:
        # Collect sub-index values for all peers
        peer_sub_indices: Dict[str, List[float]] = {}
        for peer in peer_regions:
            if peer.id != current_region.id and peer.id in sub_index_values:
                for sub_index_name, value in sub_index_values[peer.id].items():
                    if sub_index_name not in peer_sub_indices:
                        peer_sub_indices[sub_index_name] = []
                    peer_sub_indices[sub_index_name].append(value)

        # Compute averages
        average_sub_indices = {}
        for sub_index_name, values in peer_sub_indices.items():
            if values:
                average_sub_indices[sub_index_name] = sum(values) / len(values)

    # Compute rank (1-based, lower is better for stress indices)
    current_value = behavior_index_values.get(current_region.id)
    if current_value is not None:
        # Rank: how many peers have lower (better) values
        rank = sum(1 for v in peer_values if v < current_value) + 1
    else:
        rank = None

    return {
        "peer_group": current_region.region_group,
        "peer_count": len(peer_values),
        "average_behavior_index": float(average_behavior_index),
        "average_sub_indices": average_sub_indices,
        "current_rank": rank,
    }


def compute_historical_baseline(
    behavior_index_history: List[float],
    baseline_window_days: int = 30,
) -> Dict[str, Any]:
    """
    Compute historical baseline from behavior index history.

    Args:
        behavior_index_history: Historical behavior index values (most recent first)
        baseline_window_days: Number of days to use for baseline (default: 30)

    Returns:
        Dictionary with:
        - baseline_value: Average behavior index over baseline window
        - baseline_std: Standard deviation over baseline window
        - baseline_min: Minimum value over baseline window
        - baseline_max: Maximum value over baseline window
        - window_days: Actual number of days used
    """
    if not behavior_index_history:
        return {
            "baseline_value": None,
            "baseline_std": None,
            "baseline_min": None,
            "baseline_max": None,
            "window_days": 0,
        }

    # Use up to baseline_window_days of history (most recent first)
    window_values = behavior_index_history[:baseline_window_days]

    if not window_values:
        return {
            "baseline_value": None,
            "baseline_std": None,
            "baseline_min": None,
            "baseline_max": None,
            "window_days": 0,
        }

    # Compute statistics
    baseline_value = sum(window_values) / len(window_values)

    # Compute standard deviation
    variance = sum((v - baseline_value) ** 2 for v in window_values) / len(
        window_values
    )
    baseline_std = math.sqrt(variance) if variance > 0 else 0.0

    baseline_min = min(window_values)
    baseline_max = max(window_values)

    return {
        "baseline_value": float(baseline_value),
        "baseline_std": float(baseline_std),
        "baseline_min": float(baseline_min),
        "baseline_max": float(baseline_max),
        "window_days": len(window_values),
    }


def compute_deviation_from_baseline(
    current_value: float,
    baseline: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute deviation of current value from historical baseline.

    Args:
        current_value: Current behavior index value
        baseline: Baseline statistics (from compute_historical_baseline)

    Returns:
        Dictionary with:
        - absolute_deviation: Absolute difference from baseline
        - relative_deviation: Relative difference as percentage
        - z_score: Z-score (standard deviations from baseline)
        - classification: "normal", "elevated", or "anomalous"
    """
    baseline_value = baseline.get("baseline_value")
    baseline_std = baseline.get("baseline_std", 0.0)

    if baseline_value is None:
        return {
            "absolute_deviation": None,
            "relative_deviation": None,
            "z_score": None,
            "classification": "unknown",
        }

    absolute_deviation = current_value - baseline_value
    relative_deviation = (
        (absolute_deviation / baseline_value * 100.0)
        if abs(baseline_value) > 1e-10
        else 0.0
    )

    # Compute Z-score
    if baseline_std > 1e-10:
        z_score = absolute_deviation / baseline_std
    else:
        z_score = 0.0

    # Classify deviation
    if abs(z_score) < 1.0:
        classification = "normal"
    elif abs(z_score) < 2.0:
        classification = "elevated"
    else:
        classification = "anomalous"

    return {
        "absolute_deviation": float(absolute_deviation),
        "relative_deviation": float(relative_deviation),
        "z_score": float(z_score),
        "classification": classification,
    }


def compute_sub_index_benchmarks(
    current_sub_indices: Dict[str, float],
    peer_averages: Optional[Dict[str, float]] = None,
    baseline_averages: Optional[Dict[str, float]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Compute benchmarks for each sub-index.

    Args:
        current_sub_indices: Current sub-index values
        peer_averages: Optional peer group averages per sub-index
        baseline_averages: Optional historical baseline averages per sub-index

    Returns:
        Dictionary mapping sub_index_name -> benchmark data:
        - current_value: Current sub-index value
        - peer_average: Peer group average (if available)
        - peer_deviation: Deviation from peer average (if available)
        - baseline_average: Historical baseline average (if available)
        - baseline_deviation: Deviation from baseline (if available)
    """
    benchmarks = {}

    for sub_index_name, current_value in current_sub_indices.items():
        benchmark_data: Dict[str, Any] = {
            "current_value": float(current_value),
        }

        # Peer comparison
        if peer_averages and sub_index_name in peer_averages:
            peer_avg = peer_averages[sub_index_name]
            peer_deviation = current_value - peer_avg
            benchmark_data["peer_average"] = float(peer_avg)
            benchmark_data["peer_deviation"] = float(peer_deviation)
            benchmark_data["peer_deviation_percent"] = (
                (peer_deviation / peer_avg * 100.0) if abs(peer_avg) > 1e-10 else 0.0
            )

        # Baseline comparison
        if baseline_averages and sub_index_name in baseline_averages:
            baseline_avg = baseline_averages[sub_index_name]
            baseline_deviation = current_value - baseline_avg
            benchmark_data["baseline_average"] = float(baseline_avg)
            benchmark_data["baseline_deviation"] = float(baseline_deviation)
            benchmark_data["baseline_deviation_percent"] = (
                (baseline_deviation / baseline_avg * 100.0)
                if abs(baseline_avg) > 1e-10
                else 0.0
            )

        benchmarks[sub_index_name] = benchmark_data

    return benchmarks


def compose_benchmarks(
    current_region: Region,
    current_behavior_index: float,
    current_sub_indices: Dict[str, float],
    behavior_index_history: Optional[List[float]] = None,
    peer_behavior_indices: Optional[Dict[str, float]] = None,
    peer_sub_indices: Optional[Dict[str, Dict[str, float]]] = None,
    baseline_window_days: int = 30,
) -> Dict[str, Any]:
    """
    Compose complete benchmark analysis.

    This function is purely derived - it does not change any numerical outputs.

    Args:
        current_region: Current region being analyzed
        current_behavior_index: Current behavior index value
        current_sub_indices: Current sub-index values
        behavior_index_history: Historical behavior index values (most recent first)
        peer_behavior_indices: Optional dictionary mapping region_id -> behavior_index for peers
        peer_sub_indices: Optional dictionary mapping region_id -> sub_index_name -> value for peers
        baseline_window_days: Number of days to use for baseline (default: 30)

    Returns:
        Dictionary with:
        - peer_group_analysis: Peer group comparison
        - historical_baseline: Historical baseline statistics
        - baseline_deviation: Deviation from baseline
        - sub_index_benchmarks: Sub-index level benchmarks
        - metadata: Benchmark generation metadata
    """
    if behavior_index_history is None:
        behavior_index_history = []

    # Peer group analysis
    peer_analysis = None
    if peer_behavior_indices:
        # Include current region in peer_behavior_indices for rank calculation
        peer_behavior_indices_with_current = {
            **peer_behavior_indices,
            current_region.id: current_behavior_index,
        }
        peer_analysis = compute_peer_group_average(
            current_region,
            peer_behavior_indices_with_current,
            peer_sub_indices,
        )

    # Historical baseline
    baseline = compute_historical_baseline(behavior_index_history, baseline_window_days)

    # Baseline deviation
    baseline_deviation = compute_deviation_from_baseline(
        current_behavior_index, baseline
    )

    # Sub-index benchmarks
    peer_sub_index_averages = None
    if peer_analysis and peer_analysis.get("average_sub_indices"):
        peer_sub_index_averages = peer_analysis["average_sub_indices"]

    baseline_sub_index_averages = None
    # For baseline sub-indices, we'd need historical sub-index data
    # For now, we'll skip this unless provided in future iterations

    sub_index_benchmarks = compute_sub_index_benchmarks(
        current_sub_indices,
        peer_sub_index_averages,
        baseline_sub_index_averages,
    )

    return {
        "peer_group_analysis": peer_analysis,
        "historical_baseline": baseline,
        "baseline_deviation": baseline_deviation,
        "sub_index_benchmarks": sub_index_benchmarks,
        "metadata": {
            "region_id": current_region.id,
            "region_name": current_region.name,
            "peer_group": current_region.region_group,
            "baseline_window_days": baseline_window_days,
            "has_peer_data": peer_analysis is not None
            and peer_analysis.get("peer_count", 0) > 0,
            "has_baseline_data": baseline.get("window_days", 0) > 0,
        },
    }
