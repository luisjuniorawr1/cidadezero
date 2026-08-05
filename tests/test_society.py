from __future__ import annotations

import random

from app.society import CitizenLife, HumanNeeds, SocietyRules


def test_old_needs_payload_migrates_with_defaults() -> None:
    needs = HumanNeeds.from_dict({"energy": 50, "hunger": 70, "social": 20, "curiosity": 40})
    assert needs.energy == 50
    assert needs.hygiene == 18
    assert needs.health == 92


def test_legacy_life_payload_requests_profile_specific_migration() -> None:
    life = CitizenLife.from_dict(None)
    assert life.job_title == ""


def test_rent_is_paid_when_due_and_affordable() -> None:
    needs = HumanNeeds()
    life = CitizenLife(money=100, rent_amount=42, last_rent_day=0)
    decision = SocietyRules.decide({}, needs, life, day=7, minute=600,
                                   home_location="casa_teste", rng=random.Random(1))
    assert decision.category == "finance"
    SocietyRules.apply_decision(needs, life, decision)
    assert life.money == 58
    assert life.last_rent_day == 7


def test_rent_becomes_problem_when_unaffordable() -> None:
    needs = HumanNeeds()
    life = CitizenLife(money=3, rent_amount=42, last_rent_day=0)
    decision = SocietyRules.decide({}, needs, life, day=7, minute=600,
                                   home_location="casa_teste", rng=random.Random(2))
    assert decision.category == "problem"
    SocietyRules.apply_decision(needs, life, decision)
    assert life.debt == 42
    assert life.current_problem == "aluguel atrasado"


def test_food_shortage_requests_community_help() -> None:
    needs = HumanNeeds(hunger=90)
    life = CitizenLife(money=0, food_stock=0, last_rent_day=7)
    decision = SocietyRules.decide({}, needs, life, day=8, minute=720,
                                   home_location="casa_teste", rng=random.Random(3))
    assert decision.location == "centro_comunitario"
    assert decision.category == "problem"
    SocietyRules.apply_decision(needs, life, decision)
    assert life.food_stock == 18


def test_work_shift_generates_income() -> None:
    needs = HumanNeeds(energy=80, hunger=20)
    life = CitizenLife(money=50, daily_income=30, shift_start=540, shift_end=900,
                       last_work_day=0, last_rent_day=7)
    decision = SocietyRules.decide({}, needs, life, day=8, minute=600,
                                   home_location="casa_teste", rng=random.Random(4))
    assert decision.category == "work"
    SocietyRules.apply_decision(needs, life, decision)
    assert life.money == 80
    assert life.last_work_day == 8


def test_passive_update_and_sleep_recovery() -> None:
    needs = HumanNeeds(energy=20, stress=60)
    life = CitizenLife(current_activity="sleep")
    SocietyRules.update(needs, life, 30)
    assert needs.energy > 20
    assert needs.stress < 60


def test_problem_can_change_mood() -> None:
    needs = HumanNeeds(stress=50)
    life = CitizenLife(current_problem="aluguel atrasado", problem_severity=70)
    assert SocietyRules.mood(needs, life) == "preocupado"


def test_incident_is_at_most_once_per_day() -> None:
    class IncidentRng:
        @staticmethod
        def random() -> float:
            return 0.0

        @staticmethod
        def choice(values):
            return values[0]

    needs = HumanNeeds()
    life = CitizenLife()
    rng = IncidentRng()
    first = SocietyRules.maybe_incident(life, needs, day=3, rng=rng)
    assert first is not None
    assert SocietyRules.maybe_incident(life, needs, day=3, rng=rng) is None
