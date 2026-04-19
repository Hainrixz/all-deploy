# Target: Vercel

Best for Next.js, Vite, Astro, Remix, Nuxt, SvelteKit, and most static sites. Zero-config for framework projects, preview URLs for every deploy.

## Phase 3.5 — prerequisites

```bash
vercel --version                     # >= 32.x recommended
vercel whoami                         # must return an account — if not, ! vercel login
```

If CLI missing: `! npm i -g vercel`

## Link to existing project vs create new

Check for `.vercel/project.json` first. If present, the project is already linked to a Vercel project — reuse it:

```bash
# Skip `vercel link` — already linked.
# Proceed directly to env delivery + deploy.
```

If absent, link:

```bash
vercel link
# prompts for: scope (personal/team), project name, existing project or new
```

This creates `.vercel/project.json` (should be gitignored).

## Phase 4 — env delivery

For every key returned by `env_extract.py`:

```bash
vercel env add DATABASE_URL preview      # prompts for value, paste it
vercel env add DATABASE_URL production
```

Batch via a loop:

```bash
while IFS='=' read -r key value; do
  [ -z "$key" ] && continue
  [[ "$key" =~ ^# ]] && continue
  echo -n "$value" | vercel env add "$key" preview
  echo -n "$value" | vercel env add "$key" production
done < .env
```

Verify:

```bash
vercel env ls preview
vercel env ls production
```

Never log the values. Only the keys.

## Phase 4 — preview deploy

```bash
vercel                                # preview deploy — NOT --prod
```

The preview URL prints on the last non-empty stdout line, formatted like `https://<project>-<hash>-<scope>.vercel.app`. Parse it for Phase 4.5.

For a Bash tool invocation with `run_in_background: true`:

```bash
vercel 2>&1 | tee /tmp/vercel-preview.log
# Monitor /tmp/vercel-preview.log for "Preview: https://..." or "Production: https://..."
```

Extract the URL:

```bash
PREVIEW_URL=$(grep -oE 'https://[^ ]+\.vercel\.app' /tmp/vercel-preview.log | tail -1)
```

## Phase 4.5 — health check

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
```

2xx/3xx → promote. 4xx/5xx or empty → stop; run `vercel logs $PREVIEW_URL` for the build output.

## Phase 5 — prod promotion

```bash
vercel --prod
```

Prints the production URL (either the `.vercel.app` URL or the configured custom domain).

Cost note: Vercel's Hobby plan is free for personal, non-commercial use; Pro starts at a monthly fee per member. Check `https://vercel.com/pricing` for current terms.

## Phase 6 — post-deploy

```bash
curl -sSL -o /dev/null -w "%{http_code}" "https://<prod-url>"
vercel env ls production               # confirm env is set
```

**Rollback:** (verify with `vercel rollback --help` — command availability has shifted between CLI versions)
```bash
vercel rollback                        # interactive picker (recent CLI)
# or address a specific deployment:
vercel rollback https://<previous-deployment>.vercel.app

# If `rollback` is unavailable in your CLI version, promote an older deployment:
vercel promote <deployment-id-or-url>
```

**Logs:**
```bash
vercel logs <url> --follow
vercel logs                            # most recent deployment
```

## Common pitfalls

- **`NEXT_PUBLIC_*` / `VITE_*` env vars** are baked into the built bundle and visible client-side. Never put secrets in them.
- **Build-time vs runtime:** vars used during `next build` must exist at build. Set them in `preview` and `production` environments.
- **Custom domain SSL:** after adding a domain, certificate provisioning can take a minute. Wait for status to flip to "Valid Configuration" before promoting any custom-domain-dependent feature.
- **Team vs personal scope:** `vercel link` can quietly connect to the wrong scope. Verify with `vercel projects ls`.
- **Monorepo root directory:** if deploying from a subdirectory of a monorepo, set `rootDirectory` in the project's Vercel settings (dashboard) or via `vercel.json`.
- **Preview URL auth:** Vercel Pro teams can require auth on preview URLs, which breaks the Phase 4.5 curl check. Either disable "Vercel Authentication" for the project, or probe a public endpoint.

## `vercel.json` (when you need it)

Most Next.js / Vite / Astro projects need no `vercel.json`. Reach for it when:
- Setting custom headers (cache-control, CSP).
- Rewriting paths to custom domains.
- Overriding the build command or output directory.
- Configuring serverless function limits.

Minimal example:
```json
{
  "buildCommand": "pnpm build",
  "outputDirectory": "dist",
  "framework": null
}
```
