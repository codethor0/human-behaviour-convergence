# SPDX-License-Identifier: PROPRIETARY
"""Lightweight SQLite database for forecast history and metrics."""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import structlog

logger = structlog.get_logger("storage.db")


class ForecastDB:
    """
    SQLite database for storing forecast history and metrics.

    Schema:
        forecasts:
            - id (INTEGER PRIMARY KEY)
            - timestamp (TEXT, ISO format)
            - region_name (TEXT)
            - latitude (REAL)
            - longitude (REAL)
            - model_name (TEXT)
            - behavior_index (REAL)
            - sub_indices (TEXT, JSON)
            - metadata (TEXT, JSON)
            - version (TEXT)

        metrics:
            - id (INTEGER PRIMARY KEY)
            - forecast_id (INTEGER, FK to forecasts.id)
            - metric_name (TEXT)
            - metric_value (REAL)
            - computed_at (TEXT, ISO format)
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize ForecastDB.

        Args:
            db_path: Path to SQLite database file. If None, uses:
                - $HBC_DB_PATH environment variable if set
                - data/hbc.db relative to project root
        """
        if db_path is None:
            db_path = os.getenv("HBC_DB_PATH")
            if db_path is None:
                # Default to data/hbc.db relative to project root
                project_root = Path(__file__).resolve().parents[3]
                db_path = project_root / "data" / "hbc.db"
                db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create forecasts table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS forecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    region_name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    model_name TEXT NOT NULL,
                    behavior_index REAL,
                    sub_indices TEXT,
                    metadata TEXT,
                    version TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
                """
            )

            # Create metrics table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    forecast_id INTEGER NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    computed_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (forecast_id) REFERENCES forecasts(id)
                )
                """
            )

            # Create indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_forecasts_timestamp "
                "ON forecasts(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_forecasts_region "
                "ON forecasts(region_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_forecast_id "
                "ON metrics(forecast_id)"
            )

            conn.commit()
            logger.info("Database schema initialized", db_path=str(self.db_path))

    def save_forecast(
        self,
        region_name: str,
        latitude: float,
        longitude: float,
        model_name: str,
        behavior_index: float,
        sub_indices: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
        version: str = "1.0",
    ) -> int:
        """
        Save a forecast to the database.

        Args:
            region_name: Human-readable region name
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            model_name: Name of the forecasting model used
            behavior_index: Behavior index value
            sub_indices: Optional dictionary of sub-index values
            metadata: Optional dictionary of additional metadata
            timestamp: ISO format timestamp (defaults to now)
            version: Version identifier (default: "1.0")

        Returns:
            Integer ID of the inserted forecast
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO forecasts (
                    timestamp, region_name, latitude, longitude,
                    model_name, behavior_index, sub_indices, metadata, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    region_name,
                    latitude,
                    longitude,
                    model_name,
                    behavior_index,
                    json.dumps(sub_indices) if sub_indices else None,
                    json.dumps(metadata) if metadata else None,
                    version,
                ),
            )
            forecast_id = cursor.lastrowid
            conn.commit()
            logger.info(
                "Forecast saved",
                forecast_id=forecast_id,
                region_name=region_name,
                behavior_index=behavior_index,
            )
            return forecast_id

    def save_metrics(self, forecast_id: int, metrics: Dict[str, float]) -> None:
        """
        Save metrics for a forecast.

        Args:
            forecast_id: ID of the forecast from save_forecast()
            metrics: Dictionary mapping metric names to values
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for metric_name, metric_value in metrics.items():
                cursor.execute(
                    """
                    INSERT INTO metrics (forecast_id, metric_name, metric_value)
                    VALUES (?, ?, ?)
                    """,
                    (forecast_id, metric_name, metric_value),
                )
            conn.commit()
            logger.info(
                "Metrics saved", forecast_id=forecast_id, metric_count=len(metrics)
            )

    def get_forecasts(
        self,
        region_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_order: str = "DESC",
    ) -> List[Dict[str, Any]]:
        """
        Retrieve forecasts from the database.

        Args:
            region_name: Optional filter by region name (substring match)
            date_from: Optional filter by minimum timestamp (ISO format)
            date_to: Optional filter by maximum timestamp (ISO format)
            limit: Maximum number of records to return (default: 100)
            offset: Offset for pagination (default: 0)
            sort_order: Sort order, either "ASC" or "DESC" (default: "DESC")

        Returns:
            List of forecast dictionaries
        """
        if sort_order not in ("ASC", "DESC"):
            sort_order = "DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build WHERE clause dynamically
            conditions = []
            params = []

            if region_name:
                conditions.append("region_name LIKE ?")
                params.append(f"%{region_name}%")

            if date_from:
                conditions.append("timestamp >= ?")
                params.append(date_from)

            if date_to:
                conditions.append("timestamp <= ?")
                params.append(date_to)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT * FROM forecasts
                WHERE {where_clause}
                ORDER BY timestamp {sort_order}
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])

            cursor.execute(query, params)

            rows = cursor.fetchall()
            forecasts = []
            for row in rows:
                forecast = dict(row)
                # Parse JSON fields
                if forecast.get("sub_indices"):
                    forecast["sub_indices"] = json.loads(forecast["sub_indices"])
                if forecast.get("metadata"):
                    forecast["metadata"] = json.loads(forecast["metadata"])
                forecasts.append(forecast)

            return forecasts

    def get_metrics(self, forecast_id: int) -> Dict[str, float]:
        """
        Retrieve metrics for a forecast.

        Args:
            forecast_id: ID of the forecast

        Returns:
            Dictionary mapping metric names to values
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT metric_name, metric_value FROM metrics WHERE forecast_id = ?",
                (forecast_id,),
            )
            rows = cursor.fetchall()
            return {row["metric_name"]: row["metric_value"] for row in rows}

    def export_to_dataframe(self) -> pd.DataFrame:
        """
        Export all forecasts to a pandas DataFrame.

        Returns:
            DataFrame with forecast data
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                "SELECT * FROM forecasts ORDER BY timestamp DESC", conn
            )

            # Parse JSON columns
            if "sub_indices" in df.columns:
                df["sub_indices"] = df["sub_indices"].apply(
                    lambda x: json.loads(x) if x else None
                )
            if "metadata" in df.columns:
                df["metadata"] = df["metadata"].apply(
                    lambda x: json.loads(x) if x else None
                )

            return df
