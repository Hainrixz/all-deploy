"""
End-to-end tests for scripts/audit.py against synthetic fixtures.

Runs in CI. Creates temp dirs, seeds known-bad and known-good project states,
runs audit.py as a subprocess, asserts exit code and finding codes.
"""

from __future__ import annotations
import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT = REPO_ROOT / "scripts" / "audit.py"


def run_audit(project: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(AUDIT), str(project), "--json", *flags],
        capture_output=True,
        text=True,
    )


def _findings(stdout: str) -> list[dict]:
    try:
        return json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        return []


def _git_init(project: Path) -> None:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "t"
    env["GIT_AUTHOR_EMAIL"] = "t@t"
    env["GIT_COMMITTER_NAME"] = "t"
    env["GIT_COMMITTER_EMAIL"] = "t@t"
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=project, check=True)


def _git_commit(project: Path) -> None:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "t"
    env["GIT_AUTHOR_EMAIL"] = "t@t"
    env["GIT_COMMITTER_NAME"] = "t"
    env["GIT_COMMITTER_EMAIL"] = "t@t"
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=project,
        check=True,
        env=env,
    )


# ---------- Fixtures ----------

def test_clean_project_scoped_passes(tmp_path: Path) -> None:
    """A clean project in scoped mode (no git) should exit 0 with no findings."""
    (tmp_path / "main.py").write_text("print('hi')")
    result = run_audit(tmp_path, "--scoped", "--skip-cve")
    assert result.returncode == 0, result.stdout
    findings = _findings(result.stdout)
    assert findings == [], findings


def test_env_file_tracked_is_critical(tmp_path: Path) -> None:
    """A committed .env should produce a critical env-tracked finding."""
    _git_init(tmp_path)
    (tmp_path / ".env").write_text("DATABASE_URL=postgres://real")
    (tmp_path / "main.py").write_text("import os\nos.environ['DATABASE_URL']")
    _git_commit(tmp_path)
    result = run_audit(tmp_path, "--skip-cve", "--skip-remote")
    assert result.returncode == 1, result.stdout
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "secret.env-tracked" in codes


def test_envrc_is_allowed(tmp_path: Path) -> None:
    """A committed .envrc (direnv) should NOT fire secret.env-tracked."""
    _git_init(tmp_path)
    (tmp_path / ".envrc").write_text("export PROJECT=foo\ndotenv_if_exists\n")
    (tmp_path / ".gitignore").write_text(".env\nnode_modules\n__pycache__\ndist\n.next\n.venv\n.vercel\n")
    (tmp_path / ".env.example").write_text("PROJECT=\n")
    (tmp_path / "main.py").write_text("import os\nos.getenv('PROJECT')")
    _git_commit(tmp_path)
    result = run_audit(tmp_path, "--skip-cve", "--skip-remote", "--scoped")
    # scoped mode: only secrets + start-command + port-binding. .envrc is allowlisted.
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "secret.env-tracked" not in codes
    assert result.returncode == 0, result.stdout


def test_hardcoded_github_token_is_critical(tmp_path: Path) -> None:
    """A GitHub PAT in source should fire secret.GitHub_PAT_classic."""
    _git_init(tmp_path)
    # 36 hex-ish chars after ghp_ — matches the pattern
    (tmp_path / "app.js").write_text(
        'const token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789";\n'
    )
    _git_commit(tmp_path)
    result = run_audit(tmp_path, "--scoped", "--skip-cve")
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "secret.GitHub_PAT_classic" in codes
    assert result.returncode == 1


def test_dirty_tree_is_critical(tmp_path: Path) -> None:
    """An uncommitted change to a tracked file should flag git.dirty."""
    _git_init(tmp_path)
    (tmp_path / "main.py").write_text("print('hi')\n")
    (tmp_path / ".gitignore").write_text(".env\nnode_modules\n__pycache__\ndist\n.next\n.venv\n.vercel\n")
    (tmp_path / ".env.example").write_text("FOO=\n")
    _git_commit(tmp_path)
    (tmp_path / "main.py").write_text("print('changed')\n")  # dirty
    subprocess.run(["git", "remote", "add", "origin", "https://example.com/x.git"], cwd=tmp_path, check=True)
    result = run_audit(tmp_path, "--skip-cve")
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "git.dirty" in codes
    assert result.returncode == 1


def test_untracked_is_warn_not_critical(tmp_path: Path) -> None:
    """A new untracked file should warn, not fail."""
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text(".env\nnode_modules\n__pycache__\ndist\n.next\n.venv\n.vercel\n")
    (tmp_path / "main.py").write_text("import os\nos.environ['FOO']")
    (tmp_path / ".env.example").write_text("FOO=\n")
    _git_commit(tmp_path)
    (tmp_path / "new_file.py").write_text("# untracked, audit just ran and added this\n")
    subprocess.run(["git", "remote", "add", "origin", "https://example.com/x.git"], cwd=tmp_path, check=True)
    result = run_audit(tmp_path, "--skip-cve")
    findings = _findings(result.stdout)
    severities = {f["severity"] for f in findings if f["check"] == "git.untracked"}
    assert severities == {"warn"}
    assert result.returncode == 0  # untracked alone must not fail the audit


def test_destructured_env_required_in_env_example(tmp_path: Path) -> None:
    """env_extract.py handles `const { FOO } = process.env;` so audit catches missing keys."""
    _git_init(tmp_path)
    (tmp_path / "server.js").write_text(
        "const { DATABASE_URL, REDIS_URL } = process.env;\n"
        "console.log(DATABASE_URL, REDIS_URL);\n"
    )
    (tmp_path / "package.json").write_text('{"name":"x","scripts":{"start":"node server.js"},"engines":{"node":">=20"}}\n')
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion":3}\n')
    (tmp_path / ".gitignore").write_text(".env\nnode_modules\n__pycache__\ndist\n.next\n.venv\n.vercel\n")
    # Deliberately omit .env.example — audit must notice the destructured keys.
    _git_commit(tmp_path)
    subprocess.run(["git", "remote", "add", "origin", "https://example.com/x.git"], cwd=tmp_path, check=True)
    result = run_audit(tmp_path, "--skip-cve")
    findings = _findings(result.stdout)
    env_findings = [f for f in findings if f["check"] == "env.example.missing"]
    assert env_findings, f"expected env.example.missing, got {findings}"
    # The missing keys live in the `fix` field, not the `message`.
    fix = env_findings[0]["fix"] or ""
    assert "DATABASE_URL" in fix and "REDIS_URL" in fix
