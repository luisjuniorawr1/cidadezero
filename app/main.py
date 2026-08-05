from __future__ import annotations

import asyncio
import json
import os
import random
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Iterable

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
class Needs:
    energy: float = 82.0
    hunger: float = 18.0
    social: float = 38.0
    curiosity: float = 55.0

    def clamp(self) -> None:
        for name in ("energy", "hunger", "social", "curiosity"):
            setattr(self, name, max(0.0, min(100.0, float(getattr(self, name)))))


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
    needs: Needs = field(default_factory=Needs)
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
            "needs": asdict(self.needs),
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
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_day INTEGER NOT NULL, city_minute INTEGER NOT NULL,
                    event_type TEXT NOT NULL, character_id TEXT,
                    target_character_id TEXT, location TEXT,
                    summary TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
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

    def save_character(self, c: Character) -> None:
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
                (c.character_id, c.public_name, c.status, c.location, c.home_location,
                 c.action, c.mood, c.activity_until,
                 json.dumps(asdict(c.needs), ensure_ascii=False),
                 json.dumps(c.profile, ensure_ascii=False)),
            )

    def load_characters(self) -> dict[str, Character]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM characters").fetchall()
        result: dict[str, Character] = {}
        for row in rows:
            result[row["character_id"]] = Character(
                character_id=row["character_id"], public_name=row["public_name"],
                status=row["status"], location=row["location"],
                home_location=row["home_location"], action=row["action"],
                mood=row["mood"], activity_until=row["activity_until"],
                needs=Needs(**json.loads(row["needs_json"])),
                profile=json.loads(row["profile_json"]),
            )
        return result

    def event(self, day: int, minute: int, event_type: str, summary: str,
              character_id: str | None = None, target: str | None = None,
              location: str | None = None, payload: dict[str, Any] | None = None) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(city_day,city_minute,event_type,character_id,"
                "target_character_id,location,summary,payload_json) VALUES(?,?,?,?,?,?,?,?)",
                (day, minute, event_type, character_id, target, location, summary,
                 json.dumps(payload or {}, ensure_ascii=False)),
            )

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",
                              (max(1, min(500, limit)),)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result

    def ensure_relationships(self, ids: Iterable[str]) -> None:
        values = list(ids)
        with self.connect() as db:
            for a in values:
                for b in values:
                    if a != b:
                        db.execute("INSERT OR IGNORE INTO relationships(character_a,character_b) VALUES(?,?)", (a, b))

    def relation_delta(self, a: str, b: str, affinity: float, trust: float) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE relationships SET affinity=MIN(100,MAX(0,affinity+?)),"
                "trust=MIN(100,MAX(0,trust+?)),"
                "familiarity=MIN(100,familiarity+2),updated_at=CURRENT_TIMESTAMP "
                "WHERE character_a=? AND character_b=?",
                (affinity, trust, a, b),
            )

    def relationships(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM relationships ORDER BY character_a,character_b"
            ).fetchall()]


