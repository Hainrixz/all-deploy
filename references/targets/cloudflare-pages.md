# Target: Cloudflare Pages

Best for a static site that has to be free *and* usable commercially — the only one of the five free static hosts with no commercial-use restriction and no deploy-credit budget. Free subdomain, free TLS, unlimited preview deployments.

> **Where Cloudflare is heading.** The Pages docs now carry: *"Workers supports most Pages use cases and offers a broader feature set. It is Cloudflare's primary platform for building applications. Start new projects with Workers."* Pages is **not deprecated** and stays the simplest path for "connect a GitHub repo and forget about it." If the user wants the forward-looking setup, the Workers equivalent is at the bottom of this file.

## Phase 3.5 — prerequisites

```bash
npx wrangler --version                # Cloudflare recommends a local install over -g
npx wrangler whoami                   # must print an account — if not, ! npx wrangler login
```

If Wrangler is missing: `! npm i -D wrangler@latest`

**No-CLI path.** This target has a full browser route — *Workers & Pages → Create → Pages → Upload assets*, drag the publish folder in. Offer it whenever the user has no Node installed or simply doesn't want a CLI. Nothing below is required for that path except the custom-domain section.

## Link to existing project vs create new

Check for a `wrangler.toml`/`wrangler.jsonc` with a `pages_build_output_dir`, or ask whether a Pages project already exists. If it does, reuse the name — `wrangler pages deploy` targets a project by name, not by a local link file.

```bash
npx wrangler pages project list
npx wrangler pages project create <PROJECT_NAME>    # one-time, for direct-upload projects
```

**Git integration is dashboard-only.** There is no Wrangler command to connect a repository. If the user wants push-to-deploy: *Workers & Pages → Create application → Pages → Connect to Git*, install and authorize the Cloudflare GitHub App, pick the repo and branch, set build command and output directory. Hand them those steps; don't pretend a CLI flag exists.

## Phase 4 — env delivery

**For a static site: skip this phase entirely.** Everything Pages serves is public. A build-time variable (`VITE_*`, `PUBLIC_*`, `NEXT_PUBLIC_*`) is inlined into the JavaScript bundle and is readable by anyone who opens devtools. Setting it "as an environment variable" changes nothing about that. See `references/static-sites.md`.

If the project has Pages Functions (a `functions/` directory), those *do* run server-side and take real secrets:

```bash
npx wrangler pages secret put <KEY> --project-name <PROJECT_NAME>
npx wrangler pages secret list --project-name <PROJECT_NAME>
```

Never log the values. Only the keys.

## Phase 4 — preview deploy

```bash
npx wrangler pages deploy <PUBLISH_DIR> --project-name <PROJECT_NAME> --branch=preview
```

**`--branch` is what separates preview from production**, and the trap is that omitting it is not the same as asking for production:

- omitted, outside a git workspace → production, served at `<PROJECT_NAME>.pages.dev`
- omitted, **inside a git repo** → Wrangler reads your current local branch name and uses that. From a feature branch you get a preview; from `main` you get production. Docs: *"If you are in a Git workspace, Wrangler will automatically pull the branch information for you."*
- `--branch=<NAME>` → preview, served at `<NAME>.<PROJECT_NAME>.pages.dev`

Always pass `--branch` explicitly. Never rely on the inference.

Capture the URL — it is printed on the last non-empty stdout line as `https://<hash>.<project>.pages.dev`:

```bash
npx wrangler pages deploy <PUBLISH_DIR> --project-name <PROJECT_NAME> --branch=preview 2>&1 \
  | tee /tmp/cfpages-preview.log
PREVIEW_URL=$(grep -oE 'https://[a-z0-9-]+\.[a-z0-9-]+\.pages\.dev' /tmp/cfpages-preview.log | tail -1)
```

## Phase 4.5 — health check

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
```

2xx/3xx → promote. 4xx/5xx or empty → stop; check the deployment in the dashboard.

**Also probe the first stylesheet the page references.** A 200 on `/` with a 404 on `/estilo.css` is exactly what a filename-capitalisation bug looks like in production, and the root probe alone calls that deploy green:

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL/<first-stylesheet-href>"
```

## Phase 5 — prod promotion

```bash
npx wrangler pages deploy <PUBLISH_DIR> --project-name <PROJECT_NAME> --branch=main
```

`--branch` must match the project's **production branch** (`main` by default). For Direct Upload projects the production branch name cannot be changed from the dashboard — only through the API — so pick it correctly at creation time.

**Cost note:** the free plan covers 500 builds/month, 1 concurrent build, a 20-minute build timeout, 20,000 files per site, 25 MiB per file, 100 custom domains per project and 100 projects per account. Cloudflare documents static asset requests as *"free and unlimited"* and publishes **no bandwidth number** — so don't quote one. Current limits: `https://developers.cloudflare.com/pages/platform/limits/`

## Phase 6 — post-deploy

```bash
curl -sSL -o /dev/null -w "%{http_code}" "https://<PROJECT_NAME>.pages.dev"
```

**Rollback:** dashboard only. There is no Wrangler rollback command. *Workers & Pages → your project → Deployments → the three-dot menu on the deployment you want → Rollback to this deployment.* Tell the user this before they need it.

**Logs:**

```bash
npx wrangler pages deployment list --project-name <PROJECT_NAME>
npx wrangler pages deployment tail --project-name <PROJECT_NAME>
```

`deployment tail` streams **Functions** logs. For a pure static site there is nothing to tail — build output lives in the dashboard.

## Custom domain

Full DNS detail in `references/custom-domain.md`. The short version:

- **Apex (`example.com`)** — the domain must be on Cloudflare nameservers. Cloudflare then creates the flattened CNAME itself. There is no A-record path.
- **`www`** — a plain `CNAME` to `<PROJECT_NAME>.pages.dev`, which works on any DNS provider.

## Common pitfalls

- **Omitting `--branch` inside a repo does not mean production.** Wrangler reads the local branch. Deploying from a feature branch silently publishes a preview and the user thinks prod is updated. Always pass it.
- **The publish directory is the folder that *contains* `index.html`**, not the project root. For Astro that's `dist/`, Hugo `public/`, Jekyll `_site/`, Eleventy `_site/`. Getting this wrong produces a live site that 404s at `/`.
- **Build command empty for a plain HTML site.** In the dashboard, leaving build command blank and output directory `/` is correct. People fill in `npm run build` out of habit and the build fails.
- **20,000 files per deployment** is the limit that bites image-heavy photo sites, not bandwidth.
- **A `.env` in the publish folder gets uploaded and served** at `/.env`. Direct upload sends whatever you point it at. The static audit blocks on this.
- **Pages Functions are the only part that can hold a secret.** If the user's "static" page needs an API key, it needs a Function or a different architecture — not an environment variable.

## The Workers equivalent (Cloudflare's recommended path for new projects)

`wrangler.jsonc` at the project root:

```jsonc
{
  "name": "my-site",
  "compatibility_date": "2026-09-19",
  "assets": { "directory": "./dist" }
}
```

```bash
npx wrangler deploy
```

`main` and `binding` are only needed when there is also a Worker script. Same free static-asset serving, same custom-domain story, and it is where Cloudflare's new feature work lands.
