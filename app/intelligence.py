from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


ACTION_KINDS = (
    "sleep",
    "rest",
    "eat",
    "work",
    "shop",
    "study",
    "hygiene",
    "seek_health",
    "socialize",
    "help",
    "apologize",
    "confront",
    "romantic_approach",
    "propose_commitment",
    "end_relationship",
    "negotiate",
    "pursue_goal",
    "create_project",
    "change_job",
    "move_home",
    "form_group",
    "protest",
    "withdraw",
    "explore",
)

DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "current_emotion": {"type": "string", "maxLength": 80},
        "public_intention": {"type": "string", "maxLength": 240},
        "selected_action": {"type": "string", "enum": list(ACTION_KINDS)},
        "target_character": {"type": ["string", "null"]},
        "target_location": {"type": ["string", "null"]},
        "spoken_line": {"type": ["string", "null"], "maxLength": 300},
        "short_justification": {"type": "string", "maxLength": 300},
        "new_goal": {"type": ["string", "null"], "maxLength": 240},
        "memory_ids_used": {
            "type": "array",
            "items": {"type": "integer"},
            "maxItems": 12,
        },
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        "urgency": {"type": "integer", "minimum": 0, "maximum": 100},
        "duration_minutes": {"type": "integer", "minimum": 5, "maximum": 180},
    },
    "required": [
        "current_emotion",
        "public_intention",
        "selected_action",
        "target_character",
        "target_location",
        "spoken_line",
        "short_justification",
        "new_goal",
        "memory_ids_used",
        "confidence",
        "urgency",
        "duration_minutes",
    ],
}

NEWS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "edition_title": {"type": "string", "maxLength": 120},
        "edition_summary": {"type": "string", "maxLength": 420},
        "articles": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "category": {"type": "string", "maxLength": 40},
                    "title": {"type": "string", "maxLength": 140},
                    "lead": {"type": "string", "maxLength": 360},
                    "body": {"type": "string", "maxLength": 900},
                    "event_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 12,
                        "items": {"type": "integer"},
                    },
                },
                "required": ["category", "title", "lead", "body", "event_ids"],
            },
        },
    },
    "required": ["edition_title", "edition_summary", "articles"],
}


class IntelligenceError(RuntimeError):
    pass


def _clean_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


@dataclass(frozen=True)
class IntelligenceConfig:
    api_key: str
    model: str = "gpt-4o-mini"
    max_calls_per_day: int = 300
    max_output_tokens: int = 300
    character_cooldown_city_minutes: int = 180
    request_timeout_seconds: float = 35.0
    temperature: float = 0.85

    @classmethod
    def from_env(cls) -> "IntelligenceConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
            max_calls_per_day=max(1, int(os.getenv("OPENAI_MAX_CALLS_PER_DAY", "300"))),
            max_output_tokens=max(120, int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "300"))),
            character_cooldown_city_minutes=max(
                30, int(os.getenv("OPENAI_CHARACTER_COOLDOWN_CITY_MINUTES", "180"))
            ),
            request_timeout_seconds=max(
                5.0, float(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "35"))
            ),
            temperature=max(0.0, min(1.5, float(os.getenv("OPENAI_TEMPERATURE", "0.85")))),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def public(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "model": self.model,
            "max_calls_per_day": self.max_calls_per_day,
            "max_output_tokens": self.max_output_tokens,
            "character_cooldown_city_minutes": self.character_cooldown_city_minutes,
        }


