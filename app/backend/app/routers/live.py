# SPDX-License-Identifier: PROPRIETARY
"""Live monitoring endpoints for near real-time behavior index tracking."""
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.live_monitor import get_live_monitor

logger = structlog.get_logger("routers.live")

router = APIRouter(prefix="/api/live", tags=["live"])


class LiveSummaryResponse(BaseModel):
    """Response from live summary endpoint."""

    timestamp: str
    regions: dict


@router.get("/summary", response_model=LiveSummaryResponse, tags=["live"])
def get_live_summary(
    regions: Optional[List[str]] = Query(
        None,
        description=(
            "Optional list of region IDs to include. "
            "If not provided, returns all available regions."
        ),
    ),
    time_window_minutes: int = Query(
        default=60,
        ge=1,
        le=1440,
        description=(
            "Time window in minutes for historical snapshots " "(1-1440, default: 60)"
        ),
    ),
) -> LiveSummaryResponse:
    """
    Get a summary of live behavior index data for specified regions.

    This endpoint provides near real-time snapshots of behavior index values,
    sub-indices, and detected major events. Data is refreshed periodically
    by a background process.

    Args:
        regions: Optional list of region IDs (e.g., ["us_dc", "us_mn", "city_nyc"])
        time_window_minutes: Time window for historical snapshots (default: 60 minutes)

    Returns:
        LiveSummaryResponse with latest data and recent history for each region

    Example:
        GET /api/live/summary?regions=us_dc,us_mn&time_window_minutes=120
    """
    try:
        monitor = get_live_monitor()
        summary = monitor.get_summary(
            region_ids=regions, time_window_minutes=time_window_minutes
        )
        return LiveSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve live summary: {str(e)}",
        ) from e


@router.post("/refresh", tags=["live"])
def trigger_refresh(
    regions: Optional[List[str]] = Query(
        None,
        description=(
            "Optional list of region IDs to refresh. "
            "If not provided, refreshes all regions."
        ),
    ),
) -> dict:
    """
    Manually trigger a refresh of live data for specified regions.

    This endpoint allows clients to request an immediate refresh of live
    behavior index data. If no regions are specified, all regions are refreshed.

    Args:
        regions: Optional list of region IDs to refresh

    Returns:
        Dictionary with refresh results (region_id -> success status)

    Example:
        POST /api/live/refresh?regions=us_dc,us_mn
    """
    try:
        monitor = get_live_monitor()
        if regions:
            results = {}
            for region_id in regions:
                snapshot = monitor.refresh_region(region_id)
                results[region_id] = snapshot is not None
        else:
            results = monitor.refresh_all_regions()

        # Get refresh timestamp from any refreshed region
        refreshed_at = None
        if regions:
            for region_id in regions:
                snapshot = monitor.get_latest_snapshot(region_id)
                if snapshot:
                    refreshed_at = snapshot.timestamp.isoformat()
                    break
        else:
            # Find first available snapshot
            for region_id in monitor._snapshots.keys():
                snapshot = monitor.get_latest_snapshot(region_id)
                if snapshot:
                    refreshed_at = snapshot.timestamp.isoformat()
                    break

        return {
            "status": "success",
            "refreshed_at": refreshed_at or datetime.now().isoformat(),
            "results": results,
        }
    except Exception as e:
        logger.error("Failed to trigger refresh", error=str(e), exc_info=True)
        # Do not leak internal error details to clients
        raise HTTPException(
            status_code=500,
            detail="Failed to trigger refresh. Please try again later.",
        ) from e
