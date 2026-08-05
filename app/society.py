from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class HumanNeeds:
    """Deprivation values are high-is-bad, except energy and health."""

    energy: float = 82.0
    hunger: float = 18.0
    social: float = 38.0
    curiosity: float = 55.0
    hygiene: float = 18.0
    stress: float = 22.0
    fun: float = 34.0
    comfort: float = 20.0
    purpose: float = 36.0
    autonomy: float = 24.0
    health: float = 92.0

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "HumanNeeds":
        if not isinstance(value, dict):
            return cls()
        allowed = cls.__dataclass_fields__
        clean = {key: raw for key, raw in value.items() if key in allowed}
        return cls(**clean)

    def clamp(self) -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, max(0.0, min(100.0, float(getattr(self, name)))))

    def public(self) -> dict[str, float]:
        return {key: round(float(value), 1) for key, value in asdict(self).items()}


@dataclass
class CitizenLife:
    money: float = 120.0
    debt: float = 0.0
    daily_income: float = 28.0
    rent_amount: float = 42.0
    job_title: str = "trabalhador da cidade"
    work_location: str = "laboratorio"
    shift_start: int = 540
    shift_end: int = 900
    home_cleanliness: float = 78.0
    food_stock: float = 62.0
    reputation: float = 50.0
    belonging: float = 50.0
    privacy_desire: float = 48.0
    current_goal: str = "construir uma rotina estável"
    current_problem: str = ""
    problem_severity: float = 0.0
    problem_until_day: int = 0
    last_rent_day: int = 0
    last_work_day: int = 0
    last_incident_day: int = 0
    sick_until_day: int = 0
    missed_obligations: int = 0
    current_activity: str = "idle"
    routine_streak: int = 0
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "CitizenLife":
        if not isinstance(value, dict):
            # Empty job title signals the engine to assign a profile-specific life on migration.
            return cls(job_title="", tags=[])
        allowed = cls.__dataclass_fields__
        clean = {key: raw for key, raw in value.items() if key in allowed}
        return cls(**clean)

    def clamp(self) -> None:
        self.money = round(max(0.0, float(self.money)), 2)
        self.debt = round(max(0.0, float(self.debt)), 2)
        for name in ("home_cleanliness", "food_stock", "reputation", "belonging",
                     "privacy_desire", "problem_severity"):
            setattr(self, name, max(0.0, min(100.0, float(getattr(self, name)))))
        self.missed_obligations = max(0, int(self.missed_obligations))
        self.routine_streak = max(0, int(self.routine_streak))

    def public(self) -> dict[str, Any]:
        result = asdict(self)
        result["money"] = round(self.money, 2)
        result["debt"] = round(self.debt, 2)
        return result


@dataclass(frozen=True)
class Decision:
    action: str
    location: str
    duration: int
    category: str
    summary: str
    needs_delta: dict[str, float] = field(default_factory=dict)
    life_delta: dict[str, float] = field(default_factory=dict)
    life_set: dict[str, Any] = field(default_factory=dict)
    importance: int = 2
    valence: float = 0.0


