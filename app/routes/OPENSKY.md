# OpenSky API — Frontend Integration Guide

Base URL: `http://localhost:8000`

---

## Endpoints

### 1. List Ingestion Requests

```
GET /opensky/requests
```

Returns all OpenSky ingestion runs, ordered by most recent first. Each entry
includes `time_ts_count` — the number of distinct minute-level snapshots stored
for that request. Use this to know which timestamps are available before querying
states.

#### Response

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "date": "2026-04-20",
    "hour": 0,
    "minute": 1,
    "window_start_ts": 1776643260,
    "created_at": "2026-04-20T00:31:05.123456",
    "time_ts_count": 30
  }
]
```

#### Field Reference

| Field | Type | Description |
|---|---|---|
| `id` | `string (UUID)` | Unique identifier for the ingestion run |
| `date` | `string (YYYY-MM-DD)` | UTC date of the window start |
| `hour` | `integer` | UTC hour of the window start (0–23) |
| `minute` | `integer` | UTC minute of the window start (0–59) |
| `window_start_ts` | `integer` | Unix timestamp of the first snapshot in the window |
| `created_at` | `string (ISO 8601)` | When the ingestion run was registered |
| `time_ts_count` | `integer` | Number of distinct minute snapshots available for this request |

---

### 2. Get State Vectors for a Snapshot

```
GET /opensky/states/{request_id}/{time_ts}
```

Returns all aircraft state vectors for a specific ingestion request and minute
snapshot. Use the `id` from `/opensky/requests` as `request_id`, and any Unix
timestamp within that request's window as `time_ts`.

To enumerate all available `time_ts` values for a request, compute them from
`window_start_ts`:

```js
const timestamps = Array.from({ length: time_ts_count }, (_, i) =>
  window_start_ts + i * 60
);
```

#### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `request_id` | `string (UUID)` | The `id` of the ingestion request |
| `time_ts` | `integer` | Unix timestamp of the snapshot minute to fetch |

#### Response

```json
[
  {
    "time_ts": 1776643260,
    "icao24": "a12345",
    "callsign": "UAL123",
    "lat": 40.7128,
    "lon": -74.006,
    "velocity": 245.3,
    "heading": 92.1,
    "vertrate": -0.33,
    "baro_altitude": 10972.8,
    "geo_altitude": 11010.2,
    "on_ground": false,
    "squawk": "1200"
  }
]
```

#### Field Reference

| Field | Type | Description |
|---|---|---|
| `time_ts` | `integer` | Unix timestamp of this snapshot |
| `icao24` | `string \| null` | ICAO 24-bit hex address of the aircraft |
| `callsign` | `string \| null` | Aircraft callsign (may be empty) |
| `lat` | `number \| null` | Latitude in decimal degrees (WGS84), extracted from PostGIS `GEOMETRY(Point, 4326)` |
| `lon` | `number \| null` | Longitude in decimal degrees (WGS84), extracted from PostGIS `GEOMETRY(Point, 4326)` |
| `velocity` | `number \| null` | Ground speed in m/s |
| `heading` | `number \| null` | True track angle in degrees (0–360, clockwise from north) |
| `vertrate` | `number \| null` | Vertical rate in m/s (positive = climbing) |
| `baro_altitude` | `number \| null` | Barometric altitude in metres |
| `geo_altitude` | `number \| null` | Geometric (GPS) altitude in metres |
| `on_ground` | `boolean \| null` | `true` if the aircraft is on the ground |
| `squawk` | `string \| null` | Transponder squawk code |

#### Error Responses

| Status | Condition |
|---|---|
| `404` | No states found for the given `request_id` + `time_ts` combination |

---

### 3. Get Trips for deck.gl TripsLayer

```
GET /opensky/trips/{request_id}?include_ground=false
```

Returns all aircraft trajectories for a given request, pre-formatted for the
[deck.gl TripsLayer](https://deck.gl/docs/api-reference/geo-layers/trips-layer).
Each trip represents one aircraft's path across all 30 minute snapshots.

#### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `request_id` | `string (UUID)` | The `id` of the ingestion request |

#### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `include_ground` | `boolean` | `false` | Set to `true` to include on-ground aircraft |

#### Timestamp Convention

`timestamp` in each waypoint is **seconds offset from `window_start_ts`** — not
a raw Unix epoch value. This keeps values small and float32-safe, which is
required by the TripsLayer.

The full window spans `0` to `(time_ts_count - 1) * 60` seconds. Use this to
set `currentTime` and `trailLength` in the layer:

```js
// currentTime animates from 0 to maxTime
const maxTime = (time_ts_count - 1) * 60;  // e.g. 1740 for 30 snapshots
const trailLength = 60;                      // show 1 minute of trail

new TripsLayer({
  data: trips,
  getPath: d => d.waypoints.map(p => p.coordinates),
  getTimestamps: d => d.waypoints.map(p => p.timestamp),
  currentTime: currentTime,   // animated 0 → maxTime
  trailLength: trailLength,
});
```

#### Filters Applied Server-Side

- Aircraft with no valid coordinates in any snapshot → excluded
- Aircraft with fewer than 2 valid waypoints → excluded
- On-ground aircraft → excluded by default (`?include_ground=true` to include)
- Individual null-coordinate waypoints within a trip → skipped silently

#### Response

```json
[
  {
    "icao24": "a12345",
    "callsign": "UAL123",
    "waypoints": [
      { "coordinates": [-74.006, 40.7128, 10972.8], "timestamp": 0.0 },
      { "coordinates": [-73.891, 40.821,  11003.4], "timestamp": 60.0 },
      { "coordinates": [-73.774, 40.931,  10988.1], "timestamp": 120.0 }
    ]
  }
]
```

#### Field Reference

| Field | Type | Description |
|---|---|---|
| `icao24` | `string` | ICAO 24-bit hex address of the aircraft |
| `callsign` | `string \| null` | Aircraft callsign (trimmed, may be null) |
| `waypoints` | `array` | Ordered list of position + time entries |
| `waypoints[].coordinates` | `[lon, lat, alt]` | WGS84 longitude, latitude, and barometric altitude in metres (deck.gl order). Altitude defaults to `0` if null. |
| `waypoints[].timestamp` | `number` | Seconds offset from `window_start_ts` (float32-safe) |

#### Error Responses

| Status | Condition |
|---|---|
| `404` | `request_id` does not exist |
| `404` | `request_id` exists but no qualifying trips found |

---

## Typical Usage Flow

```
1. GET /opensky/requests
   → Pick a request by date/time. Note its `id`, `window_start_ts`, and `time_ts_count`.

2. GET /opensky/trips/{id}
   → Feed directly into deck.gl TripsLayer. Animate currentTime from 0 to
     (time_ts_count - 1) * 60 seconds.

3. (Optional) GET /opensky/states/{id}/{window_start_ts + n * 60}
   → Fetch a single snapshot for non-animated views or tooltips.
```
