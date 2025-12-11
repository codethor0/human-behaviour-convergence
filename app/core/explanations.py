# SPDX-License-Identifier: PROPRIETARY
"""Explanation generation for Behavior Index forecasts.

This module provides human-readable explanations of why the Behavior Index
has a particular value, based on sub-indices and component-level details.
"""
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger("core.explanations")

# Thresholds for level classification
LEVEL_THRESHOLDS = {
    "low": (0.0, 0.33),
    "moderate": (0.34, 0.66),
    "high": (0.67, 1.0),
}


def _classify_level(value: float) -> str:
    """
    Classify a normalized value (0.0-1.0) into a level.

    Args:
        value: Normalized value between 0.0 and 1.0

    Returns:
        Level string: "low", "moderate", or "high"
    """
    if value <= 0.33:
        return "low"
    elif value <= 0.66:
        return "moderate"
    else:
        return "high"


def _get_direction(value: float, baseline: float = 0.5) -> str:
    """
    Determine direction of a value relative to baseline.

    Args:
        value: Current value
        baseline: Baseline value (default: 0.5)

    Returns:
        Direction string: "up", "down", or "neutral"
    """
    if value > baseline + 0.1:
        return "up"
    elif value < baseline - 0.1:
        return "down"
    else:
        return "neutral"


def _get_importance(weight: float, value: float, baseline: float = 0.5) -> str:
    """
    Determine importance of a component based on weight and deviation from baseline.

    Args:
        weight: Weight of the component (0.0-1.0)
        value: Current value (0.0-1.0)
        baseline: Baseline value (default: 0.5)

    Returns:
        Importance string: "high", "medium", or "low"
    """
    deviation = abs(value - baseline)
    importance_score = weight * (1.0 + deviation)

    if importance_score > 0.5:
        return "high"
    elif importance_score > 0.2:
        return "medium"
    else:
        return "low"


def _explain_economic_stress(
    value: float,
    components: Optional[List[Dict]] = None,
) -> Dict:
    """
    Generate explanation for economic stress sub-index.

    Args:
        value: Economic stress value (0.0-1.0)
        components: List of component dictionaries with id, value, weight, source

    Returns:
        Dictionary with level, reason, and components
    """
    level = _classify_level(value)

    # Build reason based on level and components
    if components:
        component_names = [c.get("label", c.get("id", "")) for c in components]
        if "Market Volatility" in component_names or "market_volatility" in [
            c.get("id", "") for c in components
        ]:
            if level == "high":
                reason = (
                    "Market volatility is elevated, indicating significant "
                    "economic uncertainty."
                )
            elif level == "moderate":
                reason = (
                    "Market volatility is moderate, with some economic "
                    "uncertainty present."
                )
            else:
                reason = (
                    "Market volatility is low, suggesting relative economic stability."
                )
        else:
            if level == "high":
                reason = "Economic indicators suggest elevated stress levels."
            elif level == "moderate":
                reason = "Economic indicators show moderate stress levels."
            else:
                reason = "Economic indicators suggest low stress levels."
    else:
        if level == "high":
            reason = "Economic stress is elevated."
        elif level == "moderate":
            reason = "Economic stress is moderate."
        else:
            reason = "Economic stress is low."

    # Build component explanations
    component_explanations = []
    if components:
        for comp in components:
            comp_id = comp.get("id", "")
            comp_label = comp.get("label", comp_id.replace("_", " ").title())
            comp_value = comp.get("value", 0.5)
            comp_weight = comp.get("weight", 0.0)

            direction = _get_direction(comp_value)
            importance = _get_importance(comp_weight, comp_value)

            # Generate component-specific explanation
            if comp_id == "market_volatility":
                if direction == "up":
                    explanation = (
                        "Market volatility index is above typical levels, "
                        "indicating increased uncertainty."
                    )
                elif direction == "down":
                    explanation = (
                        "Market volatility index is below typical levels, "
                        "indicating relative stability."
                    )
                else:
                    explanation = "Market volatility index is within typical range."
            elif comp_id == "consumer_sentiment":
                if direction == "up":
                    explanation = (
                        "Consumer sentiment is below average, indicating "
                        "reduced confidence."
                    )
                elif direction == "down":
                    explanation = (
                        "Consumer sentiment is above average, indicating "
                        "strong confidence."
                    )
                else:
                    explanation = "Consumer sentiment is near average levels."
            elif comp_id == "unemployment_rate":
                if direction == "up":
                    explanation = (
                        "Unemployment rate is elevated, indicating labor market stress."
                    )
                elif direction == "down":
                    explanation = (
                        "Unemployment rate is low, indicating a healthy labor market."
                    )
                else:
                    explanation = "Unemployment rate is within typical range."
            elif comp_id == "jobless_claims":
                if direction == "up":
                    explanation = (
                        "Jobless claims are elevated, indicating increased "
                        "labor market disruption."
                    )
                elif direction == "down":
                    explanation = (
                        "Jobless claims are low, indicating stable labor "
                        "market conditions."
                    )
                else:
                    explanation = "Jobless claims are within typical range."
            else:
                # Generic explanation
                if direction == "up":
                    explanation = f"{comp_label} is elevated."
                elif direction == "down":
                    explanation = f"{comp_label} is low."
                else:
                    explanation = f"{comp_label} is within typical range."

            component_explanations.append(
                {
                    "id": comp_id,
                    "label": comp_label,
                    "direction": direction,
                    "importance": importance,
                    "explanation": explanation,
                }
            )

    return {
        "level": level,
        "reason": reason,
        "components": component_explanations,
    }


