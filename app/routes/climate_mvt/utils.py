"""Utility functions for Climate MVT endpoint."""

from pathlib import Path
import os

import numpy as np
import rasterio
from rasterio.io import MemoryFile

from app.utils.colormap_utils import (
    apply_colormap,
    DEFAULT_COLORMAP,
    RECOMMENDED_COLORMAPS,
    get_colormap,
)

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


# ---------------------------------------------------------------------------
# Stretch functions — non-linear transforms applied to [0, 1] normalised
# values *before* the colormap lookup. They redistribute value density so
# that clustered ranges (e.g. many near-zero rainfall pixels) spread across
# more of the colour gradient.
# ---------------------------------------------------------------------------

AVAILABLE_STRETCHES: dict[str, str] = {
    "linear": "No transformation (default)",
    "sqrt": "Square root — mild spread of low values",
    "cbrt": "Cube root — moderate spread of low values",
    "log": "Logarithmic — strong spread of low values (log1p-based)",
    "gamma_low": "Gamma 0.3 — aggressive spread of low values",
    "gamma_high": "Gamma 2.0 — compresses low values, spreads high values",
    "equalize": "Histogram equalization — maximises contrast across all values",
}

DEFAULT_STRETCH = "linear"


def apply_stretch(values: np.ndarray, stretch: str) -> np.ndarray:
    """
    Apply a non-linear stretch to an array of floats in [0, 1].

    The output remains in [0, 1] and is suitable for passing directly
    to a matplotlib colormap.

    Args:
        values: (H, W) float32 array, range [0, 1].
        stretch: Name from AVAILABLE_STRETCHES.

    Returns:
        (H, W) float32 array, range [0, 1].

    Raises:
        ValueError: If stretch name is unknown.
    """
    if stretch == "linear":
        return values

    if stretch == "sqrt":
        return np.sqrt(values)

    if stretch == "cbrt":
        return np.cbrt(values)

    if stretch == "log":
        # log1p maps [0, 1] → [0, ln2].  Divide by ln2 to rescale back to [0, 1].
        return np.log1p(values) / np.log(2.0)

    if stretch == "gamma_low":
        return np.power(values, 0.3)

    if stretch == "gamma_high":
        return np.power(values, 2.0)

    if stretch == "equalize":
        # Histogram equalization on the valid (non-zero) portion.
        # Zero stays zero (nodata in Band 4 is 0).
        out = values.copy()
        mask = values > 0
        if mask.any():
            flat = values[mask].ravel()
            sorted_vals = np.sort(flat)
            # Rank each pixel's value within the sorted distribution
            ranks = np.searchsorted(sorted_vals, values[mask], side="right")
            out[mask] = ranks.astype(np.float32) / len(sorted_vals)
        return out

    raise ValueError(
        f"Unknown stretch '{stretch}'. "
        f"Available: {', '.join(sorted(AVAILABLE_STRETCHES))}."
    )


def validate_stretch(name: str) -> None:
    """
    Validate that a stretch name is supported.

    Raises:
        ValueError: If the name is not in AVAILABLE_STRETCHES.
    """
    if name not in AVAILABLE_STRETCHES:
        raise ValueError(
            f"Unknown stretch '{name}'. "
            f"Available: {', '.join(sorted(AVAILABLE_STRETCHES))}."
        )


def validate_colormap(name: str) -> None:
    """
    Validate that a colormap name is recognised by matplotlib.

    Args:
        name: Colormap name.

    Raises:
        ValueError: If the name is not a valid matplotlib colormap.
    """
    try:
        get_colormap(name)
    except KeyError as exc:
        raise ValueError(str(exc)) from None


def recolor_cog(
    cog_path: Path, colormap_name: str, stretch: str = DEFAULT_STRETCH
) -> bytes:
    """
    Read an existing COG, replace Bands 1-3 using the requested colormap
    applied to Band 4 (normalized grayscale 0-255), and return the result
    as in-memory GeoTIFF bytes.

    An optional non-linear stretch is applied to the normalised values
    *before* the colormap lookup to redistribute value density.

    Band structure of source COGs:
        Band 1-3: RGB (original colormap)
        Band 4:   Grayscale normalised raw data (uint8, 0-255)
        Band 5:   Alpha (255=valid, 0=transparent)

    Args:
        cog_path: Path to the source COG file on disk.
        colormap_name: Any matplotlib colormap name.
        stretch: Non-linear stretch name (see AVAILABLE_STRETCHES).

    Returns:
        bytes of a complete GeoTIFF with the new colormap applied.
    """
    with rasterio.open(cog_path) as src:
        # Read Band 4 — normalised grayscale (uint8 0-255)
        gray = src.read(4)  # (H, W) uint8

        # Convert to float [0, 1] for matplotlib colormap
        normalized = gray.astype(np.float32) / 255.0

        # Apply non-linear stretch before colormap lookup
        stretched = apply_stretch(normalized, stretch)

        # Apply the new colormap → (H, W, 3) uint8 RGB
        rgb = apply_colormap(stretched, colormap_name)

        # Preserve remaining bands (4=grayscale, 5=alpha if present)
        profile = src.profile.copy()

        # Update metadata tags
        tags = src.tags()
        tags["COLORMAP_TYPE"] = colormap_name
        tags["STRETCH"] = stretch

        # Write to in-memory file
        with MemoryFile() as memfile:
            with memfile.open(**profile) as dst:
                # Write new RGB bands
                dst.write(rgb[:, :, 0], 1)  # Red
                dst.write(rgb[:, :, 1], 2)  # Green
                dst.write(rgb[:, :, 2], 3)  # Blue
                # Copy Band 4 (grayscale) unchanged
                dst.write(gray, 4)
                # Copy Band 5 (alpha) if present
                if src.count >= 5:
                    dst.write(src.read(5), 5)
                # Write metadata tags
                dst.update_tags(**tags)

            return memfile.read()
