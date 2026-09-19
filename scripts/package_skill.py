#!/usr/bin/env python3
"""
Build the release assets.

Two archives, two different shapes — this is the part that is easy to get
wrong by hand, which is why it lives in a script:

  all-deploy.skill        zip, everything nested under an `all-deploy/` folder
                          (matches the v0.1.0 asset layout)
  publish-website.plugin  zip, contents at the archive root, per the Cowork
                          plugin format

Neither includes README, CONTRIBUTING, tests, docs or CI config — those are
for people reading the repo, not for the installed skill.

Usage:
    package_skill.py [--out DIR]     # default: dist/
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_NAME = "all-deploy"

# Scripts that are repo maintenance, not part of the installed skill.
SCRIPT_EXCLUDES = {"package_skill.py", "sync_cowork_plugin.py"}
NOISE = {".DS_Store"}


def skill_files() -> list[Path]:
    files = [REPO / "SKILL.md", REPO / "LICENSE"]
    files += sorted(REPO.glob("references/**/*.md"))
    files += sorted(p for p in REPO.glob("scripts/*.py") if p.name not in SCRIPT_EXCLUDES)
    files += sorted(p for p in REPO.glob("assets/**/*") if p.is_file() and p.name not in NOISE)
    return files


def build_skill(out: Path) -> Path:
    target = out / f"{SKILL_NAME}.skill"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in skill_files():
            z.write(path, f"{SKILL_NAME}/{path.relative_to(REPO).as_posix()}")
    return target


def build_plugin(out: Path) -> Path:
    root = REPO / "cowork-plugin"
    name = "publish-website"
    target = out / f"{name}.plugin"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name in NOISE:
                continue
            z.write(path, path.relative_to(root).as_posix())
    return target


def verify_skill(archive: Path) -> bool:
    """Extract and run the repo's own validator against it. A release asset
    that is missing a reference file is worse than no release asset."""
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
        result = subprocess.run(
            [sys.executable, str(REPO / "tests" / "validate_skill.py"), str(Path(tmp) / SKILL_NAME)],
            capture_output=True, text=True,
        )
        print(f"  {result.stdout.strip() or result.stderr.strip()}")
        return result.returncode == 0


def verify_plugin(archive: Path) -> bool:
    with zipfile.ZipFile(archive) as z:
        names = set(z.namelist())
    required = {".claude-plugin/plugin.json", "skills/publish-website/SKILL.md"}
    missing = required - names
    if missing:
        print(f"  FAIL — missing from plugin: {', '.join(sorted(missing))}")
        return False
    print(f"  PASS — plugin valid, {len(names)} files")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build release assets")
    parser.add_argument("--out", default=str(REPO / "dist"))
    args = parser.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    ok = True
    for build, verify in ((build_skill, verify_skill), (build_plugin, verify_plugin)):
        archive = build(out)
        print(f"{archive.relative_to(REPO) if archive.is_relative_to(REPO) else archive}  "
              f"({archive.stat().st_size / 1024:.0f} KB)")
        ok &= verify(archive)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
