from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_augmented_entrypoint_imports_without_api_key(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(tmp_path / "cidade_zero.db")
    env.pop("OPENAI_API_KEY", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import app.augmented as module; "
                "assert module.app is not None; "
                "assert module.runtime.status()['enabled'] is False; "
                "print('ok')"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
