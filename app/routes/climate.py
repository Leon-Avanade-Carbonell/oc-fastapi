"""Climate data endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db import get_grid_data, get_available_times, get_available_variables

router = APIRouter(prefix="/climate", tags=["climate"])


@router.get("/grid/{variable}/{time}")
async def get_climate_grid(
    variable: str,
    time: str,
    min_lat: Optional[float] = Query(None, description="Minimum latitude"),
    max_lat: Optional[float] = Query(None, description="Maximum latitude"),
    min_lon: Optional[float] = Query(None, description="Minimum longitude"),
    max_lon: Optional[float] = Query(None, description="Maximum longitude"),
):
    """
    Retrieve grid data for a specific climate variable and time step.

    Returns columnar arrays for efficient DeckGL rendering:
    - lats: array of latitude values
    - lons: array of longitude values
    - values: array of data values

    Optional bounding box parameters allow filtering to a specific viewport.
    If none are provided, the full grid is returned.

    Args:
        variable: Variable name (e.g. "monthly_rain")
        time: ISO time string (e.g. "1989-06"). Supports partial matching.
        min_lat, max_lat, min_lon, max_lon: Optional viewport bounding box

    Example:
        GET /climate/grid/monthly_rain/1989-06
        GET /climate/grid/monthly_rain/1989-06?min_lat=-28&max_lat=-20&min_lon=140&max_lon=155
    """
    try:
        data = get_grid_data(
            variable=variable,
            time=time,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
        )

        return {
            "variable": variable,
            "time": time,
            "bbox": {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon,
            },
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variables")
async def list_variables():
    """List all available climate variables in the database."""
    try:
        variables = get_available_variables()
        return {"variables": variables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/times/{variable}")
async def list_times(variable: str):
    """List all available time steps for a specific variable."""
    try:
        times = get_available_times(variable)
        if not times:
            raise HTTPException(
                status_code=404, detail=f"No data found for variable '{variable}'"
            )
        return {"variable": variable, "times": [str(t) for t in times]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
