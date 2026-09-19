# Project class: static site

A website, not a service. No server process, no port, no dependency tree at runtime — a folder of files a host copies onto a CDN. Read this in Phase 0.0 when the project classifies as `static`.

This class exists because the app pipeline actively rejected these projects. A plain folder of HTML with no git repo used to fail the audit on `gitignore.missing` and `git.dirty` — two criticals, neither of them real.

## Detecting the class

`PROJECT_CLASS: static` when there is an HTML file (at the root, or in `dist/`, `_site/`, `public/`, `build/`, `out/`, `site/`) **and** none of: `package.json`, `pyproject.toml`, `requirements.txt`, `Pipfile`, `Dockerfile`, `docker-compose.yml`, `Procfile`, `go.mod`, `Gemfile`.

The manifest test is what keeps a Vite, Next or Astro repo — which also has an `index.html` — on the app pipeline. Those are `static-build`: they classify as `app` by default, and only move to the static profile when the user explicitly passes a publish directory.

`scripts/audit.py` implements the same rule in `detect_profile()`, so the skill and the script never disagree.

## The publish directory

The single most consequential field, and the one people get wrong when filling in a host's dashboard. It is **the folder that contains `index.html`**, not the project root.

| Project | Build command | Publish directory |
|---|---|---|
| Plain HTML/CSS/JS | *(none — leave blank)* | `.` |
| Astro | `npm run build` | `dist/` |
| Vite (no SSR) | `npm run build` | `dist/` |
| Hugo | `hugo` | `public/` |
| Jekyll | `jekyll build` | `_site/` |
| Eleventy | `npx @11ty/eleventy` | `_site/` |
| MkDocs | `mkdocs build` | `site/` |
| Docusaurus | `npm run build` | `build/` |
| Next.js with `output: 'export'` | `npm run build` | `out/` |

For a plain HTML site the build command is **empty**. People fill in `npm run build` out of habit and the deploy fails on a project that has nothing to build.

Pass it through explicitly:

```bash
python3 <SKILL_DIR>/scripts/audit.py <project> --profile static --publish-dir <dir> [--target <name>]
```

## Phase adjustments

### Phase 0 — prerequisites

| Prerequisite | App | Static |
|---|---|---|
| Git repo | Required | **Not required.** Say so and continue. Never run `git init` unprompted |
| Git remote | Required (except docker-vps) | **Only for GitHub Pages and Render.** Re-evaluate after Phase 3 |
| Node/Python boundary | Exits on other languages | **Not applicable.** HTML/CSS/JS is always in scope |

That third row is the one sentence that used to tell someone with a folder of HTML to go away.

### Phase 3.2 — the git decision (static only, when there is no repo)

Ask once, with the consequence attached, because it decides which targets are even available:

> *"Do you want to be able to update the page later by pushing a change — or is this a one-time thing?"*

**Wants to update by pushing** → they need a repo. Show the commands and **confirm before creating anything on their GitHub account**:

```bash
git init -b main
git add -A && git commit -m "Initial site"
gh repo create <NAME> --public --source=. --push
```

If `gh` is not authenticated, hand over `! gh auth login` and wait. Never authenticate on their behalf (Hard Rule 4). If they have no GitHub account and don't want one, that's a valid answer — route to direct upload.

**One-time, or no git** → route to a target that uploads a folder: Cloudflare Pages direct upload, or Netlify Drop. Tell them plainly that updating later means uploading the folder again. Don't discover that for them after launch.

### Phase 4 — env delivery is skipped, and say why

**Never offer to "put it in an environment variable so it stays secret."** On a static site that sentence is false, and it is the most damaging thing the skill could say to someone who doesn't know better.

Everything in the publish directory is served to anyone who asks for it. A build-time variable (`VITE_*`, `PUBLIC_*`, `NEXT_PUBLIC_*`) is **inlined into the JavaScript bundle at build time** — it is not read at runtime from anywhere, it is baked into a file that ships. A private repo does not help: the repo is not what's being served.

Two legitimate cases:

- **A publishable key by design** — Stripe `pk_`, a Google Maps key with an HTTP-referrer restriction. Ship it in the file, and say clearly that it is public and what protects it (for Maps: the referrer restriction, which must actually be set in Google Cloud Console).
- **A public build-time value** — an analytics ID, a public API base URL. Same thing: it ends up readable, and that's fine.

Anything else needs a server. Say that and stop: *"this can't be a static page — it needs a backend"*, then continue with the normal app pipeline.

### Phase 4.5 — health check