def _explain_environmental_stress(
    value: float,
    components: Optional[List[Dict]] = None,
) -> Dict:
    """
    Generate explanation for environmental stress sub-index.

    Args:
        value: Environmental stress value (0.0-1.0)
        components: List of component dictionaries

    Returns:
        Dictionary with level, reason, and components
    """
    level = _classify_level(value)

    # Check for earthquake component
    has_earthquake = False
    earthquake_value = 0.0

    if components:
        for comp in components:
            comp_id = comp.get("id", "")
            if comp_id == "earthquake_intensity":
                has_earthquake = True
                earthquake_value = comp.get("value", 0.0)
            elif comp_id == "weather_discomfort":
                _ = comp.get(
                    "value", 0.5
                )  # Weather value tracked but not used in current logic

    # Build reason
    if has_earthquake:
        if level == "high":
            if earthquake_value > 0.5:
                reason = (
                    "Environmental stress is elevated due to both weather "
                    "conditions and earthquake activity."
                )
            else:
                reason = (
                    "Environmental stress is elevated primarily due to "
                    "weather conditions."
                )
        elif level == "moderate":
            reason = (
                "Environmental stress is moderate, with weather and "
                "earthquake activity within typical ranges."
            )
        else:
            reason = (
                "Environmental stress is low; weather is mild and "
                "earthquake activity is minimal."
            )
    else:
        if level == "high":
            reason = "Environmental stress is elevated due to weather conditions."
        elif level == "moderate":
            reason = (
                "Environmental stress is moderate, with weather conditions "
                "within typical range."
            )
        else:
            reason = "Environmental stress is low; weather conditions are mild."

    # Build component explanations
    component_explanations = []
    if components:
        for comp in components:
            comp_id = comp.get("id", "")
            comp_label = comp.get("label", comp_id.replace("_", " ").title())
            comp_value = comp.get("value", 0.5)
            comp_weight = comp.get("weight", 0.0)

            direction = _get_direction(comp_value)
            importance = _get_importance(comp_weight, comp_value)

            if comp_id == "weather_discomfort":
                if direction == "up":
                    explanation = (
                        "Temperature, precipitation, or wind conditions are "
                        "causing elevated discomfort."
                    )
                elif direction == "down":
                    explanation = "Weather conditions are mild and comfortable."
                else:
                    explanation = (
                        "Weather conditions are within typical seasonal range."
                    )
            elif comp_id == "earthquake_intensity":
                if direction == "up":
                    explanation = (
                        "USGS reports significant earthquake activity in the "
                        "region recently."
                    )
                elif direction == "down":
                    explanation = (
                        "USGS reports no significant earthquakes in the region "
                        "recently."
                    )
                else:
                    explanation = "Earthquake activity is within typical range."
            else:
                if direction == "up":
                    explanation = f"{comp_label} is elevated."
                elif direction == "down":
                    explanation = f"{comp_label} is low."
                else:
                    explanation = f"{comp_label} is within typical range."

            component_explanations.append(
                {
                    "id": comp_id,
                    "label": comp_label,
                    "direction": direction,
                    "importance": importance,
                    "explanation": explanation,
                }
            )

    return {
        "level": level,
        "reason": reason,
        "components": component_explanations,
    }


