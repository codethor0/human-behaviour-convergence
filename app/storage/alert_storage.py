# SPDX-License-Identifier: PROPRIETARY
"""Alert persistence and state management.

This module provides DB-backed alert persistence with:
- Idempotent writes (no duplicates)
- Deterministic state transitions
- Tenant isolation
- Rate limiting support
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger("storage.alert_storage")


class AlertStorage:
    """
    SQLite-backed storage for alerts.

    Schema:
        alerts:
            - id (INTEGER PRIMARY KEY)
            - alert_id (TEXT, unique per region+type)
            - region_id (TEXT)
            - tenant_id (TEXT, default 'default')
            - alert_type (TEXT: threshold, trend)
            - severity (TEXT: low, medium, high)
            - status (TEXT: active, resolved)
            - first_triggered_at (TEXT, ISO format)
            - last_seen_at (TEXT, ISO format)
            - resolved_at (TEXT, ISO format, nullable)
            - alert_data (TEXT, JSON)
            - notification_sent_at (TEXT, ISO format, nullable)
            - created_at (TEXT, DEFAULT now)
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize AlertStorage.

        Args:
            db_path: Path to SQLite database file. If None, uses same DB as ForecastDB.
        """
        import os

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
        """Create alerts table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT NOT NULL,
                    region_id TEXT NOT NULL,
                    tenant_id TEXT DEFAULT 'default',
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    first_triggered_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    resolved_at TEXT,
                    alert_data TEXT NOT NULL,
                    notification_sent_at TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(alert_id, region_id, tenant_id)
                )
                """
            )

            # Create indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_region_status "
                "ON alerts(region_id, status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_tenant " "ON alerts(tenant_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_last_seen "
                "ON alerts(last_seen_at)"
            )

            conn.commit()
            logger.info("Alert storage schema initialized", db_path=str(self.db_path))

    def _generate_alert_key(
        self, alert_id: str, region_id: str, tenant_id: str = "default"
    ) -> str:
        """Generate deterministic alert key for idempotency."""
        key_string = f"{alert_id}:{region_id}:{tenant_id}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def upsert_alert(
        self,
        alert_id: str,
        region_id: str,
        alert_type: str,
        severity: str,
        alert_data: Dict[str, Any],
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Upsert an alert (create if new, update if exists).

        This is idempotent - calling multiple times with same alert_id+region_id
        will only create one record, updating last_seen_at.

        Args:
            alert_id: Unique alert identifier
            region_id: Region identifier
            alert_type: Type of alert (threshold, trend)
            severity: Severity level (low, medium, high)
            alert_data: Alert data dictionary (will be JSON serialized)
            tenant_id: Tenant identifier (default: 'default')

        Returns:
            Dictionary with alert record (including database id)
        """
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if alert already exists
            cursor.execute(
                """
                SELECT id, status, first_triggered_at, last_seen_at
                FROM alerts
                WHERE alert_id = ? AND region_id = ? AND tenant_id = ?
                """,
                (alert_id, region_id, tenant_id),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing alert
                alert_db_id, status, first_triggered_at, _ = existing
                # Only update if still active (don't reactivate resolved alerts)
                if status == "active":
                    cursor.execute(
                        """
                        UPDATE alerts
                        SET last_seen_at = ?, alert_data = ?
                        WHERE id = ?
                        """,
                        (now, json.dumps(alert_data), alert_db_id),
                    )
                    conn.commit()
                    logger.debug(
                        "Alert updated",
                        alert_id=alert_id,
                        region_id=region_id,
                        alert_db_id=alert_db_id,
                    )
                    return {
                        "id": alert_db_id,
                        "alert_id": alert_id,
                        "region_id": region_id,
                        "tenant_id": tenant_id,
                        "alert_type": alert_type,
                        "severity": severity,
                        "status": status,
                        "first_triggered_at": first_triggered_at,
                        "last_seen_at": now,
                        "alert_data": alert_data,
                    }
                else:
                    # Alert was resolved, don't reactivate
                    logger.debug(
                        "Alert already resolved, not reactivating",
                        alert_id=alert_id,
                        region_id=region_id,
                    )
                    return {
                        "id": alert_db_id,
                        "alert_id": alert_id,
                        "region_id": region_id,
                        "status": status,
                        "resolved": True,
                    }
            else:
                # Create new alert
                cursor.execute(
                    """
                    INSERT INTO alerts (
                        alert_id, region_id, tenant_id, alert_type, severity,
                        status, first_triggered_at, last_seen_at, alert_data
                    ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        alert_id,
                        region_id,
                        tenant_id,
                        alert_type,
                        severity,
                        now,
                        now,
                        json.dumps(alert_data),
                    ),
                )
                alert_db_id = cursor.lastrowid
                conn.commit()
                logger.info(
                    "Alert created",
                    alert_id=alert_id,
                    region_id=region_id,
                    alert_db_id=alert_db_id,
                )
                return {
                    "id": alert_db_id,
                    "alert_id": alert_id,
                    "region_id": region_id,
                    "tenant_id": tenant_id,
                    "alert_type": alert_type,
                    "severity": severity,
                    "status": "active",
                    "first_triggered_at": now,
                    "last_seen_at": now,
                    "alert_data": alert_data,
                }

    def resolve_alert(
        self, alert_id: str, region_id: str, tenant_id: str = "default"
    ) -> bool:
        """
        Resolve an alert (mark as resolved).

        Args:
            alert_id: Alert identifier
            region_id: Region identifier
            tenant_id: Tenant identifier (default: 'default')

        Returns:
            True if alert was resolved, False if not found or already resolved
        """
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE alerts
                SET status = 'resolved', resolved_at = ?
                WHERE alert_id = ? AND region_id = ? AND tenant_id = ?
                AND status = 'active'
                """,
                (now, alert_id, region_id, tenant_id),
            )
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(
                    "Alert resolved",
                    alert_id=alert_id,
                    region_id=region_id,
                    tenant_id=tenant_id,
                )
                return True
            else:
                logger.debug(
                    "Alert not found or already resolved",
                    alert_id=alert_id,
                    region_id=region_id,
                )
                return False

    def get_active_alerts(
        self,
        region_id: Optional[str] = None,
        tenant_id: str = "default",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get active alerts.

        Args:
            region_id: Optional filter by region
            tenant_id: Tenant identifier (default: 'default')
            limit: Maximum number of alerts to return

        Returns:
            List of alert dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if region_id:
                cursor.execute(
                    """
                    SELECT * FROM alerts
                    WHERE status = 'active' AND region_id = ? AND tenant_id = ?
                    ORDER BY last_seen_at DESC
                    LIMIT ?
                    """,
                    (region_id, tenant_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM alerts
                    WHERE status = 'active' AND tenant_id = ?
                    ORDER BY last_seen_at DESC
                    LIMIT ?
                    """,
                    (tenant_id, limit),
                )

            rows = cursor.fetchall()
            alerts = []
            for row in rows:
                alert = dict(row)
                # Parse JSON fields
                if alert.get("alert_data"):
                    alert["alert_data"] = json.loads(alert["alert_data"])
                alerts.append(alert)

            return alerts

    def check_rate_limit(
        self,
        alert_id: str,
        region_id: str,
        tenant_id: str = "default",
        rate_limit_hours: int = 24,
    ) -> bool:
        """
        Check if alert is within rate limit window.

        Args:
            alert_id: Alert identifier
            region_id: Region identifier
            tenant_id: Tenant identifier (default: 'default')
            rate_limit_hours: Rate limit window in hours

        Returns:
            True if alert can be sent (not rate-limited), False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT notification_sent_at FROM alerts
                WHERE alert_id = ? AND region_id = ? AND tenant_id = ?
                AND status = 'active'
                ORDER BY notification_sent_at DESC
                LIMIT 1
                """,
                (alert_id, region_id, tenant_id),
            )
            row = cursor.fetchone()

            if not row or not row[0]:
                # No previous notification, allow
                return True

            # Check if within rate limit window
            last_sent = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours_since = (now - last_sent).total_seconds() / 3600.0

            return hours_since >= rate_limit_hours

    def mark_notification_sent(
        self,
        alert_id: str,
        region_id: str,
        tenant_id: str = "default",
    ) -> None:
        """
        Mark that a notification was sent for an alert.

        Args:
            alert_id: Alert identifier
            region_id: Region identifier
            tenant_id: Tenant identifier (default: 'default')
        """
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE alerts
                SET notification_sent_at = ?
                WHERE alert_id = ? AND region_id = ? AND tenant_id = ?
                AND status = 'active'
                """,
                (now, alert_id, region_id, tenant_id),
            )
            conn.commit()
