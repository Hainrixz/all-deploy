# Target: Railway

Best for long-running Python/Node services (FastAPI, Flask, Express, Celery workers, agent loops). Native Procfile support, add-on databases, per-service env vars.

> **Railway CLI syntax evolves faster than most.** Command names (`variables`, `add`, `environment`) and their flags have changed across recent releases. Always run `railway --help` and `railway <subcommand> --help` to verify before relying on an invocation below.

## Phase 3.5 — prerequisites

```bash
railway --version                # v3+ recommended
railway whoami                    # must return email — if not, ! railway login
```

If CLI missing: `! brew install railway` (macOS) or `! npm i -g @railway/cli`.

## Link to existing project vs create new

```bash
# Link to existing project in this directory:
railway link
# prompts: project, environment (usually "production"), service

# Or init a fresh project:
railway init
# creates a new project and links it
```

Either command writes `.railway/metadata.json` locally (ignored by default).

## Add a database (if needed)

The audit flags DB deps in Phase 1. If found, provision before deploy:

```bash
railway add --database postgres        # or: --database redis, --database mysql, etc.
railway variables                       # verify DATABASE_URL is now set on the service
```

The add-on exposes its URL to every service in the same environment via `${{ Postgres.DATABASE_URL }}` or directly as `DATABASE_URL`.

## Phase 4 — env delivery

```bash
# One at a time:
railway variables --set "ANTHROPIC_API_KEY=sk-ant-..."

# Batch from a local .env — loop, since there's no single bulk-import flag:
while IFS='=' read -r key value; do
  [ -z "$key" ] && continue
  [[ "$key" =~ ^# ]] && continue
  railway variables --set "$key=$value"
done < .env
```

For bulk paste, the Railway dashboard's "Raw Editor" accepts a `.env`-format block directly.

Verify (keys only — don't log values):

```bash
railway variables | cut -d= -f1
```

## Phase 4 — preview / deploy

Railway doesn't have preview URLs in the Vercel sense, but it offers per-environment deploys. The author's recommendation:

1. Create a `preview` environment:
   ```bash
   railway environment preview
   railway link                         # re-link against the preview env
   ```
2. Deploy:
   ```bash
   railway up                            # builds + deploys to the linked environment
   ```
3. Once verified, switch back to `production` and deploy:
   ```bash
   railway environment production
   railway up
   ```

`railway up` runs in the foreground and takes 2–8 min for typical projects. Use `run_in_background: true` + `Monitor` to watch for the deploy URL line.

### Extract the preview URL

Railway prints:
```
✓ Build successful
✓ Deployment live at https://<project>-<env>.up.railway.app
```

Parse:
```bash
PREVIEW_URL=$(grep -oE 'https://[^ ]+\.up\.railway\.app' /tmp/railway-up.log | tail -1)
```

If the service is a worker (no HTTP), there's no URL — skip Phase 4.5 and check process status instead:
```bash
railway status
railway logs | head -50                 # confirm the worker started cleanly
```

## Phase 4.5 — health check (HTTP services)

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
```

2xx/3xx → promote. Failure → `railway logs` for the runtime output.

## Phase 5 — prod promotion

If you used separate environments:
```bash
railway environment production
railway up
```

If single-environment (the default pattern): `railway up` already deployed. Nothing more to do — Railway promoted on the first deploy.

Cost note: Hobby plan starts at a small monthly fee with usage credits; add-ons (Postgres, Redis) each have their own pricing. Check `https://railway.com/pricing` for current terms.

## Phase 6 — post-deploy

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$PROD_URL"
railway variables | cut -d= -f1        # confirm keys without values
```

**Rollback:** Railway keeps deploy history. Use the dashboard → Deployments → pick a prior one → "Redeploy". Via CLI:

```bash
railway deployments                     # list
# There is no first-class `railway rollback` command as of this writing —
# redeploy the prior commit with:
git checkout <previous-sha>
railway up
git checkout -
```

**Logs:**
```bash
railway logs                            # recent
railway logs --follow                   # tail
```

## `railway.toml` (optional)

For projects with multiple services or custom build/start:

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

For multi-process apps (web + worker), use a `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
worker: celery -A app.tasks worker --loglevel=info
beat: celery -A app.tasks beat --loglevel=info
```

Railway creates a separate service per Procfile line.

## Common pitfalls

- **Binding to localhost fails silently at first request.** Always use `0.0.0.0`.
- **`$PORT` is required.** Railway injects it; don't hardcode `3000` / `8000`. Audit's `port-binding.localhost-only` check covers this.
- **Cold starts on free tier:** if the service scales to zero, first request after idle takes ~10 s. Not an issue for paid tiers.
- **Environment confusion:** `railway link` can associate the local dir with an unexpected environment. Always `railway status` before a deploy.
- **DB migrations:** Railway does not run migrations automatically. Add a pre-deploy step or a release command. (Out of scope for v1; see the Out-of-Scope list in the plan.)
- **Build logs vs runtime logs:** `railway logs` shows runtime. Build failures live in the dashboard Deployments tab.
