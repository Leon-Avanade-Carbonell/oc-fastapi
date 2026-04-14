# Climate GeoTIFF Raster Tiles Endpoint Guide

## Overview

Serves **pre-generated Cloud-Optimized GeoTIFF (COG) raster tile files** (`.tif` format) for climate data visualization via DeckGL's `BitmapLayer`.

**Important:** This endpoint serves **raster tiles (GeoTIFF format)**, not vector tiles (MVT/PBF). Each response is a binary GeoTIFF image file.

- Progressive zoom levels z0-z5 (256px to 8192px)
- Dual-band: RGB visual (green colormap) + grayscale raw data
- **Web Mercator (EPSG:3857)** with embedded georeferencing
- Static files, pre-generated and ready for direct DeckGL consumption
- Coordinates in meters (Web Mercator projection), not degrees

## Request Flow

```
DeckGL BitmapLayer
  → GET /climate-mvt/{variable}/{time}/z{zoom}.tif
  → FastAPI Router (app/routes/climate_mvt/router.py)
  → Loads .tif file from /local_only/climate_mvt/
  → Returns binary GeoTIFF image (image/tiff)
```

## File Structure

```
/local_only/climate_mvt/
└── {variable}/
    └── {time}/
        ├── z0.tif   (256×256)
        ├── z1.tif   (512×512)
        ├── z2.tif   (1024×1024)
        ├── z3.tif   (2048×2048)
        ├── z4.tif   (4096×4096)
        └── z5.tif   (8192×8192)
```

All COGs cover the full Australia extent in Web Mercator projection. 
Zoom levels control pixel resolution, not geographic extent.
Note: Australia bounds in WGS84 are approximately `112.90°E, -43.65°S` to `153.65°E, -10.05°S`.

## API Endpoints

### GET `/climate-mvt/variables`

```json
{ "variables": ["monthly_rain", "temperature"] }
```

### GET `/climate-mvt/times/{variable}`

```json
{ "variable": "monthly_rain", "times": ["1989-01-16", "1989-02-15", ...] }
```

### GET `/climate-mvt/{variable}/{time}/z{zoom_level}.tif`

Returns a binary GeoTIFF. Supports HTTP 206 range requests.

```
GET /climate-mvt/monthly_rain/1989-01-16/z5.tif
```

- `zoom_level`: integer 0-5

## Response Format

All endpoints return data in the following format:

- **File Type:** Binary GeoTIFF (`.tif`)
- **Media Type:** `image/tiff`
- **Range Requests:** Supported (HTTP 206)
- **Georeferencing:** Web Mercator (EPSG:3857)
- **Coordinate System:** Meters (not degrees)

**Example Response:**
```
HTTP/1.1 200 OK
Content-Type: image/tiff
Content-Length: 2097152
Accept-Ranges: bytes

[binary GeoTIFF image data]
```

## Zoom Levels

| Zoom | Pixels | Use Case |
|------|--------|----------|
| z0 | 256×256 | Continental overview |
| z1 | 512×512 | Regional overview |
| z2 | 1024×1024 | Regional detail |
| z3 | 2048×2048 | State level |
| z4 | 4096×4096 | District level |
| z5 | 8192×8192 | Local area (max) |

z5 is the maximum. The source climate grid (~0.05° resolution) has ~820×680 native data points over Australia; z5 already provides ~10x oversampling beyond that. Higher zoom levels would add no visual information and consume excessive memory during generation.

## Band Structure

| Band | Content | Format |
|------|---------|--------|
| 1-3 | RGB (green colormap) | uint8, visual display |
| 4 | Grayscale (normalized raw) | uint8, 0-255 |

**Green colormap:** Dark `#1B5E20` (min) → Medium `#66BB6A` → Light `#C8E6C9` (max)

**Normalization:** Values are mapped to the global historical min/max across all times for that variable:
```
pixel_value = ((raw - global_min) / (global_max - global_min)) * 255
```

## Metadata Tags

Each GeoTIFF embeds these tags:

| Tag | Example |
|-----|---------|
| `VARIABLE` | `monthly_rain` |
| `TIME` | `1989-01-16` |
| `ZOOM_LEVEL` | `5` |
| `DATA_MIN` | `0.0` |
| `DATA_MAX` | `450.5` |
| `COLORMAP_TYPE` | `green_scale` |
| `CRS` | `EPSG:3857` |
| `BOUNDS_WGS84` | `[112.90, -43.65, 153.65, -10.05]` |

