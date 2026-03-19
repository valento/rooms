"""
routers/toto2.py
----------------
FastAPI router for TOTO2 endpoints.
Mount in your main app with:
    from routers.toto2 import router as toto2_router
    app.include_router(toto2_router)
"""

from fastapi import APIRouter, HTTPException
from schemas.toto2 import (
    Toto2ImportPayload,
    Toto2ImportResult,
    Toto2DrawRead,
)
from services.toto2_importer import import_draws
from services.toto2_stats import rebuild_stats, get_total_draws
from services.database import execute_query

router = APIRouter(prefix="/toto2", tags=["toto2"])


# ---------------------------------------------------------------------------
# POST /toto2/import
# ---------------------------------------------------------------------------
@router.post("/import", response_model=Toto2ImportResult)
def import_toto2(payload: Toto2ImportPayload):
    """
    Bulk import TOTO2 draws from a converted JSON payload.

    - Validates all rows via Pydantic before touching the DB
    - Skips duplicates unless overwrite=true
    - Returns a summary: inserted / skipped / overwritten / errors
    """
    if not payload.rows:
        raise HTTPException(status_code=400, detail="Payload contains no rows")

    result = import_draws(payload)

    if result.errors:
        # Partial success — still return 200 with the error list
        # so the client knows exactly which rows failed
        return result

    return result


# ---------------------------------------------------------------------------
# GET /toto2/draws
# ---------------------------------------------------------------------------
@router.get("/draws", response_model=list[Toto2DrawRead])
def get_draws(
    year:  int | None = None,
    limit: int        = 50,
    offset: int       = 0,
):
    """
    Fetch draws, optionally filtered by year.
    Ordered chronologically (year ASC, issue ASC, draw_index ASC).
    """
    if year:
        rows = execute_query(
            """
            SELECT * FROM toto2.draws
            WHERE year = %s
            ORDER BY year ASC, issue ASC, draw_index ASC
            LIMIT %s OFFSET %s
            """,
            (year, limit, offset),
        )
    else:
        rows = execute_query(
            """
            SELECT * FROM toto2.draws
            ORDER BY year ASC, issue ASC, draw_index ASC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

    return [Toto2DrawRead(**row) for row in (rows or [])]


# ---------------------------------------------------------------------------
# GET /toto2/draws/count
# ---------------------------------------------------------------------------
@router.get("/draws/count")
def get_draws_count(year: int | None = None):
    """Total number of draws stored, optionally filtered by year."""
    if year:
        result = execute_query(
            "SELECT COUNT(*) AS total FROM toto2.draws WHERE year = %s",
            (year,),
        )
    else:
        result = execute_query(
            "SELECT COUNT(*) AS total FROM toto2.draws",
        )

    return {"total": result[0]["total"] if result else 0}


# ---------------------------------------------------------------------------
# GET /toto2/stats/frequency
# ---------------------------------------------------------------------------
@router.get("/stats/frequency")
def get_frequency(
    year_from: int | None = None,
    year_to:   int | None = None,
):
    """
    Return all 49 numbers sorted by frequency descending.
    Optionally filtered by year range (year_from..year_to).

    If no range given → full history.
    The UI slider maps directly to these two query params.

    Example:
        GET /toto2/stats/frequency?year_from=2023&year_to=2025
    """
    from services.toto2_stats import compute_frequency, get_year_bounds

    freq  = compute_frequency(year_from=year_from, year_to=year_to)
    min_year, max_year = get_year_bounds()
    yf = year_from  or min_year
    yt = year_to    or max_year
    total_draws = get_total_draws(yf, yt)

    return {
        "year_from":    yf,
        "year_to":      yt,
        "total_draws":  total_draws,
        "numbers": [
            {"number": num, "frequency": count}
            for num, count in sorted(freq.items(), key=lambda x: -x[1])
        ]
    }


# ---------------------------------------------------------------------------
# POST /toto2/stats/rebuild
# ---------------------------------------------------------------------------
@router.post("/stats/rebuild")
def trigger_rebuild():
    """Manually trigger a stats rebuild (e.g. after fixing imported data)."""
    rebuild_stats()
    return {"status": "ok", "message": "Stats rebuilt successfully"}


# ---------------------------------------------------------------------------
# GET /toto2/stats/absence
# ---------------------------------------------------------------------------
@router.get("/stats/absence")
def get_absence():
    """
    Return all 49 numbers sorted by absence streak descending.
    Numbers missing from the most recent consecutive draws appear first.
    """
    result = execute_query(
        """
        SELECT number, absence_streak, frequency, updated_at
        FROM toto2.number_stats
        ORDER BY absence_streak DESC, number ASC
        """
    )
    return result or []


@router.get("/stats/number/{number}/yearly")
def get_number_yearly(number: int):
    """
    Yearly frequency breakdown for a single number.
    Used for trend charts in the UI.
    """
    if not (1 <= number <= 49):
        raise HTTPException(status_code=400, detail="Number must be between 1 and 49")

    from services.toto2_stats import get_number_yearly
    return {
        "number": number,
        "yearly": get_number_yearly(number),
    }