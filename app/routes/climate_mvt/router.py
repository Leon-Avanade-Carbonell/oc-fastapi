"""Climate MVT (Cloud-Optimized GeoTIFF) endpoint routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.db import get_available_variables, get_available_times
from app.routes.climate_mvt.utils import (
    validate_zoom_level,
    get_cog_path,
    cog_exists,
    list_generated_zoom_levels,
)

router = APIRouter(prefix="/climate-mvt", tags=["climate-mvt"])


@router.get("/variables")
async def list_variables():
    """
    List all available climate variables that have pre-generated COGs.

    Returns a list of variable names available in the climate_mvt directory.
    This mirrors the /climate/variables endpoint but only includes variables
    with pre-generated COGs.

    Returns:
        dict: {"variables": ["monthly_rain", "temperature", ...]}

    Example:
        GET /climate-mvt/variables
        Response: {"variables": ["monthly_rain", "temperature"]}
    """
    try:
        variables = get_available_variables()
        return {"variables": variables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/times/{variable}")
async def list_times(variable: str):
    """
    List all available time steps for a specific variable with pre-generated COGs.

    This mirrors the /climate/times/{variable} endpoint but only includes times
    that have pre-generated COGs available.

    Args:
        variable: Climate variable name (e.g., "monthly_rain")

    Returns:
        dict: {"variable": "monthly_rain", "times": ["1989-01-16", "1989-02-15", ...]}

    Status Codes:
        200: Success
        404: Variable not found
        500: Server error

    Example:
        GET /climate-mvt/times/monthly_rain
        Response: {"variable": "monthly_rain", "times": ["1989-01-16", "1989-02-15"]}
    """
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


@router.get("/{variable}/{time}/z{zoom_level}.tif")
async def serve_cog(variable: str, time: str, zoom_level: int):
    """
    Serve a Cloud-Optimized GeoTIFF file for a specific variable, time, and zoom level.

    This endpoint serves pre-generated COG files with embedded georeferencing in Web Mercator
    (EPSG:3857) projection. The response supports HTTP 206 range requests for efficient partial
    file access.

    **Important:** GeoTIFFs are now in Web Mercator (EPSG:3857) for seamless integration with
    MapLibre GL and DeckGL's default projection. Coordinates are in meters, not degrees.

    **Dual-band structure:**
    - Band 1: RGB visual data (green colormap applied)
    - Band 2: Grayscale raw data (normalized 0-255)

    **Metadata tags embedded in GeoTIFF:**
    - VARIABLE: Variable name
    - TIME: Temporal timestamp
    - ZOOM_LEVEL: Zoom level
    - DATA_MIN: Global historical minimum
    - DATA_MAX: Global historical maximum
    - COLORMAP_TYPE: "green_scale"
    - CRS: "EPSG:3857" (Web Mercator)
    - BOUNDS_WGS84: Original bounds in WGS84 degrees [west, south, east, north]

    Args:
        variable: Climate variable name (e.g., "monthly_rain")
        time: Time step (e.g., "1989-01-16")
        zoom_level: Zoom level 0-5 (higher levels provide greater detail)

    Returns:
        Binary GeoTIFF file in Web Mercator projection (EPSG:3857) with HTTP range request support

    Status Codes:
        200: Success (full file)
        206: Partial content (range request satisfied)
        404: Variable, time, or zoom level not found
        422: Invalid zoom level (not 0-5)
        500: Server error

    Headers:
        Content-Type: image/tiff
        Accept-Ranges: bytes
        Content-Length: {file_size}

    Example:
        GET /climate-mvt/monthly_rain/1989-01-16/z5.tif
        Range: bytes=0-1048575  (optional, for range requests)

    **Coordinate System Note:**
    - Backend generates GeoTIFFs in Web Mercator (EPSG:3857)
    - Coordinates are in meters (Web Mercator projection)
    - Frontend DeckGL BitmapLayer reads embedded georeferencing automatically
    - No manual coordinate transformation needed on the client side
    """
    try:
        # Validate zoom_level
        validate_zoom_level(zoom_level)

        # Check if COG file exists
        if not cog_exists(variable, time, zoom_level):
            # Provide helpful error message with available zoom levels
            available_zooms = list_generated_zoom_levels(variable, time)
            if not available_zooms:
                raise HTTPException(
                    status_code=404,
                    detail=f"No COGs found for variable '{variable}' at time '{time}'. "
                    f"Please generate using the notebook first.",
                )
            raise HTTPException(
                status_code=404,
                detail=f"COG not found for zoom level {zoom_level}. "
                f"Available zoom levels: {available_zooms}",
            )

        # Get the file path
        cog_path = get_cog_path(variable, time, zoom_level)

        # Serve the file with appropriate headers
        # FileResponse automatically handles Range requests (HTTP 206)
        return FileResponse(
            path=cog_path,
            media_type="image/tiff",
            headers={
                "Accept-Ranges": "bytes",
            },
        )

    except ValueError as e:
        # Zoom level validation error
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
