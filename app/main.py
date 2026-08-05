from __future__ import annotations

import asyncio
import json
import os
import random
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Iterable

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.society import CitizenLife, Decision, HumanNeeds, SocietyRules

ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/cidade_zero.db"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = ROOT_DIR / DATABASE_PATH
TICK_SECONDS = max(0.2, float(os.getenv("CITY_TICK_SECONDS", "1")))
MINUTES_PER_TICK = max(1, int(os.getenv("CITY_MINUTES_PER_TICK", "5")))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
REGISTRY_PATH = ROOT_DIR / "documentacao" / "personagens_registry.json"
SEED_PATH = ROOT_DIR / "data" / "city_seed.json"
STATIC_DIR = ROOT_DIR / "app" / "static"


@dataclass
class Character:
    character_id: str
    public_name: str
    status: str
    location: str
    home_location: str
    action: str = "observando a cidade"
    mood: str = "neutro"
    activity_until: int = 0
    needs: HumanNeeds = field(default_factory=HumanNeeds)
    life: CitizenLife = field(default_factory=CitizenLife)
    profile: dict[str, Any] = field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        operational = self.profile.get("operational_profile", {})
        return {
            "character_id": self.character_id,
            "public_name": self.public_name,
            "status": self.status,
            "location": self.location,
            "home_location": self.home_location,
            "action": self.action,
            "mood": self.mood,
            "activity_until": self.activity_until,
            "needs": self.needs.public(),
            "life": self.life.public(),
            "archetype": operational.get("archetype"),
            "city_role": operational.get("city_role"),
            "central_value": operational.get("central_value"),
            "behavioral_scores": self.profile.get("behavioral_scores", {}),
        }


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS world_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS characters (
                    character_id TEXT PRIMARY KEY, public_name TEXT NOT NULL,
                    status TEXT NOT NULL, location TEXT NOT NULL,
                    home_location TEXT NOT NULL, action TEXT NOT NULL,
                    mood TEXT NOT NULL, activity_until INTEGER NOT NULL,
                    needs_json TEXT NOT NULL, profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS citizen_life (
                    character_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_day INTEGER NOT NULL, city_minute INTEGER NOT NULL,
                    event_type TEXT NOT NULL, character_id TEXT,
                    target_character_id TEXT, location TEXT,
                    summary TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id TEXT NOT NULL,
                    city_day INTEGER NOT NULL,
                    city_minute INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    valence REAL NOT NULL DEFAULT 0,
                    importance INTEGER NOT NULL DEFAULT 1,
                    related_character_id TEXT,
                    location TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_memories_character
                    ON memories(character_id, id DESC);
                CREATE TABLE IF NOT EXISTS relationships (
                    character_a TEXT NOT NULL, character_b TEXT NOT NULL,
                    affinity REAL NOT NULL DEFAULT 50,
                    trust REAL NOT NULL DEFAULT 50,
                    familiarity REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (character_a, character_b)
                );
                """
            )

    def world_get(self, key: str, default: Any) -> Any:
        with self.connect() as db:
            row = db.execute("SELECT value FROM world_state WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row["value"])

    def world_set(self, key: str, value: Any) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO world_state(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def save_character(self, character: Character) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO characters(character_id,public_name,status,location,
                    home_location,action,mood,activity_until,needs_json,profile_json)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(character_id) DO UPDATE SET
                    public_name=excluded.public_name,status=excluded.status,
                    location=excluded.location,home_location=excluded.home_location,
                    action=excluded.action,mood=excluded.mood,
                    activity_until=excluded.activity_until,
                    needs_json=excluded.needs_json,profile_json=excluded.profile_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    character.character_id,
                    character.public_name,
                    character.status,
                    character.location,
                    character.home_location,
                    character.action,
                    character.mood,
                    character.activity_until,
                    json.dumps(character.needs.public(), ensure_ascii=False),
                    json.dumps(character.profile, ensure_ascii=False),
                ),
            )
            db.execute(
                """
                INSERT INTO citizen_life(character_id,state_json) VALUES(?,?)
                ON CONFLICT(character_id) DO UPDATE SET
                    state_json=excluded.state_json,updated_at=CURRENT_TIMESTAMP
                """,
                (character.character_id, json.dumps(character.life.public(), ensure_ascii=False)),
            )

    def load_characters(self) -> dict[str, Character]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT c.*, l.state_json
                FROM characters c
                LEFT JOIN citizen_life l ON l.character_id=c.character_id
                """
            ).fetchall()
        result: dict[str, Character] = {}
        for row in rows:
            result[row["character_id"]] = Character(
                character_id=row["character_id"],
                public_name=row["public_name"],
                status=row["status"],
                location=row["location"],
                home_location=row["home_location"],
                action=row["action"],
                mood=row["mood"],
                activity_until=row["activity_until"],
                needs=HumanNeeds.from_dict(json.loads(row["needs_json"])),
                life=CitizenLife.from_dict(json.loads(row["state_json"]) if row["state_json"] else None),
                profile=json.loads(row["profile_json"]),
            )
        return result

    def event(
        self,
        day: int,
        minute: int,
        event_type: str,
        summary: str,
        character_id: str | None = None,
        target: str | None = None,
        location: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(city_day,city_minute,event_type,character_id,"
                "target_character_id,location,summary,payload_json) VALUES(?,?,?,?,?,?,?,?)",
                (
                    day,
                    minute,
                    event_type,
                    character_id,
                    target,
                    location,
                    summary,
                    json.dumps(payload or {}, ensure_ascii=False),
                ),
            )

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                (max(1, min(500, limit)),),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result

    def memory(
        self,
        character_id: str,
        day: int,
        minute: int,
        category: str,
        summary: str,
        valence: float = 0,
        importance: int = 1,
        related_character_id: str | None = None,
        location: str | None = None,
    ) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO memories(character_id,city_day,city_minute,category,
                    summary,valence,importance,related_character_id,location)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    character_id,
                    day,
                    minute,
                    category,
                    summary,
                    max(-1.0, min(1.0, float(valence))),
                    max(1, min(5, int(importance))),
                    related_character_id,
                    location,
                ),
            )

    def memories(self, character_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM memories WHERE character_id=? ORDER BY id DESC LIMIT ?",
                    (character_id, max(1, min(100, limit))),
                ).fetchall()
            ]

    def ensure_relationships(self, ids: Iterable[str]) -> None:
        values = list(ids)
        with self.connect() as db:
            for a in values:
                for b in values:
                    if a != b:
                        db.execute(
                            "INSERT OR IGNORE INTO relationships(character_a,character_b) VALUES(?,?)",
                            (a, b),
                        )

    def relation_delta(self, a: str, b: str, affinity: float, trust: float, familiarity: float = 2) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE relationships SET "
                "affinity=MIN(100,MAX(0,affinity+?)),"
                "trust=MIN(100,MAX(0,trust+?)),"
                "familiarity=MIN(100,MAX(0,familiarity+?)),"
                "updated_at=CURRENT_TIMESTAMP WHERE character_a=? AND character_b=?",
                (affinity, trust, familiarity, a, b),
            )

    def relationship(self, a: str, b: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM relationships WHERE character_a=? AND character_b=?",
                (a, b),
            ).fetchone()
        return dict(row) if row else {
            "character_a": a,
            "character_b": b,
            "affinity": 50,
            "trust": 50,
            "familiarity": 0,
        }

    def relationships(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM relationships ORDER BY character_a,character_b"
                ).fetchall()
            ]


