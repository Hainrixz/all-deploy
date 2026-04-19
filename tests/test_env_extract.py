"""Tests for scripts/env_extract.py — JS/TS + Python, including destructuring."""

from __future__ import annotations
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXTRACT = REPO_ROOT / "scripts" / "env_extract.py"


def run_extract(project: Path) -> list[str]:
    result = subprocess.run(
        ["python3", str(EXTRACT), str(project), "--as-json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else []


def test_process_env_dot(tmp_path: Path) -> None:
    (tmp_path / "a.js").write_text("const x = process.env.DATABASE_URL;\n")
    assert run_extract(tmp_path) == ["DATABASE_URL"]


def test_process_env_bracket(tmp_path: Path) -> None:
    (tmp_path / "a.js").write_text('const x = process.env["STRIPE_SECRET"];\n')
    assert run_extract(tmp_path) == ["STRIPE_SECRET"]


def test_destructured_js(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text(
        "const { DATABASE_URL, REDIS_URL, SENTRY_DSN } = process.env;\n"
    )
    assert sorted(run_extract(tmp_path)) == ["DATABASE_URL", "REDIS_URL", "SENTRY_DSN"]


def test_destructured_with_aliases_and_defaults(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text(
        "const { DATABASE_URL: dbUrl, SENTRY_DSN = '' } = process.env;\n"
    )
    assert sorted(run_extract(tmp_path)) == ["DATABASE_URL", "SENTRY_DSN"]


def test_import_meta_env(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("const x = import.meta.env.PUBLIC_KEY;\n")
    assert run_extract(tmp_path) == ["PUBLIC_KEY"]


def test_python_os_environ_bracket(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import os\nx = os.environ['DATABASE_URL']\n")
    assert run_extract(tmp_path) == ["DATABASE_URL"]


def test_python_getenv(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import os\nx = os.getenv('STRIPE_KEY')\n")
    assert run_extract(tmp_path) == ["STRIPE_KEY"]


def test_ignore_list_excludes_platform_vars(tmp_path: Path) -> None:
    (tmp_path / "a.js").write_text(
        "const port = process.env.PORT;\n"
        "const env = process.env.NODE_ENV;\n"
        "const db = process.env.DATABASE_URL;\n"
    )
    # PORT and NODE_ENV are platform-provided → ignored.
    assert run_extract(tmp_path) == ["DATABASE_URL"]
