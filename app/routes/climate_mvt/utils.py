"""Utility functions for Climate MVT endpoint."""

from pathlib import Path
from typing import Optional
import os

# Base directory for generated COGs
COG_BASE_DIR = Path(__file__).parent.parent.parent.parent / "local_only" / "climate_mvt"


def validate_zoom_level(zoom_level: int) -> bool:
    """
    Validate that zoom_level is within valid range (0-10).

    Args:
        zoom_level: Integer zoom level

    Returns:
        True if valid, raises ValueError otherwise
    """
    if not isinstance(zoom_level, int) or zoom_level < 0 or zoom_level > 10:
        raise ValueError(
            f"Invalid zoom level {zoom_level}. Must be an integer between 0 and 10."
        )
    return True


def get_cog_path(variable: str, time: str, zoom_level: int) -> Path:
    """
    Construct the file path for a COG file.

    Args:
        variable: Climate variable name (e.g., "monthly_rain")
        time: Time step (e.g., "1989-01-16")
        zoom_level: Zoom level (0-10)

    Returns:
        Path object to the COG file

    Example:
        /local_only/climate_mvt/monthly_rain/1989-01-16/z5.tif
    """
    return COG_BASE_DIR / variable / time / f"z{zoom_level}.tif"


def cog_exists(variable: str, time: str, zoom_level: int) -> bool:
    """
    Check if a COG file exists on disk.

    Args:
        variable: Climate variable name
        time: Time step
        zoom_level: Zoom level (0-10)

    Returns:
        True if file exists, False otherwise
    """
    path = get_cog_path(variable, time, zoom_level)
    return path.exists() and path.is_file()


def get_cog_directory(variable: str, time: str) -> Path:
    """
    Get the directory containing COGs for a variable+time combination.

    Args:
        variable: Climate variable name
        time: Time step

    Returns:
        Path object to the directory
    """
    return COG_BASE_DIR / variable / time


def list_generated_zoom_levels(variable: str, time: str) -> list:
    """
    List all generated zoom levels for a variable+time combination.

    Args:
        variable: Climate variable name
        time: Time step

    Returns:
        List of zoom levels (integers) that have been generated

    Example:
        [0, 1, 2, 3, 4, 5]  # if z0-z5 have been generated
    """
    directory = get_cog_directory(variable, time)
    if not directory.exists():
        return []

    zoom_levels = []
    for i in range(11):  # Check z0 through z10
        if (directory / f"z{i}.tif").exists():
            zoom_levels.append(i)

    return sorted(zoom_levels)


def ensure_cog_directory_exists(variable: str, time: str) -> Path:
    """
    Ensure the directory for COGs exists, creating it if necessary.

    Args:
        variable: Climate variable name
        time: Time step

    Returns:
        Path object to the directory
    """
    directory = get_cog_directory(variable, time)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