@dataclass(frozen=True)
class AIDecision:
    current_emotion: str
    public_intention: str
    selected_action: str
    target_character: str | None
    target_location: str | None
    spoken_line: str | None
    short_justification: str
    new_goal: str | None
    memory_ids_used: tuple[int, ...]
    confidence: int
    urgency: int
    duration_minutes: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AIDecision":
        action = str(payload.get("selected_action", ""))
        if action not in ACTION_KINDS:
            raise IntelligenceError(f"Ação não permitida no contrato: {action!r}")

        memory_ids: list[int] = []
        for raw in payload.get("memory_ids_used", []):
            try:
                memory_ids.append(int(raw))
            except (TypeError, ValueError):
                continue

        target_character = payload.get("target_character")
        target_location = payload.get("target_location")
        spoken_line = payload.get("spoken_line")
        new_goal = payload.get("new_goal")
        return cls(
            current_emotion=_clean_text(payload.get("current_emotion"), 80) or "neutro",
            public_intention=_clean_text(payload.get("public_intention"), 240)
            or "seguir a própria rotina",
            selected_action=action,
            target_character=_clean_text(target_character, 80) if target_character else None,
            target_location=_clean_text(target_location, 80) if target_location else None,
            spoken_line=_clean_text(spoken_line, 300) if spoken_line else None,
            short_justification=_clean_text(payload.get("short_justification"), 300)
            or "A decisão combina com a situação atual.",
            new_goal=_clean_text(new_goal, 240) if new_goal else None,
            memory_ids_used=tuple(memory_ids[:12]),
            confidence=max(0, min(100, int(payload.get("confidence", 50)))),
            urgency=max(0, min(100, int(payload.get("urgency", 50)))),
            duration_minutes=max(5, min(180, int(payload.get("duration_minutes", 35)))),
        )

    def public(self) -> dict[str, Any]:
        value = asdict(self)
        value["memory_ids_used"] = list(self.memory_ids_used)
        return value


@dataclass(frozen=True)
class OpenAIResult:
    payload: dict[str, Any]
    response_id: str
    request_id: str
    input_tokens: int
    output_tokens: int


