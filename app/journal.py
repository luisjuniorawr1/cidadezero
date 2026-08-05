from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


EVENT_WEIGHTS: dict[str, float] = {
    "arrival": 90,
    "city_issue": 88,
    "city_issue_resolved": 72,
    "conflict": 82,
    "support": 68,
    "personal_problem": 70,
    "problem_resolved": 62,
    "finance": 55,
    "initiative": 66,
    "relationship": 78,
    "romantic_signal": 76,
    "rejection": 58,
    "community": 52,
    "work": 34,
    "shopping": 28,
    "interaction": 30,
    "study": 18,
    "leisure": 12,
    "meal": 8,
    "sleep": 4,
    "hygiene": 3,
    "new_day": 1,
}

CATEGORY_LABELS: dict[str, str] = {
    "arrival": "Cidade",
    "city_issue": "Serviços públicos",
    "city_issue_resolved": "Serviços públicos",
    "conflict": "Relações",
    "support": "Sociedade",
    "personal_problem": "Cotidiano",
    "problem_resolved": "Cotidiano",
    "finance": "Economia",
    "initiative": "Projetos",
    "relationship": "Relações",
    "romantic_signal": "Relações",
    "rejection": "Relações",
    "community": "Comunidade",
    "work": "Trabalho",
    "shopping": "Economia",
    "interaction": "Sociedade",
}


def _clean_sentence(value: Any, limit: int = 900) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return text[:limit]


def _headline_from_summary(summary: str) -> str:
    text = re.sub(r"\s+", " ", summary.strip()).rstrip(".!?")
    if len(text) <= 95:
        return text
    return text[:92].rsplit(" ", 1)[0] + "…"


class JournalStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS journal_editions (
                    city_day INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    ai_generated INTEGER NOT NULL DEFAULT 0,
                    source_event_min INTEGER,
                    source_event_max INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS journal_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_day INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    lead TEXT NOT NULL,
                    body TEXT NOT NULL,
                    event_ids_json TEXT NOT NULL,
                    impact REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY(city_day) REFERENCES journal_editions(city_day)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_journal_articles_day
                    ON journal_articles(city_day, position);
                """
            )

    def events_for_day(self, city_day: int) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE city_day=? ORDER BY id ASC",
                (int(city_day),),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["payload"] = json.loads(item.pop("payload_json"))
            except (json.JSONDecodeError, TypeError):
                item["payload"] = {}
                item.pop("payload_json", None)
            result.append(item)
        return result

    def events_after(self, event_id: int, limit: int = 1000) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE id>? ORDER BY id ASC LIMIT ?",
                (max(0, int(event_id)), max(1, min(5000, int(limit)))),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["payload"] = json.loads(item.pop("payload_json"))
            except (json.JSONDecodeError, TypeError):
                item["payload"] = {}
                item.pop("payload_json", None)
            result.append(item)
        return result

    def max_event_id(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COALESCE(MAX(id),0) AS value FROM events").fetchone()
        return int(row["value"] if row else 0)

    @staticmethod
    def impact(event: dict[str, Any]) -> float:
        event_type = str(event.get("event_type") or "")
        score = EVENT_WEIGHTS.get(event_type, 20.0)
        payload = event.get("payload") or {}
        if event.get("target_character_id"):
            score += 8
        if payload.get("problem"):
            score += 8
        if payload.get("topic"):
            score += 4
        if payload.get("cost"):
            try:
                score += min(18, abs(float(payload["cost"])) * 0.5)
            except (TypeError, ValueError):
                pass
        duration = payload.get("duration")
        if duration:
            try:
                score += min(10, float(duration) / 12)
            except (TypeError, ValueError):
                pass
        return round(score, 2)

    def ranked_events(self, city_day: int, limit: int = 10) -> list[dict[str, Any]]:
        events = self.events_for_day(city_day)
        for event in events:
            event["impact"] = self.impact(event)
        events.sort(key=lambda item: (item["impact"], item["id"]), reverse=True)
        return events[: max(1, int(limit))]

    def edition_exists(self, city_day: int) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT 1 FROM journal_editions WHERE city_day=?",
                (int(city_day),),
            ).fetchone()
        return row is not None

    def build_local_edition(self, city_day: int, replace: bool = False) -> dict[str, Any]:
        if not replace and self.edition_exists(city_day):
            existing = self.edition(city_day)
            return existing or {}

        events = self.ranked_events(city_day, 20)
        significant = [event for event in events if event["impact"] >= 28]
        selected: list[dict[str, Any]] = []
        seen: set[tuple[str, str | None, str | None]] = set()
        for event in significant:
            key = (
                str(event.get("event_type")),
                event.get("character_id"),
                event.get("target_character_id"),
            )
            if key in seen and len(selected) >= 2:
                continue
            seen.add(key)
            selected.append(event)
            if len(selected) >= 5:
                break

        if selected:
            articles = []
            for position, event in enumerate(selected):
                summary = _clean_sentence(event.get("summary"))
                category = CATEGORY_LABELS.get(
                    str(event.get("event_type")), "Cidade"
                )
                related = [
                    candidate
                    for candidate in events
                    if candidate["id"] != event["id"]
                    and (
                        candidate.get("character_id") == event.get("character_id")
                        or candidate.get("target_character_id")
                        == event.get("target_character_id")
                    )
                ][:2]
                event_ids = [int(event["id"])] + [int(item["id"]) for item in related]
                body = summary
                if related:
                    related_text = " ".join(
                        _clean_sentence(item.get("summary")) for item in related
                    )
                    body = f"{summary} Em registros relacionados, {related_text[0].lower() + related_text[1:]}"
                articles.append(
                    {
                        "position": position,
                        "category": category,
                        "title": _headline_from_summary(summary),
                        "lead": summary,
                        "body": body,
                        "event_ids": event_ids,
                        "impact": float(event["impact"]),
                    }
                )
            title = articles[0]["title"]
            summary = (
                f"A edição do Dia {city_day} reúne {len(articles)} "
                f"acontecimento{'s' if len(articles) != 1 else ''} de maior impacto."
            )
        else:
            articles = [
                {
                    "position": 0,
                    "category": "Cotidiano",
                    "title": "Rotina segue sem grandes ocorrências",
                    "lead": (
                        f"O Dia {city_day} terminou sem mudanças de grande impacto "
                        "registradas pelo observatório."
                    ),
                    "body": (
                        "Os moradores mantiveram atividades comuns de trabalho, cuidado "
                        "pessoal, descanso e convivência. O jornal não identificou fatos "
                        "suficientes para uma manchete extraordinária."
                    ),
                    "event_ids": [int(events[0]["id"])] if events else [],
                    "impact": float(events[0]["impact"]) if events else 0.0,
                }
            ]
            title = articles[0]["title"]
            summary = articles[0]["lead"]

        self.save_edition(
            city_day=city_day,
            title=title,
            summary=summary,
            articles=articles,
            ai_generated=False,
        )
        return self.edition(city_day) or {}

    def save_edition(
        self,
        *,
        city_day: int,
        title: str,
        summary: str,
        articles: list[dict[str, Any]],
        ai_generated: bool,
    ) -> None:
        all_ids = [
            int(event_id)
            for article in articles
            for event_id in article.get("event_ids", [])
            if isinstance(event_id, int) or str(event_id).isdigit()
        ]
        source_min = min(all_ids) if all_ids else None
        source_max = max(all_ids) if all_ids else None
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO journal_editions(
                    city_day,title,summary,ai_generated,source_event_min,source_event_max
                ) VALUES(?,?,?,?,?,?)
                ON CONFLICT(city_day) DO UPDATE SET
                    title=excluded.title,summary=excluded.summary,
                    ai_generated=excluded.ai_generated,
                    source_event_min=excluded.source_event_min,
                    source_event_max=excluded.source_event_max,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    int(city_day),
                    _clean_sentence(title, 140).rstrip("."),
                    _clean_sentence(summary, 500),
                    1 if ai_generated else 0,
                    source_min,
                    source_max,
                ),
            )
            db.execute("DELETE FROM journal_articles WHERE city_day=?", (int(city_day),))
            for position, article in enumerate(articles[:5]):
                db.execute(
                    """
                    INSERT INTO journal_articles(
                        city_day,position,category,title,lead,body,event_ids_json,impact
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        int(city_day),
                        int(article.get("position", position)),
                        str(article.get("category") or "Cidade")[:40],
                        _clean_sentence(article.get("title"), 150).rstrip("."),
                        _clean_sentence(article.get("lead"), 400),
                        _clean_sentence(article.get("body"), 1000),
                        json.dumps(
                            [int(value) for value in article.get("event_ids", [])],
                            ensure_ascii=False,
                        ),
                        float(article.get("impact", 0)),
                    ),
                )

    def apply_ai_edition(self, city_day: int, payload: dict[str, Any]) -> bool:
        events = self.events_for_day(city_day)
        allowed_ids = {int(event["id"]) for event in events}
        articles: list[dict[str, Any]] = []
        for position, raw in enumerate(payload.get("articles", [])[:5]):
            try:
                event_ids = [int(value) for value in raw.get("event_ids", [])]
            except (TypeError, ValueError):
                continue
            if not event_ids or any(event_id not in allowed_ids for event_id in event_ids):
                continue
            impact = max(
                (self.impact(event) for event in events if int(event["id"]) in event_ids),
                default=0.0,
            )
            articles.append(
                {
                    "position": position,
                    "category": str(raw.get("category") or "Cidade"),
                    "title": str(raw.get("title") or ""),
                    "lead": str(raw.get("lead") or ""),
                    "body": str(raw.get("body") or ""),
                    "event_ids": event_ids,
                    "impact": impact,
                }
            )
        if not articles:
            return False
        self.save_edition(
            city_day=city_day,
            title=str(payload.get("edition_title") or articles[0]["title"]),
            summary=str(payload.get("edition_summary") or articles[0]["lead"]),
            articles=articles,
            ai_generated=True,
        )
        return True

    def edition(self, city_day: int) -> dict[str, Any] | None:
        with self.connect() as db:
            edition = db.execute(
                "SELECT * FROM journal_editions WHERE city_day=?",
                (int(city_day),),
            ).fetchone()
            if not edition:
                return None
            article_rows = db.execute(
                """
                SELECT * FROM journal_articles
                WHERE city_day=? ORDER BY position,id
                """,
                (int(city_day),),
            ).fetchall()
        result = dict(edition)
        result["ai_generated"] = bool(result["ai_generated"])
        result["articles"] = []
        for row in article_rows:
            item = dict(row)
            try:
                item["event_ids"] = json.loads(item.pop("event_ids_json"))
            except (json.JSONDecodeError, TypeError):
                item["event_ids"] = []
                item.pop("event_ids_json", None)
            result["articles"].append(item)
        return result

    def latest(self) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT city_day FROM journal_editions ORDER BY city_day DESC LIMIT 1"
            ).fetchone()
        return self.edition(int(row["city_day"])) if row else None

    def editions(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT city_day,title,summary,ai_generated,created_at,updated_at
                FROM journal_editions ORDER BY city_day DESC LIMIT ?
                """,
                (max(1, min(365, int(limit))),),
            ).fetchall()
        return [
            {
                **dict(row),
                "ai_generated": bool(row["ai_generated"]),
            }
            for row in rows
        ]

    def ensure_backfill(self, current_day: int, days: int = 7) -> None:
        start = max(1, int(current_day) - max(1, int(days)))
        for day in range(start, int(current_day)):
            if self.events_for_day(day) and not self.edition_exists(day):
                self.build_local_edition(day)

    def context_for_ai(self, city_day: int) -> dict[str, Any]:
        ranked = self.ranked_events(city_day, 30)
        return {
            "publication": "Jornal Zero",
            "city_day": int(city_day),
            "editorial_rules": [
                "relatar somente os fatos fornecidos",
                "não inventar entrevistas ou pensamentos",
                "não escolher heróis ou vilões",
                "separar fato registrado de tendência observável",
                "não influenciar a cidade",
            ],
            "events": [
                {
                    "id": int(event["id"]),
                    "time": f"{int(event['city_minute']) // 60:02d}:"
                    f"{int(event['city_minute']) % 60:02d}",
                    "type": event.get("event_type"),
                    "character_id": event.get("character_id"),
                    "target_character_id": event.get("target_character_id"),
                    "location": event.get("location"),
                    "summary": event.get("summary"),
                    "impact": event.get("impact"),
                }
                for event in ranked
                if event.get("event_type") != "new_day"
            ],
        }

    def brief_since(self, after_event_id: int) -> dict[str, Any]:
        events = self.events_after(after_event_id)
        current_max = self.max_event_id()
        if not events:
            return {
                "has_updates": False,
                "after_event_id": int(after_event_id),
                "latest_event_id": current_max,
                "event_count": 0,
                "highlights": [],
                "counts_by_type": {},
            }

        ranked = sorted(
            ({**event, "impact": self.impact(event)} for event in events),
            key=lambda item: (item["impact"], item["id"]),
            reverse=True,
        )
        counts = Counter(str(event.get("event_type") or "other") for event in events)
        return {
            "has_updates": True,
            "after_event_id": int(after_event_id),
            "latest_event_id": current_max,
            "event_count": len(events),
            "from_day": min(int(event["city_day"]) for event in events),
            "to_day": max(int(event["city_day"]) for event in events),
            "highlights": [
                {
                    "id": int(event["id"]),
                    "city_day": int(event["city_day"]),
                    "city_minute": int(event["city_minute"]),
                    "summary": event.get("summary"),
                    "type": event.get("event_type"),
                    "impact": event["impact"],
                }
                for event in ranked[:8]
                if event["impact"] >= 28
            ],
            "counts_by_type": dict(counts),
        }
