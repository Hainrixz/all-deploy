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
    # Assemble the fake PAT at runtime so THIS test file doesn't itself
    # contain a literal match — otherwise the skill's own self-audit step
    # in CI would flag tests/test_audit.py as leaking a token.
    fake_pat = "gh" + "p_" + "abcdefghijklmnopqrstuvwxyz0123456789"
    (tmp_path / "app.js").write_text(f'const token = "{fake_pat}";\n')
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


# ---------------------------------------------------------------------------
# Static profile — a web page, not a service.
#
# The regression these guard: before the static profile existed, a plain
# folder of HTML with no git repo failed the audit with two *false* criticals
# (gitignore.missing and git.dirty), which is what kept this whole audience
# out of the skill.
# ---------------------------------------------------------------------------

GOOD_HEAD = """<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mi pagina</title>
<meta name="description" content="Una pagina.">
<meta property="og:title" content="Mi pagina">
<meta property="og:image" content="https://example.com/p.png">
<link rel="stylesheet" href="estilo.css">
</head><body><h1>Hola</h1></body></html>
"""


def run_static(project: Path, *flags: str) -> subprocess.CompletedProcess:
    return run_audit(project, "--profile", "static", "--skip-cve", *flags)


def _plain_site(project: Path) -> None:
    (project / "index.html").write_text(GOOD_HEAD)
    (project / "estilo.css").write_text("body { margin: 0 }\n")


def test_static_plain_folder_passes(tmp_path):
    """The regression anchor: a good static folder, no git, must be clean."""
    _plain_site(tmp_path)
    result = run_static(tmp_path)
    assert _findings(result.stdout) == []
    assert result.returncode == 0


def test_static_skips_git_and_dependency_checks(tmp_path):
    _plain_site(tmp_path)
    codes = {f["check"] for f in _findings(run_static(tmp_path).stdout)}
    for never in (
        "git.remote.missing", "gitignore.missing", "git.dirty",
        "env.example.missing", "lockfile.missing.node", "start-command.missing.node",
    ):
        assert never not in codes


def test_static_autodetects_without_flags(tmp_path):
    """No --profile passed: a folder of HTML with no manifest is static."""
    _plain_site(tmp_path)
    result = run_audit(tmp_path, "--skip-cve")
    assert result.returncode == 0
    assert _findings(result.stdout) == []


def test_app_profile_survives_a_root_index_html(tmp_path):
    """A Vite/Next repo also has index.html — it must stay on the app pipeline."""
    (tmp_path / "index.html").write_text(GOOD_HEAD)
    (tmp_path / "package.json").write_text('{"name": "x", "version": "1.0.0"}')
    codes = {f["check"] for f in _findings(run_audit(tmp_path, "--skip-cve").stdout)}
    assert "lockfile.missing.node" in codes


def test_static_missing_index_is_critical(tmp_path):
    (tmp_path / "home.html").write_text(GOOD_HEAD)
    result = run_static(tmp_path)
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "static.entry.missing" in codes
    assert result.returncode == 1


def test_static_index_case_variant_is_critical(tmp_path):
    (tmp_path / "Index.html").write_text(GOOD_HEAD)
    findings = _findings(run_static(tmp_path).stdout)
    entry = [f for f in findings if f["check"] == "static.entry.missing"]
    assert entry, "expected static.entry.missing for Index.html"
    assert "index.html" in entry[0]["fix"]


def test_static_case_mismatch_is_critical(tmp_path):
    """Passes on a case-insensitive Mac and on case-sensitive Linux CI alike —
    resolution goes through a case-folded index of real on-disk names, never
    Path.exists(), which lies on macOS."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "Logo.png").write_bytes(b"\x89PNG")
    (tmp_path / "index.html").write_text('<html><body><img src="assets/logo.png"></body></html>')
    result = run_static(tmp_path)
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "static.asset.case-mismatch" in codes
    assert "static.asset.missing" not in codes
    assert result.returncode == 1


def test_static_broken_reference_is_warn_not_critical(tmp_path):
    _plain_site(tmp_path)
    (tmp_path / "index.html").write_text('<html><body><img src="no-such.png"></body></html>')
    result = run_static(tmp_path)
    missing = [f for f in _findings(result.stdout) if f["check"] == "static.asset.missing"]
    assert missing and missing[0]["severity"] == "warn"


def test_static_directory_reference_with_index_is_ok(tmp_path):
    """href="about/" resolves to about/index.html on every host — don't cry wolf."""
    (tmp_path / "index.html").write_text('<html><body><a href="about/">about</a></body></html>')
    (tmp_path / "about").mkdir()
    (tmp_path / "about" / "index.html").write_text("<html><body>about</body></html>")
    codes = {f["check"] for f in _findings(run_static(tmp_path).stdout)}
    assert "static.asset.missing" not in codes


