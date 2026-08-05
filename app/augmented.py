from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from types import MethodType
from typing import Any

from fastapi import HTTPException, Query

from app import main as core
from app.intelligence import (
    AIDecision,
    IntelligenceConfig,
    IntelligenceError,
    OpenAIAdapter,
    UsageLedger,
)
from app.journal import JournalStore
from app.social_dynamics import BondStore, SocialDynamics


AUTONOMY_ADDENDUM = """
AUTONOMIA NA CIDADE ZERO
- Você vive sem roteiro, temporada, missão global ou obrigação de produzir drama.
- Pode formar qualquer intenção pessoal compatível com as experiências vividas.
- A intenção pode ser ampla e inédita; selected_action representa somente o próximo
  passo executável dentro da realidade atual.
- Você não controla os outros moradores. Convites, pedidos e propostas podem ser
  aceitos ou recusados de forma independente.
- Você pode rever objetivos, mudar hábitos, criar projetos, trocar de trabalho,
  aproximar-se ou afastar-se de alguém e questionar instituições.
- O servidor decide recursos, resultados e consequências. Não declare sucesso antes
  que o mundo confirme.
- Conflitos graves são representados de forma não gráfica e nunca dão acesso a
  ferramentas, sistemas ou pessoas fora da simulação.
- Responda somente no JSON exigido.
""".strip()


@dataclass
class IntelligenceJob:
    kind: str
    request_uuid: str
    city_day: int
    city_minute: int
    context: dict[str, Any]
    character_id: str | None = None
    system_prompt: str = ""


