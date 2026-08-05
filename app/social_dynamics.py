from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.intelligence import AIDecision


class BondStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        return db

    @staticmethod
    def pair(a: str, b: str) -> tuple[str, str]:
        first, second = sorted((a, b))
        return first, second

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS social_bonds (
                    character_a TEXT NOT NULL,
                    character_b TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'acquaintance',
                    positive_interactions INTEGER NOT NULL DEFAULT 0,
                    romantic_interactions INTEGER NOT NULL DEFAULT 0,
                    started_day INTEGER,
                    updated_day INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY(character_a, character_b)
                );
                CREATE TABLE IF NOT EXISTS autonomy_state (
                    character_id TEXT PRIMARY KEY,
                    last_intention TEXT NOT NULL DEFAULT '',
                    last_action TEXT NOT NULL DEFAULT '',
                    last_decision_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def get(self, a: str, b: str) -> dict[str, Any]:
        first, second = self.pair(a, b)
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM social_bonds WHERE character_a=? AND character_b=?",
                (first, second),
            ).fetchone()
        return dict(row) if row else {
            "character_a": first,
            "character_b": second,
            "status": "acquaintance",
            "positive_interactions": 0,
            "romantic_interactions": 0,
            "started_day": None,
            "updated_day": 1,
        }

    def record(
        self,
        a: str,
        b: str,
        *,
        day: int,
        positive: int = 0,
        romantic: int = 0,
        force_status: str | None = None,
    ) -> dict[str, Any]:
        first, second = self.pair(a, b)
        current = self.get(first, second)
        positives = max(0, int(current["positive_interactions"]) + positive)
        romances = max(0, int(current["romantic_interactions"]) + romantic)
        status = force_status or str(current["status"])
        started_day = current.get("started_day")

        if force_status is None:
            if romances >= 3 and status in {"acquaintance", "friend", "close_friend"}:
                status = "dating"
                started_day = started_day or day
            elif positives >= 8 and status == "friend":
                status = "close_friend"
            elif positives >= 3 and status == "acquaintance":
                status = "friend"

        with self.connect() as db:
            db.execute(
                """
                INSERT INTO social_bonds(
                    character_a,character_b,status,positive_interactions,
                    romantic_interactions,started_day,updated_day
                ) VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(character_a,character_b) DO UPDATE SET
                    status=excluded.status,
                    positive_interactions=excluded.positive_interactions,
                    romantic_interactions=excluded.romantic_interactions,
                    started_day=excluded.started_day,
                    updated_day=excluded.updated_day
                """,
                (first, second, status, positives, romances, started_day, day),
            )
        return self.get(first, second)

    def save_decision(self, character_id: str, decision: AIDecision) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO autonomy_state(
                    character_id,last_intention,last_action,last_decision_json
                ) VALUES(?,?,?,?)
                ON CONFLICT(character_id) DO UPDATE SET
                    last_intention=excluded.last_intention,
                    last_action=excluded.last_action,
                    last_decision_json=excluded.last_decision_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    character_id,
                    decision.public_intention,
                    decision.selected_action,
                    json.dumps(decision.public(), ensure_ascii=False),
                ),
            )

    def all(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM social_bonds ORDER BY updated_day DESC"
                ).fetchall()
            ]