def _explain_mobility_activity(
    value: float,
    components: Optional[List[Dict]] = None,
) -> Dict:
    """
    Generate explanation for mobility activity sub-index.

    Args:
        value: Mobility activity value (0.0-1.0)
        components: List of component dictionaries

    Returns:
        Dictionary with level, reason, and components
    """
    level = _classify_level(value)

    # Note: Higher mobility = lower disruption (inverse relationship in behavior index)
    if level == "high":
        reason = "Mobility activity is high, indicating normal movement patterns."
    elif level == "moderate":
        reason = (
            "Mobility activity is moderate, with some reduction in movement patterns."
        )
    else:
        reason = (
            "Mobility activity is low, indicating reduced movement and "
            "potential disruption."
        )

    component_explanations = []
    if components:
        for comp in components:
            comp_id = comp.get("id", "")
            comp_label = comp.get("label", comp_id.replace("_", " ").title())
            comp_value = comp.get("value", 0.5)
            comp_weight = comp.get("weight", 0.0)

            direction = _get_direction(comp_value)
            importance = _get_importance(comp_weight, comp_value)

            if comp_id == "mobility_index":
                if direction == "up":
                    explanation = (
                        "Mobility patterns show increased activity compared to "
                        "baseline."
                    )
                elif direction == "down":
                    explanation = (
                        "Mobility patterns show reduced activity compared to baseline."
                    )
                else:
                    explanation = "Mobility patterns are near baseline levels."
            else:
                if direction == "up":
                    explanation = f"{comp_label} shows increased activity."
                elif direction == "down":
                    explanation = f"{comp_label} shows reduced activity."
                else:
                    explanation = f"{comp_label} is near baseline levels."

            component_explanations.append(
                {
                    "id": comp_id,
                    "label": comp_label,
                    "direction": direction,
                    "importance": importance,
                    "explanation": explanation,
                }
            )

    return {
        "level": level,
        "reason": reason,
        "components": component_explanations,
    }


