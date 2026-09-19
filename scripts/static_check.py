#!/usr/bin/env python3
"""
all-deploy static-site checks — what breaks a plain web page once it's online.

Standalone by design: emits the same Finding shape audit.py uses, so audit.py
shells out to it (the way it already does for env_extract.py) and the Cowork
plugin can ship this one file and run it on its own.

Usage:
    static_check.py <publish-dir> [--json] [--target NAME] [--scoped]

Flags:
    --target   Host the page is going to. Only `github-pages` changes checks.
    --scoped   Fast subset: entry page, asset references, exposed keys.
    --json     Emit JSON (default is human-readable).

Why the case check matters, and why it can't use Path.exists(): macOS and
Windows filesystems are case-insensitive, so `Path("assets/Logo.png").exists()`
returns True when you asked for `assets/logo.png`. The page loads on the
author's machine and 404s on the host's Linux CDN. Every reference is resolved
against a case-folded index of the real on-disk names instead.

Never prints secret values. Reports locations and pattern names only.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import unquote

# Kept byte-identical to audit.py's SECRET_PATTERNS. tests/test_audit.py has
# test_secret_patterns_in_sync to make sure the two never drift apart.
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

# Keys that are *designed* to sit in client-side code. Flagging these as
# critical would block a correctly-built site and teach people to ignore the
# audit, so they warn instead.
CLIENT_PUBLIC_OK = {"Stripe_publishable", "Google_API", "JWT"}

# Files a static host actually serves as text. Anything here is world-readable
# the moment it deploys, private repo or not.
SERVED_TEXT_EXTS = {
    ".html", ".htm", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".css",
    ".json", ".txt", ".xml", ".webmanifest", ".map", ".md", ".svg",
}

HTML_EXTS = {".html", ".htm"}

ENV_ALLOWLIST = {".env.example", ".env.sample", ".env.vault", ".envrc"}

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache", ".DS_Store"}

# Home-directory roots that mean "this points at a path on someone's computer".
LOCAL_ROOT_RE = re.compile(r"^/(Users|home|root|Volumes|private|mnt|tmp|c/Users)/")
DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")
TEMPLATE_TOKENS = ("{{", "{%", "<%", "${")

CSS_URL_RE = re.compile(r"""url\(\s*['"]?([^'")]+?)['"]?\s*\)""")

# Host limits drift. They live here so there's one place to edit, they are all
# warnings, and every message tells you to check your target's current numbers.
LIMITS = {
    "file_warn_bytes": 10 * 1024 * 1024,   # a 10 MB asset is a slow page
    "total_warn_bytes": 1024 ** 3,         # GitHub Pages published-site limit
    "file_count_warn": 20_000,             # Cloudflare Pages files per deployment
}

MAX_LISTED = 8
MAX_CASE_FINDINGS = 20


@dataclass
class Finding:
    severity: str   # "critical" | "warn" | "info"
    check: str
    message: str
    fix: Optional[str] = None
    location: Optional[str] = None


class RefCollector(HTMLParser):
    """Pulls local-asset references and <head> metadata out of one HTML file.

    HTMLParser rather than a regex: it already lowercases tags and attributes,
    unescapes character references in values, handles unquoted attributes and
    self-closing tags, keeps <!-- comments --> out of handle_starttag, and
    gives getpos() so findings can say index.html:14.
    """

    URL_ATTRS = ("src", "href", "poster", "data-src")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: List[Tuple[str, str, int]] = []
        self.meta: Dict[str, str] = {}
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        line, _ = self.getpos()
        d = {k: (v or "") for k, v in attrs}
        for attr in self.URL_ATTRS:
            if d.get(attr):
                self.refs.append((attr, d[attr], line))
        if d.get("srcset"):
            for candidate in d["srcset"].split(","):
                parts = candidate.strip().split()
                if parts:
                    self.refs.append(("srcset", parts[0], line))
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (d.get("name") or d.get("property") or "").lower()
            if key:
                self.meta[key] = d.get("content", "").strip()
        elif tag == "html" and d.get("lang"):
            self.meta["__lang"] = d["lang"]

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and data.strip():
            self.meta["__title"] = data.strip()


def classify_ref(value: str) -> str:
    """One of: ignore, absolute-local, root-relative, relative.

    Order matters — the drive-letter test must run before the scheme test, or
    `C:\\Users\\x.png` parses as a URL with scheme `c`.
    """
    v = value.strip()
    if not v or v.startswith("#"):
        return "ignore"
    if DRIVE_RE.match(v) or v.startswith("\\\\"):
        return "absolute-local"
    if v.lower().startswith("file:"):
        return "absolute-local"
    if SCHEME_RE.match(v):
        return "ignore"          # http:, https:, mailto:, tel:, data:
    if v.startswith("//"):
        return "ignore"          # protocol-relative CDN
    if LOCAL_ROOT_RE.match(v):
        return "absolute-local"
    if any(tok in v for tok in TEMPLATE_TOKENS):
        return "ignore"          # templating placeholder, not a real path
    return "root-relative" if v.startswith("/") else "relative"


def build_index(root: Path) -> Tuple[Set[str], Dict[str, str], List[Path]]:
    """Real on-disk names under root.

    Returns (exact, folded, files) where exact holds every relative posix path
    as stored, folded maps casefolded path -> stored path, and files is every
    regular file. os.walk reports the stored case even on a case-insensitive
    filesystem, which is what makes the case-mismatch check possible at all.
    """
    exact: Set[str] = set()
    folded: Dict[str, str] = {}
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        filenames = sorted(filenames)
        base = Path(dirpath).relative_to(root)
        for name in list(dirnames) + filenames:
            rel = (base / name).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            exact.add(rel)
            folded.setdefault(rel.casefold(), rel)
        for name in filenames:
            files.append(Path(dirpath) / name)
    return exact, folded, files


def fs_case_insensitive(probe: Path) -> bool:
    """Only used to word the message — the check itself works either way."""
    s = str(probe)
    try:
        if s != s.upper() and os.path.exists(s.upper()):
            return True
        if s != s.lower() and os.path.exists(s.lower()):
            return True
    except OSError:
        pass
    return False


def normalize_ref(raw: str, kind: str, source_rel: str) -> Optional[str]:
    """Resolve a reference to a path relative to the publish root, or None."""
    value = raw.split("#", 1)[0].split("?", 1)[0]
    value = unquote(value).strip()
    if not value:
        return None
    if kind == "root-relative":
        joined = value.lstrip("/")
    else:
        base = os.path.dirname(source_rel)
        joined = os.path.join(base, value) if base else value
    rel = os.path.normpath(joined).replace(os.sep, "/")
    if rel in (".", ""):
        return None
    return rel


class StaticChecker:
    def __init__(self, publish_dir: Path, target: str = "generic", scoped: bool = False):
        self.dir = publish_dir
        self.target = (target or "generic").lower()
        self.scoped = scoped
        self.findings: List[Finding] = []
        self.exact: Set[str] = set()
        self.folded: Dict[str, str] = {}
        self.files: List[Path] = []

    # ---------------------------------------------------------------- run

    def run(self) -> None:
        if not self.dir.is_dir():
            self.findings.append(Finding(
                "critical", "static.publish-dir.missing",
                f"{self.dir} does not exist — there is nothing to upload.",
                fix=(
                    "Point --publish-dir at the folder that actually holds index.html.\n"
                    "If your site has a build step, run the build first (npm run build, "
                    "hugo, jekyll build) and publish its output folder."
                ),
                location=str(self.dir),
            ))
            return

        self.exact, self.folded, self.files = build_index(self.dir)
        entry = self.check_entry()
        self.check_references(entry)
        self.check_env_files()
        self.check_client_secrets()
        if self.scoped:
            return
        self.check_sizes()
        self.check_meta(entry)
        self.check_nojekyll()

    # -------------------------------------------------------------- checks

    def check_entry(self) -> Optional[str]:
        """Returns the entry page's relative path, or None."""
        if "index.html" in self.exact:
            return "index.html"

        variant = self.folded.get("index.html")
        if variant:
            self.findings.append(Finding(
                "critical", "static.entry.missing",
                f'The home page is named "{variant}" — hosts serve "index.html" exactly, '
                "so the root URL will 404.",
                fix=(
                    "Rename it, in two steps (a one-step case-only rename is a no-op on "
                    "macOS and Windows):\n"
                    f"  mv {variant} index.tmp && mv index.tmp index.html"
                ),
                location=variant,
            ))
            return variant

        candidates = sorted(p for p in self.exact if p.lower().endswith((".html", ".htm")))
        if not candidates:
            self.findings.append(Finding(
                "critical", "static.entry.missing",
                f"No HTML file in {self.dir} — there is no page to publish.",
                fix=(
                    "Check you pointed at the right folder. If the site has a build step, "
                    "run it first and publish the output folder (dist/, _site/, public/)."
                ),
                location=str(self.dir),
            ))
            return None

        pick = candidates[0]
        self.findings.append(Finding(
            "critical", "static.entry.missing",
            f"No index.html in {self.dir} — the site's root URL will 404. "
            f"Found {len(candidates)} other HTML file(s).",
            fix=(
                "Rename your main page to exactly index.html (lowercase):\n"
                f"  mv {pick} index.html"
            ),
            location=pick,
        ))
        return pick

    def _html_files(self) -> List[Path]:
        return [f for f in self.files if f.suffix.lower() in HTML_EXTS]

    def _css_files(self) -> List[Path]:
        return [f for f in self.files if f.suffix.lower() == ".css"]

    def check_references(self, entry: Optional[str]) -> None:
        missing: List[str] = []
        absolute: List[str] = []
        escapes: List[str] = []
        root_relative: List[str] = []
        case_hits: List[Tuple[str, str, str]] = []   # (referenced, actual, location)
        self.entry_meta: Dict[str, str] = {}

        def record(raw: str, source_rel: str, line: Optional[int]) -> None:
            kind = classify_ref(raw)
            if kind == "ignore":
                return
            where = f"{source_rel}:{line}" if line else source_rel
            if kind == "absolute-local":
                absolute.append(f"{raw}  <- {where}")
                return
            if kind == "root-relative" and self.target == "github-pages":
                root_relative.append(f"{raw}  <- {where}")
            rel = normalize_ref(raw, kind, source_rel)
            if rel is None:
                return
            if rel.startswith("../") or rel.startswith("/"):
                escapes.append(f"{raw}  <- {where}")
                return
            if rel in self.exact:
                return
            # Clean-URL fallbacks: href="about/" and href="about" both resolve
            # on most hosts when about/index.html or about.html exists.
            if f"{rel}/index.html" in self.exact or f"{rel}.html" in self.exact:
                return
            actual = self.folded.get(rel.casefold())
            if actual:
                case_hits.append((rel, actual, where))
            else:
                missing.append(f"{rel}  <- {where}")

        for html in self._html_files():
            try:
                source_rel = html.relative_to(self.dir).as_posix()
            except ValueError:
                continue
            parser = RefCollector()
            try:
                parser.feed(html.read_text(errors="ignore"))
                parser.close()
            except Exception:
                continue   # a malformed page must never crash the audit
            if entry and source_rel == entry:
                self.entry_meta = parser.meta
            for _attr, value, line in parser.refs:
                record(value, source_rel, line)

        for css in self._css_files():
            try:
                source_rel = css.relative_to(self.dir).as_posix()
                content = css.read_text(errors="ignore")
            except (ValueError, OSError):
                continue
            for match in CSS_URL_RE.finditer(content):
                record(match.group(1), source_rel, None)

        if absolute:
            self.findings.append(Finding(
                "critical", "static.path.absolute-local",
                f"{len(absolute)} reference(s) point at a path on your computer, "
                "not at a file in the site. Those images and styles will be blank for everyone else.",
                fix=(
                    f"Copy those files into {self.dir}/ and reference them relatively "
                    "(e.g. images/photo.jpg).\n" + _listing(absolute)
                ),
                location=absolute[0].split("<-")[-1].strip(),
            ))

        for referenced, actual, where in case_hits[:MAX_CASE_FINDINGS]:
            insensitive = fs_case_insensitive(self.dir / actual)
            why = (
                "Your filesystem is case-insensitive, so this loads on your machine "
                "and 404s on the host.\n"
                if insensitive else
                "Hosts match filenames exactly, including capitals.\n"
            )
            fix = why + f'Edit {where} and change the reference to "{actual}".'
            # Offer the rename only when the folders already match — renaming
            # across a differently-capitalised directory needs mkdir too, and a
            # one-step case-only rename is a no-op on macOS and Windows anyway.
            if os.path.dirname(referenced) == os.path.dirname(actual):
                fix += (
                    "\nOr rename the file to match, in two steps:\n"
                    f"  mv {actual} {actual}.tmp && mv {actual}.tmp {referenced}"
                )
            self.findings.append(Finding(
                "critical", "static.asset.case-mismatch",
                f'Reference is "{referenced}" but the file on disk is "{actual}" — '
                "same name, different capitals.",
                fix=fix,
                location=where,
            ))
        if len(case_hits) > MAX_CASE_FINDINGS:
            extra = len(case_hits) - MAX_CASE_FINDINGS
            self.findings.append(Finding(
                "critical", "static.asset.case-mismatch",
                f"...and {extra} more reference(s) that differ only in capitalisation.",
                fix="Fix the ones listed above, then run the audit again for the rest.",
            ))

        if missing:
            self.findings.append(Finding(
                "warn", "static.asset.missing",
                f"{len(missing)} reference(s) point at a file that isn't in the folder.",
                fix=(
                    "Check the spelling, or copy the missing file in. If a build step "
                    "generates it, run the build first.\n" + _listing(missing)
                ),
                location=missing[0].split("<-")[-1].strip(),
            ))

        if escapes:
            self.findings.append(Finding(
                "warn", "static.path.escapes-root",
                f"{len(escapes)} reference(s) resolve outside {self.dir} and won't be uploaded.",
                fix="Move those files inside the publish folder.\n" + _listing(escapes),
                location=escapes[0].split("<-")[-1].strip(),
            ))

        if root_relative:
            self.findings.append(Finding(
                "warn", "static.path.root-relative",
                f"{len(root_relative)} reference(s) start with `/`. On a GitHub Pages "
                "project site the page lives at username.github.io/repo/, so `/style.css` "
                "resolves to username.github.io/style.css and 404s.",
                fix=(
                    "Use relative paths (style.css, ./images/x.png), or publish as a user "
                    "site (username.github.io) where `/` is the site root.\n"
                    + _listing(root_relative)
                ),
                location=root_relative[0].split("<-")[-1].strip(),
            ))

    def check_env_files(self) -> None:
        for f in self.files:
            name = f.name
            if not name.startswith(".env") or name in ENV_ALLOWLIST:
                continue
            rel = f.relative_to(self.dir).as_posix()
            self.findings.append(Finding(
                "critical", "static.env-file.in-publish-dir",
                f"{rel} is inside the folder being uploaded — it will be downloadable "
                f"at /{rel} the moment the site is live.",
                fix=(
                    "Move it out of the publish folder, then rotate every value in it. "
                    "A static host serves whatever you hand it, with no way to hide a file."
                ),
                location=rel,
            ))

    def check_client_secrets(self) -> None:
        for f in self.files:
            if f.suffix.lower() not in SERVED_TEXT_EXTS or f.name in ENV_ALLOWLIST:
                continue
            try:
                content = f.read_text(errors="ignore")
            except (PermissionError, OSError):
                continue
            rel = f.relative_to(self.dir).as_posix()
            for pattern_name, pattern in SECRET_PATTERNS.items():
                if not re.search(pattern, content):
                    continue
                if pattern_name in CLIENT_PUBLIC_OK:
                    self.findings.append(Finding(
                        "warn", "static.secret.client-public-key",
                        f"{rel} contains a {pattern_name} value. Keys of this kind are "
                        "designed to be public — confirm this one is restricted.",
                        fix=(
                            "Stripe publishable keys are safe by design. Google API keys "
                            "must have an HTTP-referrer restriction set in Google Cloud "
                            "Console, or anyone can spend your quota."
                        ),
                        location=rel,
                    ))
                else:
                    self.findings.append(Finding(
                        "critical", "static.secret.client-exposed",
                        f"{rel} contains a {pattern_name} credential, and this file is "
                        "served to the public internet. A private repo does not help you here.",
                        fix=(
                            "Remove it from the file and rotate the credential now — assume "
                            "it is already compromised.\n"
                            "There is no way to keep a secret in a static site. A build-time "
                            "variable (VITE_*, PUBLIC_*, NEXT_PUBLIC_*) is inlined into the "
                            "bundle and is just as public.\n"
                            "If the page genuinely needs this key, it needs a server: run "
                            "/all-deploy and deploy it as an app instead."
                        ),
                        location=rel,
                    ))

    def check_sizes(self) -> None:
        total = 0
        count = 0
        oversized: List[str] = []
        for f in self.files:
            try:
                size = f.stat().st_size
            except OSError:
                continue
            total += size
            count += 1
            if size > LIMITS["file_warn_bytes"]:
                rel = f.relative_to(self.dir).as_posix()
                oversized.append(f"{rel}  ({size / 1024 / 1024:.1f} MB)")
        if oversized:
            self.findings.append(Finding(
                "warn", "static.asset.oversized",
                f"{len(oversized)} file(s) over {LIMITS['file_warn_bytes'] // 1024 // 1024} MB. "
                "Visitors on phone data will wait a long time.",
                fix=(
                    "Resize images to the size they're actually displayed at, and export "
                    "as WebP. Cloudflare Pages also rejects any single file over 25 MiB — "
                    "check your target's current limits.\n" + _listing(oversized)
                ),
            ))
        if total > LIMITS["total_warn_bytes"] or count > LIMITS["file_count_warn"]:
            self.findings.append(Finding(
                "warn", "static.size.total",
                f"Site is {total / 1024 / 1024:.0f} MB across {count} files.",
                fix=(
                    "GitHub Pages caps a published site around 1 GB and Cloudflare Pages "
                    "around 20,000 files per deployment. Check your target's current limits."
                ),
            ))

    def check_meta(self, entry: Optional[str]) -> None:
        if not entry:
            return
        meta = getattr(self, "entry_meta", {})
        missing = []
        if not meta.get("__title"):
            missing.append("<title>")
        if not meta.get("description"):
            missing.append('<meta name="description">')
        if not meta.get("viewport"):
            missing.append('<meta name="viewport">')
        if not meta.get("og:title"):
            missing.append('<meta property="og:title">')
        if not meta.get("og:image"):
            missing.append('<meta property="og:image">')
        if not meta.get("__lang"):
            missing.append("<html lang>")
        if not missing:
            return
        self.findings.append(Finding(
            "warn", "static.meta.incomplete",
            f"{entry} is missing {', '.join(missing)}. Without these the browser tab "
            "shows the filename, the page doesn't fit on a phone, and sharing the link "
            "on WhatsApp or Slack shows a blank card that reads as broken.",
            fix=(
                "Add to <head>:\n"
                '  <meta charset="utf-8">\n'
                '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
                "  <title>Your page name</title>\n"
                '  <meta name="description" content="One sentence about the page.">\n'
                '  <meta property="og:title" content="Your page name">\n'
                '  <meta property="og:description" content="One sentence about the page.">\n'
                '  <meta property="og:image" content="https://your-site/preview.png">\n'
                "And set the language on the html tag: <html lang=\"es\">"
            ),
            location=entry,
        ))

    def check_nojekyll(self) -> None:
        if self.target != "github-pages":
            return
        if ".nojekyll" in self.exact:
            return
        underscored = sorted(
            p for p in self.exact
            if p.startswith("_") and (self.dir / p).is_dir()
        )
        if not underscored:
            return
        self.findings.append(Finding(
            "critical", "static.nojekyll.missing",
            f"GitHub Pages runs Jekyll, which skips folders starting with an underscore "
            f"({', '.join(underscored[:3])}). Your CSS and JavaScript will silently 404 "
            "and the page will render as unstyled text.",
            fix=f"Add an empty file at the publish root:\n  touch {self.dir}/.nojekyll",
        ))