class CityEngine:
    WORLD_INCIDENTS: tuple[dict[str, Any], ...] = (
        {
            "type": "market_prices",
            "title": "Os preços do mercado subiram",
            "summary": "Os moradores precisarão rever compras e prioridades durante alguns dias.",
            "duration_days": 2,
        },
        {
            "type": "water_maintenance",
            "title": "A cidade terá manutenção no abastecimento",
            "summary": "Alguns bairros terão água reduzida e tarefas domésticas ficarão mais difíceis.",
            "duration_days": 1,
        },
        {
            "type": "community_cleanup",
            "title": "O parque precisa de um mutirão",
            "summary": "A prefeitura pediu voluntários para recuperar uma área comum.",
            "duration_days": 2,
        },
        {
            "type": "clinic_demand",
            "title": "A clínica está com atendimento sobrecarregado",
            "summary": "Consultas poderão demorar e a comunidade discute como ajudar.",
            "duration_days": 2,
        },
    )

    def __init__(self) -> None:
        self.storage = Storage(DATABASE_PATH)
        self.characters: dict[str, Character] = {}
        self.locations: dict[str, dict[str, Any]] = {}
        self.city_name = "Cidade Zero"
        self.day = 1
        self.minute = 420
        self.running = False
        self.task: asyncio.Task[None] | None = None
        self.lock = asyncio.Lock()
        self.rng = random.Random(20260805)
        self.city_issue: dict[str, Any] | None = None

    @property
    def absolute_minute(self) -> int:
        return (self.day - 1) * 1440 + self.minute

    async def initialize(self) -> None:
        self.storage.initialize()
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        self.city_name = seed["city_name"]
        self.locations = {item["id"]: item for item in seed["locations"]}
        extra_locations = (
            {"id": "clinica", "name": "Clínica Comunitária", "kind": "health"},
            {"id": "lavanderia", "name": "Lavanderia do Bairro", "kind": "service"},
            {"id": "centro_comunitario", "name": "Centro Comunitário", "kind": "social"},
        )
        for location in extra_locations:
            self.locations.setdefault(location["id"], location)
        self.day = int(self.storage.world_get("day", seed["start_day"]))
        self.minute = int(self.storage.world_get("minute", seed["start_minute"]))
        self.city_issue = self.storage.world_get("city_issue", None)
        existing = self.storage.load_characters()
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

        for index, entry in enumerate(registry["characters"]):
            if not entry.get("enabled"):
                continue
            profile_path = (REGISTRY_PATH.parent / entry["profile_path"]).resolve()
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            character_id = entry["character_id"]
            home = f"casa_{character_id}"
            self.locations[home] = {
                "id": home,
                "name": f"Casa de {entry['public_name']}",
                "kind": "home",
            }
            if character_id in existing:
                character = existing[character_id]
                character.profile = profile
                character.status = entry["status"]
                if not character.life.job_title:
                    character.life = SocietyRules.default_life(profile, index)
            else:
                character = Character(
                    character_id,
                    entry["public_name"],
                    entry["status"],
                    home,
                    home,
                    needs=HumanNeeds(
                        energy=74 + index * 3 % 18,
                        hunger=14 + index * 7 % 26,
                        social=28 + index * 9 % 35,
                        curiosity=44 + index * 11 % 41,
                        hygiene=12 + index * 5 % 27,
                        stress=17 + index * 6 % 24,
                        fun=27 + index * 7 % 34,
                        comfort=16 + index * 3 % 20,
                        purpose=31 + index * 4 % 28,
                        autonomy=18 + index * 6 % 31,
                        health=88 - index * 2,
                    ),
                    life=SocietyRules.default_life(profile, index),
                    profile=profile,
                )
                self.storage.event(
                    self.day,
                    self.minute,
                    "arrival",
                    f"{character.public_name} chegou à Cidade Zero e recebeu uma casa, um trabalho e responsabilidades.",
                    character_id,
                    location=home,
                )
                self.storage.memory(
                    character_id,
                    self.day,
                    self.minute,
                    "arrival",
                    "Chegou à Cidade Zero e começou uma vida nova.",
                    valence=0.35,
                    importance=5,
                    location=home,
                )
            character.mood = SocietyRules.mood(character.needs, character.life)
            self.characters[character_id] = character
            self.storage.save_character(character)

        self.storage.ensure_relationships(self.characters)
        self.save_clock()

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self.loop(), name="cidade-zero-society-engine")

    async def stop(self) -> None:
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    async def loop(self) -> None:
        while self.running:
            await asyncio.sleep(TICK_SECONDS)
            await self.tick(MINUTES_PER_TICK)

    def save_clock(self) -> None:
        self.storage.world_set("day", self.day)
        self.storage.world_set("minute", self.minute)
        self.storage.world_set("city_issue", self.city_issue)

    def start_new_day(self) -> None:
        self.storage.event(
            self.day,
            self.minute,
            "new_day",
            f"Começou o dia {self.day} na Cidade Zero.",
        )
        if self.city_issue and self.day > int(self.city_issue.get("until_day", self.day)):
            self.storage.event(
                self.day,
                self.minute,
                "city_issue_resolved",
                f"A situação coletiva foi encerrada: {self.city_issue.get('title', 'problema da cidade')}.",
            )
            self.city_issue = None
        if self.city_issue is None and self.rng.random() < 0.42:
            issue = dict(self.rng.choice(self.WORLD_INCIDENTS))
            issue["started_day"] = self.day
            issue["until_day"] = self.day + int(issue.pop("duration_days"))
            self.city_issue = issue
            self.storage.event(
                self.day,
                self.minute,
                "city_issue",
                f"{issue['title']}. {issue['summary']}",
                payload=issue,
            )

    async def tick(self, minutes: int) -> None:
        async with self.lock:
            self.minute += minutes
            while self.minute >= 1440:
                self.minute -= 1440
                self.day += 1
                self.start_new_day()

            for character in self.characters.values():
                SocietyRules.update(character.needs, character.life, minutes)
                incident = SocietyRules.maybe_incident(
                    character.life,
                    character.needs,
                    self.day,
                    self.rng,
                )
                if incident:
                    summary = f"{character.public_name} {incident['summary']}."
                    self.storage.event(
                        self.day,
                        self.minute,
                        "personal_problem",
                        summary,
                        character.character_id,
                        location=character.location,
                        payload=incident,
                    )
                    self.storage.memory(
                        character.character_id,
                        self.day,
                        self.minute,
                        "problem",
                        summary,
                        valence=-0.65,
                        importance=4,
                        location=character.location,
                    )

            for character in self.characters.values():
                if self.absolute_minute >= character.activity_until:
                    self.choose_action(character)
                character.mood = SocietyRules.mood(character.needs, character.life)
                self.storage.save_character(character)
            self.save_clock()

    def begin(self, character: Character, decision: Decision) -> None:
        previous = character.location
        SocietyRules.apply_decision(character.needs, character.life, decision)
        if character.life.current_problem and character.life.problem_severity <= 5:
            resolved = character.life.current_problem
            character.life.current_problem = ""
            character.life.problem_severity = 0
            character.life.problem_until_day = 0
            self.storage.event(
                self.day,
                self.minute,
                "problem_resolved",
                f"{character.public_name} conseguiu encaminhar o problema: {resolved}.",
                character.character_id,
                location=decision.location,
            )
        character.location = decision.location
        character.action = decision.action
        character.activity_until = self.absolute_minute + decision.duration
        self.storage.event(
            self.day,
            self.minute,
            decision.category,
            f"{character.public_name} {decision.summary}.",
            character.character_id,
            location=decision.location,
            payload={
                "previous_location": previous,
                "duration": decision.duration,
                "goal": character.life.current_goal,
                "problem": character.life.current_problem,
            },
        )
        if decision.importance >= 2:
            self.storage.memory(
                character.character_id,
                self.day,
                self.minute,
                decision.category,
                f"{decision.summary.capitalize()}.",
                valence=decision.valence,
                importance=decision.importance,
                location=decision.location,
            )

    def socialize(self, character: Character, decision: Decision) -> None:
        available = [
            candidate
            for candidate in self.characters.values()
            if candidate.character_id != character.character_id
            and (
                self.absolute_minute >= candidate.activity_until
                or candidate.life.current_activity in {"social", "leisure", "community", "idle"}
            )
        ]
        if not available:
            self.begin(
                character,
                Decision(
                    "tomando um café sozinho e observando as pessoas",
                    "cafe",
                    35,
                    "leisure",
                    "não encontrou companhia disponível e decidiu ficar um pouco no café",
                    needs_delta={"social": -3, "stress": -2},
                    importance=1,
                    valence=0.0,
                ),
            )
            return

        weights: list[float] = []
        for candidate in available:
            relationship = self.storage.relationship(character.character_id, candidate.character_id)
            proximity = 18 if candidate.location == character.location else 0
            availability = 15 if candidate.life.current_activity in {"social", "leisure", "idle"} else 0
            weights.append(max(1.0, relationship["affinity"] + relationship["trust"] * 0.4 + proximity + availability))
        target = self.rng.choices(available, weights=weights, k=1)[0]
        relationship = self.storage.relationship(character.character_id, target.character_id)
        diplomacy = self.score(character, "diplomacia")
        target_diplomacy = self.score(target, "diplomacia")
        combined_stress = character.needs.stress + target.needs.stress
        conflict_chance = max(0.03, min(0.48, (combined_stress - diplomacy - target_diplomacy * 0.45) / 180))
        location = target.location
        if self.locations.get(location, {}).get("kind") == "home":
            location = "cafe"

        shared_problem = character.life.current_problem or target.life.current_problem
        if self.rng.random() < conflict_chance:
            topic = shared_problem or "uma decisão sobre a rotina da cidade"
            character.location = target.location = location
            character.action = f"discutindo com {target.public_name} sobre {topic}"
            target.action = f"discutindo com {character.public_name} sobre {topic}"
            character.activity_until = target.activity_until = self.absolute_minute + 35
            character.life.current_activity = target.life.current_activity = "social"
            character.needs.stress += 13
            target.needs.stress += 9
            character.life.belonging -= 5
            target.life.belonging -= 3
            character.needs.clamp()
            target.needs.clamp()
            character.life.clamp()
            target.life.clamp()
            self.storage.relation_delta(character.character_id, target.character_id, -5.5, -4.5, 4)
            self.storage.relation_delta(target.character_id, character.character_id, -4.5, -4.0, 4)
            summary = f"{character.public_name} e {target.public_name} tiveram um desentendimento sobre {topic}."
            valence = -0.75
            importance = 4
            event_type = "conflict"
        else:
            support = bool(shared_problem)
            topic = shared_problem or character.life.current_goal
            character.location = target.location = location
            character.action = f"conversando com {target.public_name} sobre {topic}"
            target.action = f"conversando com {character.public_name} sobre {topic}"
            character.activity_until = target.activity_until = self.absolute_minute + 40
            character.life.current_activity = target.life.current_activity = "social"
            character.needs.social -= 22
            target.needs.social -= 11
            character.needs.stress -= 8 if support else 3
            target.needs.stress -= 3
            character.life.belonging += 5
            target.life.belonging += 3
            transfer = 0.0
            if support and character.life.money < 5 and target.life.money > 45:
                transfer = min(8.0, target.life.money - 40)
                target.life.money -= transfer
                character.life.money += transfer
            character.needs.clamp()
            target.needs.clamp()
            character.life.clamp()
            target.life.clamp()
            affinity = 1.2 + diplomacy / 85
            trust = 0.8 + self.score(character, "transparencia") / 150
            self.storage.relation_delta(character.character_id, target.character_id, affinity, trust, 3)
            self.storage.relation_delta(target.character_id, character.character_id, affinity * 0.8, trust, 3)
            if support:
                summary = f"{target.public_name} ouviu {character.public_name} falar sobre {topic}"
                if transfer:
                    summary += " e ofereceu uma pequena ajuda financeira"
                summary += "."
                valence = 0.65
                importance = 4
                event_type = "support"
            else:
                summary = f"{character.public_name} e {target.public_name} conversaram sobre {topic}."
                valence = 0.4
                importance = 3
                event_type = "interaction"

        self.storage.save_character(target)
        self.storage.event(
            self.day,
            self.minute,
            event_type,
            summary,
            character.character_id,
            target.character_id,
            location,
            {
                "topic": topic,
                "affinity_before": relationship["affinity"],
                "trust_before": relationship["trust"],
            },
        )
        for actor, related in ((character, target), (target, character)):
            self.storage.memory(
                actor.character_id,
                self.day,
                self.minute,
                event_type,
                summary,
                valence=valence,
                importance=importance,
                related_character_id=related.character_id,
                location=location,
            )

    def score(self, character: Character, key: str, default: int = 50) -> int:
        try:
            return int(character.profile.get("behavioral_scores", {}).get(key, default))
        except (TypeError, ValueError):
            return default

    def choose_action(self, character: Character) -> None:
        decision = SocietyRules.decide(
            character.profile,
            character.needs,
            character.life,
            self.day,
            self.minute,
            character.home_location,
            self.rng,
        )
        if decision.category == "socialize":
            self.socialize(character, decision)
        else:
            self.begin(character, decision)

    def society_summary(self) -> dict[str, Any]:
        citizens = list(self.characters.values())
        if not citizens:
            return {
                "average_stress": 0,
                "total_money": 0,
                "total_debt": 0,
                "active_problems": 0,
                "working_today": 0,
            }
        return {
            "average_stress": round(sum(c.needs.stress for c in citizens) / len(citizens), 1),
            "average_belonging": round(sum(c.life.belonging for c in citizens) / len(citizens), 1),
            "total_money": round(sum(c.life.money for c in citizens), 2),
            "total_debt": round(sum(c.life.debt for c in citizens), 2),
            "active_problems": sum(bool(c.life.current_problem) for c in citizens),
            "working_today": sum(c.life.last_work_day == self.day for c in citizens),
            "current_city_issue": self.city_issue,
        }

    async def snapshot(self) -> dict[str, Any]:
        async with self.lock:
            return {
                "city": {
                    "name": self.city_name,
                    "day": self.day,
                    "minute": self.minute,
                    "time": f"{self.minute // 60:02d}:{self.minute % 60:02d}",
                    "running": self.running,
                    "minutes_per_tick": MINUTES_PER_TICK,
                    "tick_seconds": TICK_SECONDS,
                    "engine_version": "society-0.3",
                },
                "locations": list(self.locations.values()),
                "characters": [
                    character.public()
                    for character in sorted(self.characters.values(), key=lambda item: item.public_name)
                ],
                "events": self.storage.events(40),
                "society": self.society_summary(),
                "observatory": {
                    "fictional_simulation": True,
                    "monitoring_scope": "rotina e acontecimentos dos personagens simulados",
                    "private_moments": "ações íntimas não são exibidas em detalhe",
                },
            }

    async def detail(self, character_id: str) -> dict[str, Any] | None:
        async with self.lock:
            character = self.characters.get(character_id)
            if not character:
                return None
            result = character.public()
            result["profile"] = character.profile
            result["relationships"] = [
                item
                for item in self.storage.relationships()
                if item["character_a"] == character_id
            ]
            result["memories"] = self.storage.memories(character_id, 30)
            return result


