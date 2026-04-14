# Climate API Documentation

This document provides instructions for agents (and humans) to integrate with the Climate API endpoints. The API serves gridded climate data (e.g., monthly rainfall) for visualization on DeckGL heatmap layers.

**Base URL:** `http://localhost:8000/climate` (or your deployment URL)

---

## Quick Start

Get grid data for a climate variable in 3 TypeScript calls:

```typescript
// Step 1: Discover available variables
const varsRes = await fetch('http://localhost:8000/climate/variables');
const { variables } = await varsRes.json();
const variable = variables[0]; // e.g., "monthly_rain"

// Step 2: Discover available times for that variable
const timesRes = await fetch(`http://localhost:8000/climate/times/${variable}`);
const { times } = await timesRes.json();
const time = times[0]; // e.g., "1989-01-16 12:00:00"

// Step 3: Fetch grid data
const gridRes = await fetch(
  `http://localhost:8000/climate/grid/${variable}/${time}`
);
const gridData = await gridRes.json();
console.log(gridData); // Ready for DeckGL
```

**Result:** `gridData` contains columnar arrays (`lats`, `lons`, `values`) optimized for rendering.

---

## Full Workflow: Discovery → Query

The Climate API follows a discovery-first pattern. Always call discovery endpoints before querying grid data.

### Step 1: Discover Available Variables

**Endpoint:** `GET /climate/variables`

**Purpose:** Retrieve all available climate variables in the database. Always call this first to know what you can request.

**Request:**
```typescript
const response = await fetch('http://localhost:8000/climate/variables');
const data = await response.json();
```

**Response Schema:**
```json
{
  "variables": ["string"]
}
```

**Example Response:**
```json
{
  "variables": ["monthly_rain"]
}
```

**Notes:**
- No parameters required
- Returns an array of variable names (strings)
- Use one of these names in subsequent endpoint calls
- If the array is empty, no data has been ingested yet

---

### Step 2: Discover Available Times for a Variable

**Endpoint:** `GET /climate/times/{variable}`

**Purpose:** Retrieve all available time steps for a specific variable. This tells you what dates/times you can query.

**Parameters:**
- `variable` (path, required): Variable name from Step 1 (e.g., `monthly_rain`)

**Request:**
```typescript
const variable = 'monthly_rain'; // From Step 1

const response = await fetch(
  `http://localhost:8000/climate/times/${variable}`
);
const data = await response.json();
```

**Response Schema:**
```json
{
  "variable": "string",
  "times": ["string"]
}
```

**Example Response:**
```json
{
  "variable": "monthly_rain",
  "times": [
    "1989-01-16 12:00:00",
    "1989-02-15 00:00:00",
    "1989-03-16 12:00:00"
  ]
}
```

**Notes:**
- Returns an array of ISO-formatted timestamp strings
- Each entry represents a time step in the dataset
- Use one of these time strings in the grid data endpoint
- Times are sorted chronologically

---

### Step 3: Fetch Grid Data for a Time Step

**Endpoint:** `GET /climate/grid/{variable}/{time}`

**Purpose:** Retrieve gridded climate data for a specific variable and time step. Returns columnar arrays optimized for DeckGL rendering.

**Parameters:**
- `variable` (path, required): Variable name (e.g., `monthly_rain`)
- `time` (path, required): Time string (e.g., `1989-01` or full timestamp). Supports partial ISO matching.
- `min_lat` (query, optional): Minimum latitude for bounding box filter
- `max_lat` (query, optional): Maximum latitude for bounding box filter
- `min_lon` (query, optional): Minimum longitude for bounding box filter
- `max_lon` (query, optional): Maximum longitude for bounding box filter

**Request (Full Grid):**
```typescript
const variable = 'monthly_rain';
const time = '1989-01'; // Partial ISO string, API finds nearest match

const response = await fetch(
  `http://localhost:8000/climate/grid/${variable}/${time}`
);
const data = await response.json();
```

**Request (With Bounding Box):**
```typescript
const variable = 'monthly_rain';
const time = '1989-01';

// Filter to Queensland region (latitude -28 to -20, longitude 140 to 155)
const params = new URLSearchParams({
  min_lat: '-28',
  max_lat: '-20',
  min_lon: '140',
  max_lon: '155'
});

const response = await fetch(
  `http://localhost:8000/climate/grid/${variable}/${time}?${params}`
);
const data = await response.json();
```

**Response Schema:**
```json
{
  "variable": "string",
  "time": "string",
  "bbox": {
    "min_lat": "number | null",
    "max_lat": "number | null",
    "min_lon": "number | null",
    "max_lon": "number | null"
  },
  "data": {
    "lats": [number],
    "lons": [number],
    "values": [number],
    "count": number
  }
}
```

**Example Response (Partial):**
```json
{
  "variable": "monthly_rain",
  "time": "1989-01",
  "bbox": {
    "min_lat": null,
    "max_lat": null,
    "min_lon": null,
    "max_lon": null
  },
  "data": {
    "lats": [-43.65, -43.6, -43.6, -43.6, ...],
    "lons": [146.85, 146.65, 146.7, 146.75, ...],
    "values": [88.9, 86.6, 91.1, 92.3, ...],
    "count": 281963
  }
}
```

**Notes:**
- Arrays are parallel: `lats[i]`, `lons[i]`, and `values[i]` form a single data point
- `count` is the total number of points returned
- Each `value` is in the units specified by the variable (e.g., mm for monthly_rain)
- NaN/missing values are filtered out (only valid data is returned)
- Bounding box filters reduce payload size for frontend rendering
- Time parameter supports partial ISO strings: `"1989"`, `"1989-01"`, `"1989-01-16"` all work

**For DeckGL Usage:**
```typescript
// Transform response into DeckGL HeatmapLayer positions/weights
const { data } = gridResponse;

