from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from loguru import logger

from sentinel.storage.run_store import get_runs, get_run_detail

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
def list_runs(limit: int = Query(20, ge=1, le=100)):
    """Fetch aggregated history of agent runs intercepted by Sentinel."""
    logger.info(f"API Request: list_runs with limit={limit}")
    try:
        runs = get_runs(limit=limit)
        return runs
    except Exception as e:
        logger.error(f"API Error in list_runs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching runs")

@router.get("/{run_id}", response_model=Dict[str, Any])
def retrieve_run(run_id: str):
    """Fetch exact run details including chronologic validation timeline."""
    logger.info(f"API Request: retrieve_run ID={run_id}")
    try:
        detail = get_run_detail(run_id)
        if not detail or not detail.get("metadata"):
            logger.warning(f"Run {run_id} requested but not found.")
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error in retrieve_run: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error fetching run detail")
