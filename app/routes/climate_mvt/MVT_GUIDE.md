# Climate MVT (Cloud-Optimized GeoTIFF) Endpoint Guide

## Overview

The Climate MVT endpoint serves **pre-generated Cloud-Optimized GeoTIFF (COG) files** containing rasterized climate data. This endpoint is designed for efficient visualization of climate grids using DeckGL's `BitmapLayer` with HTTP range requests.

**Key Features:**
- Pre-generated Cloud-Optimized GeoTIFF files (no runtime rasterization)
- Progressive zoom levels (z0-z10) for viewport-efficient loading
- Dual-band structure: RGB visual (green colormap) + grayscale raw data
- WGS84 (EPSG:4326) projection with embedded georeferencing
- Full GeoTIFF metadata tags for client-side data interpretation

## Architecture

### Request Flow

```
Frontend (DeckGL Application)
    ↓
BitmapLayer with HTTP range requests
    ↓
GET /climate-mvt/{variable}/{time}/z{zoom_level}.tif
    ↓
FastAPI Router (/app/routes/climate_mvt/router.py)
    ├─ Discovery endpoints (variables, times)
    └─ COG serving endpoint
    ↓
Static Files (/local_only/climate_mvt/)
```

### File Organization

```
/local_only/climate_mvt/
├── {variable}/
│   └── {time}/
│       ├── z0.tif   (256×256px, full Australia)
│       ├── z1.tif   (512×512px)
│       ├── z2.tif   (1024×1024px)
│       ├── ...
│       └── z10.tif  (262144×262144px, maximum detail)
└── [more variables]
```

## API Endpoints

### Discovery Endpoints (Reuse from `/climate`)

#### GET `/climate-mvt/variables`

Lists all available climate variables that have pre-generated COGs.

**Response:**
```json
{
  "variables": ["monthly_rain", "temperature", ...]
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

#### GET `/climate-mvt/times/{variable}`

Lists all available time steps for a specific variable with pre-generated COGs.

**Parameters:**
- `variable` (string, required): Variable name (e.g., "monthly_rain")

**Response:**
```json
{
  "variable": "monthly_rain",
  "times": ["1989-01-16", "1989-02-15", "1989-03-18", ...]
}
```

**Status Codes:**
- `200` - Success
- `404` - Variable not found
- `500` - Server error

---

### COG Serving Endpoint

#### GET `/climate-mvt/{variable}/{time}/z{zoom_level}.tif`

Serves a pre-generated Cloud-Optimized GeoTIFF file for a specific variable, time, and zoom level.

**Parameters:**
- `variable` (string, required): Variable name (e.g., "monthly_rain")
- `time` (string, required): Time step (e.g., "1989-01-16")
- `zoom_level` (integer, required): Zoom level 0-10

**Response:**
- Binary GeoTIFF file
- Supports HTTP 206 range requests for efficient partial file access

**Response Headers:**
- `Content-Type: image/tiff`
- `Content-Length: {file_size}`
- `Accept-Ranges: bytes` (enables HTTP range requests)

**Status Codes:**
- `200` - Success (full file)
- `206` - Partial content (range request)
- `404` - Variable, time, or zoom level not found
- `422` - Invalid zoom level (not 0-10)
- `500` - Server error

**Example Requests:**
```
GET /climate-mvt/monthly_rain/1989-01-16/z5.tif
GET /climate-mvt/temperature/1989-01-16/z0.tif
```

---

## GeoTIFF Specifications

### Projection & Bounds

- **CRS:** WGS84 (EPSG:4326)
- **Bounds:** Approximately `[112.85°E, -43.65°S, 154.0°E, -10.0°S]` (Australia extent)
- **Pixel Registration:** Pixel centers align with grid cells

### Band Structure

The COG contains **2 bands**:

**Band 1: Visual (RGB)**
- Colormapped climate data as shades of green
- Green scale: Dark green (#1B5E20) for minimum values → Light green (#C8E6C9) for maximum values
- Derived from raw grid values mapped to the global historical min/max range
- Suitable for direct visualization in DeckGL BitmapLayer

**Band 2: Raw Data (Grayscale)**
- Single-channel 8-bit unsigned integer (0-255)
- Normalized from raw values using global historical min/max
- Preserves quantitative data for client-side analysis
- Formula: `raw_value_normalized = ((raw_value - global_min) / (global_max - global_min)) * 255`

### Missing Data Handling

- Grid cells with missing/NaN values are **skipped** (not encoded in bands)
- Clients should interpret missing pixel areas appropriately

### Metadata Tags

GeoTIFF files embed the following metadata tags (TIFF tags):

| Tag | Type | Example | Purpose |
|-----|------|---------|---------|
| `VARIABLE` | String | "monthly_rain" | Climate variable name |
| `TIME` | String | "1989-01-16" | Temporal stamp |
| `ZOOM_LEVEL` | Integer | 5 | Zoom level of this COG |
| `DATA_MIN` | Float | 0.0 | Global historical minimum |
| `DATA_MAX` | Float | 450.5 | Global historical maximum |
| `COLORMAP_TYPE` | String | "green_scale" | Colormap specification |
| `CRS` | String | "EPSG:4326" | Coordinate reference system |

**Note:** These tags can be read by the frontend to understand data ranges, colormap, and temporal context.

---

## Zoom Level Specifications

COGs are pre-generated at 11 progressive zoom levels (z0-z10), each with increasing pixel resolution:

| Zoom | Pixel Dims | Coverage | Typical Use Case |
|------|-----------|----------|------------------|
| z0 | 256×256 | Full Australia | World/continental view |
| z1 | 512×512 | Full Australia | Regional overview (2× detail) |
| z2 | 1024×1024 | Full Australia | Regional detail (4× detail) |
| z3 | 2048×2048 | Full Australia | State level (8× detail) |
| z4 | 4096×4096 | Full Australia | District level (16× detail) |
| z5 | 8192×8192 | Full Australia | Local area (32× detail) |
| z6 | 16384×16384 | Full Australia | Neighborhood (64× detail) |
| z7 | 32768×32768 | Full Australia | Fine detail (128× detail) |
| z8 | 65536×65536 | Full Australia | Very fine detail (256× detail) |
| z9 | 131072×131072 | Full Australia | Ultra-fine detail (512× detail) |
| z10 | 262144×262144 | Full Australia | Maximum detail (1024× detail) |

**Note:** All COGs cover the full Australia extent; zoom levels control rasterization resolution, not geographic extent.

---

## Colormap Specification

The green colormap is a linear gradient from dark to light green, applied to the normalized data range.

**Color Scale:**
- **Minimum value (0%):** Dark Green `#1B5E20` (RGB: 27, 94, 32)
- **Midpoint (50%):** Medium Green `#66BB6A` (RGB: 102, 187, 106)
- **Maximum value (100%):** Light Green `#C8E6C9` (RGB: 200, 230, 201)

