from __future__ import annotations

from typing import Any

from app.intelligence import UsageLedger


def _last_attempt_city_minute(self: UsageLedger, character_id: str) -> int | None:
    """Apply cooldown after every API attempt, including errors and pending calls."""
    with self.connect() as db:
        row = db.execute(
            """
            SELECT city_day,city_minute FROM ai_requests
            WHERE character_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (character_id,),
        ).fetchone()
    if not row:
        return None
    return (int(row["city_day"]) - 1) * 1440 + int(row["city_minute"])


# Kept under the existing method name so the augmented runtime needs no migration.
UsageLedger.last_successful_city_minute = _last_attempt_city_minute  # type: ignore[method-assign]
