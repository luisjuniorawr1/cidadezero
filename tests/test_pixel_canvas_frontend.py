from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def test_pixel_canvas_is_connected_to_the_observer_page() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert 'id="city-canvas"' in html
    assert 'src="/static/city-professional.js"' in html
    assert 'href="/static/city-professional.css"' in html
    assert html.index("city-v2.js") < html.index("city-professional.js")
    assert 'src="/static/city-canvas.js"' not in html


def test_canvas_renderer_keeps_the_existing_state_contract() -> None:
    javascript = (STATIC / "city-professional.js").read_text(encoding="utf-8")

    assert "renderActors=renderActorsProfessional" in javascript
    assert "buildCity=buildCityProfessional" in javascript
    assert "requestAnimationFrame(draw)" in javascript
    assert "selectCharacter(hit.id)" in javascript
    assert "prefers-reduced-motion" in javascript


def test_canvas_is_rendered_with_crisp_pixels() -> None:
    stylesheet = (STATIC / "city-professional.css").read_text(encoding="utf-8")

    assert "image-rendering:pixelated" in stylesheet
    assert ".city-stage.professional-map" in stylesheet
    assert ".city-canvas:focus-visible" in stylesheet