engine = CityEngine()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await engine.initialize()
    await engine.start()
    try:
        yield
    finally:
        await engine.stop()


app = FastAPI(title="Cidade Zero", version="0.3.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine_running": engine.running,
        "engine_version": "society-0.3",
        "character_count": len(engine.characters),
        "database": str(DATABASE_PATH),
    }


@app.get("/api/state")
async def state() -> dict[str, Any]:
    return await engine.snapshot()


@app.get("/api/society")
async def society() -> dict[str, Any]:
    return engine.society_summary()


@app.get("/api/characters")
async def characters() -> list[dict[str, Any]]:
    return (await engine.snapshot())["characters"]


@app.get("/api/characters/{character_id}")
async def character(character_id: str) -> dict[str, Any]:
    detail = await engine.detail(character_id)
    if detail is None:
        raise HTTPException(404, "Personagem não encontrado")
    return detail


@app.get("/api/events")
async def events(limit: int = Query(50, ge=1, le=500)) -> list[dict[str, Any]]:
    return engine.storage.events(limit)


@app.get("/api/relationships")
async def relationships() -> list[dict[str, Any]]:
    return engine.storage.relationships()


@app.post("/api/admin/tick")
async def manual_tick(
    minutes: int = Query(5, ge=1, le=1440),
    x_admin_token: str | None = Header(None),
) -> dict[str, Any]:
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(403, "Token administrativo inválido")
    await engine.tick(minutes)
    return await engine.snapshot()


@app.websocket("/ws")
async def websocket_state(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(await engine.snapshot())
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
