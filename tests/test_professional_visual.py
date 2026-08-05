from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def test_index_uses_professional_renderer_only() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert "/static/city-professional.css" in html
    assert "/static/city-professional.js" in html
    assert "/static/city-canvas.css" not in html
    assert "/static/city-canvas.js" not in html
    assert 'width="960"' in html
    assert 'height="540"' in html
    assert 'id="city-tooltip"' in html
    assert 'id="map-zoom-in"' in html
    assert 'id="map-zoom-out"' in html


def test_professional_javascript_has_valid_syntax() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js não está disponível neste ambiente")

    subprocess.run(
        [node, "--check", str(STATIC / "city-professional.js")],
        check=True,
        capture_output=True,
        text=True,
    )


def test_map_keeps_text_outside_pixel_art() -> None:
    script = (STATIC / "city-professional.js").read_text(encoding="utf-8")

    assert "buildCity=buildCityProfessional" in script
    assert "renderActors=renderActorsProfessional" in script
    assert "state.hitboxes" in script
    assert "selectLocation" in script
    assert "ctx.fillText" not in script
    assert "canvas-render-badge" not in script


def test_professional_layout_is_responsive_and_accessible() -> None:
    css = (STATIC / "city-professional.css").read_text(encoding="utf-8")
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert "image-rendering:pixelated" in css
    assert ".city-tooltip" in css
    assert "@media (max-width:900px)" in css
    assert "prefers-reduced-motion" in css
    assert 'tabindex="0"' in html
    assert 'aria-label="Mapa pixel art da Cidade Zero.' in html


def test_asset_master_documents_production_scope() -> None:
    document = (ROOT / "documentacao" / "asset_list_master.md").read_text(encoding="utf-8")

    assert "32x16 pixels por tile" in document
    assert "Casa de ChatGPT" in document
    assert "Interiores" in document
    assert "Critérios de aprovação" in document