**Normalization:**
- All raw values are normalized to the **global historical min/max** across all available times for that variable
- Example: If `monthly_rain` ranges from 0mm to 450mm globally (across all months), then:
  - 0mm → Dark Green
  - 225mm → Medium Green
  - 450mm → Light Green

**Band 1 (Visual):** Uses this colormap for RGB visualization
**Band 2 (Raw):** Uses the normalized 0-255 scale (which correlates to the colormap range)

---

## COG Generation Process

### Pipeline Overview

1. **Load Grid Data** - Query PostgreSQL `climate_grid` table
2. **Compute Global Range** - Calculate min/max across all available times
3. **Progressive Rasterization** - For each zoom level (z0-z10):
   - Rasterize lat/lon/value grid to pixel image
   - Apply green colormap to create Band 1 (RGB)
   - Normalize values to 0-255 for Band 2 (grayscale)
4. **Embed Georeferencing** - Set CRS, bounds, geotransform
5. **Add Metadata Tags** - Embed VARIABLE, TIME, ZOOM_LEVEL, etc.
6. **Save COG** - Write to `/local_only/climate_mvt/{variable}/{time}/z{i}.tif`

### Generation Trigger

**Manual notebook execution** via `/notebooks/generate_climate_mvt.ipynb`:
- User selects variable and time step
- Notebook queries database, computes global ranges, generates all z0-z10 COGs
- Progress indicator shows which zoom levels are generated
- Files written to `/local_only/climate_mvt/`

### Dependencies

- `rasterio` - GeoTIFF creation and georeferencing
- `numpy` - Array operations and rasterization
- `PIL/Pillow` - Colormap application and image processing
- `psycopg2` - PostgreSQL database access
- `geopandas` - Spatial operations (optional, for grid validation)

---

## Frontend Usage (DeckGL BitmapLayer)

### Layer Instantiation

```javascript
import { BitmapLayer } from '@deck.gl/layers';

const layer = new BitmapLayer({
  id: 'climate-mvt-layer',
  image: 'http://api-server/climate-mvt/monthly_rain/1989-01/z5.tif',
  bounds: [112.85, -43.65, 154.0, -10.0],  // [left, bottom, right, top] in WGS84
  
  // Optional: Styling
  desaturate: 0,           // 0 = full color, 1 = grayscale
  tintColor: [255, 255, 255],  // RGB tint multiplier
  
  // Optional: Interactivity
  pickable: true,
  onClick: (info) => {
    if (info.bitmap) {
      console.log('Clicked pixel:', info.bitmap.pixel);
      console.log('Normalized coordinate:', info.bitmap.uv);
    }
  }
});

const deck = new DeckGL({
  container: 'map',
  initialViewState: {
    longitude: 133.5,
    latitude: -25.0,
    zoom: 5
  },
  controller: true,
  layers: [layer]
});
```