def test_static_external_references_are_ignored(tmp_path):
    (tmp_path / "index.html").write_text(
        '<html><body>'
        '<img src="https://cdn.example.com/a.png">'
        '<img src="//cdn.example.com/b.png">'
        '<img src="data:image/png;base64,iVBORw0KGgo=">'
        '<a href="mailto:x@y.com">mail</a><a href="#top">top</a>'
        '<img src="{{ url_for(\'x\') }}">'
        '</body></html>'
    )
    codes = {f["check"] for f in _findings(run_static(tmp_path).stdout)}
    assert "static.asset.missing" not in codes
    assert "static.path.absolute-local" not in codes


def test_static_absolute_local_paths_are_critical(tmp_path):
    (tmp_path / "index.html").write_text(
        '<html><body>'
        '<img src="file:///Users/someone/Desktop/a.png">'
        '<img src="C:\\Users\\someone\\b.png">'
        '<img src="/Users/someone/c.png">'
        '</body></html>'
    )
    result = run_static(tmp_path)
    finding = [f for f in _findings(result.stdout) if f["check"] == "static.path.absolute-local"]
    assert finding, "expected static.path.absolute-local"
    assert "3 reference(s)" in finding[0]["message"]
    assert result.returncode == 1


def test_static_client_side_secret_is_critical(tmp_path):
    # Assembled at runtime so this test file doesn't itself contain a literal
    # match — the repo's own self-audit step in CI scans every tracked file.
    fake = "gh" + "p_" + "a" * 36
    (tmp_path / "index.html").write_text(GOOD_HEAD)
    (tmp_path / "estilo.css").write_text("body{}")
    (tmp_path / "app.js").write_text(f'const token = "{fake}";')
    result = run_static(tmp_path)
    findings = _findings(result.stdout)
    exposed = [f for f in findings if f["check"] == "static.secret.client-exposed"]
    assert exposed, "expected static.secret.client-exposed"
    assert "served to the public internet" in exposed[0]["message"]
    # Deduped: the generic repo-secret check must not report the same file again.
    assert not [f for f in findings if f["check"].startswith("secret.")]
    assert result.returncode == 1


def test_static_publishable_key_is_warn_not_critical(tmp_path):
    """pk_live_ belongs in client JS by design. Blocking it would train people
    to ignore the audit."""
    fake = "pk_" + "live_" + "b" * 30
    _plain_site(tmp_path)
    (tmp_path / "app.js").write_text(f'const key = "{fake}";')
    result = run_static(tmp_path)
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "static.secret.client-public-key" in codes
    assert "static.secret.client-exposed" not in codes
    assert result.returncode == 0


def test_static_env_file_in_publish_dir_is_critical(tmp_path):
    _plain_site(tmp_path)
    (tmp_path / ".env").write_text("API_KEY=whatever\n")
    result = run_static(tmp_path)
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "static.env-file.in-publish-dir" in codes
    assert result.returncode == 1


def test_static_env_example_in_publish_dir_is_allowed(tmp_path):
    _plain_site(tmp_path)
    (tmp_path / ".env.example").write_text("API_KEY=\n")
    codes = {f["check"] for f in _findings(run_static(tmp_path).stdout)}
    assert "static.env-file.in-publish-dir" not in codes


def test_static_meta_missing_is_warn(tmp_path):
    (tmp_path / "index.html").write_text("<html><body><h1>hola</h1></body></html>")
    result = run_static(tmp_path)
    meta = [f for f in _findings(result.stdout) if f["check"] == "static.meta.incomplete"]
    assert meta and meta[0]["severity"] == "warn"
    assert result.returncode == 0


def test_static_nojekyll_only_fires_for_github_pages(tmp_path):
    _plain_site(tmp_path)
    (tmp_path / "_assets").mkdir()
    (tmp_path / "_assets" / "a.css").write_text("body{}")
    codes = {f["check"] for f in _findings(run_static(tmp_path).stdout)}
    assert "static.nojekyll.missing" not in codes
    result = run_static(tmp_path, "--target", "github-pages")
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "static.nojekyll.missing" in codes
    assert result.returncode == 1


def test_static_publish_dir_flag_points_at_build_output(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "x"}')
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "index.html").write_text(GOOD_HEAD)
    (tmp_path / "dist" / "estilo.css").write_text("body{}")
    result = run_audit(tmp_path, "--skip-cve", "--publish-dir", "dist")
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "lockfile.missing.node" not in codes   # --publish-dir implies static
    assert result.returncode == 0


def test_static_missing_publish_dir_is_critical(tmp_path):
    (tmp_path / "index.html").write_text(GOOD_HEAD)
    result = run_audit(tmp_path, "--skip-cve", "--publish-dir", "dist")
    codes = {f["check"] for f in _findings(result.stdout)}
    assert "static.publish-dir.missing" in codes
    assert result.returncode == 1


def test_secret_patterns_stay_in_sync():
    """static_check.py ships standalone inside the Cowork plugin, so it keeps
    its own copy of SECRET_PATTERNS. This is the anti-drift guard."""
    import importlib.util

    def _load(name: str):
        spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    assert _load("audit").SECRET_PATTERNS == _load("static_check").SECRET_PATTERNS
