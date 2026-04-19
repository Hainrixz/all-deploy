#!/usr/bin/env python3
"""
all-deploy audit — pre-deploy safety checks.

Runs every blocking check from references/audit-checklist.md. Exit code 0 on
a clean audit (no criticals), 1 if any critical finding is present. Warnings
print but do not fail the audit.

Usage:
    audit.py <project-path> [--json] [--scoped] [--skip-remote]
                            [--skip-cve] [--allow-dirty]

Flags:
    --scoped       Run-locally mode: only secrets, start command, port binding.
    --skip-remote  Don't require a git remote (docker-vps flow, or --local).
    --skip-cve     Skip npm audit / pip-audit (network-dependent).
    --allow-dirty  Don't block on uncommitted changes.
    --json         Emit JSON report instead of human-readable.

Never prints secret values. Reports locations and pattern names only.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional


SECRET_PATTERNS = {
    "AWS_access_key": r"AKIA[0-9A-Z]{16}",
    "Stripe_live": r"sk_live_[0-9a-zA-Z]{24,}",
    "Stripe_test": r"sk_test_[0-9a-zA-Z]{24,}",
    "Stripe_publishable": r"pk_live_[0-9a-zA-Z]{24,}",
    "OpenAI_classic": r"sk-[a-zA-Z0-9]{48}\b",
    "OpenAI_project": r"sk-proj-[a-zA-Z0-9_\-]{40,}",
    "Anthropic": r"sk-ant-api03-[a-zA-Z0-9_\-]{80,}",
    "GitHub_PAT_classic": r"ghp_[A-Za-z0-9]{36}",
    "GitHub_PAT_fine": r"github_pat_[A-Za-z0-9_]{80,}",
    "GitHub_OAuth": r"gho_[A-Za-z0-9]{36}",
    "Google_API": r"AIza[0-9A-Za-z\-_]{35}",
    "Google_OAuth": r"ya29\.[0-9A-Za-z\-_]+",
    "Slack_bot": r"xoxb-[0-9A-Za-z-]{10,}",
    "Slack_user": r"xoxp-[0-9A-Za-z-]{10,}",
    "SSH_private_key": r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----",
    "JWT": r"eyJ[A-Za-z0-9_\-]{20,}\.eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}",
}

GITIGNORE_REQUIRED = [
    ".env",
    "node_modules",
    "__pycache__",
    "dist",
    ".next",
    ".venv",
    ".vercel",
]

# Env files that should never be committed (flag as critical if tracked).
ENV_BLOCKLIST = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.staging",
    ".env.test",
}

# Env files that are legitimately committed (.envrc is direnv; .env.vault is
# encrypted dotenv-vault output; *.example / *.sample are templates).
ENV_ALLOWLIST = {
    ".env.example",
    ".env.sample",
    ".env.vault",
    ".envrc",
}

# Directories to skip when walking the tree (no-git fallback).
IGNORE_DIRS = {
    "node_modules", "__pycache__", ".venv", "venv",
    ".next", "dist", "build", ".git", ".vercel", ".vscode",
    "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar", ".gz",
    ".woff", ".woff2", ".ttf", ".otf", ".ico", ".webp", ".mp4", ".mov",
    ".mp3", ".wav", ".avi", ".bin", ".so", ".dylib", ".dll", ".exe",
    ".jar", ".war", ".class", ".pyc",
}


@dataclass
class Finding:
    severity: str   # "critical" | "warn" | "info"
    check: str
    message: str
    fix: Optional[str] = None
    location: Optional[str] = None


class Auditor:
    def __init__(
        self,
        project: Path,
        scoped: bool,
        skip_remote: bool,
        skip_cve: bool,
        allow_dirty: bool,
    ):
        self.project = project.resolve()
        self.scoped = scoped
        self.skip_remote = skip_remote
        self.skip_cve = skip_cve
        self.allow_dirty = allow_dirty
        self.findings: List[Finding] = []
        self._tracked_cache: Optional[List[Path]] = None

    def run(self) -> None:
        self.check_secrets()
        self.check_start_command()
        self.check_port_binding()
        if self.scoped:
            return
        self.check_gitignore()
        self.check_lockfile()
        self.check_env_example()
        self.check_runtime_version()
        if not self.allow_dirty:
            self.check_clean_tree()
        if not self.skip_remote:
            self.check_git_remote()
        if not self.skip_cve:
            self.check_known_cves()

    def _tracked_files(self) -> List[Path]:
        """Git-tracked files only. Returns [] if not a git repo.

        Use for checks that specifically require tracked status (e.g., the
        '.env is committed to git' flag). For content scans that should
        work without git, use _scannable_files()."""
        if self._tracked_cache is not None:
            return self._tracked_cache
        try:
            out = subprocess.check_output(
                ["git", "-C", str(self.project), "ls-files"],
                text=True, stderr=subprocess.DEVNULL,
            )
            self._tracked_cache = [
                self.project / line for line in out.splitlines() if line.strip()
            ]
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._tracked_cache = []
        return self._tracked_cache

    def _scannable_files(self) -> List[Path]:
        """All files worth scanning for content (secrets, port binding).

        Prefers git-tracked list, falls back to a tree walk that skips the
        standard ignore dirs. Guarantees non-empty scans in scoped/local
        mode even when the project has no git initialized."""
        tracked = self._tracked_files()
        if tracked:
            return tracked
        files: List[Path] = []
        for p in self.project.rglob("*"):
            if any(part in IGNORE_DIRS for part in p.parts):
                continue
            if p.is_file():
                files.append(p)
        return files

    def check_secrets(self) -> None:
        # (1) Flag committed env files using an explicit block/allow list —
        # .envrc (direnv) and .env.vault (encrypted) are legitimately tracked.
        for f in self._tracked_files():
            name = f.name
            if name in ENV_BLOCKLIST and name not in ENV_ALLOWLIST:
                try:
                    rel = f.relative_to(self.project)
                except ValueError:
                    rel = f
                self.findings.append(Finding(
                    "critical", "secret.env-tracked",
                    f"{rel} is committed to git.",
                    fix=(
                        "Run `git rm --cached <file>`, add to .gitignore, rotate every "
                        "value in that file, and rewrite history with `trufflehog` or "
                        "`git-filter-repo`."
                    ),
                    location=str(rel),
                ))

        # (2) Content scan for leaked credentials. Uses the scannable list so
        # scoped/local mode still scans when there's no git.
        for f in self._scannable_files():
            if not f.is_file() or f.suffix.lower() in BINARY_EXTS:
                continue
            # Skip the legitimately-tracked env files from content-scan too —
            # .envrc contains shell code that looks like many things.
            if f.name in ENV_ALLOWLIST:
                continue
            try:
                content = f.read_text(errors="ignore")
            except (PermissionError, OSError):
                continue
            try:
                rel = f.relative_to(self.project)
            except ValueError:
                rel = f
            for pattern_name, pattern in SECRET_PATTERNS.items():
                if re.search(pattern, content):
                    self.findings.append(Finding(
                        "critical", f"secret.{pattern_name}",
                        f"{pattern_name} pattern matched in {rel}.",
                        fix=(
                            "Remove the secret from source, rotate the credential, "
                            "rewrite git history, and load the value via an environment "
                            "variable instead."
                        ),
                        location=str(rel),
                    ))

    def check_gitignore(self) -> None:
        path = self.project / ".gitignore"
        if not path.exists():
            self.findings.append(Finding(
                "critical", "gitignore.missing",
                ".gitignore is missing.",
                fix="Create one covering .env, node_modules, __pycache__, dist, .next, .venv, .vercel.",
            ))
            return
        content = path.read_text()
        for req in GITIGNORE_REQUIRED:
            if req not in content:
                self.findings.append(Finding(
                    "warn", "gitignore.incomplete",
                    f".gitignore does not include `{req}`.",
                    fix=f"Append `{req}` to .gitignore.",
                ))

    def check_lockfile(self) -> None:
        node_locks = ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb"]
        py_locks = ["uv.lock", "poetry.lock", "Pipfile.lock"]
        if (self.project / "package.json").exists():
            if not any((self.project / lk).exists() for lk in node_locks):
                self.findings.append(Finding(
                    "critical", "lockfile.missing.node",
                    "No Node lockfile present.",
                    fix=(
                        "Run your package manager (`npm install` / `pnpm install` / "
                        "`yarn` / `bun install`) and commit the generated lockfile."
                    ),
                ))
        py_manifest = (
            (self.project / "pyproject.toml").exists()
            or (self.project / "Pipfile").exists()
        )
        has_req_txt = (self.project / "requirements.txt").exists()
        if py_manifest and not has_req_txt:
            if not any((self.project / lk).exists() for lk in py_locks):
                self.findings.append(Finding(
                    "warn", "lockfile.missing.python",
                    "No Python lockfile (uv.lock, poetry.lock, Pipfile.lock).",
                    fix=(
                        "Generate one with `uv lock` / `poetry lock` / `pipenv lock`, "
                        "or pin versions in requirements.txt."
                    ),
                ))

    def check_env_example(self) -> None:
        # Accept either .env.example or .env.sample — both are common.
        example_files = [
            self.project / ".env.example",
            self.project / ".env.sample",
        ]
        found_examples = [p for p in example_files if p.exists()]
        extractor = Path(__file__).parent / "env_extract.py"
        if not extractor.exists():
            return
        try:
            result = subprocess.run(
                [sys.executable, str(extractor), str(self.project), "--as-json"],
                capture_output=True, text=True, check=True, timeout=30,
            )
            used = json.loads(result.stdout) if result.stdout.strip() else []
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
            used = []
        if not used:
            return
        if not found_examples:
            self.findings.append(Finding(
                "critical", "env.example.missing",
                f"Neither .env.example nor .env.sample exists, but the code reads {len(used)} env var(s).",
                fix=(
                    "Create .env.example with placeholder values for: "
                    + ", ".join(sorted(used))
                ),
            ))
            return
        declared: set = set()
        for example in found_examples:
            for line in example.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    declared.add(line.split("=", 1)[0].strip())
        missing = set(used) - declared
        if missing:
            example_name = found_examples[0].name
            self.findings.append(Finding(
                "critical", "env.example.incomplete",
                f"{example_name} is missing {len(missing)} key(s): {', '.join(sorted(missing))}",
                fix=(
                    f"Append to {example_name}:\n"
                    + "\n".join(f"  {k}=" for k in sorted(missing))
                ),
            ))

    def check_start_command(self) -> None:
        # --- Node ---
        pkg = self.project / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text())
            except json.JSONDecodeError:
                data = {}
            scripts = data.get("scripts", {}) or {}
            if not any(scripts.get(k) for k in ("start", "dev", "build")):
                self.findings.append(Finding(
                    "warn", "start-command.missing.node",
                    "package.json has no `start`, `dev`, or `build` script.",
                    fix=(
                        'Add `"scripts": {"start": "node server.js"}` or '
                        "the equivalent for your framework."
                    ),
                ))

        # --- Python ---
        pyproject = self.project / "pyproject.toml"
        procfile = self.project / "Procfile"
        main_py = self.project / "main.py"
        py_manifest = pyproject.exists() or (self.project / "requirements.txt").exists()
        if not py_manifest:
            return

        has_pyproject_scripts = False
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                if re.search(r"\[project\.scripts\]|\[tool\.poetry\.scripts\]", content):
                    has_pyproject_scripts = True
            except (PermissionError, OSError):
                pass

        has_runnable_main = False
        if main_py.exists():
            try:
                content = main_py.read_text(errors="ignore")
                if "__main__" in content or re.search(r"\b(FastAPI|Flask|app\s*=\s*)", content):
                    has_runnable_main = True
            except (PermissionError, OSError):
                pass

        if not (has_pyproject_scripts or procfile.exists() or has_runnable_main):
            self.findings.append(Finding(
                "warn", "start-command.missing.python",
                "No Python entry point found (no [project.scripts], Procfile, or main.py).",
                fix=(
                    "Add a Procfile (e.g., `web: uvicorn main:app --host 0.0.0.0 --port $PORT`) "
                    "or declare [project.scripts] in pyproject.toml."
                ),
            ))

    def check_runtime_version(self) -> None:
        # Node runtime pinning
        pkg = self.project / "package.json"
        if pkg.exists():
            has_node_version = (
                (self.project / ".nvmrc").exists()
                or (self.project / ".node-version").exists()
            )
            if not has_node_version:
                try:
                    data = json.loads(pkg.read_text())
                    if (data.get("engines") or {}).get("node"):
                        has_node_version = True
                except json.JSONDecodeError:
                    pass
            if not has_node_version:
                self.findings.append(Finding(
                    "warn", "runtime.missing.node",
                    "Node runtime version not pinned — deploys may use an unexpected Node version.",
                    fix=(
                        "Add `.nvmrc` (e.g., `echo 'lts/*' > .nvmrc`) or set "
                        "`engines.node` in package.json."
                    ),
                ))
        # Python runtime pinning
        pyproject = self.project / "pyproject.toml"
        if pyproject.exists() or (self.project / "requirements.txt").exists():
            has_py_version = (self.project / ".python-version").exists()
            if not has_py_version and pyproject.exists():
                try:
                    content = pyproject.read_text()
                    if re.search(r'requires-python\s*=|python_version\s*=', content):
                        has_py_version = True
                except (PermissionError, OSError):
                    pass
            if not has_py_version:
                self.findings.append(Finding(
                    "warn", "runtime.missing.python",
                    "Python runtime version not pinned.",
                    fix=(
                        "Add `.python-version` (e.g., `echo '3.12' > .python-version`) "
                        "or set `requires-python` in pyproject.toml."
                    ),
                ))

    def check_port_binding(self) -> None:
        tracked = self._tracked_files()
        source_files = [
            f for f in tracked
            if f.suffix in {".js", ".ts", ".tsx", ".jsx", ".py", ".mjs", ".cjs"}
        ]
        has_localhost_listen = False
        has_zero_binding = False
        for f in source_files:
            try:
                content = f.read_text(errors="ignore")
            except (PermissionError, OSError):
                continue
            if re.search(r"['\"]0\.0\.0\.0['\"]", content):
                has_zero_binding = True
            if re.search(r"['\"](?:localhost|127\.0\.0\.1)['\"]", content) and \
                    re.search(r"\b(listen|run|serve|bind)\b", content, re.IGNORECASE):
                has_localhost_listen = True
        if has_localhost_listen and not has_zero_binding:
            self.findings.append(Finding(
                "warn", "port-binding.localhost-only",
                "Service appears to bind localhost/127.0.0.1 — most hosts (Railway, Fly, Docker) need 0.0.0.0.",
                fix='Bind to 0.0.0.0 (e.g., `host="0.0.0.0"` or `--host 0.0.0.0`).',
            ))

    def check_clean_tree(self) -> None:
        # Use diff-index so that *untracked* files don't count as "dirty" —
        # otherwise a fresh `.env.example` the audit just asked the user to
        # create would fail the next audit run.
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project), "diff-index", "--quiet", "HEAD", "--"],
                capture_output=True,
            )
        except FileNotFoundError:
            return
        if result.returncode == 0:
            # Tracked changes clean. Still warn about untracked files.
            try:
                untracked = subprocess.check_output(
                    ["git", "-C", str(self.project), "ls-files",
                     "--others", "--exclude-standard"],
                    text=True, stderr=subprocess.DEVNULL,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                untracked = ""
            lines = [ln for ln in untracked.splitlines() if ln.strip()]
            if lines:
                self.findings.append(Finding(
                    "warn", "git.untracked",
                    f"{len(lines)} untracked file(s). Consider committing before deploy.",
                    fix="`git status` to review; `git add` + commit if they belong in the repo.",
                ))
            return
        # Tracked changes exist → critical.
        try:
            diff = subprocess.check_output(
                ["git", "-C", str(self.project), "diff", "--name-only", "HEAD"],
                text=True, stderr=subprocess.DEVNULL,
            )
            count = len([ln for ln in diff.splitlines() if ln.strip()])
        except (subprocess.CalledProcessError, FileNotFoundError):
            count = 0
        self.findings.append(Finding(
            "critical", "git.dirty",
            f"Tracked files have uncommitted changes ({count} file(s)).",
            fix=(
                "`git status`, then `git add` + `git commit`, or `git stash`, "
                "or re-run with --allow-dirty."
            ),
        ))

    def check_git_remote(self) -> None:
        try:
            out = subprocess.check_output(
                ["git", "-C", str(self.project), "remote", "-v"],
                text=True, stderr=subprocess.DEVNULL,
            )
            if not out.strip():
                self.findings.append(Finding(
                    "critical", "git.remote.missing",
                    "No git remote configured.",
                    fix="Add a remote: `git remote add origin <url>`. Re-run with --skip-remote if this is intentional (docker-vps flow).",
                ))
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    def check_known_cves(self) -> None:
        if (self.project / "package.json").exists():
            self._check_npm_audit()
        if (self.project / "requirements.txt").exists() or (self.project / "pyproject.toml").exists():
            self._check_pip_audit()

    def _check_npm_audit(self) -> None:
        try:
            result = subprocess.run(
                ["npm", "audit", "--production", "--audit-level=high", "--json"],
                cwd=self.project, capture_output=True, text=True, timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return
        if not result.stdout:
            return
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return
        meta = (data.get("metadata") or {}).get("vulnerabilities") or {}
        critical = int(meta.get("critical", 0) or 0)
        high = int(meta.get("high", 0) or 0)
        if critical > 0:
            self.findings.append(Finding(
                "critical", "cve.npm.critical",
                f"{critical} critical npm vulnerability(ies).",
                fix="Run `npm audit fix` or upgrade the vulnerable packages before deploying.",
            ))
        elif high > 0:
            self.findings.append(Finding(
                "warn", "cve.npm.high",
                f"{high} high-severity npm vulnerability(ies).",
                fix="Run `npm audit fix` when convenient.",
            ))

    def _check_pip_audit(self) -> None:
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json", "--strict"],
                cwd=self.project, capture_output=True, text=True, timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return
        if not result.stdout:
            return
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return
        deps = data.get("dependencies", []) or []
        vulnerable = [d for d in deps if d.get("vulns")]
        if vulnerable:
            # pip-audit JSON doesn't expose severity consistently; treat any
            # finding as critical to match npm's default behavior for the
            # "--audit-level=high" run (which also only reports when there's
            # something worth reporting). Users can bypass with --skip-cve.
            self.findings.append(Finding(
                "critical", "cve.python",
                f"{len(vulnerable)} Python package(s) with known vulnerabilities.",
                fix=(
                    f"Upgrade (first 5): {', '.join(d['name'] for d in vulnerable[:5])}. "
                    "Run `pip-audit` without `--format json` to see full details."
                ),
            ))


def emit_report(findings: List[Finding], as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
        return
    criticals = [f for f in findings if f.severity == "critical"]
    warns = [f for f in findings if f.severity == "warn"]
    if not findings:
        print("Audit clean — no findings.")
        return
    if criticals:
        print(f"\n{len(criticals)} critical issue(s) blocking deploy:\n")
        for f in criticals:
            print(f"  [{f.check}] {f.message}")
            if f.location:
                print(f"      at:  {f.location}")
            if f.fix:
                for line in f.fix.splitlines():
                    print(f"      fix: {line}")
            print()
    if warns:
        print(f"{len(warns)} warning(s) (non-blocking):\n")
        for f in warns:
            print(f"  [{f.check}] {f.message}")
            if f.fix:
                for line in f.fix.splitlines():
                    print(f"      fix: {line}")
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="all-deploy pre-deploy audit")
    parser.add_argument("project_path", help="Path to project directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--scoped", action="store_true", help="Run-locally mode")
    parser.add_argument("--skip-remote", action="store_true", help="Don't require git remote")
    parser.add_argument("--skip-cve", action="store_true", help="Skip npm audit / pip-audit")
    parser.add_argument("--allow-dirty", action="store_true", help="Don't block on uncommitted changes")
    args = parser.parse_args()

    project = Path(args.project_path)
    if not project.exists():
        print(f"Error: {project} does not exist.", file=sys.stderr)
        sys.exit(2)

    auditor = Auditor(
        project=project,
        scoped=args.scoped,
        skip_remote=args.skip_remote,
        skip_cve=args.skip_cve,
        allow_dirty=args.allow_dirty,
    )
    auditor.run()
    emit_report(auditor.findings, as_json=args.json)
    criticals = [f for f in auditor.findings if f.severity == "critical"]
    sys.exit(1 if criticals else 0)


if __name__ == "__main__":
    main()
