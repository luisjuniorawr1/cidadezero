from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def test_pixel_canvas_is_connected_to_the_observer_page() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert 'id="city-canvas"' in html
    assert 'src="/static/city-canvas.js"' in html
    assert 'href="/static/city-canvas.css"' in html
    assert html.index("city-v2.js") < html.index("city-canvas.js")


def test_canvas_renderer_keeps_the_existing_state_contract() -> None:
    javascript = (STATIC / "city-canvas.js").read_text(encoding="utf-8")

    assert "renderActors = function renderCanvasActors" in javascript
    assert "buildCity = function buildCanvasCity" in javascript
    assert "requestAnimationFrame(frame)" in javascript
    assert "selectCharacter(match.id)" in javascript
    assert "prefers-reduced-motion" in javascript


def test_canvas_is_rendered_with_crisp_pixels() -> None:
    stylesheet = (STATIC / "city-canvas.css").read_text(encoding="utf-8")

    assert "image-rendering:pixelated" in stylesheet
    assert ".city-stage.canvas-mode" in stylesheet
    assert ".city-canvas:focus-visible" in stylesheet
