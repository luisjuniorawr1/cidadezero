from __future__ import annotations

from app.intelligence import AIDecision, IntelligenceConfig, IntelligenceError


def valid_payload() -> dict:
    return {
        "current_emotion": "curioso",
        "public_intention": "entender melhor a cidade",
        "selected_action": "explore",
        "target_character": None,
        "target_location": "praca",
        "spoken_line": None,
        "short_justification": "A curiosidade está alta e não há obrigação urgente.",
        "new_goal": None,
        "memory_ids_used": [1, 2],
        "confidence": 74,
        "urgency": 22,
        "duration_minutes": 45,
    }


def test_ai_decision_accepts_open_intention_with_bounded_action() -> None:
    decision = AIDecision.from_payload(valid_payload())
    assert decision.selected_action == "explore"
    assert decision.public_intention == "entender melhor a cidade"
    assert decision.memory_ids_used == (1, 2)


def test_ai_decision_rejects_unknown_executor_action() -> None:
    payload = valid_payload()
    payload["selected_action"] = "alterar_o_servidor"
    try:
        AIDecision.from_payload(payload)
    except IntelligenceError:
        pass
    else:
        raise AssertionError("ação fora do contrato deveria ser rejeitada")


def test_public_config_never_exposes_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "segredo")
    config = IntelligenceConfig.from_env()
    assert config.enabled is True
    assert "api_key" not in config.public()
    assert "segredo" not in str(config.public())
