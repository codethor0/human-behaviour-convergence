# SPDX-License-Identifier: PROPRIETARY
"""Model metrics integration for Prometheus."""
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import structlog

from app.core.model_evaluation import ModelEvaluator

logger = structlog.get_logger("core.model_metrics")

# Prometheus client (optional dependency)
try:
    from prometheus_client import Gauge, Counter, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Gauge = Counter = Histogram = None


def emit_model_metrics(
    history: pd.DataFrame,
    forecast: pd.DataFrame,
    model_name: str,
    region_id: str,
    region_name: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> None:
    """
    Emit Prometheus metrics for model performance.

    Args:
        history: Historical data with 'timestamp' and 'behavior_index' columns
        forecast: Forecast data with 'timestamp', 'prediction', 'lower_bound', 'upper_bound'
        model_name: Name of the model used
        region_id: Region identifier
        region_name: Optional region name for metrics labels
        metadata: Optional metadata dictionary
    """
    if not PROMETHEUS_AVAILABLE:
        return

    # Use region_name if provided, otherwise use region_id
    region_label = region_name or region_id

    try:
        # Get or create metrics (they should be defined in main.py)
        # We'll access them via a function that checks if they exist
        _emit_metrics_safe(history, forecast, model_name, region_label, metadata)
    except Exception as e:
        logger.warning(
            "Failed to emit model metrics",
            model=model_name,
            region=region_id,
            error=str(e),
        )


def _emit_metrics_safe(
    history: pd.DataFrame,
    forecast: pd.DataFrame,
    model_name: str,
    region_label: str,
    metadata: Optional[Dict] = None,
) -> None:
    """Safely emit metrics by importing from main module."""
    try:
        from app.backend.app.main import (
            model_mae_gauge,
            model_rmse_gauge,
            model_mape_gauge,
            interval_coverage_gauge,
            backtest_last_run_gauge,
            forecast_outcome_counter,
            model_selected_gauge,
            PROMETHEUS_AVAILABLE as MAIN_PROMETHEUS_AVAILABLE,
        )

        if not MAIN_PROMETHEUS_AVAILABLE:
            return

        # Track model selection
        if model_selected_gauge is not None:
            # Set current model to 1, others to 0 (if we had a way to reset all)
            # For now, just set the current one
            model_selected_gauge.labels(region=region_label, model=model_name).set(1.0)

        # Track forecast outcome
        if forecast_outcome_counter is not None:
            outcome = "success" if not forecast.empty else "empty"
            forecast_outcome_counter.labels(
                region=region_label, model=model_name, outcome=outcome
            ).inc()

        # Evaluate model if we have overlapping data (backtesting)
        if not history.empty and not forecast.empty:
            try:
                evaluator = ModelEvaluator()
                eval_result = evaluator.evaluate(
                    history=history,
                    forecast=forecast,
                    model_name=model_name,
                    region_id=region_label,
                )

                # Emit evaluation metrics
                if model_mae_gauge is not None and not pd.isna(eval_result.get("mae")):
                    model_mae_gauge.labels(region=region_label, model=model_name).set(
                        eval_result["mae"]
                    )

                if model_rmse_gauge is not None and not pd.isna(
                    eval_result.get("rmse")
                ):
                    model_rmse_gauge.labels(region=region_label, model=model_name).set(
                        eval_result["rmse"]
                    )

                if model_mape_gauge is not None and not pd.isna(
                    eval_result.get("mape")
                ):
                    model_mape_gauge.labels(region=region_label, model=model_name).set(
                        eval_result["mape"]
                    )

                if interval_coverage_gauge is not None and not pd.isna(
                    eval_result.get("interval_coverage")
                ):
                    interval_coverage_gauge.labels(
                        region=region_label, model=model_name
                    ).set(eval_result["interval_coverage"])

                # Update backtest timestamp
                if backtest_last_run_gauge is not None:
                    backtest_last_run_gauge.labels(
                        region=region_label, model=model_name
                    ).set(datetime.now().timestamp())

                logger.info(
                    "Emitted model evaluation metrics",
                    model=model_name,
                    region=region_label,
                    mae=eval_result.get("mae"),
                    rmse=eval_result.get("rmse"),
                )
            except Exception as e:
                logger.warning(
                    "Failed to evaluate model for metrics",
                    model=model_name,
                    region=region_label,
                    error=str(e),
                )
    except ImportError:
        # Metrics not available in main module (graceful degradation)
        logger.debug("Model metrics not available in main module")
    except Exception as e:
        logger.warning(
            "Failed to emit model metrics",
            model=model_name,
            region=region_label,
            error=str(e),
        )


def track_forecast_computation(
    model_name: str,
    region_label: str,
    duration_seconds: float,
) -> None:
    """
    Track forecast computation duration by model.

    Args:
        model_name: Name of the model used
        region_label: Region label for metrics
        duration_seconds: Computation duration in seconds
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        from app.backend.app.main import (
            forecast_compute_duration_by_model,
            PROMETHEUS_AVAILABLE as MAIN_PROMETHEUS_AVAILABLE,
        )

        if not MAIN_PROMETHEUS_AVAILABLE:
            return

        if forecast_compute_duration_by_model is not None:
            forecast_compute_duration_by_model.labels(
                region=region_label, model=model_name
            ).observe(duration_seconds)
    except (ImportError, Exception) as e:
        logger.debug("Failed to track forecast computation duration", error=str(e))
