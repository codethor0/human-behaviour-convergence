# SPDX-License-Identifier: MIT-0
"""Forecasting endpoints for behavioral prediction."""
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.prediction import BehavioralForecaster
from app.services.ingestion import DataHarmonizer, EnvironmentalImpactFetcher, MarketSentimentFetcher

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
    default_parameters: Dict[str, any]


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
def get_forecasting_status() -> Dict[str, any]:
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
        },
        "models": {
            "exponential_smoothing": "available",
            "moving_average": "available",
        },
        "cache_status": "healthy",
    }

