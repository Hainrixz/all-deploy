# Project-type fingerprints

Map project files and markers to framework classification and a ranked target list. Read this in Phase 1 (Detect).

## Fingerprint table

| Signal files / markers | Framework | Primary target | Fallback | Notes |
|---|---|---|---|---|
| `next.config.js` / `next.config.mjs` / `next.config.ts` | Next.js | Vercel | Railway (for custom servers) | Preview URLs are native to Vercel. If `server.js` custom server → Railway. |
| `app/` dir + `package.json` with `next` dep | Next.js (App Router) | Vercel | Railway | |
| `pages/` dir + `package.json` with `next` dep | Next.js (Pages Router) | Vercel | Railway | |
| `vite.config.js` / `vite.config.ts` | Vite (SPA) | Vercel | cloudflared (dev) | Build outputs to `dist/`. |
| `astro.config.mjs` / `astro.config.ts` | Astro | Vercel | Cloudflare Pages | SSR via Vercel adapter. Static output (`dist/`) deploys anywhere. |
| `remix.config.js` + `@remix-run/*` | Remix | Vercel | Railway | |
| `nuxt.config.ts` | Nuxt | Vercel | Railway | |
| `svelte.config.js` + `@sveltejs/kit` | SvelteKit | Vercel | Railway | |
| `package.json` with `"fastify"` / `"express"` / `"koa"` / `"hono"` / `"@nestjs/core"` dep | Node HTTP API | Railway | Docker+SSH | |
| `main.py` with `FastAPI()` or `from fastapi import` | FastAPI | Railway | Docker+SSH | Needs `uvicorn main:app --host 0.0.0.0 --port $PORT`. |
| `main.py` with `Flask()` or `app.py` with `from flask` | Flask | Railway | Docker+SSH | Needs `gunicorn app:app` or equivalent. |
| `Procfile` | Heroku-style | Railway (native) | Docker+SSH | Railway reads Procfile. |
| `Dockerfile` (no framework marker) | Containerized service | Docker+SSH | Railway | Railway builds from Dockerfile too. |
| `docker-compose.yml` (multi-service) | Compose stack | Docker+SSH | — | Railway does not deploy compose files directly. |
| `mcp.json` or package `mcp`-related deps | MCP server | see `agents.md` | — | stdio vs HTTP mode — see agents reference. |
| `claude-agent-sdk` or `@anthropic-ai/sdk` usage + long loop | Agent loop | Railway (worker) | Docker+SSH | See `agents.md`. |
| `index.html` at root, no manifest of any kind | **Static, plain** | Cloudflare Pages | Netlify | Publish dir `.`, build command **empty**. No git repo needed — see `static-sites.md` |
| HTML file at root named something else (`inicio.html`, `home.html`) | **Static, plain** | Cloudflare Pages | Netlify | Still a website. The audit flags the name: hosts serve `index.html` exactly, so `/` 404s |
| `config.toml` / `hugo.toml` + `content/` | Static, build (Hugo) | Cloudflare Pages | Netlify | Build `hugo`, publish `public/` |
| `_config.yml` + `_posts/` | Static, build (Jekyll) | GitHub Pages | Cloudflare Pages | Build `jekyll build`, publish `_site/`. GitHub Pages builds Jekyll natively |
| `.eleventy.js` / `eleventy.config.js` | Static, build (Eleventy) | Cloudflare Pages | Netlify | Build `npx @11ty/eleventy`, publish `_site/` |
| `mkdocs.yml` | Static, build (MkDocs) | Cloudflare Pages | GitHub Pages | Build `mkdocs build`, publish `site/` |
| `docusaurus.config.js` | Static, build (Docusaurus) | Cloudflare Pages | Netlify | Build `npm run build`, publish `build/` |
| `next.config.*` with `output: 'export'` | Static, build (Next export) | Cloudflare Pages | Vercel | Publish `out/`. No SSR — it's a folder of files |
| `pyproject.toml` with `[project.scripts]`/`console_scripts` AND no HTTP framework import (`fastapi`, `flask`, `uvicorn`, `gunicorn`) | Python library / CLI | **exit** | — | Not a web deploy — direct user to PyPI publish. Do **not** use `[build-system]` as a signal; it's required by PEP 517 for nearly every Python project including web apps. |
| `package.json` with `bin:` present OR (`files:` array + no `scripts.start` + no HTTP framework import like `express`/`fastify`/`next`/`hono`) | Node library / CLI | **exit** | — | Not a web deploy — direct user to npm publish. Do **not** use `main:` alone; almost every Node web app sets `main:` too. |

