"""
Colormap utility for climate GeoTIFF generation.

Wraps matplotlib named colormaps and provides a simple interface for
applying any supported colormap to normalized (0-1) float arrays.
The colormap name is embedded as a GeoTIFF metadata tag (COLORMAP_TYPE)
so generated files are self-describing.

Default: 'vanimo' — a dark-mode diverging colormap from F. Crameri's
scientific colour maps (https://doi.org/10.5281/zenodo.1243862).
Bright at the extremes, dark at the centre. Perceptually balanced.

Usage (notebook)::

    from app.utils.colormap_utils import apply_colormap, DEFAULT_COLORMAP

    COLORMAP_NAME = DEFAULT_COLORMAP  # or any name from RECOMMENDED_COLORMAPS
    rgb = apply_colormap(normalized_array, COLORMAP_NAME)

Usage (listing options)::

    from app.utils.colormap_utils import RECOMMENDED_COLORMAPS
    for name, description in RECOMMENDED_COLORMAPS.items():
        print(f"{name:20s} {description}")
"""

import numpy as np
import matplotlib as mpl


# ---------------------------------------------------------------------------
# Default
# ---------------------------------------------------------------------------

DEFAULT_COLORMAP = "vanimo"


# ---------------------------------------------------------------------------
# Curated catalogue — any matplotlib name works, these are highlighted picks
# ---------------------------------------------------------------------------

RECOMMENDED_COLORMAPS: dict[str, str] = {
    # Diverging — good for anomaly / deviation data
    "vanimo": "Dark-mode diverging: bright extremes, dark centre (Crameri)",
    "berlin": "Dark-mode diverging: blue → white → orange (Crameri)",
    "managua": "Dark-mode diverging: teal → white → red (Crameri)",
    "RdBu": "Classic red–blue diverging",
    "coolwarm": "Blue–white–red diverging (narrow lightness range)",
    "BrBG": "Brown–blue-green diverging",
    "PuOr": "Purple–orange diverging",
    # Perceptually uniform sequential — good for absolute magnitude
    "viridis": "Sequential purple → yellow (perceptually uniform)",
    "plasma": "Sequential purple → orange (perceptually uniform)",
    "inferno": "Sequential black → yellow (perceptually uniform)",
    "magma": "Sequential black → white (perceptually uniform)",
    # Sequential — intuitive for rainfall / temperature
    "Blues": "Sequential white → dark blue (intuitive for rainfall)",
    "YlGnBu": "Sequential yellow → green → blue",
    "YlOrRd": "Sequential yellow → orange → red (temperature/heat)",
    # Miscellaneous
    "turbo": "Extended rainbow — good for depth / disparity data",
    "Spectral": "Spectral diverging: red → yellow → blue",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_colormap(name: str = DEFAULT_COLORMAP) -> mpl.colors.Colormap:
    """
    Return a matplotlib colormap by name.

    Args:
        name: Any registered matplotlib colormap name.
              See RECOMMENDED_COLORMAPS for curated options.

    Returns:
        matplotlib.colors.Colormap instance.

    Raises:
        KeyError: If ``name`` is not registered in matplotlib.
    """
    try:
        return mpl.colormaps[name]
    except KeyError:
        available = ", ".join(sorted(RECOMMENDED_COLORMAPS))
        raise KeyError(
            f"Unknown colormap '{name}'. "
            f"Recommended options: {available}. "
            f"Any registered matplotlib name also works."
        ) from None


def apply_colormap(
    values_normalized: np.ndarray,
    name: str = DEFAULT_COLORMAP,
) -> np.ndarray:
    """
    Apply a named matplotlib colormap to a normalized float array.

    Args:
        values_normalized: (H, W) float array with values in [0, 1].
                           NaN values propagate as black (R=G=B=0) in the
                           output RGB array; the caller is responsible for
                           masking them via a separate alpha channel.
        name: Matplotlib colormap name. Defaults to DEFAULT_COLORMAP.

    Returns:
        (H, W, 3) uint8 RGB array with values in [0, 255].
    """
    cmap = get_colormap(name)
    rgba = cmap(values_normalized)  # (H, W, 4) float64 in [0, 1]
    rgb = (rgba[:, :, :3] * 255).astype(np.uint8)
    return rgb


def list_colormaps() -> None:
    """Print all recommended colormaps with descriptions."""
    print(f"Default: {DEFAULT_COLORMAP}\n")
    print(f"{'Name':<20} Description")
    print("-" * 70)
    for name, desc in RECOMMENDED_COLORMAPS.items():
        marker = " *" if name == DEFAULT_COLORMAP else ""
        print(f"{name:<20} {desc}{marker}")
