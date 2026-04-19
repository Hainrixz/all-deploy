# all-deploy

A Claude Code skill that takes any web app, API, or agent and deploys it — with a strict pre-deploy audit and a preview → health-check → prod flow.

Built on the [Anthropic skill-creator spec](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md). Works with Claude Code, the Claude Agent SDK, and anywhere else that loads `.skill` files.

## What it does

One command (`/all-deploy`) walks your project through six phases:

1. **Detect** — fingerprints the framework (Next.js, Vite, Astro, Remix, Nuxt, SvelteKit, FastAPI, Flask, Express, MCP server, Claude Agent SDK script, Python worker, Dockerized, static).
2. **Audit (strict, blocking)** — scans for secrets in tracked files, missing `.gitignore` entries, missing lockfile, missing `.env.example` keys (including destructured access), missing start command, localhost-only port binding, dirty working tree, missing git remote, `npm audit` / `pip-audit` criticals, and runtime version pinning.
3. **Target selection** — ranks candidates (Vercel, Railway, Docker+SSH VPS, cloudflared tunnel), loads only the chosen target's playbook.
4. **Execute (preview first)** — delivers env vars to the target, runs the preview deploy, captures the preview URL.
5. **Health check + prod promotion** — `curl` gates prod on a 2xx/3xx preview; full-auto or step-by-step per your choice.
6. **Post-deploy** — confirms env, prints rollback + log-tail commands for the target.

A **run-locally** mode runs the same audit (scoped) and then starts the app on your machine, optionally chained to cloudflared for a temporary public URL.

## Install

### Option 1 — clone into your skills directory (easiest)

```bash
git clone https://github.com/Hainrixz/all-deploy.git ~/.claude/skills/all-deploy
```

The skill is now available. Restart Claude Code if it's open.

### Option 2 — install a released `.skill` file

Download `all-deploy.skill` from the [Releases page](https://github.com/Hainrixz/all-deploy/releases) and install via Claude Code's skill installer (drop into `~/.claude/skills/` or use your plugin manager).

## Usage

In Claude Code, say any of:

- `/all-deploy` — starts the cloud deploy flow (asks full-auto vs step-by-step)
- `/all-deploy auto` — full-auto with a 5-second ESC window before prod
- `/all-deploy step` — step-by-step, requires explicit "yes" before prod
- `/all-deploy local` — run the app locally instead
- Natural language: "deploy this", "ship this to prod", "run it locally", "deploy my FastAPI", "despliega", "paso a paso"

## Supported targets (v1)

| Target | Best for |
|---|---|
| **Vercel** | Next.js, Vite, Astro, Remix, Nuxt, SvelteKit, static |
| **Railway** | FastAPI, Flask, Express, Python workers, MCP HTTP, agent loops |
| **Docker + SSH VPS** | Self-hosted, stateful, multi-service compose stacks |
| **cloudflared tunnel** | Local dev exposure, quick demos, webhook testing |

More targets (Netlify, Fly, Modal, Hugging Face Spaces, Cloudflare Pages/Workers) are planned — see the Out of Scope list in the architecture docs.

## The hard rules

The skill ships with 8 non-negotiable safety rules at the top of [`SKILL.md`](SKILL.md). The short version:

1. Never bypass the audit.
2. Never prod before a green preview.
3. Never print, log, or commit secrets.
4. Never auto-install or auto-authenticate third-party CLIs.
5. Never wrap target CLIs in scripts that hide flags.
6. Never modify code without showing the diff first.
7. Never deploy from a dirty tree without explicit opt-in.
8. "Wait" always wins.

## Mode selection

The default `CONFIRMATION_MODE: ask_at_start` lets the user pick full-auto or step-by-step at runtime for each deploy. Fast-path triggers ("auto" / "step by step" / "yolo" / "paso a paso" in the invocation) skip the question. You can also pin to `full_auto` or `always_ask` in the config block at the top of `SKILL.md`.

## Project layout

```
all-deploy/
├── SKILL.md                                  # orchestrator + 8 hard rules + phases 0–6
├── scripts/
│   ├── audit.py                              # 16 secret regexes + 10 check types
│   └── env_extract.py                        # JS/TS/Python (handles destructuring)
├── references/
│   ├── project-types.md                      # framework fingerprint table
│   ├── audit-checklist.md                    # every audit rule explained
│   ├── env-mapping.md                        # env-var delivery per target
│   ├── agents.md                             # FastAPI / MCP / Agent SDK / worker
│   └── targets/
│       ├── vercel.md
│       ├── railway.md
│       ├── docker-vps.md
│       └── cloudflared-tunnel.md
└── assets/templates/
    ├── Dockerfile.node
    ├── Dockerfile.python
    ├── docker-compose.example.yml
    └── .env.example.template
```

Progressive disclosure: Claude loads `SKILL.md` on trigger, `project-types.md` in Phase 1, and only the chosen target's playbook in Phase 3.

## Platform support

macOS and Linux in v1. Windows users should install under WSL2 for path and shell compatibility.

## Contributing

Issues and pull requests welcome. Some good starter contributions:

- Add a new target reference under `references/targets/` (Netlify, Fly, Modal, Cloudflare Pages, etc.).
- Extend `scripts/audit.py`'s secret patterns, or tighten the port-binding heuristic.
- Improve framework detection in `references/project-types.md`.

When adding a target, keep the reference under ~200 lines and follow the existing layout (prereqs → env delivery → preview → health check → prod → rollback + logs).

## License

MIT — see [LICENSE](LICENSE).