def _listing(items: List[str]) -> str:
    shown = items[:MAX_LISTED]
    out = "\n".join(f"  {item}" for item in shown)
    if len(items) > MAX_LISTED:
        out += f"\n  ...and {len(items) - MAX_LISTED} more"
    return out


def emit(findings: List[Finding], as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
        return
    if not findings:
        print("Static checks clean — no findings.")
        return
    for severity, header in (("critical", "critical issue(s)"), ("warn", "warning(s)")):
        group = [f for f in findings if f.severity == severity]
        if not group:
            continue
        print(f"\n{len(group)} {header}:\n")
        for f in group:
            print(f"  [{f.check}] {f.message}")
            if f.location:
                print(f"      at:  {f.location}")
            if f.fix:
                for line in f.fix.splitlines():
                    print(f"      fix: {line}")
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="all-deploy static-site checks")
    parser.add_argument("publish_dir", help="Folder that gets uploaded")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--target", default="generic", help="Target host name")
    parser.add_argument("--scoped", action="store_true", help="Fast subset")
    args = parser.parse_args()

    checker = StaticChecker(Path(args.publish_dir), target=args.target, scoped=args.scoped)
    checker.run()
    emit(checker.findings, as_json=args.json)
    sys.exit(1 if any(f.severity == "critical" for f in checker.findings) else 0)


if __name__ == "__main__":
    main()
