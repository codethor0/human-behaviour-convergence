# SPDX-License-Identifier: PROPRIETARY
"""Model evaluation and backtesting for forecasting models."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger("core.model_evaluation")


def compute_mae(actual: pd.Series, predicted: pd.Series) -> float:
    """Compute Mean Absolute Error."""
    if len(actual) == 0 or len(predicted) == 0:
        return float("nan")
    aligned = pd.DataFrame({"actual": actual, "predicted": predicted}).dropna()
    if len(aligned) == 0:
        return float("nan")
    return float(np.mean(np.abs(aligned["actual"] - aligned["predicted"])))


def compute_rmse(actual: pd.Series, predicted: pd.Series) -> float:
    """Compute Root Mean Squared Error."""
    if len(actual) == 0 or len(predicted) == 0:
        return float("nan")
    aligned = pd.DataFrame({"actual": actual, "predicted": predicted}).dropna()
    if len(aligned) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((aligned["actual"] - aligned["predicted"]) ** 2)))


def compute_mape(actual: pd.Series, predicted: pd.Series) -> float:
    """Compute Mean Absolute Percentage Error."""
    if len(actual) == 0 or len(predicted) == 0:
        return float("nan")
    aligned = pd.DataFrame({"actual": actual, "predicted": predicted}).dropna()
    if len(aligned) == 0:
        return float("nan")
    # Avoid division by zero
    mask = aligned["actual"] != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((aligned.loc[mask, "actual"] - aligned.loc[mask, "predicted"]) / aligned.loc[mask, "actual"])) * 100)


def compute_smape(actual: pd.Series, predicted: pd.Series) -> float:
    """Compute Symmetric Mean Absolute Percentage Error."""
    if len(actual) == 0 or len(predicted) == 0:
        return float("nan")
    aligned = pd.DataFrame({"actual": actual, "predicted": predicted}).dropna()
    if len(aligned) == 0:
        return float("nan")
    denominator = (np.abs(aligned["actual"]) + np.abs(aligned["predicted"])) / 2
    mask = denominator != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(aligned.loc[mask, "actual"] - aligned.loc[mask, "predicted"]) / denominator.loc[mask]) * 100)


def compute_interval_coverage(
    actual: pd.Series, lower: pd.Series, upper: pd.Series
) -> Tuple[float, float]:
    """
    Compute prediction interval coverage and average width.

    Returns:
        (coverage_percentage, average_width)
    """
    if len(actual) == 0 or len(lower) == 0 or len(upper) == 0:
        return float("nan"), float("nan")
    
    aligned = pd.DataFrame({
        "actual": actual,
        "lower": lower,
        "upper": upper
    }).dropna()
    
    if len(aligned) == 0:
        return float("nan"), float("nan")
    
    # Coverage: percentage of actuals within interval
    in_interval = (aligned["actual"] >= aligned["lower"]) & (aligned["actual"] <= aligned["upper"])
    coverage = float(in_interval.sum() / len(aligned) * 100)
    
    # Average width
    width = aligned["upper"] - aligned["lower"]
    avg_width = float(width.mean())
    
    return coverage, avg_width


class ModelEvaluator:
    """Evaluates forecasting model performance using backtesting."""
    
    def __init__(self, window_days: int = 30):
        """
        Initialize model evaluator.
        
        Args:
            window_days: Number of days to use for rolling-origin evaluation
        """
        self.window_days = window_days
    
    def evaluate(
        self,
        history: pd.DataFrame,
        forecast: pd.DataFrame,
        model_name: str,
        region_id: str,
    ) -> Dict[str, float]:
        """
        Evaluate forecast against actual values.
        
        Args:
            history: Historical data with 'timestamp' and 'behavior_index' columns
            forecast: Forecast data with 'timestamp', 'prediction', 'lower_bound', 'upper_bound'
            model_name: Name of the model
            region_id: Region identifier
        
        Returns:
            Dictionary with evaluation metrics
        """
        if history.empty or forecast.empty:
            logger.warning("Empty history or forecast", model=model_name, region=region_id)
            return {
                "mae": float("nan"),
                "rmse": float("nan"),
                "mape": float("nan"),
                "smape": float("nan"),
                "interval_coverage": float("nan"),
                "average_interval_width": float("nan"),
            }
        
        # Align timestamps
        history_ts = pd.to_datetime(history["timestamp"])
        forecast_ts = pd.to_datetime(forecast["timestamp"])
        
        # Find overlapping timestamps (for backtesting)
        overlap = set(history_ts) & set(forecast_ts)
        if not overlap:
            logger.warning("No overlapping timestamps for evaluation", model=model_name, region=region_id)
            return {
                "mae": float("nan"),
                "rmse": float("nan"),
                "mape": float("nan"),
                "smape": float("nan"),
                "interval_coverage": float("nan"),
                "average_interval_width": float("nan"),
            }
        
        # Extract aligned series
        history_aligned = history.set_index("timestamp").loc[list(overlap), "behavior_index"]
        forecast_aligned = forecast.set_index("timestamp").loc[list(overlap), "prediction"]
        lower_aligned = forecast.set_index("timestamp").loc[list(overlap), "lower_bound"]
        upper_aligned = forecast.set_index("timestamp").loc[list(overlap), "upper_bound"]
        
        # Compute metrics
        mae = compute_mae(history_aligned, forecast_aligned)
        rmse = compute_rmse(history_aligned, forecast_aligned)
        mape = compute_mape(history_aligned, forecast_aligned)
        smape = compute_smape(history_aligned, forecast_aligned)
        coverage, avg_width = compute_interval_coverage(history_aligned, lower_aligned, upper_aligned)
        
        return {
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "smape": smape,
            "interval_coverage": coverage,
            "average_interval_width": avg_width,
        }
    
    def rolling_origin_evaluation(
        self,
        full_history: pd.DataFrame,
        model_forecast_fn,
        model_name: str,
        region_id: str,
        forecast_horizon: int = 7,
    ) -> List[Dict[str, float]]:
        """
        Perform rolling-origin evaluation.
        
        Args:
            full_history: Complete historical data
            model_forecast_fn: Function that takes (history, horizon) and returns forecast DataFrame
            model_name: Name of the model
            region_id: Region identifier
            forecast_horizon: Forecast horizon in days
        
        Returns:
            List of evaluation results (one per rolling window)
        """
        if full_history.empty:
            return []
        
        results = []
        full_history["timestamp"] = pd.to_datetime(full_history["timestamp"])
        full_history = full_history.sort_values("timestamp")
        
        # Rolling windows
        end_date = full_history["timestamp"].max()
        start_date = end_date - timedelta(days=self.window_days)
        
        window_history = full_history[
            (full_history["timestamp"] >= start_date) & (full_history["timestamp"] <= end_date)
        ]
        
        if len(window_history) < forecast_horizon:
            logger.warning("Insufficient history for rolling evaluation", model=model_name, region=region_id)
            return []
        
        try:
            forecast = model_forecast_fn(window_history, forecast_horizon)
            eval_result = self.evaluate(window_history, forecast, model_name, region_id)
            eval_result["model"] = model_name
            eval_result["region"] = region_id
            eval_result["evaluation_date"] = datetime.now().isoformat()
            results.append(eval_result)
        except Exception as e:
            logger.error("Rolling evaluation failed", model=model_name, region=region_id, error=str(e))
        
        return results
