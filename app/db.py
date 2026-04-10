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
