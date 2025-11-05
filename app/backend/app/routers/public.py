# SPDX-License-Identifier: MIT-0
"""Public data endpoints for Behaviour Convergence Explorer."""
from datetime import datetime
from typing import Dict, List, Literal

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from connectors.firms_fires import FIRMSFiresSync
from connectors.osm_changesets import OSMChangesetsSync
from connectors.wiki_pageviews import WikiPageviewsSync

router = APIRouter(prefix="/api/public", tags=["public"])


class PublicDataResponse(BaseModel):
    """Generic response for public data endpoints."""

    source: str
    date: str
    row_count: int
    data: List[Dict]


class SyntheticScoreResponse(BaseModel):
    """Response for synthetic behavioural score."""

    h3_res: int
    date: str
    scores: List[Dict]


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
        date = (datetime.now().date() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        if source == "wiki":
            connector = WikiPageviewsSync(date=date)
        elif source == "osm":
            connector = OSMChangesetsSync(date=date)
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
    Compute synthetic behavioural score from public data sources.

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
        # Fetch all sources
        wiki = WikiPageviewsSync(date=date).pull()
        osm = OSMChangesetsSync(date=date).pull()
        firms = FIRMSFiresSync(date=date).pull()

        # If any source is empty, return empty scores
        if wiki.empty or osm.empty or firms.empty:
            return SyntheticScoreResponse(h3_res=h3_res, date=date, scores=[])

        # Normalize wiki views (0-1)
        wiki_total = wiki["views"].sum()
        wiki_norm = wiki["views"] / wiki_total if wiki_total > 0 else 0

        # Normalize OSM changesets (0-1)
        osm_total = osm["changeset_count"].sum()
        osm_norm_values = (
            osm["changeset_count"] / osm_total
            if osm_total > 0
            else pd.Series([0] * len(osm))
        )

        # Fire inverse (fewer fires = higher score)
        firms_total = firms["fire_count"].sum()
        fire_inv = (
            1 - (firms["fire_count"] / firms_total)
            if firms_total > 0
            else pd.Series([1] * len(firms))
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