### Dynamic Zoom Level Selection

Frontend should select appropriate zoom level based on current MapView zoom:

```javascript
function selectZoomLevel(mapZoom) {
  // Map DeckGL zoom (0-20) to COG zoom level (0-10)
  // Simple heuristic: DeckGL zoom 0-20 → COG zoom 0-10
  const cogZoom = Math.floor((mapZoom / 20) * 10);
  return Math.min(Math.max(cogZoom, 0), 10);
}
```

### Reading Metadata

Frontend can read GeoTIFF metadata tags using a GeoTIFF parser:

```javascript
// Requires a GeoTIFF library like geotiff.js or gdal-wasm
const response = await fetch('http://api-server/climate-mvt/monthly_rain/1989-01/z5.tif');
const arrayBuffer = await response.arrayBuffer();
const metadata = parseGeoTIFFMetadata(arrayBuffer);

console.log(metadata.VARIABLE);      // "monthly_rain"
console.log(metadata.TIME);          // "1989-01-16"
console.log(metadata.DATA_MIN);      // 0.0
console.log(metadata.DATA_MAX);      // 450.5
console.log(metadata.COLORMAP_TYPE); // "green_scale"
```

---

## Error Handling

### Invalid Zoom Level

**Request:** `GET /climate-mvt/monthly_rain/1989-01/z15.tif`

**Response:**
```json
{
  "detail": "Invalid zoom level 15. Must be 0-10."
}
```

**Status Code:** `422 Unprocessable Entity`

### Variable Not Found

**Request:** `GET /climate-mvt/invalid_variable/1989-01/z5.tif`

**Response:**
```json
{
  "detail": "Variable 'invalid_variable' not found."
}
```

**Status Code:** `404 Not Found`

### Time Not Found

**Request:** `GET /climate-mvt/monthly_rain/1985-01/z5.tif`

**Response:**
```json
{
  "detail": "No COG found for monthly_rain at 1985-01. Available times: [...]"
}
```

**Status Code:** `404 Not Found`

### File Not Yet Generated

**Request:** `GET /climate-mvt/monthly_rain/2020-01/z5.tif` (before generation)

**Response:**
```json
{
  "detail": "COG file not yet generated for monthly_rain at 2020-01. Please generate using the notebook."
}
```

**Status Code:** `404 Not Found`

---

## Performance Considerations

### HTTP Range Requests

Cloud-Optimized GeoTIFFs support HTTP 206 range requests. Clients can fetch only the visible portion of a file:

```
GET /climate-mvt/monthly_rain/1989-01/z5.tif
Range: bytes=0-1048575

Response: 206 Partial Content
Content-Length: 1048576
```

This is especially useful for large z9-z10 files.

### Caching Strategy

- **Server side:** COG files are static; use standard HTTP caching headers
- **Client side:** Cache COGs in browser/app storage; requests are idempotent
- **CDN:** COGs can be served via CDN for global distribution

### Storage Requirements

Approximate storage per variable (all times):
- Assuming 100 time steps and Australia extent
- z0-z10 average file size per time: ~5-50MB (depending on data compression and variation)
- **Total per variable:** ~500MB - 5GB for full historical archive

---

## Development Notes for AI Agents

### Reusable Functions

- **`get_available_variables()`** - Reuse from `/app/db.py`
- **`get_available_times(variable)`** - Reuse from `/app/db.py`
- **`validate_zoom_level(zoom)`** - Check zoom is 0-10
- **`get_cog_path(variable, time, zoom_level)`** - Construct file path
- **`cog_exists(variable, time, zoom_level)`** - Check file existence

### Common Patterns

1. **Endpoint validation:** Always validate zoom_level, variable, and time
2. **Error responses:** Use HTTPException with appropriate status codes
3. **File serving:** Use FileResponse with `media_type='image/tiff'`
4. **Range requests:** FileResponse automatically handles `Range` header

### Testing the Endpoint

```bash
# Get variables
curl http://localhost:8000/climate-mvt/variables

# Get times
curl http://localhost:8000/climate-mvt/times/monthly_rain

# Download a COG
curl http://localhost:8000/climate-mvt/monthly_rain/1989-01/z5.tif > output.tif

# Test range request
curl -H "Range: bytes=0-1048575" http://localhost:8000/climate-mvt/monthly_rain/1989-01/z5.tif
```

---

## References

- **Cloud-Optimized GeoTIFF (COG):** https://www.cogeo.org/
- **GeoTIFF Specification:** https://www.ogc.org/standards/geotiff
- **DeckGL BitmapLayer:** https://deck.gl/docs/api-reference/layers/bitmap-layer
- **WGS84 (EPSG:4326):** https://epsg.io/4326
- **HTTP Range Requests (RFC 7233):** https://tools.ietf.org/html/rfc7233
