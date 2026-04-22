"""OpenSky API routes."""

from fastapi import APIRouter, HTTPException, Query

from app.db import get_opensky_requests, get_opensky_states, get_opensky_trips

router = APIRouter(prefix="/opensky", tags=["opensky"])


@router.get("/requests")
def list_opensky_requests():
    """
    Return all OpenSky ingestion requests, ordered by most recent first.

    Each entry includes a `time_ts_count` — the number of distinct minute
    snapshots stored for that request — so the frontend knows which timestamps
    are available to query.
    """
    return get_opensky_requests()


@router.get("/states/{request_id}/{time_ts}")
def get_states(request_id: str, time_ts: int):
    """
    Return all aircraft state vectors for a given request and timestamp.

    - `request_id`: UUID of the ingestion run (from `/opensky/requests`)
    - `time_ts`: Unix timestamp of the snapshot (one of the minute-level
      timestamps stored for that request)

    Raises 404 if no states are found for the given combination.
    """
    states = get_opensky_states(request_id, time_ts)

    if not states:
        raise HTTPException(
            status_code=404,
            detail=f"No states found for request_id={request_id} and time_ts={time_ts}.",
        )

    return states


@router.get("/trips/{request_id}")
def get_trips(
    request_id: str,
    include_ground: bool = Query(
        False, description="Include on-ground aircraft in the response."
    ),
):
    """
    Return all aircraft trips for a given request, formatted for deck.gl TripsLayer.

    Each trip contains the aircraft's `icao24`, `callsign`, and a `waypoints` array
    of `{coordinates: [lon, lat], timestamp}` objects where `timestamp` is seconds
    offset from `window_start_ts` (float32-safe for deck.gl).

    Filters:
    - Aircraft with no valid coordinates are excluded.
    - Aircraft with fewer than 2 valid waypoints are excluded.
    - On-ground aircraft are excluded by default (`?include_ground=true` to include).
    - Individual null-geometry waypoints within a trip are skipped.

    Raises 404 if the request_id does not exist.
    """
    trips = get_opensky_trips(request_id, include_ground=include_ground)

    if trips is None:
        raise HTTPException(
            status_code=404,
            detail=f"No request found for request_id={request_id}.",
        )

    if not trips:
        raise HTTPException(
            status_code=404,
            detail=f"No qualifying trips found for request_id={request_id}.",
        )

    return trips
