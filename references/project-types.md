# Project-type fingerprints

Map project files and markers to framework classification and a ranked target list. Read this in Phase 1 (Detect).

## Fingerprint table

| Signal files / markers | Framework | Primary target | Fallback | Notes |
|---|---|---|---|---|
| `next.config.js` / `next.config.mjs` / `next.config.ts` | Next.js | Vercel | Railway (for custom servers) | Preview URLs are native to Vercel. If `server.js` custom server → Railway. |
| `app/` dir + `package.json` with `next` dep | Next.js (App Router) | Vercel | Railway | |
| `pages/` dir + `package.json` with `next` dep | Next.js (Pages Router) | Vercel | Railway | |
| `vite.config.js` / `vite.config.ts` | Vite (SPA) | Vercel | cloudflared (dev) | Build outputs to `dist/`. |
| `astro.config.mjs` / `astro.config.ts` | Astro | Vercel | — | Supports SSR via Vercel adapter. |
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
| Static `index.html` at root, no framework | Static site | Vercel | cloudflared | |
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
| `next.config.*` / `vite.config.*` / `astro.config.*` / static | Vercel | — |
| FastAPI / Flask / Express (long-running) | Railway | Docker+SSH |
| `Dockerfile` + `docker-compose.yml` | Docker+SSH | Railway (if single service) |
| MCP server | see `agents.md` | — |
| Claude Agent SDK script | Railway (worker) | Docker+SSH |
| Local dev, wants quick public URL | cloudflared tunnel | — |

If two targets tie, present both with a one-line rationale and let the user pick.