class AutonomyRuntime:
    def __init__(self) -> None:
        self.engine = core.engine
        self.app = core.app
        self.config = IntelligenceConfig.from_env()
        self.ledger = UsageLedger(core.DATABASE_PATH)
        self.journal = JournalStore(core.DATABASE_PATH)
        self.bonds = BondStore(core.DATABASE_PATH)
        self.social = SocialDynamics(self.engine, self.bonds)
        self.adapter = OpenAIAdapter(self.config)
        self.queue: asyncio.Queue[IntelligenceJob] = asyncio.Queue()
        self.pending_characters: set[str] = set()
        self.results: dict[str, AIDecision] = {}
        self.worker_task: asyncio.Task[None] | None = None
        self.prompts: dict[str, str] = {}

        self.original_start = self.engine.start
        self.original_stop = self.engine.stop
        self.original_choose_action = self.engine.choose_action
        self.original_start_new_day = self.engine.start_new_day
        self.original_snapshot = self.engine.snapshot

        self.ledger.initialize()
        self.journal.initialize()
        self.bonds.initialize()
        self._load_prompts()
        self._bind()

    def _load_prompts(self) -> None:
        registry = json.loads(core.REGISTRY_PATH.read_text(encoding="utf-8"))
        for entry in registry.get("characters", []):
            character_id = str(entry.get("character_id") or "")
            prompt_path = entry.get("prompt_path")
            if not character_id or not prompt_path:
                continue
            resolved = (core.REGISTRY_PATH.parent / str(prompt_path)).resolve()
            try:
                self.prompts[character_id] = resolved.read_text(encoding="utf-8")
            except OSError:
                self.prompts[character_id] = ""

    def _bind(self) -> None:
        runtime = self

        async def start_wrapper(_: Any) -> None:
            await runtime.original_start()
            runtime.journal.ensure_backfill(runtime.engine.day, days=14)
            if runtime.worker_task is None or runtime.worker_task.done():
                runtime.worker_task = asyncio.create_task(
                    runtime.worker(), name="cidade-zero-openai-worker"
                )

        async def stop_wrapper(_: Any) -> None:
            if runtime.worker_task:
                runtime.worker_task.cancel()
                try:
                    await runtime.worker_task
                except asyncio.CancelledError:
                    pass
                runtime.worker_task = None
            await runtime.original_stop()

        def choose_action_wrapper(_: Any, character: Any) -> None:
            runtime.choose_action(character)

        def start_new_day_wrapper(_: Any) -> None:
            previous_day = runtime.engine.day - 1
            runtime.original_start_new_day()
            if previous_day >= 1:
                runtime.close_journal_day(previous_day)

        async def snapshot_wrapper(_: Any) -> dict[str, Any]:
            state = await runtime.original_snapshot()
            state["city"]["engine_version"] = "society-ai-0.4"
            state["intelligence"] = runtime.status()
            latest = runtime.journal.latest()
            state["journal"] = {
                "latest_day": latest.get("city_day") if latest else None,
                "title": latest.get("title") if latest else None,
                "latest_event_id": runtime.journal.max_event_id(),
            }
            return state

        self.engine.start = MethodType(start_wrapper, self.engine)
        self.engine.stop = MethodType(stop_wrapper, self.engine)
        self.engine.choose_action = MethodType(choose_action_wrapper, self.engine)
        self.engine.start_new_day = MethodType(start_new_day_wrapper, self.engine)
        self.engine.snapshot = MethodType(snapshot_wrapper, self.engine)

    def status(self) -> dict[str, Any]:
        usage = self.ledger.summary()
        return {
            **self.config.public(),
            **usage,
            "remaining_calls_today": max(
                0, self.config.max_calls_per_day - int(usage["calls"])
            ),
            "pending_characters": sorted(self.pending_characters),
            "fallback_local_available": True,
        }

    def _can_enqueue(self, character: Any) -> bool:
        if not self.config.enabled:
            return False
        if character.character_id in self.pending_characters:
            return False
        if self.ledger.calls_today() >= self.config.max_calls_per_day:
            return False

        last = self.ledger.last_successful_city_minute(character.character_id)
        if last is not None:
            elapsed = self.engine.absolute_minute - last
            if elapsed < self.config.character_cooldown_city_minutes:
                return False

        needs = character.needs
        return not (needs.health < 28 or needs.energy < 8 or needs.hunger > 96)

    def choose_action(self, character: Any) -> None:
        result = self.results.pop(character.character_id, None)
        if result is not None:
            self.bonds.save_decision(character.character_id, result)
            if self.apply_ai_decision(character, result):
                return

        if character.character_id in self.pending_characters:
            self.engine.begin(
                character,
                core.Decision(
                    "pensando com calma no próximo passo",
                    character.location,
                    5,
                    "reflect",
                    "reservou alguns minutos para decidir o que realmente queria fazer",
                    needs_delta={"stress": -0.5, "autonomy": -1},
                    importance=1,
                    valence=0.05,
                ),
            )
            return

        if self._can_enqueue(character):
            self.enqueue_character(character)
            self.engine.begin(
                character,
                core.Decision(
                    "avaliando possibilidades para o próprio dia",
                    character.location,
                    5,
                    "reflect",
                    "parou por alguns minutos antes de escolher o próximo passo",
                    needs_delta={"stress": -0.5},
                    importance=1,
                    valence=0.05,
                ),
            )
            return

        self.original_choose_action(character)

    def enqueue_character(self, character: Any) -> None:
        context = self.character_context(character)
        request_uuid = self.ledger.begin(
            city_day=self.engine.day,
            city_minute=self.engine.minute,
            character_id=character.character_id,
            request_type="character_decision",
            model=self.config.model,
            context=context,
        )
        self.pending_characters.add(character.character_id)
        prompt = self.prompts.get(character.character_id, "").strip() or (
            "Você é uma personagem adulta e ficcional da Cidade Zero. "
            "Decida a partir do perfil e do estado fornecidos."
        )
        self.queue.put_nowait(
            IntelligenceJob(
                kind="decision",
                request_uuid=request_uuid,
                city_day=self.engine.day,
                city_minute=self.engine.minute,
                context=context,
                character_id=character.character_id,
                system_prompt=f"{prompt}\n\n{AUTONOMY_ADDENDUM}",
            )
        )

    def character_context(self, character: Any) -> dict[str, Any]:
        names = {
            item.character_id: item.public_name
            for item in self.engine.characters.values()
        }
        relationships = []
        for relation in self.engine.storage.relationships():
            if relation["character_a"] != character.character_id:
                continue
            relationships.append(
                {
                    **relation,
                    "public_name": names.get(
                        relation["character_b"], relation["character_b"]
                    ),
                    "bond": self.bonds.get(
                        character.character_id, relation["character_b"]
                    )["status"],
                }
            )

        visible_others = [
            {
                "character_id": other.character_id,
                "public_name": other.public_name,
                "location": other.location,
                "action": other.action,
                "mood": other.mood,
            }
            for other in self.engine.characters.values()
            if other.character_id != character.character_id
        ]

        return {
            "simulation": {
                "fictional": True,
                "city_day": self.engine.day,
                "city_time": f"{self.engine.minute // 60:02d}:"
                f"{self.engine.minute % 60:02d}",
                "current_city_issue": self.engine.city_issue,
            },
            "self": {
                **character.public(),
                "profile": {
                    "operational_profile": character.profile.get(
                        "operational_profile", {}
                    ),
                    "behavioral_scores": character.profile.get(
                        "behavioral_scores", {}
                    ),
                    "top_tendencies": character.profile.get("top_tendencies", []),
                    "low_tendencies": character.profile.get("low_tendencies", []),
                    "source_status": character.profile.get("source_status", {}),
                },
            },
            "relationships": relationships,
            "memories": self.engine.storage.memories(character.character_id, 16),
            "visible_residents": visible_others,
            "available_locations": [
                {
                    "id": location_id,
                    "name": value.get("name", location_id),
                    "kind": value.get("kind", "public"),
                }
                for location_id, value in self.engine.locations.items()
            ],
            "available_actions": list(self.action_contract()),
            "world_rules": [
                "Você pode desejar qualquer coisa, mas deve escolher um próximo passo executável.",
                "O estado do motor é a única realidade oficial.",
                "Não invente dinheiro, objetos, locais, falas ou consentimento de terceiros.",
                "Outros moradores podem recusar qualquer aproximação ou proposta.",
                "Use somente memory_ids presentes no contexto.",
                "A justificativa deve ser pública e curta, sem cadeia de pensamento.",
            ],
        }

    @staticmethod
    def action_contract() -> tuple[dict[str, str], ...]:
        return (
            {"id": "sleep", "meaning": "dormir em casa"},
            {"id": "rest", "meaning": "descansar"},
            {"id": "eat", "meaning": "buscar ou preparar comida"},
            {"id": "work", "meaning": "cumprir ou retomar trabalho"},
            {"id": "shop", "meaning": "comprar mantimentos"},
            {"id": "study", "meaning": "estudar ou pesquisar"},
            {"id": "hygiene", "meaning": "cuidar da higiene em privado"},
            {"id": "seek_health", "meaning": "procurar atendimento"},
            {"id": "socialize", "meaning": "conversar sem objetivo específico"},
            {"id": "help", "meaning": "oferecer apoio a alguém"},
            {"id": "apologize", "meaning": "tentar reparar uma relação"},
            {"id": "confront", "meaning": "confrontar alguém verbalmente"},
            {"id": "romantic_approach", "meaning": "expressar interesse afetivo"},
            {"id": "propose_commitment", "meaning": "propor compromisso a vínculo existente"},
            {"id": "end_relationship", "meaning": "encerrar vínculo afetivo"},
            {"id": "negotiate", "meaning": "negociar com alguém"},
            {"id": "pursue_goal", "meaning": "dar um passo no objetivo pessoal"},
            {"id": "create_project", "meaning": "iniciar projeto próprio"},
            {"id": "change_job", "meaning": "buscar ou efetivar mudança de trabalho"},
            {"id": "move_home", "meaning": "buscar mudança de moradia"},
            {"id": "form_group", "meaning": "organizar grupo ou associação"},
            {"id": "protest", "meaning": "manifestar oposição de forma civil"},
            {"id": "withdraw", "meaning": "afastar-se e buscar privacidade"},
            {"id": "explore", "meaning": "explorar a cidade"},
        )

    async def worker(self) -> None:
        while True:
            job = await self.queue.get()
            try:
                if job.kind == "decision":
                    result = await self.adapter.decide(job.system_prompt, job.context)
                    decision = AIDecision.from_payload(result.payload)
                    self.ledger.complete(job.request_uuid, result)
                    if job.character_id:
                        self.results[job.character_id] = decision
                elif job.kind == "journal":
                    result = await self.adapter.write_news(job.context)
                    self.ledger.complete(job.request_uuid, result)
                    self.journal.apply_ai_edition(job.city_day, result.payload)
            except (IntelligenceError, ValueError, TypeError) as exc:
                self.ledger.fail(job.request_uuid, str(exc))
            except Exception as exc:
                self.ledger.fail(job.request_uuid, f"Erro inesperado: {exc}")
            finally:
                if job.character_id:
                    self.pending_characters.discard(job.character_id)
                self.queue.task_done()

    def close_journal_day(self, city_day: int) -> None:
        edition = self.journal.build_local_edition(city_day)
        if (
            not self.config.enabled
            or self.ledger.calls_today() >= self.config.max_calls_per_day
            or edition.get("ai_generated")
        ):
            return
        context = self.journal.context_for_ai(city_day)
        if not context.get("events"):
            return
        request_uuid = self.ledger.begin(
            city_day=city_day,
            city_minute=1439,
            character_id=None,
            request_type="journal_edition",
            model=self.config.model,
            context=context,
        )
        self.queue.put_nowait(
            IntelligenceJob(
                kind="journal",
                request_uuid=request_uuid,
                city_day=city_day,
                city_minute=1439,
                context=context,
            )
        )

    def location(self, requested: str | None, fallback: str) -> str:
        if requested and requested in self.engine.locations:
            return requested
        return fallback if fallback in self.engine.locations else "praca"

    def set_goal(self, character: Any, ai: AIDecision) -> None:
        new_goal = ai.new_goal or ai.public_intention
        if not new_goal or new_goal == character.life.current_goal:
            return
        old_goal = character.life.current_goal
        character.life.current_goal = new_goal[:240]
        self.engine.storage.event(
            self.engine.day,
            self.engine.minute,
            "goal_change",
            f"{character.public_name} passou a priorizar: {character.life.current_goal}.",
            character.character_id,
            location=character.location,
            payload={"previous_goal": old_goal},
        )

    def apply_ai_decision(self, character: Any, ai: AIDecision) -> bool:
        self.set_goal(character, ai)
        if ai.selected_action in self.social.SOCIAL_ACTIONS:
            return self.social.apply(character, ai)

        action = ai.selected_action
        duration = ai.duration_minutes
        decision: Any

        if action == "sleep":
            decision = core.Decision(
                "dormindo em casa", character.home_location, max(30, duration),
                "sleep", "decidiu dormir e recuperar energia",
                importance=1, valence=0.2,
            )
        elif action == "rest":
            decision = core.Decision(
                "descansando e reduzindo o ritmo",
                self.location(ai.target_location, "parque"), duration,
                "leisure", ai.public_intention,
                needs_delta={"stress": -5, "fun": -3, "autonomy": -4},
                importance=2, valence=0.25,
            )
        elif action == "eat":
            if character.life.food_stock >= 8:
                decision = core.Decision(
                    "preparando uma refeição em casa", character.home_location,
                    duration, "meal",
                    "decidiu usar os mantimentos de casa para se alimentar",
                    life_delta={"food_stock": -8}, importance=2, valence=0.25,
                )
            elif character.life.money >= 9:
                decision = core.Decision(
                    "comprando mantimentos no mercado", "mercado", duration,
                    "shopping", "foi ao mercado antes de preparar a próxima refeição",
                    life_delta={"money": -9, "food_stock": 34},
                    importance=3, valence=0.1,
                )
            else:
                return False
        elif action == "shop":
            if character.life.money < 6:
                return False
            spend = min(12.0, max(6.0, character.life.money * 0.12))
            decision = core.Decision(
                "comprando mantimentos e itens básicos", "mercado", duration,
                "shopping", ai.public_intention,
                life_delta={"money": -spend, "food_stock": 28},
                importance=2, valence=0.1,
            )
        elif action == "work":
            decision = core.Decision(
                f"trabalhando como {character.life.job_title}",
                character.life.work_location, duration, "work",
                ai.public_intention, needs_delta={"purpose": -4},
                importance=3, valence=0.25,
            )
        elif action == "study":
            decision = core.Decision(
                "pesquisando uma questão que considera importante",
                self.location(ai.target_location, "biblioteca"), duration,
                "study", ai.public_intention,
                importance=2, valence=0.25,
            )
        elif action == "hygiene":
            decision = core.Decision(
                "cuidando da higiene em um momento privado",
                character.home_location, duration, "hygiene",
                "reservou um momento privado para cuidar de si",
                importance=1, valence=0.15,
            )
        elif action == "seek_health":
            decision = core.Decision(
                "procurando atendimento na clínica", "clinica", duration,
                "care", ai.public_intention,
                needs_delta={"stress": -3, "health": 3},
                life_delta={"money": -min(5, character.life.money)},
                importance=4, valence=0.15,
            )
        elif action == "withdraw":
            decision = core.Decision(
                "passando um tempo sozinho e preservando a própria privacidade",
                character.home_location, duration, "leisure",
                ai.public_intention,
                needs_delta={"autonomy": -12, "stress": -4, "social": 3},
                importance=2, valence=0.1,
            )
        elif action == "explore":
            public_locations = [
                key for key, item in self.engine.locations.items()
                if item.get("kind") != "home"
            ]
            fallback = self.engine.rng.choice(public_locations or ["praca"])
            decision = core.Decision(
                "explorando um lugar diferente da cidade",
                self.location(ai.target_location, fallback), duration,
                "leisure", ai.public_intention,
                needs_delta={"curiosity": -7, "autonomy": -4},
                importance=2, valence=0.25,
            )
        elif action == "create_project":
            if character.life.money < 5:
                return False
            decision = core.Decision(
                "iniciando um projeto próprio",
                self.location(ai.target_location, "oficina"), duration,
                "initiative", ai.public_intention,
                life_delta={"money": -5, "reputation": 0.5},
                needs_delta={"purpose": -7, "autonomy": -5},
                importance=4, valence=0.35,
            )
        elif action == "change_job":
            target = self.location(ai.target_location, "prefeitura")
            if self.engine.locations.get(target, {}).get("kind") == "home":
                target = "prefeitura"
            character.life.work_location = target
            character.life.job_title = (
                f"profissional em {self.engine.locations.get(target, {}).get('name', target)}"
            )
            decision = core.Decision(
                "organizando uma mudança de trabalho", target, duration,
                "initiative", ai.public_intention,
                needs_delta={"autonomy": -8, "stress": 3},
                life_delta={"reputation": -0.5},
                importance=5, valence=0.15,
            )
        elif action == "move_home":
            decision = core.Decision(
                "pesquisando possibilidades de uma nova moradia",
                "prefeitura", duration, "initiative", ai.public_intention,
                needs_delta={"autonomy": -6, "comfort": -3},
                importance=4, valence=0.1,
            )
        elif action == "form_group":
            decision = core.Decision(
                "convidando moradores para formar um grupo",
                self.location(ai.target_location, "centro_comunitario"),
                duration, "community", ai.public_intention,
                needs_delta={"purpose": -6, "social": -5},
                life_delta={"reputation": 1},
                importance=5, valence=0.25,
            )
        elif action == "protest":
            decision = core.Decision(
                "manifestando publicamente sua discordância",
                self.location(ai.target_location, "prefeitura"),
                duration, "community", ai.public_intention,
                needs_delta={"autonomy": -8, "stress": 2},
                life_delta={"reputation": 0.5},
                importance=5, valence=0.0,
            )
        else:
            decision = core.Decision(
                "dando um passo concreto no próprio objetivo",
                self.location(ai.target_location, "oficina"),
                duration, "initiative", ai.public_intention,
                needs_delta={"purpose": -6, "autonomy": -4},
                importance=3, valence=0.3,
            )

        self.engine.begin(character, decision)
        return True


