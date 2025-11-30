# SPDX-License-Identifier: PROPRIETARY
"""Public data endpoints for Behavior Convergence Explorer."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Literal, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from connectors.firms_fires import FIRMSFiresSync
from connectors.osm_changesets import OSMChangesetsSync
from connectors.wiki_pageviews import WikiPageviewsSync

router = APIRouter(prefix="/api/public", tags=["public"])
# Resolve to repository root (one level above top-level `app/` package)
PROJECT_ROOT = Path(__file__).resolve().parents[4]
PUBLIC_DATA_DIR = PROJECT_ROOT / "data" / "public"


class PublicDataResponse(BaseModel):
    """Generic response for public data endpoints."""

    source: str
    date: str
    row_count: int
    data: List[Dict]


class SyntheticScoreResponse(BaseModel):
    """Response for synthetic behavioral score."""

    h3_res: int
    date: str
    scores: List[Dict]


class SourceSnapshot(BaseModel):
    rows: int
    path: Optional[str] = None
    error: Optional[str] = None


class PublicSnapshotResponse(BaseModel):
    """Summary of the latest downloaded public data snapshot."""

    available: bool
    date: Optional[str]
    generated_at: Optional[str]
    sources: Dict[str, SourceSnapshot] = Field(default_factory=dict)
    errors: Dict[str, str] = Field(default_factory=dict)


@router.get("/{source}/latest", response_model=PublicDataResponse)
async def get_public_data_latest(
    source: Literal["wiki", "osm", "firms"],
    date: str = Query(
        default=None,
        description="Date in YYYY-MM-DD format. Defaults to yesterday.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
) -> PublicDataResponse:
    """
    Fetch latest data from a public source.

    Args:
        source: Data source (wiki, osm, firms)
        date: Optional date filter in YYYY-MM-DD format

    Returns:
        JSON with source metadata and data rows
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).date().strftime("%Y-%m-%d")

    try:
        if source == "wiki":
            # Limit to 1 hour for API responses to avoid timeout/OOM
            connector = WikiPageviewsSync(date=date, max_hours=1)
        elif source == "osm":
            # Limit OSM data size to prevent OOM
            connector = OSMChangesetsSync(date=date, max_bytes=10 * 1024 * 1024)
        elif source == "firms":
            connector = FIRMSFiresSync(date=date)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

        df = connector.pull()

        if df.empty:
            return PublicDataResponse(source=source, date=date, row_count=0, data=[])

        return PublicDataResponse(
            source=source,
            date=date,
            row_count=len(df),
            data=df.to_dict(orient="records"),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch {source} data: {str(e)}"
        ) from e


@router.get("/synthetic_score/{h3_res}/{date}", response_model=SyntheticScoreResponse)
async def get_synthetic_score(h3_res: int, date: str) -> SyntheticScoreResponse:
    """
    Compute synthetic behavioral score from public data sources.

    Formula: 0.3 * wiki_norm + 0.3 * osm_norm + 0.4 * fire_inv

    Args:
        h3_res: H3 resolution (5-9, coarser to finer)
        date: Date in YYYY-MM-DD format

    Returns:
        JSON with synthetic scores per H3 cell (0-100 scale)
    """
    # Validate h3_res
    if not 5 <= h3_res <= 9:
        raise HTTPException(status_code=422, detail="h3_res must be between 5 and 9")

    # Validate date format
    import re

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(status_code=422, detail="date must be in YYYY-MM-DD format")
    try:
        # Fetch all sources with limits to prevent OOM
        wiki = WikiPageviewsSync(date=date, max_hours=1).pull()
        osm = OSMChangesetsSync(date=date, max_bytes=10 * 1024 * 1024).pull()
        firms = FIRMSFiresSync(date=date).pull()

        # If any source is empty, return empty scores
        if wiki.empty or osm.empty or firms.empty:
            return SyntheticScoreResponse(h3_res=h3_res, date=date, scores=[])

        # Normalize wiki views (0-1)
        wiki_total = wiki["views"].sum()
        wiki_norm = (
            wiki["views"] / wiki_total
            if wiki_total > 0
            else pd.Series([0] * len(wiki), dtype=float)
        )

        # Normalize OSM changesets (0-1)
        osm_total = osm["changeset_count"].sum()
        osm_norm_values = (
            osm["changeset_count"] / osm_total
            if osm_total > 0
            else pd.Series([0] * len(osm), dtype=float)
        )

        # Fire inverse (fewer fires = higher score)
        firms_total = firms["fire_count"].sum()
        fire_inv = (
            1 - (firms["fire_count"] / firms_total)
            if firms_total > 0
            else pd.Series([1] * len(firms), dtype=float)
        )

        # Compute synthetic score (0-100 scale)
        # For simplicity, aggregate by taking mean of available data
        synthetic_score = (
            0.3 * wiki_norm.mean()
            + 0.3 * osm_norm_values.mean()
            + 0.4 * fire_inv.mean()
        ) * 100

        # Return a single global score (could be per-H3 cell with more logic)
        scores = [{"h3_cell": "global", "score": round(synthetic_score, 2)}]

        return SyntheticScoreResponse(h3_res=h3_res, date=date, scores=scores)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to compute synthetic score: {str(e)}"
        ) from e


@router.get("/stats", response_model=PublicSnapshotResponse)
async def get_public_snapshot_stats() -> PublicSnapshotResponse:
    """
    Return metadata about the latest `sync-public-data` snapshot, if available.

    Snapshot files are produced by `hbc-cli sync-public-data --apply` and copied into
    `data/public/latest/`.
    """

    manifest_path = PUBLIC_DATA_DIR / "latest" / "snapshot.json"

    if not manifest_path.exists():
        return PublicSnapshotResponse(
            available=False,
            date=None,
            generated_at=None,
            sources={},
            errors={
                "snapshot": (
                    "No snapshot found. Run `hbc-cli sync-public-data --apply` "
                    "to populate data/public/latest."
                )
            },
        )

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - unexpected file edits
        return PublicSnapshotResponse(
            available=False,
            date=None,
            generated_at=None,
            sources={},
            errors={"manifest": f"Invalid JSON: {exc}"},
        )

    sources: Dict[str, SourceSnapshot] = {}
    for key, value in manifest.get("sources", {}).items():
        sources[key] = SourceSnapshot(
            rows=int(value.get("rows", 0)),
            path=value.get("path"),
            error=value.get("error"),
        )

    return PublicSnapshotResponse(
        available=True,
        date=manifest.get("date"),
        generated_at=manifest.get("generated_at"),
        sources=sources,
        errors=manifest.get("errors", {}),
    )
