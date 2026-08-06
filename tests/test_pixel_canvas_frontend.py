from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def test_ai_art_is_connected_to_the_observer_page() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert 'id="city-stage"' in html
    assert 'src="/static/city-ai-art.js"' in html
    assert 'href="/static/city-ai-art.css"' in html
    assert html.index("city-v2.js") < html.index("city-ai-art.js")
    assert 'src="/static/city-professional.js"' not in html


def test_ai_art_overlay_keeps_character_selection() -> None:
    javascript = (STATIC / "city-ai-art.js").read_text(encoding="utf-8")

    assert "latestState" in javascript
    assert "selectCharacter(id)" in javascript
    assert "character.public_name" in javascript
    assert "character.action" in javascript
    assert "character.location" in javascript
    assert "stage.classList.add('ai-art-mode', 'professional-map')" in javascript


def test_generated_background_and_markers_are_styled() -> None:
    stylesheet = (STATIC / "city-ai-art.css").read_text(encoding="utf-8")

    assert "cidade-zero-ai-map-v1.webp" in stylesheet
    assert ".city-stage.ai-art-mode" in stylesheet
    assert "aspect-ratio:16/9" in stylesheet
    assert "center/100% 100% no-repeat" in stylesheet
    assert "center/cover no-repeat" not in stylesheet
    assert ".ai-resident-pin" in stylesheet
    assert ".ai-resident-label" in stylesheet
    assert "prefers-reduced-motion" in stylesheet
