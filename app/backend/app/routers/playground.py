# SPDX-License-Identifier: PROPRIETARY
"""Playground endpoints for interactive scenario exploration."""
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.playground import compare_regions

router = APIRouter(prefix="/api/playground", tags=["playground"])


class ScenarioConfig(BaseModel):
    """Optional scenario configuration for what-if adjustments."""

    economic_stress_offset: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Offset to apply to economic_stress sub-index (-1.0 to 1.0)",
    )
    environmental_stress_offset: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Offset to apply to environmental_stress sub-index (-1.0 to 1.0)",
    )
    mobility_activity_offset: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Offset to apply to mobility_activity sub-index (-1.0 to 1.0)",
    )
    digital_attention_offset: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Offset to apply to digital_attention sub-index (-1.0 to 1.0)",
    )
    public_health_stress_offset: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="Offset to apply to public_health_stress sub-index (-1.0 to 1.0)",
    )


class PlaygroundCompareRequest(BaseModel):
    """Request for multi-region forecast comparison."""

    regions: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of region IDs to compare (e.g., ['us_dc', 'us_mn', 'city_nyc'])",
    )
    historical_days: int = Field(
        default=30,
        ge=7,
        le=365,
        description="Number of historical days to use for forecasting",
    )
    forecast_horizon_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Number of days to forecast ahead",
    )
    include_explanations: bool = Field(
        default=True,
        description="Whether to include explanation objects in responses",
    )
    scenario: Optional[ScenarioConfig] = Field(
        default=None,
        description="Optional scenario configuration for what-if adjustments (experimental)",
    )


class PlaygroundCompareResponse(BaseModel):
    """Response from playground comparison endpoint."""

    config: Dict
    results: List[Dict]
    errors: List[Dict] = Field(default_factory=list)


@router.post("/compare", response_model=PlaygroundCompareResponse, tags=["playground"])
def compare_forecasts(payload: PlaygroundCompareRequest) -> PlaygroundCompareResponse:
    """
    Compare behavioral forecasts across multiple regions with optional scenario adjustments.

    This is an experimental playground endpoint for exploring "what-if" scenarios
    and comparing forecasts across different regions. All scenario adjustments are
    post-processing transformations and do not affect the underlying forecasting model.

    Args:
        payload: PlaygroundCompareRequest with regions, configuration, and optional scenario

    Returns:
        PlaygroundCompareResponse with forecast results for each region

    Example:
        POST /api/playground/compare
        {
            "regions": ["us_dc", "us_mn", "city_nyc"],
            "historical_days": 30,
            "forecast_horizon_days": 7,
            "include_explanations": true,
            "scenario": {
                "digital_attention_offset": 0.1
            }
        }
    """
    # Convert scenario config to dict if provided
    scenario_dict = None
    if payload.scenario:
        scenario_dict = {}
        if payload.scenario.economic_stress_offset is not None:
            scenario_dict["economic_stress_offset"] = (
                payload.scenario.economic_stress_offset
            )
        if payload.scenario.environmental_stress_offset is not None:
            scenario_dict["environmental_stress_offset"] = (
                payload.scenario.environmental_stress_offset
            )
        if payload.scenario.mobility_activity_offset is not None:
            scenario_dict["mobility_activity_offset"] = (
                payload.scenario.mobility_activity_offset
            )
        if payload.scenario.digital_attention_offset is not None:
            scenario_dict["digital_attention_offset"] = (
                payload.scenario.digital_attention_offset
            )
        if payload.scenario.public_health_stress_offset is not None:
            scenario_dict["public_health_stress_offset"] = (
                payload.scenario.public_health_stress_offset
            )

    try:
        result = compare_regions(
            region_ids=payload.regions,
            historical_days=payload.historical_days,
            forecast_horizon_days=payload.forecast_horizon_days,
            include_explanations=payload.include_explanations,
            scenario=scenario_dict if scenario_dict else None,
        )
        return PlaygroundCompareResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate playground comparison: {str(e)}",
        ) from e
