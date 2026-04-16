# Frontend Migration Guide: Multi-Dataset API

## Context for AI

This document instructs you on how to update the frontend to support a new multi-dataset API.
The backend has two parallel systems:

1. **Legacy system** (`/climate`, `/climate-mvt`) — single dataset, `climate_grid` table. **Do not remove. Keep working.**
2. **New system** (`/climate-gt` — not yet implemented, API endpoints TBD) — multi-dataset, `climate_gt` + `datasets` tables.

The new system introduces a `dataset_id` (UUID) concept. Every data request is scoped to a specific dataset.
COG files are stored at `local_only/climate_gt/{dataset_id}/{variable}/{time}/z{zoom}.tif`.

---

## New Backend Data Model

### Dataset object
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "rainfall_1989",
  "filename": "1989.monthly_rain.nc",
  "created_at": "2026-04-16T12:00:00",
  "metadata": {
    "variable": "monthly_rain",
    "time_steps": 12,
    "total_rows": 843200
  }
}
```

### COG file path pattern (server-side)
```
local_only/climate_gt/{dataset_id}/{variable}/{time}/z{0-5}.tif
```

---

## New API Endpoints (to be implemented — `/climate-gt` prefix)

These endpoints do not exist yet. When the backend team adds them, this is their shape.
Build the frontend against these contracts.

### 1. List all datasets
```
GET /climate-gt/datasets
```
Response:
```json
{
  "datasets": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "rainfall_1989",
      "filename": "1989.monthly_rain.nc",
      "created_at": "2026-04-16T12:00:00",
      "metadata": { "variable": "monthly_rain", "time_steps": 12, "total_rows": 843200 }
    }
  ]
}
```

### 2. Get dataset detail
```
GET /climate-gt/datasets/{dataset_id}
```
Response: single dataset object (same shape as above).

### 3. List variables for a dataset
```
GET /climate-gt/variables?dataset_id={uuid}
```
Response:
```json
{ "dataset_id": "550e8400-...", "variables": ["monthly_rain"] }
```

### 4. List times for a variable in a dataset
```
GET /climate-gt/times/{variable}?dataset_id={uuid}
```
Response:
```json
{ "dataset_id": "550e8400-...", "variable": "monthly_rain", "times": ["1989-01-16", "1989-02-15"] }
```

### 5. Serve COG (GeoTIFF)
```
GET /climate-gt/{variable}/{time}/z{zoom}.tif?dataset_id={uuid}
GET /climate-gt/{variable}/{time}/z{zoom}.tif?dataset_id={uuid}&colormap=viridis
GET /climate-gt/{variable}/{time}/z{zoom}.tif?dataset_id={uuid}&colormap=RdBu&stretch=sqrt
```
- `dataset_id` (required): UUID of the dataset
- `colormap` (optional): matplotlib colormap name — dynamically recolors RGB bands from Band 4
- `stretch` (optional): `linear` | `sqrt` | `cbrt` | `log` | `gamma_low` | `gamma_high` | `equalize`
- Returns: `image/tiff` binary — Web Mercator (EPSG:3857), 5-band COG

Band structure (same as legacy):
- Band 1-3: RGB (colormap applied)
- Band 4: Grayscale raw data (normalized 0-255)
- Band 5: Alpha (255=valid, 0=transparent)

### 6. List colormaps & stretches
```
GET /climate-gt/colormaps
```
Response: same shape as `GET /climate-mvt/colormaps`.

### 7. Raw grid data (JSON, no COG)
```
GET /climate-gt/grid/{variable}/{time}?dataset_id={uuid}
GET /climate-gt/grid/{variable}/{time}?dataset_id={uuid}&min_lat=...&max_lat=...&min_lon=...&max_lon=...
```
Response: same shape as `GET /climate/grid/{variable}/{time}`.

---

## Legacy Endpoints (unchanged — keep all existing calls working)

| Endpoint | Notes |
|---|---|
| `GET /climate/variables` | No dataset scoping |
| `GET /climate/times/{variable}` | No dataset scoping |
| `GET /climate/grid/{variable}/{time}` | No dataset scoping |
| `GET /climate-mvt/variables` | No dataset scoping |
| `GET /climate-mvt/times/{variable}` | No dataset scoping |
| `GET /climate-mvt/colormaps` | Unchanged |
| `GET /climate-mvt/{variable}/{time}/z{zoom}.tif` | No dataset scoping |

---

## Frontend Implementation Tasks

### Phase 1 — Dataset selector UI
1. On app load, call `GET /climate-gt/datasets` and store the list in state.
2. Render a dataset selector component (dropdown or list) showing `dataset.name` as label and `dataset.id` as value.
3. When user selects a dataset, store `selectedDatasetId` in state.
4. Clear selected variable and time when dataset changes.

### Phase 2 — Variable & time selectors (dataset-scoped)
1. When `selectedDatasetId` is set, call `GET /climate-gt/variables?dataset_id={selectedDatasetId}`.
2. Populate variable selector from response.
3. When variable is selected, call `GET /climate-gt/times/{variable}?dataset_id={selectedDatasetId}`.
4. Populate time slider/selector from response.

### Phase 3 — COG layer (dataset-scoped)
1. Build COG URL:
   ```
   /climate-gt/{variable}/{time}/z{zoom}.tif?dataset_id={selectedDatasetId}
   ```
   Optionally append `&colormap={colormap}&stretch={stretch}`.
2. Pass URL to DeckGL `BitmapLayer` (same usage as legacy `/climate-mvt/` COG URL).
3. The GeoTIFF is Web Mercator (EPSG:3857) — same projection as legacy. No changes needed to the layer render logic.

### Phase 4 — Colormap & stretch controls
1. Call `GET /climate-gt/colormaps` once on load (or reuse `GET /climate-mvt/colormaps` — identical response shape).
2. Render colormap picker and stretch selector.
3. Append `?colormap=...&stretch=...` to the COG URL when set.

---

## Key Differences: Legacy vs New

| | Legacy | New |
|---|---|---|
| Dataset concept | None (single implicit dataset) | Explicit UUID per dataset |
| URL prefix | `/climate`, `/climate-mvt` | `/climate-gt` |
| `dataset_id` param | Not present | Required query param |
| COG path | `climate_mvt/{var}/{time}/z{n}.tif` | `climate_gt/{uuid}/{var}/{time}/z{n}.tif` |
| DB table | `climate_grid` | `climate_gt` |
| Multiple files | No | Yes |

---

## State Shape (suggested)

```ts
interface DatasetState {
  datasets: Dataset[];
  selectedDatasetId: string | null;
  variables: string[];
  selectedVariable: string | null;
  times: string[];
  selectedTime: string | null;
  colormap: string | null;
  stretch: string | null;
}

