#!/usr/bin/env python3
"""
Extract environment variable names used in source code.

Scans JavaScript/TypeScript and Python source files for references to
environment variables and emits a unique, sorted list.

Detects:
  JS/TS: process.env.FOO, process.env["FOO"], process.env['FOO'],
         import.meta.env.FOO, Deno.env.get("FOO"), Bun.env.FOO
  Python: os.environ["FOO"], os.environ.get("FOO"), os.getenv("FOO"),
          environ["FOO"], getenv("FOO")

Usage:
    env_extract.py <project-path> [--as-json]

Ignores platform-provided vars (NODE_ENV, PORT, PATH, etc.) to keep the
output focused on application-level configuration.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set


JS_PATTERNS = [
    r"process\.env\.([A-Z][A-Z0-9_]*)",
    r"process\.env\[['\"]([A-Z][A-Z0-9_]*)['\"]\]",
    r"import\.meta\.env\.([A-Z][A-Z0-9_]*)",
    r"Deno\.env\.get\(['\"]([A-Z][A-Z0-9_]*)['\"]\)",
    r"Bun\.env\.([A-Z][A-Z0-9_]*)",
]

# Destructuring patterns — captures the contents between { } for later parsing.
# Handles:
#   const { FOO } = process.env;
#   const { FOO, BAR } = import.meta.env;
#   const { FOO: renamed, BAR = 'default' } = process.env;
JS_DESTRUCTURE_PATTERNS = [
    r"(?:const|let|var)\s*\{\s*([^}]+?)\s*\}\s*=\s*process\.env",
    r"(?:const|let|var)\s*\{\s*([^}]+?)\s*\}\s*=\s*import\.meta\.env",
    r"(?:const|let|var)\s*\{\s*([^}]+?)\s*\}\s*=\s*Bun\.env",
]

PY_PATTERNS = [
    r"os\.environ\[['\"]([A-Z][A-Z0-9_]*)['\"]\]",
    r"os\.environ\.get\(['\"]([A-Z][A-Z0-9_]*)['\"]",
    r"os\.getenv\(['\"]([A-Z][A-Z0-9_]*)['\"]",
    r"(?<!os\.)environ\[['\"]([A-Z][A-Z0-9_]*)['\"]\]",
    r"(?<!os\.)getenv\(['\"]([A-Z][A-Z0-9_]*)['\"]",
]

IGNORE = {
    "NODE_ENV", "PORT", "HOST", "HOSTNAME", "PYTHONPATH", "PYTHONUNBUFFERED",
    "PATH", "HOME", "USER", "SHELL", "LANG", "LC_ALL", "TERM", "TZ", "PWD",
    "CI", "DEBUG", "LOG_LEVEL",
}

JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
PY_EXTS = {".py"}


def list_source_files(project: Path) -> List[Path]:
    """Prefer git-tracked files; fall back to walking the tree."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(project), "ls-files"],
            text=True, stderr=subprocess.DEVNULL,
        )
        return [project / line for line in out.splitlines() if line.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    ignore_dirs = {
        "node_modules", "__pycache__", ".venv", "venv",
        ".next", "dist", "build", ".git", ".vercel", "coverage",
    }
    files: List[Path] = []
    for p in project.rglob("*"):
        if any(part in ignore_dirs for part in p.parts):
            continue
        if p.is_file():
            files.append(p)
    return files


def _parse_destructure_block(block: str) -> Set[str]:
    """Split a destructuring block on commas, strip `:alias` and `=default`,
    and return any identifiers that look like UPPERCASE env var names."""
    names: Set[str] = set()
    for segment in block.split(","):
        segment = segment.strip()
        if not segment:
            continue
        # Keep only the part before `:` (alias) or `=` (default).
        segment = re.split(r"[:=]", segment, maxsplit=1)[0].strip()
        m = re.match(r"([A-Z][A-Z0-9_]*)$", segment)
        if m:
            names.add(m.group(1))
    return names


def extract(project: Path) -> Set[str]:
    found: Set[str] = set()
    for f in list_source_files(project):
        if not f.is_file():
            continue
        ext = f.suffix
        if ext not in JS_EXTS and ext not in PY_EXTS:
            continue
        try:
            content = f.read_text(errors="ignore")
        except (PermissionError, OSError):
            continue
        if ext in JS_EXTS:
            for pat in JS_PATTERNS:
                for m in re.finditer(pat, content):
                    name = m.group(1)
                    if name not in IGNORE:
                        found.add(name)
            for pat in JS_DESTRUCTURE_PATTERNS:
                for m in re.finditer(pat, content):
                    for name in _parse_destructure_block(m.group(1)):
                        if name not in IGNORE:
                            found.add(name)
        else:
            for pat in PY_PATTERNS:
                for m in re.finditer(pat, content):
                    name = m.group(1)
                    if name not in IGNORE:
                        found.add(name)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract env vars used in source")
    parser.add_argument("project_path", help="Path to project directory")
    parser.add_argument("--as-json", action="store_true", help="Emit JSON array to stdout")
    args = parser.parse_args()

    project = Path(args.project_path)
    if not project.exists():
        print(f"Error: {project} does not exist.", file=sys.stderr)
        sys.exit(2)

    names = sorted(extract(project))
    if args.as_json:
        print(json.dumps(names))
    else:
        for n in names:
            print(n)


if __name__ == "__main__":
    main()
