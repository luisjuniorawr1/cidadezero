from __future__ import annotations

from pathlib import Path

from app.intelligence import UsageLedger


def test_failed_or_pending_attempt_also_starts_cooldown(tmp_path: Path) -> None:
    ledger = UsageLedger(tmp_path / "city.db")
    ledger.initialize()
    ledger.begin(
        city_day=4,
        city_minute=321,
        character_id="chatgpt",
        request_type="character_decision",
        model="gpt-4o-mini",
        context={"test": True},
    )
    assert ledger.last_successful_city_minute("chatgpt") == (3 * 1440) + 321
