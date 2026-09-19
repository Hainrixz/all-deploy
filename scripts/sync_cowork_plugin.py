#!/usr/bin/env python3
"""
Keep cowork-plugin/ in sync with its sources in this repo.

The Cowork plugin has to be self-contained — someone installs it on its own,
without the rest of the skill — so it carries copies of three files. Copies
drift. This script regenerates them, and `--check` fails CI when they have.

Usage:
    sync_cowork_plugin.py            # rewrite the copies
    sync_cowork_plugin.py --check    # exit 1 if any copy is stale
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "cowork-plugin" / "skills" / "publish-website"

# (source, destination, [(find, replace), ...]) — the rewrites fix links that
# point at files which only exist in the full skill.
FILES = [
    (
        REPO / "scripts" / "static_check.py",
        PLUGIN / "scripts" / "static_check.py",
        [],
    ),
    (
        REPO / "references" / "static-hosting.md",
        PLUGIN / "references" / "hosts.md",
        [
            ("`references/custom-domain.md`", "`custom-domain.md`"),
            (
                "`references/targets/cloudflare-pages.md`",
                "the all-deploy skill's Cloudflare Pages playbook",
            ),
            ("see `references/static-sites.md`", "see SKILL.md, step 2"),
        ],
    ),
    (
        REPO / "references" / "custom-domain.md",
        PLUGIN / "references" / "custom-domain.md",
        [],
    ),
]


def render(source: Path, rewrites) -> str:
    text = source.read_text()
    for find, replace in rewrites:
        if find not in text:
            print(f"WARN: rewrite target not found in {source.name}: {find}", file=sys.stderr)
        text = text.replace(find, replace)
    return text


def main() -> int:
    check_only = "--check" in sys.argv
    stale = []
    for source, dest, rewrites in FILES:
        if not source.exists():
            print(f"FAIL: missing source {source}", file=sys.stderr)
            return 1
        expected = render(source, rewrites)
        current = dest.read_text() if dest.exists() else None
        if current == expected:
            continue
        if check_only:
            stale.append(dest.relative_to(REPO))
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(expected)
            print(f"updated {dest.relative_to(REPO)}")
    if stale:
        print(
            "FAIL — cowork-plugin copies are out of date:\n"
            + "\n".join(f"  - {p}" for p in stale)
            + "\n\nRun: python3 scripts/sync_cowork_plugin.py",
            file=sys.stderr,
        )
        return 1
    print("cowork-plugin is in sync." if check_only else "done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
