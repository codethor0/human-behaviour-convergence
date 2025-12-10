# SPDX-License-Identifier: PROPRIETARY
"""Correlation & Relationship Analytics Engine.

Computes correlations and relationships between behavioral indices.
"""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import structlog
from scipy import stats

logger = structlog.get_logger("analytics.correlation")


class CorrelationEngine:
    """Analyzes correlations and relationships between indices."""

    def __init__(self):
        """Initialize correlation engine."""
        pass

    def calculate_correlations(
        self,
        history_df: pd.DataFrame,
        index_columns: Optional[List[str]] = None,
        methods: Optional[List[str]] = None,
    ) -> Dict:
        """
        Calculate correlations between indices using multiple methods.

        Args:
            history_df: DataFrame with index columns
            index_columns: List of index column names
            methods: List of correlation methods ('pearson', 'spearman', 'mutual_info')

        Returns:
            Dictionary with correlation matrices and relationships
        """
        if history_df.empty or len(history_df) == 0:
            return self._empty_correlations()

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

        if methods is None:
            methods = ["pearson", "spearman"]

        # Filter to available columns and ensure numeric
        available_columns = []
        for col in index_columns:
            if col in history_df.columns:
                try:
                    pd.to_numeric(history_df[col], errors="coerce")
                    available_columns.append(col)
                except Exception:
                    continue

        if len(available_columns) < 2:
            return self._empty_correlations()

        correlations = {}

        # Calculate Pearson correlation
        if "pearson" in methods:
            pearson_matrix = self._calculate_pearson(history_df[available_columns])
            correlations["pearson"] = pearson_matrix

        # Calculate Spearman correlation
        if "spearman" in methods:
            spearman_matrix = self._calculate_spearman(history_df[available_columns])
            correlations["spearman"] = spearman_matrix

        # Calculate Mutual Information (if scipy available)
        if "mutual_info" in methods:
            try:
                mi_matrix = self._calculate_mutual_info(history_df[available_columns])
                correlations["mutual_info"] = mi_matrix
            except Exception as e:
                logger.warning("Mutual information calculation failed", error=str(e))

        # Extract strongest relationships
        relationships = self._extract_relationships(correlations, available_columns)

        result = {
            "correlations": correlations,
            "relationships": relationships,
            "indices_analyzed": available_columns,
        }

        logger.info(
            "Correlation analysis completed",
            indices=len(available_columns),
            methods=methods,
            relationships_found=len(relationships),
        )

        return result

    def _calculate_pearson(self, df: pd.DataFrame) -> Dict:
        """Calculate Pearson correlation matrix."""
        df_clean = df.dropna()

        if len(df_clean) < 2:
            return {}

        corr_matrix = df_clean.corr(method="pearson")
        corr_matrix = corr_matrix.fillna(0.0)

        # Invariant: Correlation matrix must be symmetric
        # pandas.corr() guarantees symmetry, but we verify and enforce it
        if not corr_matrix.index.equals(corr_matrix.columns):
            logger.warning("Correlation matrix index/columns mismatch, reindexing")
            corr_matrix = corr_matrix.reindex(
                index=corr_matrix.columns, columns=corr_matrix.columns, fill_value=0.0
            )

        # Convert to dictionary format
        result = {}
        for col1 in corr_matrix.index:
            result[col1] = {}
            for col2 in corr_matrix.columns:
                # Ensure symmetry: corr(i,j) == corr(j,i)
                if col1 == col2:
                    result[col1][col2] = 1.0  # Self-correlation is always 1.0
                else:
                    # Use the value from the matrix (pandas guarantees symmetry)
                    result[col1][col2] = float(corr_matrix.loc[col1, col2])
                    # Verify symmetry invariant
                    if col2 in result and col1 in result[col2]:
                        if abs(result[col1][col2] - result[col2][col1]) > 1e-10:
                            logger.warning(
                                "Correlation matrix asymmetry detected",
                                col1=col1,
                                col2=col2,
                                value1=result[col1][col2],
                                value2=result[col2][col1],
                            )
                            # Enforce symmetry by averaging
                            avg_corr = (result[col1][col2] + result[col2][col1]) / 2.0
                            result[col1][col2] = avg_corr
                            result[col2][col1] = avg_corr

        return result

    def _calculate_spearman(self, df: pd.DataFrame) -> Dict:
        """Calculate Spearman correlation matrix."""
        df_clean = df.dropna()

        if len(df_clean) < 2:
            return {}

        corr_matrix = df_clean.corr(method="spearman")
        corr_matrix = corr_matrix.fillna(0.0)

        # Invariant: Correlation matrix must be symmetric
        # pandas.corr() guarantees symmetry, but we verify and enforce it
        if not corr_matrix.index.equals(corr_matrix.columns):
            logger.warning("Correlation matrix index/columns mismatch, reindexing")
            corr_matrix = corr_matrix.reindex(
                index=corr_matrix.columns, columns=corr_matrix.columns, fill_value=0.0
            )

        # Convert to dictionary format
        result = {}
        for col1 in corr_matrix.index:
            result[col1] = {}
            for col2 in corr_matrix.columns:
                # Ensure symmetry: corr(i,j) == corr(j,i)
                if col1 == col2:
                    result[col1][col2] = 1.0  # Self-correlation is always 1.0
                else:
                    # Use the value from the matrix (pandas guarantees symmetry)
                    result[col1][col2] = float(corr_matrix.loc[col1, col2])
                    # Verify symmetry invariant
                    if col2 in result and col1 in result[col2]:
                        if abs(result[col1][col2] - result[col2][col1]) > 1e-10:
                            logger.warning(
                                "Correlation matrix asymmetry detected",
                                col1=col1,
                                col2=col2,
                                value1=result[col1][col2],
                                value2=result[col2][col1],
                            )
                            # Enforce symmetry by averaging
                            avg_corr = (result[col1][col2] + result[col2][col1]) / 2.0
                            result[col1][col2] = avg_corr
                            result[col2][col1] = avg_corr

        return result

    def _calculate_mutual_info(self, df: pd.DataFrame) -> Dict:
        """Calculate Mutual Information matrix."""
        df_clean = df.dropna()

        if len(df_clean) < 2:
            return {}

        # Discretize for mutual information
        df_discrete = df_clean.copy()
        for col in df_discrete.columns:
            # Bin into 10 bins
            df_discrete[col] = pd.cut(
                df_discrete[col], bins=10, labels=False, duplicates="drop"
            )

        result = {}
        for col1 in df_discrete.columns:
            result[col1] = {}
            for col2 in df_discrete.columns:
                if col1 == col2:
                    result[col1][col2] = 1.0
                else:
                    try:
                        mi = stats.mutual_info_regression(
                            df_discrete[[col1]],
                            df_discrete[col2],
                            discrete_features=True,
                        )[0]
                        # Normalize to [0, 1] range (rough approximation)
                        result[col1][col2] = float(np.clip(mi, 0.0, 1.0))
                    except Exception:
                        result[col1][col2] = 0.0

        return result

    def _extract_relationships(
        self, correlations: Dict, columns: List[str]
    ) -> List[Dict]:
        """Extract strongest positive and negative relationships."""
        relationships = []

        # Use Pearson as primary method
        if "pearson" not in correlations:
            return relationships

        pearson = correlations["pearson"]

        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i >= j:  # Avoid duplicates
                    continue

                if col1 in pearson and col2 in pearson[col1]:
                    corr_value = pearson[col1][col2]

                    if abs(corr_value) > 0.3:  # Significant relationship
                        relationships.append(
                            {
                                "index1": col1,
                                "index2": col2,
                                "correlation": float(corr_value),
                                "strength": (
                                    "strong"
                                    if abs(corr_value) > 0.7
                                    else "moderate" if abs(corr_value) > 0.5 else "weak"
                                ),
                                "direction": (
                                    "positive" if corr_value > 0 else "negative"
                                ),
                            }
                        )

        # Sort by absolute correlation
        relationships.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        return relationships

    def _empty_correlations(self) -> Dict:
        """Return empty correlation result."""
        return {
            "correlations": {},
            "relationships": [],
            "indices_analyzed": [],
        }