class SocialDynamics:
    SOCIAL_ACTIONS = {
        "socialize",
        "help",
        "apologize",
        "confront",
        "romantic_approach",
        "propose_commitment",
        "end_relationship",
        "negotiate",
    }

    def __init__(self, engine: Any, bonds: BondStore) -> None:
        self.engine = engine
        self.bonds = bonds

    @staticmethod
    def score(character: Any, key: str, default: int = 50) -> int:
        try:
            return max(
                0,
                min(
                    100,
                    int(character.profile.get("behavioral_scores", {}).get(key, default)),
                ),
            )
        except (TypeError, ValueError):
            return default

    def target_for(self, actor: Any, requested: str | None) -> Any | None:
        if requested:
            target = self.engine.characters.get(requested)
            if target and target.character_id != actor.character_id:
                return target
        candidates = [
            item
            for item in self.engine.characters.values()
            if item.character_id != actor.character_id
        ]
        if not candidates:
            return None
        weights = []
        for target in candidates:
            relation = self.engine.storage.relationship(
                actor.character_id, target.character_id
            )
            weights.append(
                max(
                    1.0,
                    float(relation["affinity"])
                    + float(relation["trust"]) * 0.5
                    + float(relation["familiarity"]) * 0.2,
                )
            )
        return self.engine.rng.choices(candidates, weights=weights, k=1)[0]

    def acceptance(self, actor: Any, target: Any, action: str) -> float:
        relation = self.engine.storage.relationship(
            target.character_id, actor.character_id
        )
        value = (
            float(relation["affinity"]) * 0.34
            + float(relation["trust"]) * 0.33
            + float(relation["familiarity"]) * 0.18
            + self.score(target, "empatia_aparente") * 0.08
            + self.score(target, "flexibilidade_opiniao") * 0.07
            - target.needs.stress * 0.18
        )
        if target.life.current_activity in {"sleep", "work", "care"}:
            value -= 18
        if action == "confront":
            value += self.score(target, "assertividade") * 0.08
        if action in {"romantic_approach", "propose_commitment"}:
            value += self.score(target, "extroversao") * 0.05
            value -= self.score(target, "cautela") * 0.05
        return max(0.0, min(100.0, value))

    def apply(self, actor: Any, ai: AIDecision) -> bool:
        target = self.target_for(actor, ai.target_character)
        if target is None:
            return False

        relation = self.engine.storage.relationship(
            actor.character_id, target.character_id
        )
        acceptance = self.acceptance(actor, target, ai.selected_action)
        accepted = self.engine.rng.random() * 100 < acceptance
        location = target.location
        if self.engine.locations.get(location, {}).get("kind") == "home":
            location = (
                ai.target_location
                if ai.target_location in self.engine.locations
                else "cafe"
            )

        actor.location = target.location = location
        actor.activity_until = target.activity_until = (
            self.engine.absolute_minute + ai.duration_minutes
        )
        actor.life.current_activity = target.life.current_activity = "social"

        action = ai.selected_action
        spoken = f' e disse: “{ai.spoken_line}”' if ai.spoken_line else ""
        event_type = "interaction"
        summary = (
            f"{actor.public_name} procurou {target.public_name} para "
            f"{ai.public_intention.lower()}{spoken}."
        )
        affinity_delta, trust_delta = 1.0, 0.8
        positive, romantic = 1, 0
        force_status = None
        valence, importance = 0.2, 3

        if action == "confront":
            actor.action = f"confrontando {target.public_name}"
            target.action = f"respondendo a {actor.public_name}"
            actor.needs.stress += 7
            target.needs.stress += 6
            event_type = "conflict"
            affinity_delta, trust_delta = -4.0, -3.0
            positive, valence, importance = -1, -0.6, 4
            summary = (
                f"{actor.public_name} confrontou {target.public_name} "
                f"por considerar importante {ai.public_intention.lower()}{spoken}."
            )
        elif action == "help":
            actor.action = f"oferecendo ajuda a {target.public_name}"
            target.action = f"conversando com {actor.public_name}"
            transfer = 0.0
            if accepted and target.life.money < 6 and actor.life.money > 35:
                transfer = min(8.0, actor.life.money - 30)
                actor.life.money -= transfer
                target.life.money += transfer
            event_type = "support"
            affinity_delta, trust_delta = (2.5, 2.0) if accepted else (0.5, 0.2)
            positive, valence = (2, 0.55) if accepted else (0, 0.05)
            summary = (
                f"{actor.public_name} ofereceu ajuda a {target.public_name}"
                + (f" e transferiu {transfer:.0f} créditos" if transfer else "")
                + f"{spoken}."
            )
        elif action == "apologize":
            actor.action = f"tentando se desculpar com {target.public_name}"
            target.action = (
                f"ouvindo {actor.public_name}"
                if accepted
                else f"mantendo distância de {actor.public_name}"
            )
            if accepted:
                event_type = "relationship"
                affinity_delta, trust_delta = 2.5, 3.5
                positive, valence = 2, 0.55
                summary = (
                    f"{target.public_name} aceitou ouvir o pedido de desculpas "
                    f"de {actor.public_name}{spoken}."
                )
            else:
                event_type = "rejection"
                affinity_delta, trust_delta = -0.5, 0.0
                positive, valence = 0, -0.2
                summary = (
                    f"{target.public_name} não quis retomar a conversa com "
                    f"{actor.public_name} naquele momento."
                )
        elif action == "romantic_approach":
            enough_history = (
                float(relation["familiarity"]) >= 20
                and float(relation["affinity"]) >= 48
            )
            accepted = accepted and enough_history
            actor.action = f"expressando interesse afetivo por {target.public_name}"
            target.action = f"conversando em particular com {actor.public_name}"
            importance = 5
            if accepted:
                event_type = "romantic_signal"
                affinity_delta, trust_delta = 3.2, 2.2
                positive, romantic, valence = 2, 1, 0.65
                summary = (
                    f"{actor.public_name} demonstrou interesse afetivo por "
                    f"{target.public_name}, que recebeu a aproximação de forma positiva"
                    f"{spoken}."
                )
            else:
                event_type = "rejection"
                affinity_delta, trust_delta = -1.0, -0.4
                positive, valence = 0, -0.4
                summary = (
                    f"{target.public_name} não correspondeu à aproximação afetiva "
                    f"de {actor.public_name}."
                )
        elif action == "propose_commitment":
            bond = self.bonds.get(actor.character_id, target.character_id)
            days = self.engine.day - int(bond["started_day"] or self.engine.day)
            eligible = bond["status"] in {"dating", "committed"}
            accepted = (
                accepted and eligible and days >= 4 and float(relation["trust"]) >= 60
            )
            actor.action = f"fazendo uma proposta a {target.public_name}"
            target.action = f"respondendo a {actor.public_name}"
            importance = 5
            if accepted:
                force_status = (
                    "married"
                    if bond["status"] == "committed" and days >= 12
                    else "committed"
                )
                event_type = "relationship"
                affinity_delta, trust_delta = 3.0, 4.0
                positive, romantic, valence = 2, 2, 0.8
                label = "casamento" if force_status == "married" else "compromisso"
                summary = (
                    f"{actor.public_name} e {target.public_name} aceitaram assumir "
                    f"um {label} após uma aproximação gradual."
                )
            else:
                event_type = "rejection"
                affinity_delta, trust_delta = -1.0, -0.5
                positive, valence = 0, -0.45
                summary = (
                    f"{target.public_name} não aceitou a proposta de compromisso "
                    f"de {actor.public_name} naquele momento."
                )
        elif action == "end_relationship":
            bond = self.bonds.get(actor.character_id, target.character_id)
            if bond["status"] not in {"dating", "committed", "married"}:
                return False
            actor.action = f"encerrando o vínculo com {target.public_name}"
            target.action = f"processando o fim do vínculo com {actor.public_name}"
            force_status = "separated"
            event_type = "relationship"
            affinity_delta, trust_delta = -5.0, -4.0
            positive, valence, importance = -2, -0.75, 5
            summary = (
                f"{actor.public_name} decidiu encerrar o vínculo afetivo com "
                f"{target.public_name}."
            )
        else:
            actor.action = (
                f"negociando com {target.public_name}"
                if action == "negotiate"
                else f"conversando com {target.public_name}"
            )
            target.action = f"conversando com {actor.public_name}"
            actor.needs.social -= 12
            target.needs.social -= 7
            actor.needs.stress -= 2
            target.needs.stress -= 1
            if action == "negotiate" and not accepted:
                event_type = "rejection"
                affinity_delta, trust_delta = -0.5, -0.8
                positive, valence = 0, -0.2

        actor.needs.clamp()
        target.needs.clamp()
        actor.life.clamp()
        target.life.clamp()
        self.engine.storage.relation_delta(
            actor.character_id,
            target.character_id,
            affinity_delta,
            trust_delta,
            3,
        )
        self.engine.storage.relation_delta(
            target.character_id,
            actor.character_id,
            affinity_delta * 0.8,
            trust_delta * 0.8,
            3,
        )
        self.bonds.record(
            actor.character_id,
            target.character_id,
            day=self.engine.day,
            positive=positive,
            romantic=romantic,
            force_status=force_status,
        )
        self.engine.storage.save_character(target)
        self.engine.storage.event(
            self.engine.day,
            self.engine.minute,
            event_type,
            summary,
            actor.character_id,
            target.character_id,
            location,
            {
                "ai_directed": True,
                "selected_action": action,
                "accepted": accepted,
                "acceptance_score": round(acceptance, 1),
                "public_justification": ai.short_justification,
            },
        )
        for resident, related in ((actor, target), (target, actor)):
            self.engine.storage.memory(
                resident.character_id,
                self.engine.day,
                self.engine.minute,
                event_type,
                summary,
                valence=valence,
                importance=importance,
                related_character_id=related.character_id,
                location=location,
            )
        return True