def _explain_digital_attention(
    value: float,
    components: Optional[List[Dict]] = None,
) -> Dict:
    """
    Generate explanation for digital attention sub-index.

    Args:
        value: Digital attention value (0.0-1.0)
        components: List of component dictionaries

    Returns:
        Dictionary with level, reason, and components
    """
    level = _classify_level(value)

    # Check for GDELT component
    has_gdelt = False
    gdelt_value = 0.0

    if components:
        for comp in components:
            comp_id = comp.get("id", "")
            if comp_id == "gdelt_tone" or "gdelt" in comp_id.lower():
                has_gdelt = True
                gdelt_value = comp.get("value", 0.0)

    # Build reason
    if has_gdelt:
        if level == "high":
            if gdelt_value > 0.5:
                reason = (
                    "Digital attention is elevated, with recent global news "
                    "events suggesting increased information-seeking behavior."
                )
            else:
                reason = (
                    "Digital attention is elevated, with increased search "
                    "interest and information-seeking behavior."
                )
        elif level == "moderate":
            reason = (
                "Digital attention is moderate, with normal levels of search "
                "interest and media coverage."
            )
        else:
            reason = (
                "Digital attention is low, with minimal search interest and "
                "media coverage."
            )
    else:
        if level == "high":
            reason = (
                "Digital attention is elevated, indicating increased "
                "information-seeking behavior."
            )
        elif level == "moderate":
            reason = (
                "Digital attention is moderate, with normal levels of search interest."
            )
        else:
            reason = "Digital attention is low, with minimal search interest."

    # Build component explanations
    component_explanations = []
    if components:
        for comp in components:
            comp_id = comp.get("id", "")
            comp_label = comp.get("label", comp_id.replace("_", " ").title())
            comp_value = comp.get("value", 0.5)
            comp_weight = comp.get("weight", 0.0)

            direction = _get_direction(comp_value)
            importance = _get_importance(comp_weight, comp_value)

            if comp_id == "gdelt_tone" or "gdelt" in comp_id.lower():
                if direction == "up":
                    explanation = (
                        "Recent global news events suggest elevated digital "
                        "attention and crisis awareness."
                    )
                elif direction == "down":
                    explanation = (
                        "Global news coverage suggests low digital attention "
                        "and minimal crisis awareness."
                    )
                else:
                    explanation = (
                        "Global news coverage suggests moderate digital "
                        "attention levels."
                    )
            elif comp_id == "search_interest":
                if direction == "up":
                    explanation = (
                        "Search interest is elevated, indicating increased "
                        "information-seeking behavior."
                    )
                elif direction == "down":
                    explanation = (
                        "Search interest is low, indicating minimal "
                        "information-seeking behavior."
                    )
                else:
                    explanation = "Search interest is within typical range."
            else:
                if direction == "up":
                    explanation = f"{comp_label} is elevated."
                elif direction == "down":
                    explanation = f"{comp_label} is low."
                else:
                    explanation = f"{comp_label} is within typical range."

            component_explanations.append(
                {
                    "id": comp_id,
                    "label": comp_label,
                    "direction": direction,
                    "importance": importance,
                    "explanation": explanation,
                }
            )

    return {
        "level": level,
        "reason": reason,
        "components": component_explanations,
    }


def _explain_public_health_stress(
    value: float,
    components: Optional[List[Dict]] = None,
) -> Dict:
    """
    Generate explanation for public health stress sub-index.

    Args:
        value: Public health stress value (0.0-1.0)
        components: List of component dictionaries

    Returns:
        Dictionary with level, reason, and components
    """
    level = _classify_level(value)

    # Check for OWID component
    has_owid = False
    owid_value = 0.0

    if components:
        for comp in components:
            comp_id = comp.get("id", "")
            if "owid" in comp_id.lower():
                has_owid = True
                owid_value = comp.get("value", 0.0)

    # Build reason
    if has_owid:
        if level == "high":
            if owid_value > 0.5:
                reason = (
                    "Public health stress is elevated, with OWID data showing "
                    "increased health burden and excess mortality."
                )
            else:
                reason = (
                    "Public health stress is elevated, with health indicators "
                    "showing increased burden."
                )
        elif level == "moderate":
            reason = (
                "Public health stress is moderate, with health indicators "
                "within typical range."
            )
        else:
            reason = (
                "Public health stress is low, with health indicators showing "
                "minimal burden."
            )
    else:
        if level == "high":
            reason = (
                "Public health stress is elevated, with health indicators "
                "showing increased burden."
            )
        elif level == "moderate":
            reason = (
                "Public health stress is moderate, with health indicators "
                "within typical range."
            )
        else:
            reason = (
                "Public health stress is low, with health indicators showing "
                "minimal burden."
            )

    # Build component explanations
    component_explanations = []
    if components:
        for comp in components:
            comp_id = comp.get("id", "")
            comp_label = comp.get("label", comp_id.replace("_", " ").title())
            comp_value = comp.get("value", 0.5)
            comp_weight = comp.get("weight", 0.0)

            direction = _get_direction(comp_value)
            importance = _get_importance(comp_weight, comp_value)

            if "owid" in comp_id.lower():
                if direction == "up":
                    explanation = (
                        "OWID health data shows elevated excess mortality or "
                        "health burden."
                    )
                elif direction == "down":
                    explanation = (
                        "OWID health data shows low excess mortality and "
                        "minimal health burden."
                    )
                else:
                    explanation = (
                        "OWID health data shows health indicators within typical range."
                    )
            elif comp_id == "health_risk_index":
                if direction == "up":
                    explanation = "Health risk indicators show elevated burden."
                elif direction == "down":
                    explanation = "Health risk indicators show low burden."
                else:
                    explanation = "Health risk indicators are within typical range."
            else:
                if direction == "up":
                    explanation = f"{comp_label} is elevated."
                elif direction == "down":
                    explanation = f"{comp_label} is low."
                else:
                    explanation = f"{comp_label} is within typical range."

            component_explanations.append(
                {
                    "id": comp_id,
                    "label": comp_label,
                    "direction": direction,
                    "importance": importance,
                    "explanation": explanation,
                }
            )

    return {
        "level": level,
        "reason": reason,
        "components": component_explanations,
    }


