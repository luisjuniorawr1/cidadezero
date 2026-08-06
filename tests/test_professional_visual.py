from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
GENERATED_MAP = STATIC / "generated" / "cidade-zero-ai-map-v1.webp"


def test_index_uses_ai_art_renderer() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert "/static/city-professional.css" in html
    assert "/static/city-ai-art.css" in html
    assert "/static/city-ai-art.js" in html
    assert "/static/city-professional.js" not in html
    assert "/static/city-canvas.js" not in html
    assert 'width="960"' in html
    assert 'height="540"' in html
    assert html.index("city-v2.js") < html.index("city-ai-art.js")


def test_ai_art_javascript_has_valid_syntax() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js não está disponível neste ambiente")

    subprocess.run(
        [node, "--check", str(STATIC / "city-ai-art.js")],
        check=True,
        capture_output=True,
        text=True,
    )


def test_generated_map_asset_is_present() -> None:
    assert GENERATED_MAP.exists()
    assert GENERATED_MAP.stat().st_size > 1_000
    assert GENERATED_MAP.read_bytes().startswith(b"RIFF")


def test_ai_art_keeps_the_existing_state_contract() -> None:
    script = (STATIC / "city-ai-art.js").read_text(encoding="utf-8")

    assert "latestState" in script
    assert "selectCharacter" in script
    assert "snapshot.characters" in script
    assert "character.location" in script
    assert "window.setInterval(renderPins" in script
    assert "anchors" in script
    assert "professional-map" in script


def test_ai_art_uses_native_widescreen_without_cover_crop() -> None:
    css = (STATIC / "city-ai-art.css").read_text(encoding="utf-8")

    assert "height:auto!important" in css
    assert "min-height:0!important" in css
    assert "aspect-ratio:16/9" in css
    assert "center/100% 100% no-repeat" in css
    assert "center/cover no-repeat" not in css
    assert "mix-blend-mode:normal" in css


def test_ai_art_layout_is_responsive_and_accessible() -> None:
    css = (STATIC / "city-ai-art.css").read_text(encoding="utf-8")
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert "cidade-zero-ai-map-v1.webp" in css
    assert ".ai-residents-layer" in css
    assert ".ai-resident-pin" in css
    assert "@media(max-width:900px)" in css
    assert "prefers-reduced-motion" in css
    assert 'aria-label="Vista ilustrada da Cidade Zero' in html


def test_asset_master_documents_production_scope() -> None:
    document = (ROOT / "documentacao" / "asset_list_master.md").read_text(encoding="utf-8")

    assert "32x16 pixels por tile" in document
    assert "Casa de ChatGPT" in document
    assert "Interiores" in document
    assert "Critérios de aprovação" in document
