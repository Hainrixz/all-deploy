# Agent deployment guide

Four agent shapes commonly encountered, each with a recommended target and per-type adjustments. Load this in Phase 3 when the project signals "agent" (LLM calls, MCP server, Claude Agent SDK, long-running loop).

---

## 1. FastAPI / Flask HTTP agent

**Shape:** Python web service exposing LLM calls behind HTTP endpoints. Stateless or light Redis-backed memory. Examples: a chatbot API, a webhook-driven analysis service.

**Signals:**
- `main.py` or `app.py` with `FastAPI()` / `Flask()` / `from fastapi import`
- Imports from `anthropic`, `openai`, `langchain`, `llama-index`
- Optional: `redis`, `sqlalchemy` for memory/session

**Recommended target:** **Railway** (long-running, fast deploy, env via dashboard or CLI).

**Start command (Procfile-style):**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Key env vars to set on Railway:**
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — the LLM key.
- `DATABASE_URL` — if using a DB; provision via `railway add` → PostgreSQL.
- `REDIS_URL` — if using cache/memory; provision via `railway add` → Redis.

**Audit adjustments for this shape:**
- Block on missing `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in `.env.example` (not in the allowlist of safe defaults — these are critical).
- Warn if the code calls `anthropic.Anthropic()` without passing an explicit `api_key=` (relies on env, which is fine but worth confirming).

**Docker alternative:** See `assets/templates/Dockerfile.python`. Use when you need custom system deps (e.g., `ffmpeg`, `chromium`).

---

## 2. MCP server

**Shape:** Model Context Protocol server. Two wire modes that deploy very differently.

### 2a. MCP over stdio (local-only)

**Signals:**
- `@modelcontextprotocol/sdk` import with `StdioServerTransport`
- `from mcp.server.stdio` in Python
- Package declares `"bin"` in `package.json` intended for local install

**Deploy target:** **Not deployable as a service.** stdio MCP servers run as a subprocess of the client (Claude Code, etc.).

**"Deploy" flow:**
1. Publish to npm (`npm publish`) or PyPI (`uv publish`) so users can install.
2. Provide install instructions: `claude mcp add <name> <path-or-package>`.
3. `/all-deploy` exits cleanly for stdio MCP — this is a package publish, not a web deploy. Direct the user to npm/PyPI publishing.

### 2b. MCP over HTTP

**Signals:**
- `StreamableHTTPServerTransport` or equivalent HTTP transport
- Listens on a port

**Recommended target:** **Railway** (long-running) or **Docker+SSH VPS**.

**Start command:**
```
web: node dist/server.js            # Node
web: python -m mcp_server.http      # Python
```

**Authentication note:** MCP HTTP servers are normally accessed by authenticated clients only. Put the server behind a bearer-token check at minimum, or behind a reverse proxy that handles auth. Don't expose a raw MCP HTTP endpoint publicly.

---

## 3. Claude Agent SDK script

**Shape:** Python/Node script that loops, calls the LLM, takes actions (runs tools, writes files, sends messages). May run continuously or on a cron.

**Signals:**
- Imports `claude_agent_sdk` / `@anthropic-ai/claude-agent-sdk`
- A top-level `while True:` or equivalent loop
- No HTTP framework

**Deploy target decision:**
- **Long-running loop** → Railway worker service (no exposed port) or Docker+SSH with `restart: always`.
- **Scheduled run** → Railway's cron feature or a cron on the VPS.

**Railway worker service:**
```toml
# railway.toml
[deploy]
startCommand = "python agent.py"
restartPolicyType = "ALWAYS"
```

No `web:` in the Procfile — Railway creates a non-HTTP worker.

**Key env vars:**
- `ANTHROPIC_API_KEY` — required.
- `ANTHROPIC_LOG` — optional, for structured logs.
- Any tool-specific credentials the agent uses (GitHub token, Slack bot token, etc.).

**Safety considerations for an autonomous agent:**
- Rate limits: API rate limiting or a max-iterations cap in the loop.
- Kill switch: a file or env var the agent checks each iteration (`if Path("/tmp/STOP").exists(): break`).
- Observability: pipe logs to a central collector (Axiom, Grafana, or Railway's built-in logs at minimum).
- Budget cap: track token usage and bail when the monthly budget is exhausted.

**The audit should warn** if the script has no visible rate limit or iteration cap. This is manual — audit.py doesn't detect it.

---

## 4. Generic Python worker

**Shape:** Background job, queue consumer, scheduled task. No HTTP. Examples: RQ/Celery worker, SQS consumer, APScheduler job, cron-triggered batch.

**Signals:**
- `celery`, `rq`, `dramatiq`, `apscheduler`, `redis-om` imports
- Long-lived process without HTTP framework

**Recommended target:** **Railway worker** or **Docker+SSH** (with systemd or `restart: always`).

**Railway configuration (no `web:` Procfile):**
```
# Procfile
worker: celery -A app.tasks worker --loglevel=info
```

For Celery + Redis + beat:
```
worker: celery -A app.tasks worker --loglevel=info
beat: celery -A app.tasks beat --loglevel=info
```

Railway creates separate services for each Procfile entry.

**Docker+SSH alternative:**

`docker-compose.yml`:
```yaml
services:
  worker:
    build: .
    command: celery -A app.tasks worker --loglevel=info
    restart: always
    environment:
      - REDIS_URL=${REDIS_URL}
  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis-data:/data
volumes:
  redis-data:
```

**Audit adjustments:**
- Port-binding check is N/A (no HTTP).
- Health check in Phase 4.5: for workers without HTTP, skip the curl step. Instead, check that the worker process is running: `ssh host 'docker compose ps worker' | grep Up`.

---

## Cross-cutting: API keys for LLM providers

All four agent shapes require LLM credentials. **Never** put them in source or `.env.example` with real values.

Standard setup:
1. Create keys with scopes limited to what the agent needs (Anthropic workspace-scoped key, OpenAI project key, etc.).
2. Store in target secret manager (Railway variables, Docker compose `.env`).
3. Monitor usage via the provider's dashboard — set a budget alert.
4. Rotate on any suspected leak (git-history scan, logs with accidental echo, etc.).

## Cross-cutting: storage

| Need | Recommendation |
|---|---|
| Short-term session/cache | Redis via Railway add-on or `redis:7-alpine` container |
| Durable structured data | Postgres via Railway add-on or external managed (Neon, Supabase) |
| Vector embeddings | `pgvector` on Postgres or a dedicated vector DB (Qdrant, Weaviate — not covered in v1) |
| Files / artifacts | S3-compatible (Cloudflare R2, AWS S3, Supabase Storage) — not covered in v1 |

For the four agent shapes, Railway's add-ons handle Redis and Postgres cleanly. Docker+SSH can run both in the same compose file.