interface Dataset {
  id: string;
  name: string;
  filename: string;
  created_at: string;
  metadata: {
    variable: string;
    time_steps: number;
    total_rows: number;
  } | null;
}
```

---

## COG URL Builder (reference)

```ts
function buildCogUrl(
  baseUrl: string,
  datasetId: string,
  variable: string,
  time: string,
  zoom: number,
  colormap?: string,
  stretch?: string
): string {
  const params = new URLSearchParams({ dataset_id: datasetId });
  if (colormap) params.set("colormap", colormap);
  if (stretch) params.set("stretch", stretch);
  return `${baseUrl}/climate-gt/${variable}/${time}/z${zoom}.tif?${params}`;
}
```

---

## Notes

- All legacy `/climate` and `/climate-mvt` code paths must remain intact. The new UI is additive.
- `dataset_id` is always a UUID string (e.g. `"550e8400-e29b-41d4-a716-446655440000"`).
- COG zoom levels: 0 (256×256) → 5 (8192×8192). Match zoom level to viewport zoom for performance.
- COG projection: Web Mercator EPSG:3857. Bounds cover Australia (112.9°E–153.65°E, 43.65°S–10.05°S).
- Backend API (`/climate-gt`) is not yet implemented. Coordinate with backend before building Phase 2+.