The usual `curl` on `/`, **plus a probe of the first stylesheet the entry page references**. A 200 on `/` with a 404 on `/estilo.css` is exactly what a filename-capitalisation bug looks like in production, and the root probe alone reports that deploy as green.

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL/<first-stylesheet-href>"
```

### Phase 5 — where preview → prod doesn't exist

| Target | Preview → prod |
|---|---|
| Cloudflare Pages | `--branch=<name>` → preview; production branch → prod. Holds |
| Netlify | `netlify deploy` → draft; `--prod` → prod. Holds |
| Vercel | Holds — **except the first deploy of a new project, which is always production** even without `--prod` |
| GitHub Pages | One branch = one site. **No preview exists** |
| Direct upload / Drop | The upload *is* prod |

For the last two, satisfy the gate by serving the **exact publish directory** locally and health-checking that. No install, ships with Python, Hard Rule 4 intact:

```bash
python3 -m http.server -d <PUBLISH_DIR> 8000
curl -sSL -o /dev/null -w "%{http_code}" http://localhost:8000
```

Serve the publish directory, not the project root — serving the root hides exactly the "wrong folder" bug this is meant to catch. Then publish once, behind the normal confirmation.

### Phase 6 — handover

Rollback matters less here than "how do I change it later", which is what this audience will actually ask. Cover both:

- **Cloudflare Pages / Netlify** — roll back to a previous deployment from the dashboard, instantly.
- **GitHub Pages** — `git revert <sha> && git push`.
- **Direct upload / Drop** — the only rollback is re-uploading the previous folder, so **tell them to keep a copy before publishing.**

## The static checks

Run by `scripts/static_check.py`, invoked by `audit.py` in the static profile. Full list:

| id | Severity | Fires when |
|---|---|---|
| `static.publish-dir.missing` | critical | The publish folder doesn't exist — usually a build that hasn't been run |
| `static.entry.missing` | critical | No `index.html` at the publish root |
| `static.asset.case-mismatch` | critical | A reference misses exactly but hits case-insensitively |
| `static.path.absolute-local` | critical | `file://`, `C:\`, or `/Users/…` in a `src`/`href` |
| `static.secret.client-exposed` | critical | A secret-by-definition credential in a served file |
| `static.env-file.in-publish-dir` | critical | A real `.env*` inside the folder being uploaded |
| `static.nojekyll.missing` | critical | `--target github-pages` and a top-level `_directory/` with no `.nojekyll` |
| `static.asset.missing` | warn | A reference resolves to nothing |
| `static.path.escapes-root` | warn | A reference resolves outside the publish folder |
| `static.path.root-relative` | warn | `--target github-pages` and a `/foo` reference |
| `static.secret.client-public-key` | warn | A publishable key (`pk_live_`, Google API, JWT) in a served file |
| `static.asset.oversized` | warn | A single file over 10 MB |
| `static.size.total` | warn | The site is near 1 GB or 20,000 files |
| `static.meta.incomplete` | warn | The entry page is missing title / description / viewport / OG tags / `lang` |

### Why `static.asset.case-mismatch` is the important one

macOS and Windows filesystems are case-insensitive. `<img src="imagenes/foto.png">` loads perfectly on the author's machine when the file is actually `Imagenes/Foto.PNG`. Every free static host serves from Linux, where it is a 404. The page goes live, the images are broken, and nothing in the build log mentions it.

This is why the check does **not** use `Path.exists()` — on macOS that returns `True` for the wrong spelling, so the check would silently never fire for exactly the people who need it. References are resolved against a case-folded index of the real on-disk names instead.

**Fixing it:** prefer editing the reference to match the file on disk. A rename is the fallback, and on a case-insensitive filesystem it needs two steps — a one-step case-only rename is a no-op, and `git mv Logo.png logo.png` fails with "destination exists":

```bash
mv assets/Logo.png assets/Logo.png.tmp && mv assets/Logo.png.tmp assets/logo.png
```

A rename is a change to the user's files. Show the full list of commands and get approval before running any of them (Hard Rule 6).

### Why publishable keys only warn

`pk_live_` is *designed* to sit in client JavaScript. So is a referrer-restricted Google Maps key. Blocking those as criticals would stop a correctly-built site and teach the user that the audit cries wolf — which costs more than the warning saves. They warn, with a note on what actually protects them.

## What a static site can't do, and the real alternative

Worth saying before launch rather than after:

| They want | Static answer |
|---|---|
| A contact form | Netlify Forms (free), Formspree, or a Google Form embed |
| To take payments | A Stripe Payment Link or a Gumroad/Lemon Squeezy button — a hosted checkout, not code on the page |
| To store what visitors type | A form service, or a hosted backend — at which point it isn't static |
| To send email | A form service's notification, never from the page |
| Anything behind a login | Not a static site. Run `/all-deploy` and deploy it as an app |
