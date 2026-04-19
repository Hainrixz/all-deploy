# Environment-variable mapping

How env vars move from a local `.env` to each supported target. Use in Phase 4 before the preview runs.

## Source of truth

The local `.env` is the authoritative source during development. **Never commit it.** `.env.example` (or `.env.sample`) lists the keys without values for onboarding and for the audit's completeness check.

For cloud deploys, the local `.env` values must be pushed to the target's secret store *before* the preview is built — most targets inject env vars at build + runtime.

## Vercel

Vercel separates env vars by environment: `development`, `preview`, `production`. Build-time and runtime vars share the same interface.

### Push from local `.env` to Vercel

```bash
# Add a single key, prompting for the value:
vercel env add DATABASE_URL preview
vercel env add DATABASE_URL production

# Pipe a value in non-interactively:
echo -n "$DATABASE_URL" | vercel env add DATABASE_URL preview
echo -n "$DATABASE_URL" | vercel env add DATABASE_URL production

# Pull what Vercel already has (into a gitignored local file):
vercel env pull .env.vercel.local

# For bulk upload from an existing .env, see the loop example in
# references/targets/vercel.md (Phase 4 — env delivery).
```

### Verify

```bash
vercel env ls production
vercel env ls preview
```

### NEXT_PUBLIC_* caveat

For Next.js / Vite / Astro: any var that needs to be readable from client-side code must be prefixed appropriately (`NEXT_PUBLIC_`, `VITE_`, `PUBLIC_`). These are baked into the built bundle and visible to anyone inspecting the page — never put secrets in them.

## Railway

Railway stores env vars per service (project → environment → service). All vars are available at build and runtime.

### Push from local `.env`

```bash
# One at a time:
railway variables --set "DATABASE_URL=postgres://..."

# Batch from a local .env (loop — no single-command bulk import exists):
while IFS='=' read -r key value; do
  [ -z "$key" ] && continue
  [[ "$key" =~ ^# ]] && continue
  railway variables --set "$key=$value"
done < .env
```

For very large `.env` files, the Railway dashboard's "Raw Editor" accepts a pasted `.env` block directly. CLI syntax has varied across versions — `railway variables --help` for the current flag names.

### Verify

```bash
railway variables
```

### Reference another service

Railway lets one service reference another's env vars (e.g., the app uses the Postgres add-on's `DATABASE_URL`):

```
DATABASE_URL=${{ Postgres.DATABASE_URL }}
```

Written into the app service's env via `railway variables --set ...`.

## Docker + SSH VPS

Two common patterns:

### Pattern 1: `environment:` block in `docker-compose.yml`

```yaml
services:
  app:
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - STRIPE_SECRET=${STRIPE_SECRET}
```

The host shell reads from a `.env` file next to `docker-compose.yml`. Push `.env.production` to the host:

```bash
scp .env.production user@host:/app/.env
# then on the host:
ssh user@host 'cd /app && docker compose up -d --pull=always'
```

### Pattern 2: Inline secrets via SSH

For one-off deploys, pipe env at compose time:

```bash
ssh user@host 'cat > /app/.env' < .env.production
```

**Never** commit a `.env.production` file to git. Use `.gitignore` entry `.env.*` (with `.env.example` allowlisted).

### Verify

```bash
ssh user@host 'cd /app && docker compose config'   # prints resolved compose with env expanded (redact before sharing)
ssh user@host 'cd /app && docker compose exec app env | grep -v ^_'
```

## cloudflared tunnel

Local server → public URL. Env vars stay **local** — cloudflared is just a tunnel, there is no remote environment to push to. The server reads `process.env.X` from the current shell (your machine's `.env` loaded via `dotenv` or the framework's equivalent).

## Summary table

| Target | Where vars live | How to push | How to verify |
|---|---|---|---|
| Vercel | Per-environment (dev/preview/prod), dashboard or CLI | `vercel env add KEY <env>` | `vercel env ls <env>` |
| Railway | Per-service, per-environment | `railway variables --set KEY=value` | `railway variables` |
| Docker+SSH | `.env` file on host + compose `environment:` | `scp .env.production host:/app/.env` | `docker compose config` |
| cloudflared | Local shell only | N/A — local | `env \| grep YOUR_KEY` |

## Build-time vs runtime (Vercel-specific)

- **Build-time:** reads at `vercel build`. Needed for `NEXT_PUBLIC_*`, `VITE_*`, any env referenced during static generation.
- **Runtime:** available in server functions and edge functions at request time.

When in doubt, set the var for both `preview` and `production` environments. Vercel applies build-time vars to both.

## Redaction rules

When reporting env status to the user, **never print values**. Only print keys. Example audit output:

> Set on Vercel (preview): DATABASE_URL, STRIPE_SECRET, SENTRY_DSN
> Missing: REDIS_URL

Never:

> Set DATABASE_URL=postgres://real:password@host/db ✓

Even in debug output.
