"""Database connection and utilities for the FastAPI app."""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional

# Database connection parameters
DB_PARAMS = {
    "host": "localhost",
    "user": "leon",
    "password": "leon",
    "database": "oc-database",
    "port": 5432,
}


def get_db_connection():
    """Get a new database connection."""
    return psycopg2.connect(**DB_PARAMS)


@contextmanager
def get_db_cursor():
    """Context manager for database cursor. Automatically commits on success, rolls back on error."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_grid_data(
    variable: str,
    time: str,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
) -> dict:
    """
    Retrieve grid data from the climate_grid table.

    Returns columnar arrays:
    {
        "lats": [lat1, lat2, ...],
        "lons": [lon1, lon2, ...],
        "values": [value1, value2, ...]
    }

    Args:
        variable: Variable name (e.g. "monthly_rain")
        time: ISO time string (e.g. "1989-06")
        min_lat, max_lat, min_lon, max_lon: Optional bounding box filters

    Returns:
        Dictionary with columnar arrays {lats, lons, values}
    """

    with get_db_cursor() as cur:
        # Build the query
        query = """
            SELECT lat, lon, value
            FROM climate_grid
            WHERE variable = %s AND time::text LIKE %s
        """
        params = [variable, f"{time}%"]  # LIKE allows partial time matching

        # Add optional bounding box filters
        if min_lat is not None:
            query += " AND lat >= %s"
            params.append(min_lat)
        if max_lat is not None:
            query += " AND lat <= %s"
            params.append(max_lat)
        if min_lon is not None:
            query += " AND lon >= %s"
            params.append(min_lon)
        if max_lon is not None:
            query += " AND lon <= %s"
            params.append(max_lon)

        query += " ORDER BY lat, lon"

        cur.execute(query, params)
        rows = cur.fetchall()

        # Convert to columnar format
        lats = [row["lat"] for row in rows]
        lons = [row["lon"] for row in rows]
        values = [row["value"] for row in rows]

        return {"lats": lats, "lons": lons, "values": values, "count": len(rows)}


def get_available_times(variable: str) -> list:
    """Get all unique time steps for a given variable."""

    with get_db_cursor() as cur:
        cur.execute(
            """SELECT DISTINCT time FROM climate_grid
               WHERE variable = %s
               ORDER BY time""",
            [variable],
        )
        times = [row["time"] for row in cur.fetchall()]
        return times


def get_available_variables() -> list:
    """Get all unique variables in the database."""

    with get_db_cursor() as cur:
        cur.execute(
            """SELECT DISTINCT variable FROM climate_grid
               ORDER BY variable"""
        )
        variables = [row["variable"] for row in cur.fetchall()]
        return variables


def get_opensky_requests() -> list:
    """
    Retrieve all OpenSky ingestion requests, each annotated with the count of
    distinct time_ts snapshots stored in opensky_states for that request.

    Returns a list of dicts with keys:
        id, date, hour, minute, window_start_ts, created_at, time_ts_count
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                r.id,
                r.date,
                r.hour,
                r.minute,
                r.window_start_ts,
                r.created_at,
                COUNT(DISTINCT s.time_ts) AS time_ts_count
            FROM opensky_requests r
            LEFT JOIN opensky_states s ON s.request_id = r.id
            GROUP BY r.id, r.date, r.hour, r.minute, r.window_start_ts, r.created_at
            ORDER BY r.created_at DESC
            """
        )
        return [dict(row) for row in cur.fetchall()]


def get_opensky_states(request_id: str, time_ts: int) -> list:
    """
    Retrieve all state vectors for a given request_id and time_ts snapshot.

    Returns a list of dicts with keys:
        time_ts, icao24, callsign, lat, lon, velocity, heading,
        vertrate, baro_altitude, geo_altitude, on_ground, squawk

    Returns an empty list if no rows match.
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                time_ts, icao24, callsign,
                ST_Y(geom) AS lat,
                ST_X(geom) AS lon,
                velocity, heading, vertrate,
                baro_altitude, geo_altitude,
                on_ground, squawk
            FROM opensky_states
            WHERE request_id = %s AND time_ts = %s
            ORDER BY icao24
            """,
            [request_id, time_ts],
        )
        return [dict(row) for row in cur.fetchall()]


def get_opensky_trips(request_id: str, include_ground: bool = False) -> list:
    """
    Retrieve all aircraft trips for a given request, formatted for deck.gl TripsLayer.

    Each trip is one aircraft's trajectory across all snapshots in the window.
    Timestamps are seconds offset from window_start_ts (float32-safe).

    Filters applied:
    - Aircraft with no valid geometry in any snapshot are excluded.
    - Aircraft with fewer than 2 valid waypoints are excluded.
    - On-ground aircraft are excluded unless include_ground=True.
    - Individual waypoints with null geometry are skipped (gap in path).

    Returns a list of dicts with keys:
        icao24, callsign, waypoints: [{coordinates: [lon, lat], timestamp: float}]

    Returns None if request_id does not exist (signals 404 to the caller).
    """
    with get_db_cursor() as cur:
        # Fetch window_start_ts for the request to compute relative timestamps
        cur.execute(
            "SELECT window_start_ts FROM opensky_requests WHERE id = %s",
            [request_id],
        )
        row = cur.fetchone()
        if row is None:
            return None  # signals 404 to the caller

        window_start_ts = row["window_start_ts"]

        ground_filter = (
            "" if include_ground else "AND (s.on_ground = false OR s.on_ground IS NULL)"
        )

        cur.execute(
            f"""
            SELECT
                s.icao24,
                MAX(s.callsign) AS callsign,
                array_agg(
                    ARRAY[ST_X(s.geom), ST_Y(s.geom), COALESCE(s.baro_altitude, 0), (s.time_ts - %s)::float]
                    ORDER BY s.time_ts
                ) FILTER (WHERE s.geom IS NOT NULL) AS waypoints
            FROM opensky_states s
            WHERE s.request_id = %s
              AND s.geom IS NOT NULL
              {ground_filter}
            GROUP BY s.icao24
            HAVING COUNT(s.geom) >= 2
            ORDER BY s.icao24
            """,
            [window_start_ts, request_id],
        )

        trips = []
        for row in cur.fetchall():
            waypoints = [
                {"coordinates": [wp[0], wp[1], wp[2]], "timestamp": wp[3]}
                for wp in row["waypoints"]
            ]
            trips.append(
                {
                    "icao24": row["icao24"],
                    "callsign": row["callsign"].strip() if row["callsign"] else None,
                    "waypoints": waypoints,
                }
            )

        return trips