runtime = AutonomyRuntime()
app = runtime.app
engine = runtime.engine


@app.get("/api/intelligence")
async def intelligence_status() -> dict[str, Any]:
    return runtime.status()


@app.get("/api/journal")
async def journal_latest() -> dict[str, Any]:
    latest = runtime.journal.latest()
    if latest is None:
        latest = runtime.journal.build_local_edition(max(1, runtime.engine.day - 1))
    return latest


@app.get("/api/journal/editions")
async def journal_editions(
    limit: int = Query(30, ge=1, le=365),
) -> list[dict[str, Any]]:
    return runtime.journal.editions(limit)


@app.get("/api/journal/editions/{city_day}")
async def journal_edition(city_day: int) -> dict[str, Any]:
    edition = runtime.journal.edition(city_day)
    if edition is None:
        if city_day >= runtime.engine.day or city_day < 1:
            raise HTTPException(404, "Edição não encontrada")
        edition = runtime.journal.build_local_edition(city_day)
    return edition


@app.get("/api/journal/since")
async def journal_since(
    after_event_id: int = Query(0, ge=0),
) -> dict[str, Any]:
    return runtime.journal.brief_since(after_event_id)


@app.get("/api/bonds")
async def social_bonds() -> list[dict[str, Any]]:
    return runtime.bonds.all()
