"""
Dynamic reprojection utilities for climate GeoTIFFs.

Provides optional on-demand reprojection from Web Mercator (EPSG:3857) back to
WGS84 (EPSG:4326) or other projections if needed, with caching support.
"""

import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.io import MemoryFile
import numpy as np


class GeoTIFFReprojector:
    """
    Handles on-demand reprojection of GeoTIFFs between projections.
    Caches results to disk for performance optimization.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize reprojector.

        Args:
            cache_dir: Directory to cache reprojected files. If None, uses temp directory.
        """
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "climate_mvt_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, source_path: Path, target_crs: str) -> Path:
        """Generate cache path for reprojected file."""
        cache_name = f"{source_path.stem}_{target_crs.replace(':', '_')}.tif"
        return self.cache_dir / cache_name

    def reproject_file(
        self,
        source_path: Path,
        target_crs: str,
        use_cache: bool = True,
    ) -> Path:
        """
        Reproject a GeoTIFF file to a target CRS.

        Args:
            source_path: Path to source GeoTIFF
            target_crs: Target CRS (e.g., 'EPSG:4326')
            use_cache: Whether to use cached reprojected files

        Returns:
            Path to reprojected GeoTIFF (either cached or newly created)

        Raises:
            FileNotFoundError: If source file doesn't exist
            Exception: If reprojection fails
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        cache_path = self._get_cache_path(source_path, target_crs)

        if use_cache and cache_path.exists():
            return cache_path

        # Read source
        with rasterio.open(source_path) as src:
            source_crs = src.crs
            if str(source_crs) == target_crs:
                # Already in target CRS, just return source
                return source_path

            # Calculate transform for target CRS
            transform, width, height = calculate_default_transform(
                source_crs, target_crs, src.width, src.height, *src.bounds
            )

            # Prepare output profile
            kwargs = src.profile.copy()
            kwargs.update(
                {
                    "crs": target_crs,
                    "transform": transform,
                    "width": width,
                    "height": height,
                }
            )

            # Reproject and save
            with rasterio.open(cache_path, "w", **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        rasterio.band(src, i),
                        rasterio.band(dst, i),
                        resampling=Resampling.bilinear,
                    )

                # Copy metadata tags
                if src.tags():
                    dst.update_tags(src.tags())

        return cache_path

    def reproject_to_memory(
        self,
        source_path: Path,
        target_crs: str,
    ) -> Tuple[np.ndarray, Dict]:
        """
        Reproject a GeoTIFF to memory and return as numpy array with metadata.

        Args:
            source_path: Path to source GeoTIFF
            target_crs: Target CRS (e.g., 'EPSG:4326')

        Returns:
            Tuple of (reprojected_array, profile)
        """
        with rasterio.open(source_path) as src:
            source_crs = src.crs

            # Calculate transform for target CRS
            transform, width, height = calculate_default_transform(
                source_crs, target_crs, src.width, src.height, *src.bounds
            )

            # Prepare output profile
            profile = src.profile.copy()
            profile.update(
                {
                    "crs": target_crs,
                    "transform": transform,
                    "width": width,
                    "height": height,
                }
            )

            # Create memory file and reproject
            with MemoryFile() as memfile:
                with memfile.open(**profile) as dst:
                    for i in range(1, src.count + 1):
                        reproject(
                            rasterio.band(src, i),
                            rasterio.band(dst, i),
                            resampling=Resampling.bilinear,
                        )

                    # Read back the reprojected data
                    reprojected = dst.read()

            return reprojected, profile

    def clear_cache(self):
        """Clear all cached reprojected files."""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global reprojector instance
_reprojector = GeoTIFFReprojector()


def reproject_geotiff(
    source_path: Path,
    target_crs: str,
    use_cache: bool = True,
) -> Path:
    """
    Convenience function to reproject a GeoTIFF using the global reprojector.

    Args:
        source_path: Path to source GeoTIFF
        target_crs: Target CRS (e.g., 'EPSG:4326')
        use_cache: Whether to use cached reprojected files

    Returns:
        Path to reprojected GeoTIFF
    """
    return _reprojector.reproject_file(source_path, target_crs, use_cache)


def get_reprojector() -> GeoTIFFReprojector:
    """Get the global reprojector instance."""
    return _reprojector