## COG Generation

Run `notebooks/generate_climate_mvt.ipynb`:

1. Queries `climate_grid` table from PostgreSQL
2. Computes global min/max across all times for the variable
3. **Transforms geographic bounds from WGS84 (EPSG:4326) to Web Mercator (EPSG:3857)**
4. Rasterizes grid at native resolution (~820×680), then resizes via PIL bilinear interpolation for each zoom level
5. Writes dual-band COGs with Web Mercator georeferencing and metadata to `/local_only/climate_mvt/`

**Dependencies:** `rasterio`, `pyproj`, `numpy`, `PIL/Pillow`, `psycopg2`

**Projection Details:**
- GeoTIFFs are generated in Web Mercator (EPSG:3857) to ensure seamless alignment with MapLibre GL and DeckGL's default projection
- Coordinates are in meters, not degrees
- WGS84 bounds are preserved in metadata (`BOUNDS_WGS84` tag) for reference

## Frontend Usage

GeoTIFFs are now in Web Mercator (EPSG:3857) with embedded georeferencing. DeckGL's `BitmapLayer` reads the georeference information directly from the GeoTIFF file, so no manual bounds specification is required.

**Important: Do NOT manually specify bounds** - DeckGL will automatically extract them from the GeoTIFF georeferencing.

```javascript
import { BitmapLayer } from '@deck.gl/layers';

const layer = new BitmapLayer({
  id: 'climate-mvt-layer',
  image: 'http://api-server/climate-mvt/monthly_rain/1989-01-16/z5.tif',
  // Note: bounds are automatically extracted from GeoTIFF georeferencing
  // The GeoTIFF is in Web Mercator (EPSG:3857), so it aligns automatically
  pickable: true,
});
```

**Important:** The GeoTIFF now includes complete Web Mercator georeferencing information.
DeckGL will automatically:
1. Read the projection (EPSG:3857) from the GeoTIFF
2. Determine the correct geographic extent in meters
3. Position the image correctly on the map

No additional coordinate transformation is needed!

### Zoom Level Selection

```javascript
function selectCogZoom(mapZoom) {
  const cogZoom = Math.min(Math.floor(mapZoom), 5);
  return Math.max(cogZoom, 0);
}
```

## Coordinate System Details

### Web Mercator (EPSG:3857)
- **Used for:** All GeoTIFF tiles in this API
- **Coordinate Unit:** Meters (not degrees)
- **Advantage:** Aligns with MapLibre GL and DeckGL default projections
- **Result:** Pixel-perfect overlay on web maps without client-side transformation

### WGS84 Reference (EPSG:4326)
- **Original Data:** Australia bounds approximately `112.90°E to 153.65°E`, `-43.65°S to -10.05°S`
- **Usage:** Reference information only; stored in `BOUNDS_WGS84` metadata tag
- **When Needed:** If you need to reproject tiles back to WGS84 for analysis or comparison

### Transformation Path
```
Database (WGS84)
    ↓
Notebook Rasterization (WGS84)
    ↓
PyProj Reprojection (WGS84 → Web Mercator)
    ↓
GeoTIFF Generation (Web Mercator)
    ↓
API Serving (Web Mercator)
    ↓
DeckGL Display (Web Mercator)
```

### Reprojection Utilities
If you need to convert tiles back to WGS84 or another projection for advanced use cases:

```python
from app.routes.climate_mvt.reprojection_utils import reproject_geotiff
from pathlib import Path

# Reproject a Web Mercator tile to WGS84
source_tif = Path("path/to/web_mercator_tile.tif")
reprojected = reproject_geotiff(source_tif, "EPSG:4326", use_cache=True)
```

See `app/routes/climate_mvt/reprojection_utils.py` for more advanced options.

## Quick Test

```bash
# Verify API endpoints
curl http://localhost:8000/climate-mvt/variables
curl http://localhost:8000/climate-mvt/times/monthly_rain

# Download a GeoTIFF (now in Web Mercator/EPSG:3857)
curl -o output.tif http://localhost:8000/climate-mvt/monthly_rain/1989-01-16/z5.tif

# Verify the GeoTIFF projection (requires GDAL tools)
gdalinfo output.tif | grep PROJCS  # Should show: PROJCS["Web Mercator",...]

# Verify metadata tags
gdalinfo output.tif | grep -A 20 "Image Structure Metadata"
```
