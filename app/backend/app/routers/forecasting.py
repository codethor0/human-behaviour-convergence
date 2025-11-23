# SPDX-License-Identifier: MIT-0
"""Forecasting endpoints for behavioral prediction."""
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.prediction import BehavioralForecaster
from app.services.ingestion import (
    DataHarmonizer,
    EnvironmentalImpactFetcher,
    MarketSentimentFetcher,
    MobilityFetcher,
    PublicHealthFetcher,
    SearchTrendsFetcher,
)

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


@router.get("/data-sources", response_model=List[DataSourceInfo])
def get_data_sources() -> List[DataSourceInfo]:
    """
    List all available public data sources for forecasting.

    Returns:
        List of data source information including name, description, status, and parameters
    """
    return [
        DataSourceInfo(
            name="economic_indicators",
            description="Market sentiment indicators from public financial data (volatility index, market indices)",
            status="active",
            available=True,
            parameters={
                "type": "time_series",
                "frequency": "daily",
                "refresh_rate": "5 minutes",
            },
        ),
        DataSourceInfo(
            name="weather_patterns",
            description="Environmental data including temperature, precipitation, and wind patterns",
            status="active",
            available=True,
            parameters={
                "type": "time_series",
                "frequency": "daily",
                "requires": "latitude, longitude",
                "refresh_rate": "30 minutes",
            },
        ),
        DataSourceInfo(
            name="search_trends",
            description="Digital attention signals from search interest trends (requires API configuration)",
            status="active",
            available=False,
            parameters={
                "type": "time_series",
                "frequency": "daily",
                "requires": "query parameter, API credentials",
                "refresh_rate": "60 minutes",
            },
        ),
        DataSourceInfo(
            name="public_health",
            description="Public health indicators from aggregated health statistics (requires API configuration)",
            status="active",
            available=False,
            parameters={
                "type": "time_series",
                "frequency": "daily",
                "requires": "region_code (optional), API credentials",
                "refresh_rate": "24 hours",
            },
        ),
        DataSourceInfo(
            name="mobility_patterns",
            description="Mobility and activity pattern data from public APIs (requires API configuration)",
            status="active",
            available=False,
            parameters={
                "type": "time_series",
                "frequency": "daily",
                "requires": "region_code or coordinates, API credentials",
                "refresh_rate": "60 minutes",
            },
        ),
    ]


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
            description="Exponential smoothing (Holt-Winters) for time series forecasting with trend and seasonality",
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
            description="Simple moving average with trend extension (fallback when advanced models unavailable)",
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
    accuracy_score: float = None


@router.get("/history", response_model=List[HistoricalForecastItem])
def get_forecast_history(
    region_name: Optional[str] = Query(None, description="Filter by region name"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
) -> List[HistoricalForecastItem]:
    """
    Retrieve historical forecasts and their performance metrics.

    Args:
        region_name: Optional filter by region name
        limit: Maximum number of historical forecasts to return (default: 100, max: 1000)

    Returns:
        List of historical forecast entries with metadata and accuracy scores

    Note:
        This endpoint currently returns an empty list as historical tracking
        is not yet implemented. Future versions will store forecasts in a database.
    """
    return []