class CityEngine:
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

    @property
    def absolute_minute(self) -> int:
        return (self.day - 1) * 1440 + self.minute

    async def initialize(self) -> None:
        self.storage.initialize()
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        self.city_name = seed["city_name"]
        self.locations = {x["id"]: x for x in seed["locations"]}
        self.day = int(self.storage.world_get("day", seed["start_day"]))
        self.minute = int(self.storage.world_get("minute", seed["start_minute"]))
        existing = self.storage.load_characters()
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        for index, entry in enumerate(registry["characters"]):
            if not entry.get("enabled"):
                continue
            profile_path = (REGISTRY_PATH.parent / entry["profile_path"]).resolve()
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            cid = entry["character_id"]
            home = f"casa_{cid}"
            self.locations[home] = {"id": home, "name": f"Casa de {entry['public_name']}", "kind": "home"}
            if cid in existing:
                c = existing[cid]
                c.profile = profile
                c.status = entry["status"]
            else:
                c = Character(cid, entry["public_name"], entry["status"], home, home,
                    needs=Needs(74 + index * 3 % 18, 14 + index * 7 % 26,
                                28 + index * 9 % 35, 44 + index * 11 % 41),
                    profile=profile)
                self.storage.event(self.day, self.minute, "arrival",
                    f"{c.public_name} chegou à Cidade Zero.", cid, location=home)
            self.characters[cid] = c
            self.storage.save_character(c)
        self.storage.ensure_relationships(self.characters)
        self.save_clock()

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self.loop(), name="cidade-zero-engine")

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

    async def tick(self, minutes: int) -> None:
        async with self.lock:
            self.minute += minutes
            while self.minute >= 1440:
                self.minute -= 1440
                self.day += 1
                self.storage.event(self.day, self.minute, "new_day", f"Começou o dia {self.day} na Cidade Zero.")
            for c in self.characters.values():
                self.update_needs(c, minutes)
            for c in self.characters.values():
                if self.absolute_minute >= c.activity_until:
                    self.choose_action(c)
                self.storage.save_character(c)
            self.save_clock()

    def update_needs(self, c: Character, minutes: int) -> None:
        f = minutes / 5
        c.needs.hunger += .55 * f
        c.needs.social += .28 * f
        c.needs.curiosity += .20 * f
        c.needs.energy -= .34 * f
        if c.action.startswith("dormindo"):
            c.needs.energy += 2.8 * f
        elif c.action.startswith("comendo"):
            c.needs.hunger -= 4 * f
        elif c.action.startswith("conversando"):
            c.needs.social -= 2.7 * f
        elif c.action.startswith("estudando"):
            c.needs.curiosity -= 2.4 * f
        c.needs.clamp()
        c.mood = self.mood(c)

    def mood(self, c: Character) -> str:
        n = c.needs
        if n.energy < 20: return "exausto"
        if n.hunger > 82: return "faminto"
        if n.social > 78: return "solitário"
        if n.curiosity > 82: return "inquieto"
        if n.energy > 70 and n.hunger < 45: return "disposto"
        return "neutro"

    def score(self, c: Character, key: str, default: int = 50) -> int:
        try:
            return int(c.profile.get("behavioral_scores", {}).get(key, default))
        except (TypeError, ValueError):
            return default

    def begin(self, c: Character, action: str, location: str, duration: int) -> None:
        previous = c.location
        c.location, c.action = location, action
        c.activity_until = self.absolute_minute + duration
        self.storage.event(self.day, self.minute, "action",
            f"{c.public_name} começou: {action}.", c.character_id,
            location=location, payload={"previous_location": previous, "duration": duration})

    def socialize(self, c: Character) -> None:
        candidates = [x for x in self.characters.values() if x.character_id != c.character_id]
        if not candidates:
            self.begin(c, "refletindo em silêncio", "praca", 30)
            return
        target = self.rng.choice(candidates)
        location = target.location if self.locations.get(target.location, {}).get("kind") != "home" else "cafe"
        c.location = target.location = location
        c.action = f"conversando com {target.public_name}"
        target.action = f"conversando com {c.public_name}"
        c.activity_until = target.activity_until = self.absolute_minute + 35
        affinity = 1 + self.score(c, "diplomacia") / 100
        trust = .5 + self.score(c, "transparencia") / 180
        self.storage.relation_delta(c.character_id, target.character_id, affinity, trust)
        self.storage.relation_delta(target.character_id, c.character_id, affinity, trust)
        c.needs.social = max(0, c.needs.social - 18)
        target.needs.social = max(0, target.needs.social - 8)
        self.storage.save_character(target)
        self.storage.event(self.day, self.minute, "interaction",
            f"{c.public_name} iniciou uma conversa com {target.public_name}.",
            c.character_id, target.character_id, location,
            {"affinity_delta": round(affinity, 2), "trust_delta": round(trust, 2)})

    def choose_action(self, c: Character) -> None:
        hour, n = self.minute // 60, c.needs
        if n.energy < 24 or ((hour >= 23 or hour < 6) and n.energy < 68):
            self.begin(c, "dormindo em casa", c.home_location, 90); return
        if n.hunger > 72:
            self.begin(c, "comendo e recuperando energia",
                       "mercado" if self.rng.random() < .35 else c.home_location, 30); return
        if n.social > 68:
            self.socialize(c); return
        if n.curiosity > 70:
            self.begin(c, "estudando novas ideias",
                       "biblioteca" if self.score(c, "curiosidade") >= 75 else "praca", 45); return
        choices = [
            ("trabalhando em um projeto", "laboratorio", 60, self.score(c, "organizacao") / 100),
            ("planejando melhorias para a cidade", "oficina", 50, self.score(c, "iniciativa") / 100),
            ("observando o movimento", "praca", 35, self.score(c, "curiosidade") / 130),
            ("descansando no parque", "parque", 40, max(.15, (100 - self.score(c, "ambicao")) / 150)),
            ("participando de assuntos coletivos", "prefeitura", 55, self.score(c, "lideranca") / 130),
        ]
        roll = self.rng.random() * sum(x[3] for x in choices)
        selected = choices[-1]
        for item in choices:
            roll -= item[3]
            if roll <= 0:
                selected = item; break
        self.begin(c, selected[0], selected[1], selected[2])

    async def snapshot(self) -> dict[str, Any]:
        async with self.lock:
            return {
                "city": {"name": self.city_name, "day": self.day, "minute": self.minute,
                         "time": f"{self.minute // 60:02d}:{self.minute % 60:02d}",
                         "running": self.running, "minutes_per_tick": MINUTES_PER_TICK,
                         "tick_seconds": TICK_SECONDS},
                "locations": list(self.locations.values()),
                "characters": [c.public() for c in sorted(self.characters.values(), key=lambda x: x.public_name)],
                "events": self.storage.events(30),
            }

    async def detail(self, cid: str) -> dict[str, Any] | None:
        async with self.lock:
            c = self.characters.get(cid)
            if not c: return None
            result = c.public()
            result["profile"] = c.profile
            result["relationships"] = [x for x in self.storage.relationships() if x["character_a"] == cid]
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


app = FastAPI(title="Cidade Zero", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "engine_running": engine.running,
            "character_count": len(engine.characters), "database": str(DATABASE_PATH)}


@app.get("/api/state")
async def state() -> dict[str, Any]:
    return await engine.snapshot()


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
async def manual_tick(minutes: int = Query(5, ge=1, le=1440),
                      x_admin_token: str | None = Header(None)) -> dict[str, Any]:
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
