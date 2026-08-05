from __future__ import annotations

import asyncio
from pathlib import Path

import app.main as city


def configure_temp_database(tmp_path: Path) -> None:
    city.DATABASE_PATH = tmp_path / "test.db"
    city.engine = city.CityEngine()


def test_engine_initializes_and_persists(tmp_path: Path) -> None:
    async def scenario() -> None:
        configure_temp_database(tmp_path)
        await city.engine.initialize()
        assert len(city.engine.characters) == 7
        before = city.engine.minute
        await city.engine.tick(15)
        assert city.engine.minute == before + 15
        assert city.engine.storage.events(10)

        restarted = city.CityEngine()
        await restarted.initialize()
        assert restarted.minute == city.engine.minute
        assert len(restarted.characters) == 7

    asyncio.run(scenario())


def test_character_detail_contains_relationships(tmp_path: Path) -> None:
    async def scenario() -> None:
        configure_temp_database(tmp_path)
        await city.engine.initialize()
        detail = await city.engine.detail("chatgpt")
        assert detail is not None
        assert detail["public_name"] == "ChatGPT"
        assert len(detail["relationships"]) == 6

    asyncio.run(scenario())
