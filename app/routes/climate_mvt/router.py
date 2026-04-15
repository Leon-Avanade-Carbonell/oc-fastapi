"""Climate MVT (Cloud-Optimized GeoTIFF) endpoint routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from app.db import get_available_variables, get_available_times
from app.routes.climate_mvt.utils import (
    validate_zoom_level,
    get_cog_path,
    cog_exists,
    list_generated_zoom_levels,
    validate_colormap,
    validate_stretch,
    recolor_cog,
    AVAILABLE_STRETCHES,
    DEFAULT_STRETCH,
)
from app.utils.colormap_utils import DEFAULT_COLORMAP, RECOMMENDED_COLORMAPS

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


@router.get("/colormaps")
async def list_colormaps():
    """
    List available colormaps and stretch modes for dynamic COG recoloring.

    Returns the default colormap/stretch names and dictionaries of available
    options with descriptions. Any valid matplotlib colormap name is accepted
    by the serve_cog endpoint; the colormaps listed here are curated picks.

    Returns:
        dict with "default_colormap", "colormaps", "default_stretch", "stretches" keys.

    Example:
        GET /climate-mvt/colormaps
    """
    return {
        "default_colormap": DEFAULT_COLORMAP,
        "colormaps": RECOMMENDED_COLORMAPS,
        "default_stretch": DEFAULT_STRETCH,
        "stretches": AVAILABLE_STRETCHES,
    }


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
async def serve_cog(
    variable: str,
    time: str,
    zoom_level: int,
    colormap: Optional[str] = Query(
        None,
        description="Matplotlib colormap name. When omitted, serves the pre-generated "
        "COG as-is. When provided, Bands 1-3 are dynamically recolored from "
        "Band 4 (grayscale). Use GET /climate-mvt/colormaps for curated options.",
    ),
    stretch: Optional[str] = Query(
        None,
        description="Non-linear stretch applied to normalised values before the "
        "colormap lookup. Redistributes value density so clustered ranges "
        "show more colour variation. Requires colormap to be set. "
        "Options: linear, sqrt, cbrt, log, gamma_low, gamma_high, equalize.",
    ),
):
    """
    Serve a Cloud-Optimized GeoTIFF file for a specific variable, time, and zoom level.

    This endpoint serves pre-generated COG files with embedded georeferencing in Web Mercator
    (EPSG:3857) projection.

    When the optional `colormap` query parameter is provided, Bands 1-3 are dynamically
    recolored using the requested matplotlib colormap applied to Band 4 (normalized
    grayscale). This allows the frontend to switch visualisation styles without regenerating
    the underlying data. Use GET /climate-mvt/colormaps for a curated list.

    The optional `stretch` parameter applies a non-linear transformation to the normalised
    values before the colormap lookup. This is useful when data values are heavily
    concentrated in a narrow range (e.g. most rainfall near zero) — a stretch like `sqrt`
    or `log` spreads those values across more of the colour gradient.

    **Band structure:**
    - Bands 1-3: RGB visual data (colormap applied)
    - Band 4: Grayscale raw data (normalized 0-255)
    - Band 5: Alpha (255=valid, 0=transparent)

    **Metadata tags embedded in GeoTIFF:**
    - VARIABLE: Variable name
    - TIME: Temporal timestamp
    - ZOOM_LEVEL: Zoom level
    - DATA_MIN: Global historical minimum
    - DATA_MAX: Global historical maximum
    - COLORMAP_TYPE: Colormap name used for RGB bands
    - STRETCH: Stretch mode applied
    - CRS: "EPSG:3857" (Web Mercator)
    - BOUNDS_WGS84: Original bounds in WGS84 degrees [west, south, east, north]

    Args:
        variable: Climate variable name (e.g., "monthly_rain")
        time: Time step (e.g., "1989-01-16")
        zoom_level: Zoom level 0-5 (higher levels provide greater detail)
        colormap: Optional matplotlib colormap name (e.g., "viridis", "plasma", "RdBu")
        stretch: Optional non-linear stretch (e.g., "sqrt", "log", "equalize")

    Returns:
        Binary GeoTIFF file in Web Mercator projection (EPSG:3857)

    Status Codes:
        200: Success
        206: Partial content (range request, only when colormap is omitted)
        404: Variable, time, or zoom level not found
        422: Invalid zoom level, colormap name, or stretch name
        500: Server error

    Example:
        GET /climate-mvt/monthly_rain/1989-01-16/z5.tif
        GET /climate-mvt/monthly_rain/1989-01-16/z5.tif?colormap=viridis
        GET /climate-mvt/monthly_rain/1989-01-16/z5.tif?colormap=RdBu&stretch=sqrt
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

        # If no colormap or stretch requested, serve the pre-generated file directly
        if colormap is None and stretch is None:
            return FileResponse(
                path=cog_path,
                media_type="image/tiff",
                headers={
                    "Accept-Ranges": "bytes",
                },
            )

        # stretch without colormap — use the default colormap
        effective_colormap = colormap or DEFAULT_COLORMAP
        effective_stretch = stretch or DEFAULT_STRETCH

        # Validate parameters
        validate_colormap(effective_colormap)
        validate_stretch(effective_stretch)

        # Recolor Bands 1-3 using Band 4, the requested colormap, and stretch
        tiff_bytes = recolor_cog(cog_path, effective_colormap, effective_stretch)

        return Response(
            content=tiff_bytes,
            media_type="image/tiff",
            headers={
                "Content-Length": str(len(tiff_bytes)),
            },
        )

    except ValueError as e:
        # Zoom level, colormap, or stretch validation error
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
