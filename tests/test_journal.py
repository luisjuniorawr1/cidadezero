from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.journal import JournalStore


def create_events_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_day INTEGER NOT NULL,
                city_minute INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                character_id TEXT,
                target_character_id TEXT,
                location TEXT,
                summary TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        rows = [
            (3, 540, "work", "chatgpt", None, "laboratorio",
             "ChatGPT compareceu ao trabalho.", {}),
            (3, 680, "conflict", "grok", "claude", "cafe",
             "Grok e Claude tiveram um desentendimento.", {"topic": "uma decisão coletiva"}),
            (3, 710, "support", "gemini", "claude", "cafe",
             "Gemini ofereceu apoio a Claude.", {}),
        ]
        for row in rows:
            db.execute(
                """
                INSERT INTO events(
                    city_day,city_minute,event_type,character_id,
                    target_character_id,location,summary,payload_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (*row[:-1], json.dumps(row[-1])),
            )


def test_local_edition_uses_only_recorded_events(tmp_path: Path) -> None:
    database = tmp_path / "city.db"
    create_events_db(database)
    journal = JournalStore(database)
    journal.initialize()
    edition = journal.build_local_edition(3)
    assert edition["city_day"] == 3
    assert edition["articles"]
    allowed = {1, 2, 3}
    cited = {
        event_id
        for article in edition["articles"]
        for event_id in article["event_ids"]
    }
    assert cited <= allowed


def test_ai_edition_rejects_invented_event_ids(tmp_path: Path) -> None:
    database = tmp_path / "city.db"
    create_events_db(database)
    journal = JournalStore(database)
    journal.initialize()
    journal.build_local_edition(3)
    accepted = journal.apply_ai_edition(
        3,
        {
            "edition_title": "Título",
            "edition_summary": "Resumo",
            "articles": [
                {
                    "category": "Cidade",
                    "title": "Fato inventado",
                    "lead": "Texto",
                    "body": "Texto",
                    "event_ids": [999],
                }
            ],
        },
    )
    assert accepted is False
    assert journal.edition(3)["ai_generated"] is False


def test_brief_since_returns_high_impact_updates(tmp_path: Path) -> None:
    database = tmp_path / "city.db"
    create_events_db(database)
    journal = JournalStore(database)
    journal.initialize()
    brief = journal.brief_since(1)
    assert brief["has_updates"] is True
    assert brief["latest_event_id"] == 3
    assert any(item["type"] == "conflict" for item in brief["highlights"])