class UsageLedger:
    """Persistent call audit. The API key is never written to SQLite."""

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
                CREATE TABLE IF NOT EXISTS ai_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_uuid TEXT NOT NULL UNIQUE,
                    real_date TEXT NOT NULL,
                    city_day INTEGER NOT NULL,
                    city_minute INTEGER NOT NULL,
                    character_id TEXT,
                    request_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    model TEXT NOT NULL,
                    context_hash TEXT NOT NULL,
                    response_id TEXT,
                    provider_request_id TEXT,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    response_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_ai_requests_real_date
                    ON ai_requests(real_date, status);
                CREATE INDEX IF NOT EXISTS idx_ai_requests_character
                    ON ai_requests(character_id, id DESC);
                """
            )

    @staticmethod
    def real_date() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def calls_today(self) -> int:
        with self.connect() as db:
            row = db.execute(
                "SELECT COUNT(*) AS total FROM ai_requests WHERE real_date=?",
                (self.real_date(),),
            ).fetchone()
        return int(row["total"] if row else 0)

    def begin(
        self,
        *,
        city_day: int,
        city_minute: int,
        character_id: str | None,
        request_type: str,
        model: str,
        context: dict[str, Any],
    ) -> str:
        request_uuid = str(uuid.uuid4())
        serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        context_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO ai_requests(
                    request_uuid,real_date,city_day,city_minute,character_id,
                    request_type,status,model,context_hash
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    request_uuid,
                    self.real_date(),
                    int(city_day),
                    int(city_minute),
                    character_id,
                    request_type,
                    "pending",
                    model,
                    context_hash,
                ),
            )
        return request_uuid

    def complete(self, request_uuid: str, result: OpenAIResult) -> None:
        with self.connect() as db:
            db.execute(
                """
                UPDATE ai_requests SET status='success',response_id=?,
                    provider_request_id=?,input_tokens=?,output_tokens=?,
                    response_json=?,completed_at=CURRENT_TIMESTAMP
                WHERE request_uuid=?
                """,
                (
                    result.response_id,
                    result.request_id,
                    result.input_tokens,
                    result.output_tokens,
                    json.dumps(result.payload, ensure_ascii=False),
                    request_uuid,
                ),
            )

    def fail(self, request_uuid: str, error: str) -> None:
        with self.connect() as db:
            db.execute(
                """
                UPDATE ai_requests SET status='error',error=?,
                    completed_at=CURRENT_TIMESTAMP WHERE request_uuid=?
                """,
                (_clean_text(error, 700), request_uuid),
            )

    def last_successful_city_minute(self, character_id: str) -> int | None:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT city_day,city_minute FROM ai_requests
                WHERE character_id=? AND status='success'
                ORDER BY id DESC LIMIT 1
                """,
                (character_id,),
            ).fetchone()
        if not row:
            return None
        return (int(row["city_day"]) - 1) * 1440 + int(row["city_minute"])

    def summary(self) -> dict[str, Any]:
        today = self.real_date()
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT status,COUNT(*) AS calls,
                    COALESCE(SUM(input_tokens),0) AS input_tokens,
                    COALESCE(SUM(output_tokens),0) AS output_tokens
                FROM ai_requests WHERE real_date=? GROUP BY status
                """,
                (today,),
            ).fetchall()
        totals = {
            "calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "pending_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
        for row in rows:
            count = int(row["calls"])
            totals["calls"] += count
            totals["input_tokens"] += int(row["input_tokens"])
            totals["output_tokens"] += int(row["output_tokens"])
            if row["status"] == "success":
                totals["successful_calls"] = count
            elif row["status"] == "error":
                totals["failed_calls"] = count
            elif row["status"] == "pending":
                totals["pending_calls"] = count
        totals["real_date_utc"] = today
        return totals


class OpenAIAdapter:
    """Small async HTTP adapter using Structured Outputs."""

    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, config: IntelligenceConfig) -> None:
        self.config = config

    async def _request(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
        schema_name: str,
        schema: dict[str, Any],
        max_tokens: int,
        temperature: float,
    ) -> OpenAIResult:
        if not self.config.enabled:
            raise IntelligenceError("OPENAI_API_KEY não configurada")

        client_request_id = str(uuid.uuid4())
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "X-Client-Request-Id": client_request_id,
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise IntelligenceError(f"Falha de rede ao consultar a OpenAI: {exc}") from exc

        provider_request_id = response.headers.get("x-request-id", "")
        if response.status_code >= 400:
            try:
                error_body = response.json()
                message = error_body.get("error", {}).get("message") or str(error_body)
            except (ValueError, TypeError):
                message = response.text
            raise IntelligenceError(
                f"OpenAI respondeu HTTP {response.status_code}: {_clean_text(message, 500)}"
            )

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IntelligenceError("Resposta estruturada inválida recebida da OpenAI") from exc

        usage = body.get("usage") or {}
        return OpenAIResult(
            payload=parsed,
            response_id=str(body.get("id") or ""),
            request_id=provider_request_id or client_request_id,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
        )

    async def decide(self, system_prompt: str, context: dict[str, Any]) -> OpenAIResult:
        return await self._request(
            system_prompt=system_prompt,
            context=context,
            schema_name="cidade_zero_decision",
            schema=DECISION_SCHEMA,
            max_tokens=self.config.max_output_tokens,
            temperature=self.config.temperature,
        )

    async def write_news(self, context: dict[str, Any]) -> OpenAIResult:
        system_prompt = (
            "Você é o redator automático e impessoal do Jornal Zero. "
            "Não é personagem e não participa da cidade. Relate somente os eventos fornecidos. "
            "Não invente entrevistas, pensamentos, causas, culpados ou resultados. "
            "Use tom jornalístico sóbrio em português do Brasil. "
            "Cada artigo deve citar apenas event_ids presentes no contexto."
        )
        return await self._request(
            system_prompt=system_prompt,
            context=context,
            schema_name="jornal_zero_edition",
            schema=NEWS_SCHEMA,
            max_tokens=max(500, self.config.max_output_tokens * 2),
            temperature=0.35,
        )