def generate_explanation(
    behavior_index: float,
    sub_indices: Dict[str, float],
    subindex_details: Optional[Dict[str, Dict]] = None,
    region_name: Optional[str] = None,
) -> Dict:
    """
    Generate a comprehensive explanation for a Behavior Index forecast.

    Args:
        behavior_index: Overall behavior index value (0.0-1.0)
        sub_indices: Dictionary mapping sub-index names to values
        subindex_details: Optional dictionary with component-level details
        region_name: Optional region name for context

    Returns:
        Dictionary with summary, subindices explanations, and component details
    """
    # Classify overall behavior index
    overall_level = _classify_level(behavior_index)

    # Generate high-level summary
    if overall_level == "high":
        summary = (
            "Behavior Index indicates high disruption, with multiple stress "
            "factors elevated."
        )
    elif overall_level == "moderate":
        summary = (
            "Behavior Index indicates moderate disruption, with some stress "
            "factors present."
        )
    else:
        summary = (
            "Behavior Index indicates low disruption, with most indicators "
            "showing stability."
        )

    # Add region context if available
    if region_name:
        summary = f"For {region_name}: {summary.lower()}"

    # Generate sub-index explanations
    subindex_explanations = {}

    # Economic stress
    economic_components = None
    if subindex_details and "economic_stress" in subindex_details:
        economic_components = subindex_details["economic_stress"].get("components", [])
    subindex_explanations["economic_stress"] = _explain_economic_stress(
        sub_indices.get("economic_stress", 0.5),
        economic_components,
    )

    # Environmental stress
    environmental_components = None
    if subindex_details and "environmental_stress" in subindex_details:
        environmental_components = subindex_details["environmental_stress"].get(
            "components", []
        )
    subindex_explanations["environmental_stress"] = _explain_environmental_stress(
        sub_indices.get("environmental_stress", 0.5),
        environmental_components,
    )

    # Mobility activity
    mobility_components = None
    if subindex_details and "mobility_activity" in subindex_details:
        mobility_components = subindex_details["mobility_activity"].get(
            "components", []
        )
    subindex_explanations["mobility_activity"] = _explain_mobility_activity(
        sub_indices.get("mobility_activity", 0.5),
        mobility_components,
    )

    # Digital attention
    digital_components = None
    if subindex_details and "digital_attention" in subindex_details:
        digital_components = subindex_details["digital_attention"].get("components", [])
    subindex_explanations["digital_attention"] = _explain_digital_attention(
        sub_indices.get("digital_attention", 0.5),
        digital_components,
    )

    # Public health stress
    health_components = None
    if subindex_details and "public_health_stress" in subindex_details:
        health_components = subindex_details["public_health_stress"].get(
            "components", []
        )
    subindex_explanations["public_health_stress"] = _explain_public_health_stress(
        sub_indices.get("public_health_stress", 0.5),
        health_components,
    )

    return {
        "summary": summary,
        "subindices": subindex_explanations,
    }
