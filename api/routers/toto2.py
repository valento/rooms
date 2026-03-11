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
from services.toto2_stats import rebuild_stats
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
def get_frequency():
    """
    Return all 49 numbers sorted by frequency descending.
    Hot numbers (most drawn) at the top, cold numbers at the bottom.
    """
    result = execute_query(
        """
        SELECT number, frequency, updated_at
        FROM toto2.number_stats
        ORDER BY frequency DESC, number ASC
        """
    )
    return result or []


# ---------------------------------------------------------------------------
# POST /toto2/stats/rebuild
# ---------------------------------------------------------------------------
@router.post("/stats/rebuild")
def trigger_rebuild():
    """Manually trigger a stats rebuild (e.g. after fixing imported data)."""
    rebuild_stats()
    return {"status": "ok", "message": "Stats rebuilt successfully"}