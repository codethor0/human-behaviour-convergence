# SPDX-License-Identifier: PROPRIETARY
"""Forecasting endpoints for behavioral prediction."""
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.regions import get_all_regions
from app.services.ingestion.source_registry import get_all_sources, get_source_statuses

router = APIRouter(prefix="/api/forecasting", tags=["forecasting"])


class DataSourceInfo(BaseModel):
    """Information about an available data source."""

    name: str
    description: str
    status: str
    available: bool
    parameters: Dict[str, str]


class ModelInfo(BaseModel):
    """Information about an available forecasting model."""

    name: str
    description: str
    type: str
    parameters: Dict[str, str]
    default_parameters: Dict[str, Any]


class RegionInfo(BaseModel):
    """Information about an available region."""

    id: str
    name: str
    country: str
    region_type: str
    latitude: float
    longitude: float
    region_group: Optional[str] = None


@router.get("/data-sources", response_model=List[DataSourceInfo])
def get_data_sources() -> List[DataSourceInfo]:
    """
    List all available public data sources for forecasting.

    Generated from single source of truth registry.

    NOTE: This endpoint is fault-tolerant - if source registry fails,
    returns empty list rather than blocking the region selector.

    Returns:
        List of data source information including name, description, status,
        and parameters
    """
    try:
        sources = get_all_sources()
        statuses = get_source_statuses()

        result = []
        for source_id, source_def in sorted(sources.items()):
            status_info = statuses.get(
                source_id, {"status": "unknown", "ok": False, "error_type": "unknown"}
            )

            # Map registry status to DataSourceInfo format
            status = status_info.get("status", "unknown")
            available = status_info.get("ok", False)

            parameters = {
                "type": "time_series",
                "frequency": "daily",
                "refresh_rate": "60 minutes",
            }

            if source_def.required_env_vars:
                parameters["requires"] = ", ".join(source_def.required_env_vars)

            if status_info.get("error_type") == "missing_key":
                parameters["required_env_vars"] = ", ".join(
                    source_def.required_env_vars
                )

            result.append(
                DataSourceInfo(
                    name=source_id,
                    description=source_def.description,
                    status=status,
                    available=available,
                    parameters=parameters,
                )
            )

        return result
    except Exception as e:
        # Fail gracefully - don't block region selector if data sources fail
        import structlog

        logger = structlog.get_logger("routers.forecasting")
        logger.warning(
            "Failed to fetch data sources, returning empty list", error=str(e)
        )
        return []  # Return empty list instead of blocking


@router.get("/regions", response_model=List[RegionInfo])
def get_regions() -> List[RegionInfo]:
    """
    List all available regions for forecasting.

    This endpoint MUST always return a valid list of regions, even if empty.
    It does not depend on external APIs or data sources, ensuring reliability.

    Returns:
        List of region information including global cities and US states.
    """
    try:
        regions = get_all_regions()
        return [
            RegionInfo(
                id=region.id,
                name=region.name,
                country=region.country,
                region_type=region.region_type,
                latitude=region.latitude,
                longitude=region.longitude,
                region_group=region.region_group,
            )
            for region in regions
        ]
    except Exception as e:
        # Log error but return empty list rather than failing the request
        # This ensures the endpoint is always available
        import structlog

        logger = structlog.get_logger("routers.forecasting")
        logger.error("Failed to get regions list", error=str(e), exc_info=True)
        return []  # Return empty list on error - frontend will use fallback


@router.get("/models", response_model=List[ModelInfo])
def get_models() -> List[ModelInfo]:
    """
    List all available forecasting models.

    Returns:
        List of model information including name, description, type, and parameters
    """
    models = [
        ModelInfo(
            name="exponential_smoothing",
            description=(
                "Exponential smoothing (Holt-Winters) for time series "
                "forecasting with trend and seasonality"
            ),
            type="time_series",
            parameters={
                "trend": "additive or multiplicative",
                "seasonal": "additive or multiplicative",
                "seasonal_periods": "integer",
            },
            default_parameters={
                "trend": "add",
                "seasonal": "add",
                "seasonal_periods": 7,
            },
        ),
        ModelInfo(
            name="moving_average",
            description=(
                "Simple moving average with trend extension "
                "(fallback when advanced models unavailable)"
            ),
            type="time_series",
            parameters={
                "window_size": "integer (default: 7)",
                "trend": "linear extrapolation",
            },
            default_parameters={
                "window_size": 7,
            },
        ),
    ]

    return models