## Monorepo signals

If any of these exist, enumerate packages and **ask which one to deploy**:
- `pnpm-workspace.yaml`
- `turbo.json`
- `nx.json`
- `lerna.json`
- `rush.json`
- `"workspaces"` field in root `package.json`

Common layouts:
- `apps/<name>` + `packages/<name>` → deploy from `apps/<name>`.
- `packages/*` only (workspaces) → library-shaped; usually exit unless one package has a server entry.

Ask: *"This is a monorepo. Which package do you want to deploy? I see: `<list>`."*

## Runtime version detection

Check in this order; use the first hit:

### Node
1. `.nvmrc`
2. `.node-version`
3. `engines.node` in `package.json`
4. (nothing pinned) — warn in audit, recommend adding `.nvmrc`.

### Python
1. `.python-version`
2. `requires-python` in `pyproject.toml`
3. `python_version` in `Pipfile`
4. (nothing pinned) — warn in audit, recommend adding `.python-version`.

## Package manager detection

### Node
- `pnpm-lock.yaml` → pnpm
- `yarn.lock` → yarn
- `bun.lockb` → bun
- `package-lock.json` → npm
- (multiple lockfiles) — warn; ask which to use.

### Python
- `uv.lock` → uv (`uv sync`)
- `poetry.lock` → poetry (`poetry install`)
- `Pipfile.lock` → pipenv (`pipenv install`)
- `requirements.txt` → pip (`pip install -r requirements.txt`)
- `pyproject.toml` only → default to `uv pip install -e .` or similar.

## Existing deploy-config detection

If any of these files exist, **respect them, audit them, do not regenerate** unless the user explicitly asks:
- `vercel.json`
- `railway.toml`
- `fly.toml`
- `Dockerfile`
- `docker-compose.yml`
- `render.yaml`
- `.buildpacks`
- `heroku.yml`

## Existing-project linkage

If present, **reuse** the linked project instead of creating a new one:
- `.vercel/project.json` → Vercel project ID + org ID.
- `railway.toml` with a `project` field → Railway project.
- `.fly/` or `fly.toml` with `app =` → Fly app.

Creating a fresh project when one is already linked duplicates infrastructure and breaks env vars / domain wiring. Require an explicit "start fresh" from the user.

## Target ranking (quick reference)

| Has | Top candidate | Second |
|---|---|---|
| Static site, **and anyone is being paid** for it | Cloudflare Pages | Netlify |
| Static site needing a contact form, no backend | Netlify | Cloudflare Pages + Formspree |
| Static site, personal, already on GitHub | GitHub Pages | Cloudflare Pages |
| Static site, one-time, no git repo | Netlify Drop | Cloudflare Pages (direct upload) |
| `next.config.*` / `vite.config.*` / `astro.config.*`, personal project | Vercel | Cloudflare Pages |
| FastAPI / Flask / Express (long-running) | Railway | Docker+SSH |
| `Dockerfile` + `docker-compose.yml` | Docker+SSH | Railway (if single service) |
| MCP server | see `agents.md` | — |
| Claude Agent SDK script | Railway (worker) | Docker+SSH |
| Local dev, wants quick public URL | cloudflared tunnel | — |

If two targets tie, present both with a one-line rationale and let the user pick.

**For any static row, read `references/static-hosting.md` before ranking.** The deciding question is *"is anyone being paid in connection with this page?"* — a yes removes Vercel Hobby, whose Fair Use terms count *"receiving payment to create, update, or host the site"* as commercial usage, and usually GitHub Pages too. That single question reorders the list more than any technical signal does.
