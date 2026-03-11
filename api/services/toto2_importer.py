"""
services/toto2_importer.py
--------------------------
Handles bulk import of TOTO2 draws into toto2.draws.
Uses the existing execute_query() pattern from services/database.py.
"""

from services.database import execute_query
from services.toto2_stats import rebuild_stats
from schemas.toto2 import Toto2ImportPayload, Toto2ImportResult, Toto2ImportRow


def _row_exists(issue: int, year: int, draw_index: int) -> bool:
    """Check if a draw already exists in the DB."""
    result = execute_query(
        """
        SELECT id FROM toto2.draws
        WHERE issue = %s AND year = %s AND draw_index = %s
        """,
        (issue, year, draw_index),
    )
    return bool(result)


def _insert_draw(row: Toto2ImportRow) -> None:
    """Insert a single draw row."""
    nums = sorted(row.numbers)  # always store sorted ascending
    execute_query(
        """
        INSERT INTO toto2.draws
            (issue, year, draw_index, n1, n2, n3, n4, n5, n6, draw_date)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (row.issue, row.year, row.draw_index,
         nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
         row.draw_date),
    )


def _update_draw(row: Toto2ImportRow) -> None:
    """Overwrite an existing draw row."""
    nums = sorted(row.numbers)
    execute_query(
        """
        UPDATE toto2.draws
        SET n1 = %s, n2 = %s, n3 = %s, n4 = %s, n5 = %s, n6 = %s,
            draw_date = %s,
            imported_at = NOW()
        WHERE issue = %s AND year = %s AND draw_index = %s
        """,
        (nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
         row.draw_date,
         row.issue, row.year, row.draw_index),
    )


def import_draws(payload: Toto2ImportPayload) -> Toto2ImportResult:
    """
    Process a full import payload.

    For each row:
      - If not in DB  → insert
      - If in DB and overwrite=True  → update
      - If in DB and overwrite=False → skip
    """
    inserted    = 0
    skipped     = 0
    overwritten = 0
    errors: list[str] = []

    for row in payload.rows:
        label = f"тираж {row.issue}/{row.year} теглене {row.draw_index}"
        try:
            exists = _row_exists(row.issue, row.year, row.draw_index)

            if not exists:
                _insert_draw(row)
                inserted += 1

            elif payload.overwrite:
                _update_draw(row)
                overwritten += 1

            else:
                skipped += 1

        except Exception as e:
            errors.append(f"{label}: {e}")

    # Rebuild statistics in toto2.number_stats
    rebuild_stats()

    return Toto2ImportResult(
        inserted=inserted,
        skipped=skipped,
        overwritten=overwritten,
        errors=errors,
    )