const positions = data.lats.map((lat, i) => [data.lons[i], lat, data.values[i]]);

const layer = new HeatmapLayer({
  data: positions,
  getPosition: (d) => [d[0], d[1]],
  getWeight: (d) => d[2],
  radiusPixels: 20
});
```

---

## Time String Formats

The API accepts flexible time strings due to partial ISO matching. All of these work:

```typescript
// Full timestamp
'1989-01-16T12:00:00'

// Date only
'1989-01-16'

// Year-month
'1989-01'

// Year only
'1989'
```

The API automatically finds the **nearest time step** in the dataset. If you request `1989-01-15` but the closest data is `1989-01-16`, you get `1989-01-16`.

---

## Coordinate System

- **Latitude:** Decimal degrees, range -90 to 90 (south to north)
- **Longitude:** Decimal degrees, range -180 to 180 (west to east)

For Queensland, Australia:
- Latitude: -28 to -10
- Longitude: 112 to 154

---

## Agent Implementation Checklist

When implementing this API in an agent:

- [ ] **Always call `/climate/variables` first** to discover available data
- [ ] **Always call `/climate/times/{variable}` before querying grid data** to know what times exist
- [ ] **Use time strings for querying, not indices** — let the API handle the matching
- [ ] **Include bounding box parameters when possible** to reduce payload size and improve frontend performance
- [ ] **Check the `count` field in responses** to verify data was actually returned (non-zero count)
- [ ] **Assume the API returns valid data** — all values are non-NaN, all coordinates are within bounds
- [ ] **Cache discovered variables and times** to avoid repeated API calls for discovery
- [ ] **Parse response arrays in parallel** — index into all three arrays (`lats`, `lons`, `values`) using the same index `i`

---

## Example: Complete Agent Workflow

This example shows a complete TypeScript workflow for an agent to fetch and display climate data:

```typescript
/**
 * Fetch and prepare climate data for DeckGL visualization
 * 
 * This workflow:
 * 1. Discovers available variables
 * 2. Discovers available times for the first variable
 * 3. Fetches grid data for the first time step
 * 4. Returns data ready for DeckGL
 */
async function fetchClimateDataForDeckGL(
  baseURL: string = 'http://localhost:8000/climate'
): Promise<{
  variable: string;
  time: string;
  positions: [number, number, number][]; // [lon, lat, value]
  count: number;
}> {
  // Step 1: Discover variables
  const varsRes = await fetch(`${baseURL}/variables`);
  const { variables } = await varsRes.json();
  
  if (variables.length === 0) {
    throw new Error('No climate variables available in database');
  }
  
  const variable = variables[0];
  console.log(`Selected variable: ${variable}`);

  // Step 2: Discover times for this variable
  const timesRes = await fetch(`${baseURL}/times/${variable}`);
  const { times } = await timesRes.json();
  
  if (times.length === 0) {
    throw new Error(`No time steps available for variable: ${variable}`);
  }
  
  const time = times[0];
  console.log(`Selected time: ${time}`);

  // Step 3: Fetch grid data (with bounding box for Queensland)
  const gridRes = await fetch(
    `${baseURL}/grid/${variable}/${time}?` +
    `min_lat=-28&max_lat=-20&min_lon=140&max_lon=155`
  );
  const gridData = await gridRes.json();
  
  console.log(`Fetched ${gridData.data.count} data points`);

  // Step 4: Transform to DeckGL format
  const { lats, lons, values } = gridData.data;
  const positions = lats.map((lat, i) => [lons[i], lat, values[i]]);

  return {
    variable,
    time,
    positions,
    count: gridData.data.count
  };
}

// Usage
const climateData = await fetchClimateDataForDeckGL();

// Now use climateData.positions with DeckGL:
// const layer = new HeatmapLayer({
//   data: climateData.positions,
//   getPosition: (d) => [d[0], d[1]],
//   getWeight: (d) => d[2]
// });
```

---

## HTTP Status Codes

- **200 OK** — Request succeeded, data returned
- **404 Not Found** — Variable doesn't exist, no data for requested time
- **500 Internal Server Error** — Server error (database connection issue, etc.)

---

## Data Format Notes

**Columnar Format:**
The API returns data in columnar format (separate arrays for lats, lons, values) rather than rows. This is more efficient for:
- Network transmission (smaller JSON payload)
- GPU rendering (DeckGL can consume directly)
- Parallel processing (arrays are easier to vectorize)

**NaN Handling:**
Missing or invalid values are filtered out on the server. If a grid cell has no data, it's excluded from the response entirely. This means the response may have fewer points than the original grid size.

**Coordinate Precision:**
- Latitude/Longitude: float64 precision (~10 decimal places = 1mm accuracy)
- Values: float64 precision (sufficient for most climate measurements)

---

## Troubleshooting

**"Variable not found" errors:**
- Always call `/climate/variables` first to get valid variable names
- Don't guess variable names

**"No time steps available" errors:**
- The variable exists but has no data ingested yet
- Run the ingestion notebook (`notebooks/netcdf_ingestion.ipynb`) to load data

**Empty results (count = 0):**
- Your bounding box may not intersect with the data grid
- Try removing bbox parameters to get the full grid
- Data covers Australia; check your coordinates are within expected range

**Timeout errors:**
- The API is fetching a large grid (300K+ points)
- Use bounding box parameters to reduce payload
- Consider client-side decimation/downsampling for visualization

---

## API Evolution

As the Climate API grows:
- New variables will appear in `/climate/variables`
- New time steps will appear in `/climate/times/{variable}`
- Grid structure stays consistent (always columnar format)

Your agent should handle new variables and times gracefully without code changes.
