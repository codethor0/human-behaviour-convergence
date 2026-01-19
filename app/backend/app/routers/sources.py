# SPDX-License-Identifier: PROPRIETARY
"""Source registry and health monitoring endpoints."""
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.services.ingestion.source_registry import get_all_sources, get_source_statuses
from app.storage import SourceRegistryDB

logger = structlog.get_logger("routers.sources")

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("/registry")
def get_source_registry() -> Dict[str, Any]:
    """
    Get the complete source registry with metadata for all registered sources.

    Returns:
        Dictionary mapping source IDs to source definitions with metadata
    """
    try:
        sources = get_all_sources()

        # Format sources for API response
        registry_data = {}
        for source_id, source_def in sources.items():
            registry_data[source_id] = {
                "id": source_def.id,
                "name": source_def.display_name,
                "category": source_def.category,
                "description": source_def.description,
                "requires_key": source_def.requires_key,
                "required_env_vars": source_def.required_env_vars,
                "can_run_without_key": source_def.can_run_without_key,
            }

        return {
            "sources": registry_data,
            "count": len(registry_data),
        }
    except Exception as e:
        logger.error("Failed to get source registry", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve source registry: {str(e)}"
        )


@router.get("/health")
def get_source_health(
    source_id: Optional[str] = Query(
        None, description="Optional source ID to filter by"
    )
) -> Dict[str, Any]:
    """
    Get health metrics for one or all data sources.

    Args:
        source_id: Optional source ID to get health for a specific source.
                   If not provided, returns health for all sources.

    Returns:
        Dictionary containing health metrics for requested source(s)
    """
    try:
        # Try to get health from database first
        try:
            db = SourceRegistryDB()

            if source_id:
                # Single source health
                health_data = db.get_source_health(source_id)
                if health_data is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Source '{source_id}' not found in health database",
                    )

                return {
                    "source_id": source_id,
                    "health": health_data,
                }
            else:
                # All sources health
                all_sources = get_all_sources()
                health_response = {}

                for source_id in all_sources.keys():
                    health_data = db.get_source_health(source_id)
                    if health_data:
                        health_response[source_id] = health_data

                return {
                    "sources": health_response,
                    "count": len(health_response),
                }
        except Exception as db_error:
            logger.warning(
                "Database health query failed, falling back to in-memory status",
                error=str(db_error),
            )
            # Fall back to in-memory status computation
            statuses = get_source_statuses()

            if source_id:
                if source_id not in statuses:
                    raise HTTPException(
                        status_code=404, detail=f"Source '{source_id}' not found"
                    )
                return {
                    "source_id": source_id,
                    "health": statuses[source_id],
                }
            else:
                return {
                    "sources": statuses,
                    "count": len(statuses),
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get source health", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve source health: {str(e)}"
        )
