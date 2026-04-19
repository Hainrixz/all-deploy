#!/usr/bin/env python3
"""
Minimal skill validator — runs in CI without external deps.

Checks:
  - SKILL.md exists with YAML frontmatter.
  - name + description fields present.
  - name matches the containing directory (or a configured expected value).
  - Required script and reference files exist.

Usage:
    validate_skill.py [<skill-dir>]   # defaults to repo root
"""

from __future__ import annotations
import re
import sys
from pathlib import Path


EXPECTED_NAME = "all-deploy"

REQUIRED_FILES = [
    "SKILL.md",
    "scripts/audit.py",
    "scripts/env_extract.py",
    "references/project-types.md",
    "references/audit-checklist.md",
    "references/env-mapping.md",
    "references/agents.md",
    "references/targets/vercel.md",
    "references/targets/railway.md",
    "references/targets/docker-vps.md",
    "references/targets/cloudflared-tunnel.md",
    "assets/templates/Dockerfile.node",
    "assets/templates/Dockerfile.python",
    "assets/templates/docker-compose.example.yml",
    "assets/templates/.env.example.template",
]


def parse_frontmatter(text: str) -> dict:
    """Tiny YAML subset parser — handles `key: value` and folded `>` scalars."""
    if not text.startswith("---"):
        raise ValueError("SKILL.md does not start with frontmatter (---)")
    end = text.find("\n---", 3)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed (missing trailing ---)")
    fm = text[3:end].strip()

    result: dict = {}
    current_key = None
    folded_lines: list[str] = []
    for raw_line in fm.splitlines():
        line = raw_line.rstrip()
        if not line:
            if current_key and folded_lines:
                folded_lines.append("")
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            if current_key is not None:
                result[current_key] = " ".join(
                    s for s in (x.strip() for x in folded_lines) if s
                )
                folded_lines = []
            key, val = m.group(1), m.group(2).strip()
            if val in (">", "|"):
                current_key = key
            elif val:
                result[key] = val
                current_key = None
            else:
                current_key = key
        else:
            if current_key is not None:
                folded_lines.append(line)
    if current_key is not None:
        result[current_key] = " ".join(
            s for s in (x.strip() for x in folded_lines) if s
        )
    return result


def main() -> int:
    skill_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors: list[str] = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"FAIL: {skill_md} does not exist", file=sys.stderr)
        return 1

    try:
        fm = parse_frontmatter(skill_md.read_text())
    except ValueError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    if "name" not in fm:
        errors.append("frontmatter missing `name`")
    elif fm["name"] != EXPECTED_NAME:
        errors.append(f"name must be '{EXPECTED_NAME}', got '{fm['name']}'")

    if "description" not in fm:
        errors.append("frontmatter missing `description`")
    elif len(fm["description"]) < 50:
        errors.append(
            f"description is too short ({len(fm['description'])} chars) — "
            "include trigger cues for the skill router"
        )

    for rel in REQUIRED_FILES:
        path = skill_dir / rel
        if not path.exists():
            errors.append(f"required file missing: {rel}")

    if errors:
        print(f"FAIL — {len(errors)} issue(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"PASS — SKILL.md valid, name='{fm['name']}', "
          f"{len(REQUIRED_FILES)} required files present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
