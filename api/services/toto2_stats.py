"""
services/toto2_stats.py
-----------------------
Stats engine for TOTO2. Built incrementally — one stat at a time.

Current stats:
  [x] frequency       — how many times each number appeared across all draws
  [ ] absence_streak  — coming next
  [ ] last_seen       — coming next
"""

from services.database import execute_query

def get_year_bounds() -> tuple[int, int]:
    """Return the min and max years available in toto2.draws."""
    result = execute_query(
        "SELECT MIN(year) AS year_from, MAX(year) AS year_to FROM toto2.draws"
    )
    row = result[0] if result else {}
    return row.get("year_from", 2020), row.get("year_to", 2025)


def compute_frequency(
    year_from: int | None = None,
    year_to:   int | None = None,
) -> dict[int, int]:
    """
    Count how many times each number (1..49) appeared.

    Args:
        year_from: start of range (inclusive). Defaults to earliest year in DB.
        year_to:   end of range (inclusive). Defaults to latest year in DB.

    Returns:
        dict { number: count } for all 49 numbers.
    """
    min_year, max_year = get_year_bounds()
    year_from = year_from or min_year
    year_to   = year_to   or max_year

    result = execute_query(
        """
        SELECT num, COUNT(*) AS freq
        FROM toto2.draws,
             UNNEST(ARRAY[n1, n2, n3, n4, n5, n6]) AS num
        WHERE year BETWEEN %s AND %s
        GROUP BY num
        ORDER BY num
        """,
        (year_from, year_to),
    )

    # Start with all 49 numbers at 0 so missing numbers are always included
    freq = {n: 0 for n in range(1, 50)}
    for row in (result or []):
        freq[row["num"]] = row["freq"]

    return freq


def rebuild_stats() -> None:
    """
    Rebuild toto2.number_stats from scratch using full date range.
    Called automatically after every import.

    Currently updates: frequency, absence_streak.
    """
    freq    = compute_frequency()
    streaks = compute_absence_streaks()

    for number in range(1, 50):
        execute_query(
            """
            UPDATE toto2.number_stats
            SET frequency      = %s,
                absence_streak = %s,
                updated_at     = NOW()
            WHERE number = %s
            """,
            (freq[number], streaks[number], number),
        )


def compute_absence_streaks() -> dict[int, int]:
    """
    For each number 1..49, count how many consecutive draws
    (going backwards from the most recent) it has NOT appeared in.

    Example: if the last 3 draws were:
        draw 522: [2, 15, 23, 34, 41, 49]
        draw 521: [5, 12, 23, 33, 40, 47]
        draw 520: [1,  7, 15, 28, 34, 42]

    Number 23 → streak = 0 (appeared in draw 522)
    Number 40 → streak = 1 (not in 522, appeared in 521)
    Number  1 → streak = 2 (not in 522, not in 521, appeared in 520)

    Returns:
        dict { number: absence_streak }
    """
    # Fetch all draws ordered newest first
    # Each row gives us the 6 numbers as a set for fast lookup
    rows = execute_query(
        """
        SELECT id, n1, n2, n3, n4, n5, n6
        FROM toto2.draws
        ORDER BY year DESC, issue DESC, draw_index DESC
        """
    )

    if not rows:
        return {n: 0 for n in range(1, 50)}

    # Track which numbers have been "found" and their streak
    streaks  = {}          # number → streak (finalized once found)
    not_found = set(range(1, 50))  # numbers still being counted

    for step, row in enumerate(rows):
        draw_numbers = {row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"]}

        found_this_draw = not_found & draw_numbers
        for num in found_this_draw:
            streaks[num] = step  # step = how many draws we walked back before finding it

        not_found -= found_this_draw
        if not not_found:
            break  # all numbers found, no need to continue

    # Any number never found in history gets streak = total draws
    total_draws = len(rows)
    for num in not_found:
        streaks[num] = total_draws

    return streaks


def get_total_draws(year_from: int, year_to: int) -> int:
    """Count draws in a given year range."""
    result = execute_query(
        "SELECT COUNT(*) AS total FROM toto2.draws WHERE year BETWEEN %s AND %s",
        (year_from, year_to),
    )
    return result[0]["total"] if result else 0

#  ====== Get Number stats =======================

def get_number_pairs(number: int, year_from: int, year_to: int) -> list[dict]:
    """
    Find the 10 numbers that appeared most often in the same draw as `number`
    within the given year range.
    """
    result = execute_query(
        """
        SELECT partner, COUNT(*) AS count
        FROM (
            SELECT UNNEST(ARRAY[n1,n2,n3,n4,n5,n6]) AS partner
            FROM toto2.draws
            WHERE year BETWEEN %s AND %s
              AND %s = ANY(ARRAY[n1,n2,n3,n4,n5,n6])
        ) sub
        WHERE partner != %s
        GROUP BY partner
        ORDER BY count DESC
        LIMIT 10
        """,
        (year_from, year_to, number, number),
    )
    return [{"partner": row["partner"], "count": row["count"]} for row in (result or [])]


def get_number_yearly(number: int) -> list[dict]:
    """
    Frequency of a single number broken down by year.
    Includes total draws per year for normalization in the UI.
    """
    result = execute_query(
        """
        SELECT
            d.year,
            COUNT(*) FILTER (
                WHERE %s = ANY(ARRAY[d.n1,d.n2,d.n3,d.n4,d.n5,d.n6])
            )                        AS frequency,
            COUNT(*)                 AS draws
        FROM toto2.draws d
        GROUP BY d.year
        ORDER BY d.year
        """,
        (number,),
    )
    return [
        {
            "year":      row["year"],
            "frequency": row["frequency"],
            "draws":     row["draws"],
        }
        for row in (result or [])
    ]