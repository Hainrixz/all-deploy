---
name: all-deploy
description: >
  Deploys any web app, API, or agent to the internet with a strict pre-deploy
  audit and a preview → health-check → prod flow. Detects Next, Vite, Astro,
  Remix, Nuxt, SvelteKit, FastAPI, Flask, Express, MCP server, Claude Agent
  SDK script, Python worker, Dockerized, and static projects; routes to
  Vercel, Railway, Docker+SSH VPS, or cloudflared tunnel. Also supports a
  first-class "run locally" mode. At the start of each cloud deploy the skill
  asks the user whether to run full-auto (audit → preview → prod in one
  sequence) or step-by-step (confirm each phase); the user can skip that
  question by saying "auto" or "step by step" up front. Use when the user
  says "/all-deploy", "/deploy", "/despliega", "deploy this", "ship this",
  "push to prod", "get this online", "deploy my agent", "deploy my FastAPI",
  "run it locally", "corre esto localmente", "deploy auto", "deploy step by
  step", "paso a paso", "how do I put this on the internet", or otherwise
  asks to publish a project to a URL or run it locally.
---

# all-deploy

Detects, audits, and deploys projects to the right host with a confirmed preview → prod flow. The unique value is **detect → audit → route to the right CLI**, not wrapping the CLI.

## Configuration (edit these lines to change default behavior)

```
CONFIRMATION_MODE: ask_at_start
  # ask_at_start (default): the skill asks at the start of each cloud deploy
  #                         whether to run full-auto or step-by-step.
  # full_auto:              skip the question. Audit → preview → prod with a
  #                         5-second ESC window before prod.
  # always_ask:             skip the question. Require explicit "yes" before prod.
VISUAL_VERIFY: false           # true → screenshot preview via chrome-bridge-automation (frontend only)
ALLOW_DIRTY_TREE: false        # true → skip the "HEAD is clean" audit check
```

The default `ask_at_start` works for both solo authors and community users — the mode choice moves to runtime. Pinning to `full_auto` or `always_ask` is only useful when wrapping the skill in automation that can't answer the question interactively.

## Hard Rules (never violate — these are the safety contract)

1. **Never bypass or soften the audit.** The audit is the only gate between the user's intent and live infra in `full_auto` mode. If a check cannot run, that itself is a block, not a reason to skip.
2. **Never deploy to prod before a successful preview with a 2xx/3xx health check.** Preview → summary → prod. No prod without a green preview in the same session.
3. **Never commit, print, or log secrets.** If a secret is found in tracked files, halt and guide removal + history rewrite as a separate user-approved step. Secret values never appear in summaries, logs, or commit messages.
4. **Never auto-install or auto-authenticate third-party CLIs.** Hand the user the command with the `!` prefix (e.g., `! vercel login`, `! railway login`).
5. **Never wrap a target CLI in a custom script that hides flags.** Reference files document real commands the user can read and verify.
6. **Never modify code to make audit pass without showing the diff first.** `.gitignore`, `.env.example`, Dockerfile scaffolding, port-binding fixes — all shown and approved before applying.
7. **Never deploy from a dirty working tree** unless `ALLOW_DIRTY_TREE: true` is set. Uncommitted changes complicate rollback.
8. **Respect "wait."** Between preview and prod, any user utterance resembling hesitation (wait/hold/stop/not yet/abort) aborts the prod step cleanly.

## Two Modes

Decide up front from the user's phrasing:

- **Cloud deploy** (default) — Phases 0 through 6 below. Triggers: "deploy", "ship", "push to prod", "get it online", "/all-deploy".
- **Run locally** — Phases 0, 1, 2, then a local-run step. Triggers: "run it locally", "corre esto localmente", "/all-deploy local", "just run it", or `--local`.

In **run locally** mode, run a **scoped audit** — only secrets-in-tracked-files, start-command-exists, and sane port binding. Skip: git-remote, clean HEAD, `npm audit`/`pip-audit`, `.env.example` completeness, and env-var delivery (no remote to deliver to). Then execute the detected start command (`npm run dev` / `uvicorn main:app --reload --host 0.0.0.0 --port $PORT` / `docker compose up` etc.) in the foreground, streaming output via `Monitor`. If the user asks to also expose the local server, chain into `references/targets/cloudflared-tunnel.md`. Everything else in this file concerns cloud deploy.

## Cloud Deploy Workflow

### Mode selection (runs before Phase 0 in `ask_at_start` mode)

Resolve the effective `CONFIRMATION_MODE` for this run:

1. **If the user's invocation contains an explicit mode marker**, adopt it and skip the question:
   - `full_auto` triggers: "auto", "full auto", "auto deploy", "deploy auto", "/all-deploy auto", "yolo".
   - `always_ask` triggers: "step", "step by step", "one at a time", "confirm each step", "paso a paso", "/all-deploy step".