@router.get("/status")
def get_forecasting_status() -> Dict[str, Any]:
    """
    Get status of forecasting system components.

    Returns:
        Dictionary with status of data sources, models, and overall system health
    """
    return {
        "system": "operational",
        "data_sources": {
            "economic_indicators": "active",
            "weather_patterns": "active",
            "search_trends": (
                "configured"
                if os.getenv("SEARCH_TRENDS_API_ENDPOINT")
                else "not_configured"
            ),
            "public_health": (
                "configured"
                if os.getenv("PUBLIC_HEALTH_API_ENDPOINT")
                else "not_configured"
            ),
            "mobility_patterns": (
                "configured" if os.getenv("MOBILITY_API_ENDPOINT") else "not_configured"
            ),
        },
        "models": {
            "exponential_smoothing": "available",
            "moving_average": "available",
        },
        "cache_status": "healthy",
    }


class HistoricalForecastItem(BaseModel):
    """Historical forecast entry."""

    forecast_id: str
    region_name: str
    latitude: float
    longitude: float
    forecast_date: str
    forecast_horizon: int
    model_type: str
    sources: List[str]
    accuracy_score: Optional[float] = None


@router.get("/history", response_model=List[HistoricalForecastItem])
def get_forecast_history(
    region_name: Optional[str] = Query(
        None, description="Filter by region name (substring match)"
    ),
    date_from: Optional[str] = Query(
        None, description="Filter by minimum timestamp (ISO format)"
    ),
    date_to: Optional[str] = Query(
        None, description="Filter by maximum timestamp (ISO format)"
    ),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    sort_order: str = Query(
        "DESC", description="Sort order: ASC (oldest first) or DESC (newest first)"
    ),
) -> List[HistoricalForecastItem]:
    """
    Retrieve historical forecasts and their performance metrics.

    Args:
        region_name: Optional filter by region name (substring match)
        date_from: Optional filter by minimum timestamp (ISO format)
        date_to: Optional filter by maximum timestamp (ISO format)
        limit: Maximum number of historical forecasts to return
            (default: 100, max: 1000)
        sort_order: Sort order, either "ASC" (oldest first) or "DESC" (newest first)

    Returns:
        List of historical forecast entries with metadata and accuracy scores

    Note:
        Forecasts are stored in SQLite database. Returns empty list if database
        is not available or contains no forecasts.
    """
    try:
        from app.storage import ForecastDB

        db = ForecastDB()
        forecasts = db.get_forecasts(
            region_name=region_name,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            sort_order=sort_order.upper(),
        )

        result = []
        for f in forecasts:
            forecast_id = f.get("id")
            accuracy_score = None

            # Compute accuracy_score from metrics table if available
            if forecast_id is not None:
                try:
                    metrics = db.get_metrics(forecast_id)
                    # Use RMSE as primary accuracy metric, fallback to MAE
                    if "rmse" in metrics:
                        accuracy_score = metrics["rmse"]
                    elif "mae" in metrics:
                        accuracy_score = metrics["mae"]
                    # If neither available, accuracy_score remains None
                except Exception:
                    # If metrics retrieval fails, accuracy_score remains None
                    pass

            result.append(
                HistoricalForecastItem(
                    forecast_id=str(forecast_id) if forecast_id is not None else "",
                    region_name=f.get("region_name", ""),
                    latitude=f.get("latitude", 0.0),
                    longitude=f.get("longitude", 0.0),
                    forecast_date=f.get("timestamp", ""),
                    forecast_horizon=f.get("metadata", {}).get("forecast_horizon", 7),
                    model_type=f.get("model_name", "Unknown"),
                    sources=f.get("metadata", {}).get("sources", []),
                    accuracy_score=accuracy_score,
                )
            )

        return result
    except Exception:
        # Database is optional, return empty list on error
        return []