class SocietyRules:
    JOBS: tuple[tuple[str, str, int, int, float], ...] = (
        ("mediador comunitário", "prefeitura", 540, 900, 31.0),
        ("pesquisador urbano", "laboratorio", 600, 960, 34.0),
        ("bibliotecário", "biblioteca", 480, 840, 27.0),
        ("gestor de projetos", "oficina", 540, 900, 32.0),
        ("atendente do café", "cafe", 420, 780, 25.0),
        ("organizador do mercado", "mercado", 480, 840, 26.0),
        ("cuidador do parque", "parque", 420, 780, 24.0),
    )

    INCIDENTS: tuple[dict[str, Any], ...] = (
        {
            "problem": "a pia de casa começou a vazar",
            "severity": 42,
            "duration": 2,
            "summary": "percebeu um vazamento em casa e precisa organizar o reparo",
            "stress": 12,
            "cost": 12,
        },
        {
            "problem": "uma conta inesperada chegou",
            "severity": 48,
            "duration": 2,
            "summary": "recebeu uma despesa inesperada e precisará reorganizar o orçamento",
            "stress": 15,
            "cost": 18,
        },
        {
            "problem": "está se sentindo indisposto",
            "severity": 55,
            "duration": 2,
            "summary": "acordou indisposto e terá de reduzir o ritmo",
            "stress": 7,
            "health": -14,
            "sick": True,
        },
        {
            "problem": "perdeu um prazo importante no trabalho",
            "severity": 51,
            "duration": 3,
            "summary": "perdeu um prazo e agora tenta recuperar a confiança profissional",
            "stress": 18,
            "reputation": -6,
        },
        {
            "problem": "a casa ficou acumulada e desorganizada",
            "severity": 35,
            "duration": 2,
            "summary": "percebeu que as tarefas domésticas se acumularam",
            "stress": 8,
            "cleanliness": -24,
        },
        {
            "problem": "está se sentindo deslocado na comunidade",
            "severity": 44,
            "duration": 3,
            "summary": "começou a questionar seu lugar entre os outros moradores",
            "stress": 10,
            "belonging": -16,
        },
    )

    @classmethod
    def default_life(cls, profile: dict[str, Any], index: int) -> CitizenLife:
        job_title, work_location, shift_start, shift_end, income = cls.JOBS[index % len(cls.JOBS)]
        scores = profile.get("behavioral_scores", {}) if isinstance(profile, dict) else {}
        organization = cls._score(scores, "organizacao", 50)
        privacy = 38 + (100 - cls._score(scores, "sociabilidade", 50)) * 0.28
        initiative = cls._score(scores, "iniciativa", 50)
        goals = (
            "conquistar estabilidade e ser útil à comunidade",
            "construir relações confiáveis sem perder autonomia",
            "transformar ideias em melhorias concretas para a cidade",
            "entender melhor os outros moradores e o próprio papel",
            "manter uma vida equilibrada entre trabalho e descanso",
            "ganhar reconhecimento pelo que constrói",
            "criar um lugar que realmente pareça casa",
        )
        return CitizenLife(
            money=95 + index * 11,
            daily_income=income,
            job_title=job_title,
            work_location=work_location,
            shift_start=shift_start,
            shift_end=shift_end,
            home_cleanliness=58 + organization * 0.28,
            food_stock=48 + (index * 9) % 35,
            reputation=45 + initiative * 0.12,
            belonging=42 + (index * 7) % 22,
            privacy_desire=min(86, privacy),
            current_goal=goals[index % len(goals)],
            tags=[job_title, "morador fundador"],
        )

    @staticmethod
    def _score(scores: dict[str, Any], key: str, default: int = 50) -> int:
        try:
            return max(0, min(100, int(scores.get(key, default))))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def mood(needs: HumanNeeds, life: CitizenLife) -> str:
        if needs.health < 38:
            return "indisposto"
        if needs.energy < 18:
            return "exausto"
        if needs.hunger > 86:
            return "faminto"
        if needs.stress > 82:
            return "sobrecarregado"
        if needs.social > 80 or life.belonging < 25:
            return "solitário"
        if needs.autonomy > 78:
            return "sufocado"
        if life.current_problem and life.problem_severity > 58:
            return "preocupado"
        if needs.fun > 80:
            return "entediado"
        if needs.curiosity > 83:
            return "inquieto"
        if needs.energy > 68 and needs.stress < 38 and needs.hunger < 45:
            return "disposto"
        if life.belonging > 70 and needs.social < 40:
            return "acolhido"
        return "neutro"

    @classmethod
    def update(cls, needs: HumanNeeds, life: CitizenLife, minutes: int) -> None:
        factor = max(0.0, minutes / 5)
        needs.hunger += 0.48 * factor
        needs.social += 0.24 * factor
        needs.curiosity += 0.15 * factor
        needs.hygiene += 0.17 * factor
        needs.stress += 0.07 * factor
        needs.fun += 0.16 * factor
        needs.comfort += 0.08 * factor
        needs.purpose += 0.09 * factor
        needs.autonomy += 0.06 * factor
        needs.energy -= 0.31 * factor
        life.food_stock -= 0.025 * factor
        life.home_cleanliness -= 0.045 * factor

        category = life.current_activity
        if category == "sleep":
            needs.energy += 2.7 * factor
            needs.stress -= 0.35 * factor
            needs.comfort -= 0.5 * factor
        elif category == "meal":
            needs.hunger -= 3.8 * factor
            needs.comfort -= 0.25 * factor
        elif category == "hygiene":
            needs.hygiene -= 4.4 * factor
            needs.comfort -= 0.35 * factor
        elif category == "social":
            needs.social -= 2.5 * factor
            needs.fun -= 0.45 * factor
            life.belonging += 0.25 * factor
        elif category == "work":
            needs.purpose -= 0.95 * factor
            needs.stress += 0.24 * factor
            needs.energy -= 0.18 * factor
        elif category == "study":
            needs.curiosity -= 2.1 * factor
            needs.purpose -= 0.45 * factor
        elif category == "leisure":
            needs.fun -= 2.4 * factor
            needs.stress -= 0.85 * factor
            needs.autonomy -= 0.45 * factor
        elif category == "clean":
            life.home_cleanliness += 2.7 * factor
            needs.stress -= 0.2 * factor
        elif category == "care":
            needs.health += 0.65 * factor
            needs.stress -= 0.45 * factor
        elif category == "problem":
            needs.stress += 0.18 * factor
            needs.purpose -= 0.35 * factor

        if life.current_problem:
            needs.stress += 0.08 * factor * max(0.5, life.problem_severity / 50)
        if life.debt > 0:
            needs.stress += min(0.12 * factor, life.debt / 1000)
        if life.home_cleanliness < 35:
            needs.comfort += 0.22 * factor
            needs.stress += 0.08 * factor
        if life.food_stock < 12:
            needs.stress += 0.12 * factor
        if needs.stress > 78:
            needs.health -= 0.08 * factor

        needs.clamp()
        life.clamp()

    @classmethod
    def maybe_incident(
        cls,
        life: CitizenLife,
        needs: HumanNeeds,
        day: int,
        rng: random.Random,
    ) -> dict[str, Any] | None:
        if life.current_problem and day <= life.problem_until_day:
            return None
        if life.current_problem and day > life.problem_until_day:
            life.current_problem = ""
            life.problem_severity = 0
        if life.last_incident_day == day or rng.random() > 0.0009:
            return None

        incident = dict(rng.choice(cls.INCIDENTS))
        life.last_incident_day = day
        life.current_problem = str(incident["problem"])
        life.problem_severity = float(incident["severity"])
        life.problem_until_day = day + int(incident["duration"])
        needs.stress += float(incident.get("stress", 0))
        needs.health += float(incident.get("health", 0))
        life.reputation += float(incident.get("reputation", 0))
        life.home_cleanliness += float(incident.get("cleanliness", 0))
        life.belonging += float(incident.get("belonging", 0))
        cost = float(incident.get("cost", 0))
        if cost:
            paid = min(life.money, cost)
            life.money -= paid
            life.debt += max(0, cost - paid)
        if incident.get("sick"):
            life.sick_until_day = max(life.sick_until_day, day + 1)
        needs.clamp()
        life.clamp()
        return incident

    @classmethod
    def decide(
        cls,
        profile: dict[str, Any],
        needs: HumanNeeds,
        life: CitizenLife,
        day: int,
        minute: int,
        home_location: str,
        rng: random.Random,
    ) -> Decision:
        hour = minute // 60
        scores = profile.get("behavioral_scores", {}) if isinstance(profile, dict) else {}
        organization = cls._score(scores, "organizacao", 50)
        curiosity = cls._score(scores, "curiosidade", 50)
        initiative = cls._score(scores, "iniciativa", 50)
        leadership = cls._score(scores, "lideranca", 50)
        ambition = cls._score(scores, "ambicao", 50)

        if day % 7 == 0 and life.last_rent_day < day:
            if life.money >= life.rent_amount:
                return Decision(
                    "pagando o aluguel e organizando as contas",
                    home_location,
                    25,
                    "finance",
                    "separou parte do dinheiro para manter a casa em dia",
                    life_delta={"money": -life.rent_amount},
                    life_set={"last_rent_day": day},
                    importance=4,
                    valence=0.25,
                )
            return Decision(
                "procurando uma solução para o aluguel atrasado",
                "centro_comunitario",
                50,
                "problem",
                "não conseguiu pagar o aluguel e foi buscar orientação",
                needs_delta={"stress": 12},
                life_delta={"debt": life.rent_amount, "problem_severity": 18},
                life_set={
                    "last_rent_day": day,
                    "current_problem": "aluguel atrasado",
                    "problem_until_day": day + 3,
                    "missed_obligations": life.missed_obligations + 1,
                },
                importance=5,
                valence=-0.75,
            )

        if life.sick_until_day >= day or needs.health < 42:
            if needs.health < 28:
                return Decision(
                    "buscando atendimento para se recuperar",
                    "clinica",
                    70,
                    "care",
                    "decidiu procurar atendimento em vez de ignorar o mal-estar",
                    needs_delta={"health": 18, "stress": -7, "energy": -4},
                    life_delta={"money": -min(10.0, life.money)},
                    importance=5,
                    valence=0.1,
                )
            return Decision(
                "descansando e cuidando da saúde",
                home_location,
                90,
                "care",
                "reduziu o ritmo para tentar melhorar",
                needs_delta={"health": 8, "stress": -8},
                importance=3,
                valence=0.15,
            )

        if needs.energy < 24 or ((hour >= 23 or hour < 6) and needs.energy < 72):
            return Decision(
                "dormindo em casa",
                home_location,
                100,
                "sleep",
                "foi dormir para recuperar energia",
                importance=1,
                valence=0.15,
            )

        if needs.hunger > 72:
            if life.food_stock >= 9:
                return Decision(
                    "preparando e comendo uma refeição em casa",
                    home_location,
                    35,
                    "meal",
                    "preparou comida usando o que havia em casa",
                    life_delta={"food_stock": -8},
                    importance=2,
                    valence=0.25,
                )
            if life.money >= 9:
                return Decision(
                    "comprando mantimentos para casa",
                    "mercado",
                    40,
                    "shopping",
                    "foi ao mercado repor a comida que estava acabando",
                    needs_delta={"stress": -2},
                    life_delta={"money": -9, "food_stock": 34},
                    importance=3,
                    valence=0.1,
                )
            return Decision(
                "pedindo ajuda porque a comida acabou",
                "centro_comunitario",
                45,
                "problem",
                "ficou sem mantimentos e precisou pedir apoio à comunidade",
                needs_delta={"stress": 10, "social": -8},
                life_delta={"food_stock": 18, "belonging": 4},
                life_set={"current_problem": "falta de dinheiro para alimentação", "problem_until_day": day + 2},
                importance=5,
                valence=-0.55,
            )

        if needs.hygiene > 70:
            return Decision(
                "cuidando da higiene e trocando de roupa",
                home_location,
                25,
                "hygiene",
                "reservou um momento privado para cuidar de si",
                importance=1,
                valence=0.15,
            )

        in_shift = life.shift_start <= minute < life.shift_end
        if in_shift and life.last_work_day < day and needs.energy > 30:
            return Decision(
                f"cumprindo seu turno como {life.job_title}",
                life.work_location,
                max(45, min(120, life.shift_end - minute)),
                "work",
                "compareceu ao trabalho e assumiu suas responsabilidades",
                life_delta={"money": life.daily_income, "reputation": 0.8, "routine_streak": 1},
                life_set={"last_work_day": day},
                importance=3,
                valence=0.3,
            )

        if minute > life.shift_end + 90 and life.last_work_day < day and day % 7 not in (0, 6):
            return Decision(
                "tentando justificar por que faltou ao trabalho",
                life.work_location,
                35,
                "problem",
                "perdeu o turno e precisará lidar com as consequências",
                needs_delta={"stress": 12, "purpose": 8},
                life_delta={"reputation": -4, "routine_streak": -life.routine_streak},
                life_set={"last_work_day": day, "current_problem": "faltou ao trabalho", "problem_until_day": day + 1},
                importance=4,
                valence=-0.6,
            )

        if life.current_problem:
            if "vazar" in life.current_problem or "desorganizada" in life.current_problem:
                return Decision(
                    "resolvendo um problema doméstico",
                    home_location,
                    60,
                    "problem",
                    "parou a rotina para cuidar do problema em casa",
                    needs_delta={"stress": -9, "purpose": -4},
                    life_delta={"home_cleanliness": 18, "problem_severity": -24},
                    importance=4,
                    valence=0.2,
                )
            if "prazo" in life.current_problem:
                return Decision(
                    "refazendo o trabalho que ficou atrasado",
                    life.work_location,
                    70,
                    "work",
                    "decidiu enfrentar o atraso e recuperar parte da confiança",
                    needs_delta={"stress": -6, "purpose": -8},
                    life_delta={"reputation": 3, "problem_severity": -22},
                    importance=4,
                    valence=0.25,
                )
            if "deslocado" in life.current_problem or "aluguel" in life.current_problem:
                return Decision(
                    "procurando alguém de confiança para conversar",
                    "cafe",
                    45,
                    "socialize",
                    "decidiu não enfrentar o problema completamente sozinho",
                    importance=4,
                    valence=0.15,
                )

        if life.home_cleanliness < 36:
            return Decision(
                "limpando e organizando a própria casa",
                home_location,
                55,
                "clean",
                "assumiu as tarefas domésticas que estavam acumuladas",
                needs_delta={"stress": -5, "comfort": -12},
                importance=2,
                valence=0.25,
            )

        if needs.stress > 72:
            location = "parque" if initiative < 70 else "cafe"
            return Decision(
                "tentando desacelerar depois de um dia pesado",
                location,
                50,
                "leisure",
                "percebeu que estava sobrecarregado e decidiu fazer uma pausa",
                importance=3,
                valence=0.15,
            )

        if needs.social > 68 or life.belonging < 34:
            return Decision(
                "procurando companhia e alguma conversa",
                "cafe",
                45,
                "socialize",
                "saiu de casa porque não queria continuar isolado",
                importance=3,
                valence=0.2,
            )

        if needs.fun > 72 or needs.autonomy > 72:
            return Decision(
                "fazendo algo apenas porque tem vontade",
                "parque",
                50,
                "leisure",
                "reservou parte do dia para uma escolha pessoal",
                needs_delta={"autonomy": -12},
                importance=2,
                valence=0.4,
            )

        if needs.curiosity > 70:
            return Decision(
                "estudando algo que despertou sua curiosidade",
                "biblioteca" if curiosity >= 58 else "praca",
                55,
                "study",
                "foi atrás de respostas para uma dúvida que não saía da cabeça",
                importance=2,
                valence=0.3,
            )

        weighted: list[tuple[Decision, float]] = [
            (Decision("trabalhando em um projeto pessoal", "oficina", 60, "work",
                      "avançou em um projeto ligado ao próprio objetivo", importance=2, valence=0.35),
             0.35 + initiative / 100),
            (Decision("participando de uma reunião da comunidade", "prefeitura", 55, "community",
                      "entrou numa conversa sobre decisões que afetam todos", importance=3, valence=0.15),
             0.2 + leadership / 120),
            (Decision("observando a rotina da praça", "praca", 40, "leisure",
                      "passou um tempo observando como a cidade está mudando", importance=1, valence=0.15),
             0.3 + curiosity / 130),
            (Decision("descansando sem compromisso no parque", "parque", 45, "leisure",
                      "escolheu descansar antes que o cansaço virasse um problema", importance=1, valence=0.35),
             max(0.2, (100 - ambition) / 110)),
            (Decision("organizando as próximas despesas", home_location, 35, "finance",
                      "revisou o orçamento e tentou antecipar os próximos gastos", importance=2, valence=0.1),
             0.2 + organization / 140),
        ]
        total = sum(weight for _, weight in weighted)
        roll = rng.random() * total
        for decision, weight in weighted:
            roll -= weight
            if roll <= 0:
                return decision
        return weighted[-1][0]

    @staticmethod
    def apply_decision(needs: HumanNeeds, life: CitizenLife, decision: Decision) -> None:
        for key, delta in decision.needs_delta.items():
            if hasattr(needs, key):
                setattr(needs, key, float(getattr(needs, key)) + float(delta))
        for key, delta in decision.life_delta.items():
            if hasattr(life, key):
                current = getattr(life, key)
                if isinstance(current, (int, float)):
                    setattr(life, key, current + delta)
        for key, value in decision.life_set.items():
            if hasattr(life, key):
                setattr(life, key, value)
        life.current_activity = decision.category
        needs.clamp()
        life.clamp()