2. **Else if `CONFIRMATION_MODE` is pinned to `full_auto` or `always_ask`** in the config block above, use that and skip the question.
3. **Otherwise (`ask_at_start`, default)**, ask the user once, before Phase 0 runs:

   > *"Before we start — how should I run the deploy?*
   >
   > *1. Full auto — I run audit → preview → prod promotion in sequence. Prod fires after a 5-second ESC window.*
   > *2. Step by step — I stop for your OK between audit, preview, and prod.*
   >
   > *Reply 'auto' or 'step'."*

The chosen mode scopes to this run only — a future invocation asks again (unless the user explicitly opts in via trigger phrase or the config block is pinned).

"Wait" / "stop" / "hold" at any point still aborts the prod step in both modes (Hard Rule 8). The difference is whether you get a 5-second ESC window (full_auto) or an explicit "yes"-required pause (always_ask) before the prod command runs.

### Phase 0 — Prerequisites (target-independent)

Check in order. Each failure halts with a `!` command for the user.

1. **Git repo.** Run `git rev-parse --is-inside-work-tree`. If not a repo, halt unless mode is `run locally` (which doesn't require git).
2. **Git remote** (cloud deploy only). Run `git remote -v`. If no remote is configured, halt *unless* the target will be `docker-vps` (deployable without a remote). This second clause is re-evaluated after Phase 3.
3. **Language boundary.** v1 fingerprints Node and Python. If the primary language is Go, Rust, Ruby, Elixir, Bun, or Deno, exit with: *"v1 detects Node/Python ecosystems only. Run the target CLI directly (`vercel`, `railway`, `flyctl`, `docker`). Support for this language is planned in v2."*

Target-CLI authentication is checked in **Phase 3.5** (below), after the target is chosen.

### Phase 0.5 — Permission-prompt seeding (first run only)

Tell the user: *"Run the `fewer-permission-prompts` skill once on this project to seed `.claude/settings.json` with a deploy allowlist — otherwise every step will prompt."* Pointer only. Never edit the user's settings here.

### Phase 1 — Detect

Read `references/project-types.md` (skill-relative path — Claude resolves it against the installed skill directory) for the full fingerprint table. Inspect:

- **Package managers & manifests:** `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `bun.lockb`, `pyproject.toml`, `requirements.txt`, `poetry.lock`, `uv.lock`, `Pipfile`.
- **Framework signals:** `next.config.*`, `vite.config.*`, `astro.config.*`, `remix.config.*`, `nuxt.config.*`, `svelte.config.*`, `app/` vs `pages/`, `main.py` with `FastAPI()`, `Flask()`, `app = FastAPI()`, `server.py`, `index.html` at root.
- **Runtime version:** `.nvmrc`, `.node-version`, `engines` in `package.json`, `.python-version`, `python_version` in `pyproject.toml`. If a long-running target is chosen and no runtime is pinned, audit blocks.
- **DB / stateful deps:** imports of `sqlalchemy`, `psycopg`, `prisma`, `mongoose`, `redis`, `ioredis`, `sqlmodel`. If found, surface *"this service needs a database — provision one before prod"* with the Railway add-on command from the Railway reference.
- **Port + start command:** `uvicorn`, `gunicorn`, `next start`, `node server.js`, `python -m ...`. Check for `0.0.0.0` binding and `$PORT` usage. Localhost-only binding blocks for long-running targets.
- **Monorepo:** `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, or `"workspaces"` in root `package.json` → enumerate packages and **ask which one to deploy**. Do not guess.
- **Library / CLI (not a web deploy):** Node signal — `bin:` field present in `package.json` OR (`files:` array present AND no `scripts.start` AND no HTTP framework imports like `express`, `fastify`, `hono`, `next`, `koa`). Python signal — `[project.scripts]` / `console_scripts` in `pyproject.toml` AND no `uvicorn`/`gunicorn`/`flask`/`fastapi` in declared scripts or imports. **Do not use `main:` alone as a library signal** — almost every Node web app also sets `main:`. Exit cleanly: *"This looks like a package — `/all-deploy` targets web services, not npm/PyPI publishes."*
- **Existing deploy config:** `vercel.json`, `railway.toml`, `fly.toml`, `Dockerfile`, `render.yaml` — respect, audit, do not regenerate without explicit ask.
- **Existing project linkage:** `.vercel/project.json` → reuse that Vercel project ID. `railway.toml` with `project` field → reuse. Re-deploy is the common case; fresh projects require an explicit "start fresh."

Output: a classification block and a ranked list of candidate targets with one-line rationale each. See `references/project-types.md` for the full target-ranking rubric.

### Phase 2 — Audit (strict, blocking)

Run the audit script bundled with this skill (`scripts/audit.py`) against the current project directory. Claude resolves the skill path at load time — the invocation looks like:

```
python3 <SKILL_DIR>/scripts/audit.py <project-path>
```

Where `<SKILL_DIR>` is wherever the skill is installed (typically `~/.claude/skills/all-deploy/`) and `<project-path>` is usually `.`. The script checks every item in `references/audit-checklist.md`: secrets in tracked files, `.gitignore` coverage, lockfile sanity, `.env.example` completeness (via `scripts/env_extract.py`), build/start script existence, port binding, clean HEAD, git-remote match, `npm audit --production --audit-level=high` or `pip-audit`.

Any failure halts. For each issue, show the fix as a diff (if applicable) and wait for the user's OK before applying. Auto-mode does not bypass audit.

**Git-history secret scan** is user-run, not automatic. In the audit output, surface: `trufflehog git file://.` or `git log -p -S 'sk_' -S 'AKIA' -S 'ghp_'` as a separate step. The skill never rewrites git history.

### Phase 3 — Target selection

Present the ranked candidates from Phase 1 with one-line rationales. User picks or accepts the top pick with "ok". Only now load the target reference:

- `references/targets/vercel.md` — Next, Vite, Astro, Remix, Nuxt, SvelteKit, static
- `references/targets/railway.md` — FastAPI, Flask, Express, Python workers, MCP HTTP, Claude Agent SDK
- `references/targets/docker-vps.md` — any Dockerfile, stateful workloads, self-hosted
- `references/targets/cloudflared-tunnel.md` — expose local dev, quick demo

For agent-shaped projects, also load `references/agents.md` for per-agent-type adjustments (FastAPI/Flask HTTP, MCP stdio vs HTTP, Claude Agent SDK script, generic Python worker).

### Phase 3.5 — Target CLI installed + authenticated

With the target chosen, verify its CLI is installed and authenticated. Do not auto-install or auto-login — hand the user the command with a `!` prefix.

- **Vercel:** `vercel whoami` (install: `npm i -g vercel`; login: `! vercel login`).
- **Railway:** `railway whoami` (install: `npm i -g @railway/cli` or `brew install railway`; login: `! railway login`).
- **Docker + SSH:** `ssh -o BatchMode=yes <host> true` (requires pre-configured SSH key); `docker --version` locally.
- **cloudflared:** `cloudflared tunnel list` (install: `brew install cloudflared`; login: `! cloudflared tunnel login`).

If the check fails, stop and surface the install/login command. Resume from Phase 3.5 after the user reports done.

### Phase 4 — Execute (preview first, always) + env-var delivery

Follow the target reference's preview playbook. First pass is always preview/staging — never `--prod` on this phase.

**Long-running command handling.** Deploy commands take 3–10 min; the default 2-min Bash timeout will kill them.

- **Default:** run the deploy command via the Bash tool with `run_in_background: true`. You'll receive a completion notification when the CLI exits; `Read` the Bash output file at that point to parse the URL and detect errors. Do not chain `sleep` loops.
- **When you need an early line** (e.g., Railway prints the preview URL mid-run, cloudflared prints the tunnel URL before settling): use the `Monitor` tool against the same output file with a regex that matches the URL pattern plus known error signatures (`Traceback`, `FAILED`, `error:`). Monitor emits each match as a notification; the first URL match is what Phase 4.5 probes.

**Env-var delivery** (before preview runs). Source of truth is the user's local `.env` (never committed). Push required keys to the target:

- **Vercel:** `vercel env add <KEY> preview` then `vercel env add <KEY> production` (paste the value, or pipe it in — `echo -n "$value" | vercel env add <KEY> <env>`). Verify with `vercel env ls`.
- **Railway:** `railway variables --set "KEY=value"` — one call per key. There's no bulk-import flag; loop in shell over your local `.env` (see `references/targets/railway.md`).
- **Docker+SSH:** `scp .env.production user@host:/app/.env` or the `environment:` block in `docker-compose.yml`.
- **cloudflared:** inherits local environment; no remote vars needed.

Never print values. Confirm keys only.

### Phase 4.5 — Preview health check (BLOCKING)

**Capture the preview URL** from the deploy CLI's stdout. Each target reference documents the exact parsing step; examples:
- **Vercel:** the preview URL is printed on the last non-empty stdout line, formatted like `https://<project>-<hash>-<scope>.vercel.app`.
- **Railway:** look for `Deployment live at <url>` in the `railway up` output.
- **Docker+SSH:** the URL is the user-configured `http://<host>[:port]` — the skill must ask or derive from `docker-compose.yml` port mappings.
- **cloudflared:** the URL is printed as `https://<random>.trycloudflare.com` or the configured hostname.

Assign the captured URL to `$PREVIEW_URL`, then probe:

```
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
```

(No `-f` — that would suppress the `%{http_code}` output on HTTP errors. `-sSL` keeps curl silent on success but still surfaces transport errors and follows redirects.)

A **2xx or 3xx** status promotes to Phase 5. **4xx/5xx**, empty output (connection refused, DNS failure), or a curl non-zero exit → stop. Report the failing endpoint with the target's log command (`vercel logs`, `railway logs`, `ssh ... 'docker compose logs'`). Do not promote.

**Optional visual verify.** If `VISUAL_VERIFY: true` and the project is a frontend, use `chrome-bridge-automation` to screenshot the preview and confirm the page renders (not blank, not error page). Curl 2xx/3xx is still the gate; screenshot is a bonus.

### Phase 5 — Prod promotion

In `full_auto` mode, after audit + preview health both pass:

1. Print a one-screen summary block: target URL, exact command about to run, DNS impact if any, cost implication. For pricing, prefer a live `deep-research` lookup of current Vercel/Railway pricing. If unavailable, link the provider's pricing page. Do not hardcode plan prices in this file.
2. Print: *"Prod promotion in 5 seconds — press ESC to interrupt."* Then issue a real `sleep 5` via the Bash tool as its own call. This is not theater — ESC during that sleep actually stops the turn. If the user does interrupt, do not issue the prod command on resume; ask what they want to do instead.
3. After the sleep returns cleanly, issue the prod command as a separate Bash call with `run_in_background: true`. Wait for the completion notification, then `Read` the Bash output file to extract the production URL. Use `Monitor` on the same output file only if you need to parse the URL before the CLI exits (Railway, cloudflared).

In `always_ask` mode, skip steps 2–3 and require an explicit "yes" in-turn before running the prod command. No sleep.

**Respect interruption after preview.** If between preview and prod the user types anything resembling hesitation (wait/hold/stop/not yet/abort), do not proceed to prod — treat the preview as the last green state and wait for explicit direction.

### Phase 6 — Post-deploy verify + rollback surfacing

- Curl the production URL; confirm status.
- Confirm env vars are set on the remote (`vercel env ls`, `railway variables`, `ssh ... 'docker compose config'`).
- Print the rollback path for this target (the user copies if needed later):
  - Vercel: `vercel rollback` (interactive picker) or `vercel rollback <previous-deployment-url>` — verify current CLI syntax.
  - Railway: no first-class `rollback` command. Redeploy a prior commit: `git checkout <prev-sha> && railway up && git checkout -`, or use the dashboard's Deployments → "Redeploy" on a prior build.
  - Docker+SSH: `ssh <host> 'docker compose up -d --no-deps <service>'` after re-tagging the prior image, or re-rsync a prior SHA and rebuild. See `references/targets/docker-vps.md` for both flows.
- Print the log-tail command: `vercel logs <url> --follow`, `railway logs --follow`, `ssh <host> 'cd /app && docker compose logs -f'`.

## Target Selection — ranking rubric (quick reference)

| Project signals | Top candidate | Why |
|---|---|---|
| `next.config.*`, `vite.config.*`, `astro.config.*`, SPA, SSG | Vercel | Zero-config, preview URLs, edge network |
| FastAPI / Flask / Express with long-running server | Railway | Simple, fast deploy, DB add-ons available |
| Any `Dockerfile` present, DB/volumes needed, self-host preference | Docker + SSH VPS | Full control, stateful-friendly |
| Local dev running, wants a quick public URL | cloudflared tunnel | No host needed, instant |
| MCP server | Railway (HTTP mode) or Docker+SSH | See `references/agents.md` |
| Claude Agent SDK script | Railway (worker mode) or cron | See `references/agents.md` |

If signals conflict, present the top two with rationale and let the user pick.

## Bundled Resources

- `scripts/audit.py` — deterministic pre-deploy audit. Invoked in Phase 2.
- `scripts/env_extract.py` — scans source for env-var usage, used by audit to verify `.env.example` completeness.
- `references/project-types.md` — full framework fingerprint table.
- `references/audit-checklist.md` — every audit rule explained with fix guidance.
- `references/env-mapping.md` — how env vars move between local `.env` and each target.
- `references/agents.md` — four agent shapes with per-type deploy adjustments.
- `references/targets/*.md` — one playbook per target, loaded only after Phase 3.
- `assets/templates/` — Dockerfile.node, Dockerfile.python, docker-compose.example.yml, .env.example.template.

## Platform Notes

- **macOS + Linux only in v1.** Windows community users should use WSL2 for path and shell compatibility.
- All commands assume bash/zsh. Paths use POSIX conventions.
- Network required for all cloud modes; `run locally` mode works offline.
