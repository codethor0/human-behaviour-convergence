# SPDX-License-Identifier: PROPRIETARY
"""Cross-Index Convergence Engine (CICE).

Analyzes interactions between behavioral indices to detect convergence patterns.
"""
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger("convergence.engine")


class ConvergenceEngine:
    """Analyzes cross-index convergence patterns."""

    def __init__(self, convergence_threshold: float = 0.6):
        """
        Initialize convergence engine.

        Args:
            convergence_threshold: Minimum correlation for convergence (default: 0.6)
        """
        self.convergence_threshold = convergence_threshold

    def analyze_convergence(
        self,
        history_df: pd.DataFrame,
        index_columns: Optional[List[str]] = None,
    ) -> Dict:
        """
        Analyze convergence between indices.

        Args:
            history_df: DataFrame with timestamp and index columns
            index_columns: List of index column names to analyze

        Returns:
            Dictionary with convergence analysis results
        """
        if history_df.empty or len(history_df) == 0:
            return self._empty_convergence()

        if index_columns is None:
            index_columns = [
                "economic_stress",
                "environmental_stress",
                "mobility_activity",
                "digital_attention",
                "public_health_stress",
                "political_stress",
                "crime_stress",
                "misinformation_stress",
                "social_cohesion_stress",
            ]

        # Filter to available columns and ensure numeric
        available_columns = []
        for col in index_columns:
            if col in history_df.columns:
                try:
                    # Ensure column is numeric
                    pd.to_numeric(history_df[col], errors="coerce")
                    available_columns.append(col)
                except Exception:
                    continue

        if len(available_columns) < 2:
            return self._empty_convergence()

        # Calculate correlations with error handling
        try:
            correlation_matrix = self._calculate_correlation_matrix(
                history_df[available_columns]
            )
        except Exception as e:
            logger.warning("Failed to calculate correlation matrix", error=str(e))
            return self._empty_convergence()

        # Detect reinforcing signals (positive correlations)
        reinforcing_signals = self._detect_reinforcing_signals(
            correlation_matrix, available_columns
        )

        # Detect conflicting signals (negative correlations)
        conflicting_signals = self._detect_conflicting_signals(
            correlation_matrix, available_columns
        )

        # Calculate overall convergence score
        convergence_score = self._calculate_convergence_score(
            correlation_matrix, available_columns
        )

        # Detect convergence patterns
        patterns = self._detect_convergence_patterns(
            history_df[available_columns], correlation_matrix
        )

        result = {
            "score": float(convergence_score),
            "reinforcing_signals": reinforcing_signals,
            "conflicting_signals": conflicting_signals,
            "patterns": patterns,
            "correlation_matrix": (
                correlation_matrix.to_dict()
                if isinstance(correlation_matrix, pd.DataFrame)
                else correlation_matrix
            ),
        }

        # Add trace for explainability
        try:
            from app.core.trace import create_convergence_trace

            # Extract correlations from matrix for trace
            correlations = []
            for i, col1 in enumerate(available_columns):
                for j, col2 in enumerate(available_columns):
                    if (
                        i < j
                        and col1 in correlation_matrix.index
                        and col2 in correlation_matrix.columns
                    ):
                        corr_value = correlation_matrix.loc[col1, col2]
                        if not pd.isna(corr_value):
                            correlations.append(float(corr_value))

            result["trace"] = create_convergence_trace(
                score=float(convergence_score),
                correlations=correlations,
                indices=available_columns,
                correlation_matrix=result["correlation_matrix"],
            )
        except Exception as e:
            logger.warning("Failed to create convergence trace", error=str(e))
            result["trace"] = {"reconciliation": {"valid": False, "error": str(e)}}

        logger.info(
            "Convergence analysis completed",
            score=convergence_score,
            reinforcing_count=len(reinforcing_signals),
            conflicting_count=len(conflicting_signals),
        )

        return result

    def _calculate_correlation_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix between indices."""
        # Remove any rows with all NaN
        df_clean = df.dropna(how="all")

        if len(df_clean) < 2:
            # Return identity matrix if insufficient data
            return pd.DataFrame(
                np.eye(len(df.columns)),
                index=df.columns,
                columns=df.columns,
            )

        # Calculate Pearson correlation
        corr_matrix = df_clean.corr(method="pearson")

        # Fill NaN with 0 (happens when std is 0)
        corr_matrix = corr_matrix.fillna(0.0)

        # Invariant: Correlation matrix must be symmetric
        # pandas.corr() guarantees symmetry, but verify index/columns match
        if not corr_matrix.index.equals(corr_matrix.columns):
            logger.warning("Correlation matrix index/columns mismatch, reindexing")
            corr_matrix = corr_matrix.reindex(
                index=corr_matrix.columns, columns=corr_matrix.columns, fill_value=0.0
            )
            # Ensure diagonal is 1.0 (self-correlation)
            for col in corr_matrix.columns:
                corr_matrix.loc[col, col] = 1.0

        return corr_matrix

    def _detect_reinforcing_signals(
        self, corr_matrix: pd.DataFrame, columns: List[str]
    ) -> List[Tuple[str, str, float]]:
        """Detect pairs of indices with strong positive correlation."""
        reinforcing = []

        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i >= j:  # Avoid duplicates and self-correlation
                    continue

                if col1 in corr_matrix.index and col2 in corr_matrix.columns:
                    corr_value = corr_matrix.loc[col1, col2]

                    if corr_value >= self.convergence_threshold:
                        reinforcing.append((col1, col2, float(corr_value)))

        # Sort by correlation strength
        reinforcing.sort(key=lambda x: x[2], reverse=True)

        return reinforcing

    def _detect_conflicting_signals(
        self, corr_matrix: pd.DataFrame, columns: List[str]
    ) -> List[Tuple[str, str, float]]:
        """Detect pairs of indices with strong negative correlation."""
        conflicting = []

        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i >= j:
                    continue

                if col1 in corr_matrix.index and col2 in corr_matrix.columns:
                    corr_value = corr_matrix.loc[col1, col2]

                    if corr_value <= -self.convergence_threshold:
                        conflicting.append((col1, col2, float(corr_value)))

        # Sort by absolute correlation strength
        conflicting.sort(key=lambda x: abs(x[2]), reverse=True)

        return conflicting

    def _calculate_convergence_score(
        self, corr_matrix: pd.DataFrame, columns: List[str]
    ) -> float:
        """Calculate overall convergence score (0-100)."""
        if len(columns) < 2:
            return 0.0

        # Get upper triangle of correlation matrix (excluding diagonal)
        correlations = []
        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i < j and col1 in corr_matrix.index and col2 in corr_matrix.columns:
                    corr_value = corr_matrix.loc[col1, col2]
                    if not pd.isna(corr_value):
                        correlations.append(abs(corr_value))

        if not correlations:
            return 0.0

        # Average absolute correlation, scaled to 0-100
        avg_correlation = np.mean(correlations)
        score = avg_correlation * 100.0

        return float(np.clip(score, 0.0, 100.0))

    def _detect_convergence_patterns(
        self, df: pd.DataFrame, corr_matrix: pd.DataFrame
    ) -> List[Dict]:
        """Detect specific convergence patterns."""
        patterns = []

        # Pattern 1: Political + Misinformation + Social Cohesion (unrest risk)
        if all(
            col in df.columns
            for col in [
                "political_stress",
                "misinformation_stress",
                "social_cohesion_stress",
            ]
        ):
            pattern_score = self._calculate_pattern_score(
                df,
                ["political_stress", "misinformation_stress", "social_cohesion_stress"],
            )
            if pattern_score > 0.5:
                patterns.append(
                    {
                        "type": "unrest_risk",
                        "indices": [
                            "political_stress",
                            "misinformation_stress",
                            "social_cohesion_stress",
                        ],
                        "score": float(pattern_score),
                        "description": (
                            "Political stress, misinformation, and social cohesion "
                            "decline indicate potential unrest risk"
                        ),
                    }
                )

        # Pattern 2: Economic + Public Health (consumer behavior shift)
        if all(
            col in df.columns for col in ["economic_stress", "public_health_stress"]
        ):
            pattern_score = self._calculate_pattern_score(
                df, ["economic_stress", "public_health_stress"]
            )
            if pattern_score > 0.5:
                patterns.append(
                    {
                        "type": "consumer_shift",
                        "indices": ["economic_stress", "public_health_stress"],
                        "score": float(pattern_score),
                        "description": (
                            "Economic and public health stress indicate potential "
                            "consumer behavior shift"
                        ),
                    }
                )

        # Pattern 3: Crime + Social Cohesion (local instability)
        if all(col in df.columns for col in ["crime_stress", "social_cohesion_stress"]):
            pattern_score = self._calculate_pattern_score(
                df, ["crime_stress", "social_cohesion_stress"]
            )
            if pattern_score > 0.5:
                patterns.append(
                    {
                        "type": "local_instability",
                        "indices": ["crime_stress", "social_cohesion_stress"],
                        "score": float(pattern_score),
                        "description": (
                            "Crime spike and social cohesion decline indicate "
                            "local instability"
                        ),
                    }
                )

        return patterns

    def _calculate_pattern_score(self, df: pd.DataFrame, columns: List[str]) -> float:
        """Calculate pattern strength score."""
        if len(columns) < 2:
            return 0.0

        # Get latest values
        latest_values = df[columns].iloc[-1] if len(df) > 0 else pd.Series()

        if latest_values.empty or latest_values.isna().any():
            return 0.0

        # Calculate average stress level
        avg_stress = latest_values.mean()

        # Calculate trend (increasing = higher score)
        if len(df) >= 7:
            trends = []
            for col in columns:
                recent = df[col].tail(7)
                if len(recent) > 1:
                    trend = (recent.iloc[-1] - recent.iloc[0]) / len(recent)
                    trends.append(trend)
            avg_trend = np.mean(trends) if trends else 0.0
        else:
            avg_trend = 0.0

        # Combine stress level and trend
        score = (avg_stress * 0.7) + (min(avg_trend, 0.3) * 0.3)

        return float(np.clip(score, 0.0, 1.0))

    def _empty_convergence(self) -> Dict:
        """Return empty convergence result."""
        result = {
            "score": 0.0,
            "reinforcing_signals": [],
            "conflicting_signals": [],
            "patterns": [],
            "correlation_matrix": {},
        }
        # Add minimal trace for empty result
        try:
            from app.core.trace import create_convergence_trace

            result["trace"] = create_convergence_trace(
                score=0.0,
                reinforcing_signals=[],
                conflicting_signals=[],
                patterns=[],
                correlation_matrix={},
            )
        except Exception:
            result["trace"] = {
                "reconciliation": {
                    "valid": True,
                    "sum": 0.0,
                    "output": 0.0,
                    "difference": 0.0,
                }
            }
        return result
