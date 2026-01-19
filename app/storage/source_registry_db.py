# SPDX-License-Identifier: PROPRIETARY
"""SQLite-backed storage for source registry and health tracking."""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger("storage.source_registry_db")


# Database file location (relative to project root)
# Use same pattern as ForecastDB: data/hbc.db or env var
def _get_db_path() -> Path:
    """Get database path using same logic as ForecastDB."""
    import os

    db_path = os.getenv("HBC_DB_PATH")
    if db_path:
        return Path(db_path)
    # Default to data/hbc.db (same as ForecastDB) or data/source_registry.db
    project_root = Path(__file__).resolve().parents[3]
    # Use separate DB for source registry to avoid schema conflicts
    return project_root / "data" / "source_registry.db"


DB_PATH = _get_db_path()


class SourceRegistryDB:
    """SQLite-backed storage for source registry and health metrics."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the source registry database.

        Args:
            db_path: Path to SQLite database file (default: data/source_registry.db)
        """
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Sources table: registry metadata
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    geographic_resolution TEXT,
                    temporal_resolution TEXT,
                    update_cadence TEXT,
                    requires_key INTEGER NOT NULL DEFAULT 0,
                    config_env_vars TEXT,  -- JSON array of env var names
                    endpoint_template TEXT,
                    license_tag TEXT,
                    license_note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Source health table: current health status
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_health (
                    source_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,  -- Active, Available, Degraded, Disabled, NotConfigured
                    last_success_at TIMESTAMP,
                    last_attempt_at TIMESTAMP,
                    freshness_seconds INTEGER,
                    coverage_pct REAL,
                    missingness_pct REAL,
                    latency_ms INTEGER,
                    error_rate REAL,
                    error_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES sources(id)
                )
            """
            )

            # Source runs table: per-run diagnostics (optional, for detailed history)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,  -- success, error, timeout
                    latency_ms INTEGER,
                    records_fetched INTEGER,
                    error_message TEXT,
                    metadata TEXT,  -- JSON blob for additional diagnostics
                    FOREIGN KEY (source_id) REFERENCES sources(id)
                )
            """
            )

            # Indexes for performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_runs_source_id ON source_runs(source_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_runs_timestamp ON source_runs(run_timestamp)"
            )

            conn.commit()

    def upsert_source(
        self,
        source_id: str,
        name: str,
        category: str,
        description: str = "",
        geographic_resolution: Optional[str] = None,
        temporal_resolution: Optional[str] = None,
        update_cadence: Optional[str] = None,
        requires_key: bool = False,
        config_env_vars: Optional[List[str]] = None,
        endpoint_template: Optional[str] = None,
        license_tag: Optional[str] = None,
        license_note: Optional[str] = None,
    ) -> None:
        """
        Insert or update a source definition.

        Args:
            source_id: Unique identifier (snake_case)
            name: Human-readable display name
            category: Category (e.g., "economic", "environmental")
            description: Description text
            geographic_resolution: Geographic resolution (e.g., "country", "state", "city")
            temporal_resolution: Temporal resolution (e.g., "daily", "hourly")
            update_cadence: Update frequency (e.g., "daily", "hourly")
            requires_key: Whether API key is required
            config_env_vars: List of environment variable names needed
            endpoint_template: Template URL or endpoint pattern
            license_tag: License identifier
            license_note: License notes
        """
        with self._get_connection() as conn:
            import json

            config_env_vars_json = (
                json.dumps(config_env_vars) if config_env_vars else None
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO sources (
                    id, name, category, description,
                    geographic_resolution, temporal_resolution, update_cadence,
                    requires_key, config_env_vars, endpoint_template,
                    license_tag, license_note, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    source_id,
                    name,
                    category,
                    description,
                    geographic_resolution,
                    temporal_resolution,
                    update_cadence,
                    1 if requires_key else 0,
                    config_env_vars_json,
                    endpoint_template,
                    license_tag,
                    license_note,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def update_source_health(
        self,
        source_id: str,
        status: str,
        last_success_at: Optional[datetime] = None,
        last_attempt_at: Optional[datetime] = None,
        freshness_seconds: Optional[int] = None,
        coverage_pct: Optional[float] = None,
        missingness_pct: Optional[float] = None,
        latency_ms: Optional[int] = None,
        error_rate: Optional[float] = None,
        error_count: Optional[int] = None,
        success_count: Optional[int] = None,
    ) -> None:
        """
        Update health metrics for a source.

        Args:
            source_id: Source identifier
            status: Status (Active, Available, Degraded, Disabled, NotConfigured)
            last_success_at: Timestamp of last successful fetch
            last_attempt_at: Timestamp of last attempt
            freshness_seconds: Age of most recent data in seconds
            coverage_pct: Percentage of expected data points present
            missingness_pct: Percentage of missing data points
            latency_ms: Average latency in milliseconds
            error_rate: Error rate (0.0-1.0)
            error_count: Total error count
            success_count: Total success count
        """
        with self._get_connection() as conn:
            # Check if health record exists
            cursor = conn.execute(
                "SELECT source_id FROM source_health WHERE source_id = ?", (source_id,)
            )
            exists = cursor.fetchone() is not None

            last_success_iso = last_success_at.isoformat() if last_success_at else None
            last_attempt_iso = last_attempt_at.isoformat() if last_attempt_at else None

            if exists:
                # Update existing record
                conn.execute(
                    """
                    UPDATE source_health SET
                        status = ?,
                        last_success_at = COALESCE(?, last_success_at),
                        last_attempt_at = COALESCE(?, last_attempt_at),
                        freshness_seconds = COALESCE(?, freshness_seconds),
                        coverage_pct = COALESCE(?, coverage_pct),
                        missingness_pct = COALESCE(?, missingness_pct),
                        latency_ms = COALESCE(?, latency_ms),
                        error_rate = COALESCE(?, error_rate),
                        error_count = COALESCE(?, error_count),
                        success_count = COALESCE(?, success_count),
                        updated_at = ?
                    WHERE source_id = ?
                """,
                    (
                        status,
                        last_success_iso,
                        last_attempt_iso,
                        freshness_seconds,
                        coverage_pct,
                        missingness_pct,
                        latency_ms,
                        error_rate,
                        error_count,
                        success_count,
                        datetime.now(timezone.utc).isoformat(),
                        source_id,
                    ),
                )
            else:
                # Insert new record
                conn.execute(
                    """
                    INSERT INTO source_health (
                        source_id, status, last_success_at, last_attempt_at,
                        freshness_seconds, coverage_pct, missingness_pct,
                        latency_ms, error_rate, error_count, success_count, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        source_id,
                        status,
                        last_success_iso,
                        last_attempt_iso,
                        freshness_seconds,
                        coverage_pct,
                        missingness_pct,
                        latency_ms,
                        error_rate,
                        error_count,
                        success_count,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            conn.commit()

    def log_source_run(
        self,
        source_id: str,
        status: str,
        latency_ms: Optional[int] = None,
        records_fetched: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a single source run for diagnostics.

        Args:
            source_id: Source identifier
            status: Run status (success, error, timeout)
            latency_ms: Latency in milliseconds
            records_fetched: Number of records fetched
            error_message: Error message if failed
            metadata: Additional metadata as dict (stored as JSON)
        """
        with self._get_connection() as conn:
            import json

            metadata_json = json.dumps(metadata) if metadata else None

            conn.execute(
                """
                INSERT INTO source_runs (
                    source_id, run_timestamp, status, latency_ms,
                    records_fetched, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    source_id,
                    datetime.now(timezone.utc).isoformat(),
                    status,
                    latency_ms,
                    records_fetched,
                    error_message,
                    metadata_json,
                ),
            )
            conn.commit()

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a source definition by ID.

        Args:
            source_id: Source identifier

        Returns:
            Source definition dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_sources(self) -> List[Dict[str, Any]]:
        """
        Get all source definitions.

        Returns:
            List of source definition dicts
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sources ORDER BY category, name")
            return [dict(row) for row in cursor.fetchall()]

    def get_source_health(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Get health metrics for a source.

        Args:
            source_id: Source identifier

        Returns:
            Health metrics dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM source_health WHERE source_id = ?", (source_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_source_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health metrics for all sources.

        Returns:
            Dict mapping source_id to health metrics
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM source_health")
            return {row["source_id"]: dict(row) for row in cursor.fetchall()}

    def get_source_history(
        self, source_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent run history for a source.

        Args:
            source_id: Source identifier
            limit: Maximum number of records to return

        Returns:
            List of run history dicts (most recent first)
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM source_runs
                WHERE source_id = ?
                ORDER BY run_timestamp DESC
                LIMIT ?
            """,
                (source_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def compute_health_stats(
        self, source_id: str, window_days: int = 7
    ) -> Dict[str, Any]:
        """
        Compute aggregated health statistics from run history.

        Args:
            source_id: Source identifier
            window_days: Number of days to look back

        Returns:
            Dict with aggregated stats (error_rate, avg_latency, etc.)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        cutoff_iso = cutoff.isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as error_count,
                    AVG(latency_ms) as avg_latency_ms,
                    AVG(records_fetched) as avg_records
                FROM source_runs
                WHERE source_id = ? AND run_timestamp >= ?
            """,
                (source_id, cutoff_iso),
            )
            row = cursor.fetchone()
            if row and row["total_runs"]:
                total = row["total_runs"]
                error_rate = row["error_count"] / total if total > 0 else 0.0
                return {
                    "total_runs": total,
                    "success_count": row["success_count"],
                    "error_count": row["error_count"],
                    "error_rate": error_rate,
                    "avg_latency_ms": row["avg_latency_ms"],
                    "avg_records": row["avg_records"],
                }
            return {
                "total_runs": 0,
                "success_count": 0,
                "error_count": 0,
                "error_rate": 0.0,
                "avg_latency_ms": None,
                "avg_records": None,
            }
