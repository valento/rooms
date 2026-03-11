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


def compute_frequency() -> dict[int, int]:
    """
    Count how many times each number (1..49) appeared across all draws.
    Returns a dict: { number: count }
    """
    result = execute_query(
        """
        SELECT num, COUNT(*) AS freq
        FROM toto2.draws,
             UNNEST(ARRAY[n1, n2, n3, n4, n5, n6]) AS num
        GROUP BY num
        ORDER BY num
        """
    )

    # Start with all 49 numbers at 0 so missing numbers are included
    freq = {n: 0 for n in range(1, 50)}
    for row in (result or []):
        freq[row["num"]] = row["freq"]

    return freq


def rebuild_stats() -> None:
    """
    Rebuild toto2.number_stats from scratch.
    Called after every import.

    Currently updates: frequency only.
    """
    freq = compute_frequency()

    for number, frequency in freq.items():
        execute_query(
            """
            UPDATE toto2.number_stats
            SET frequency  = %s,
                updated_at = NOW()
            WHERE number = %s
            """,
            (frequency, number),
        )