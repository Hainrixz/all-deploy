# Target: Render (static site)

A simple static host with free managed TLS, free custom domains and rollbacks. Worth knowing about, but **check the bandwidth number before recommending it** — it is no longer competitive with Cloudflare Pages or Netlify for a public site.

> **5 GB of outbound bandwidth per month on the free (Hobby) plan.** That is roughly 2,500 loads of a 2 MB page. Overage is billed at **$0.15/GB** on the public internet, and unused bandwidth does not roll over. Hobby also caps you at 1 team member, 25 services, and **2 custom domains** ($0.25/month each beyond that). Choose Render for a low-traffic internal or personal site; choose Cloudflare Pages for anything that might actually get visitors. Current numbers: `https://render.com/docs/outbound-bandwidth`

## Phase 3.5 — prerequisites

The verified creation paths are the dashboard and a `render.yaml` blueprint. An official CLI exists:

```bash
render --version                      # install: brew install render-oss/render/render
render login                          # opens a browser
render services                       # must list your services
```

`render services create` supports non-interactive mode, but Render's docs do not demonstrate creating a **static site** with it. Treat the dashboard or `render.yaml` as the confirmed path and verify the CLI route by test before relying on it.

**No-CLI path.** The dashboard is the primary route here: *New → Static Site → connect repo → set build details → Create Static Site.* Render has no drag-and-drop upload — it always deploys from a git repo, so this target needs a remote.

## Link to existing project vs create new

Check for `render.yaml` at the repo root. If it exists, Render already knows this project and a push redeploys it.

```yaml
services:
  - name: my-static-site
    type: web          # static sites are type: web ...
    runtime: static    # ... plus runtime: static. Both lines are required.
    repo: https://github.com/<owner>/<repo>
    branch: main
    buildCommand: npm install && npm run build   # omit for a plain HTML site
    staticPublishPath: ./dist                    # the folder holding index.html
```

`type: web` **plus** `runtime: static` is the non-obvious pair — neither alone works. No `startCommand`, no `region`.

```bash
render blueprints validate            # check render.yaml before pushing
```

## Phase 4 — env delivery

**Skip for a static site.** Render serves the publish folder as-is; anything in it is public, and a build-time variable is inlined into the bundle. See `references/static-sites.md`.

Render does inject build-time environment variables for the build command, which is legitimate for public values (an analytics ID, a public API base URL) and never for a secret.

## Phase 4 — preview deploy

Render's preview story for static sites is **pull-request previews**, configured per service in the dashboard (*Settings → Pull Request Previews*), not a CLI flag. With them enabled, opening a PR builds a preview at `<service>-pr-<n>.onrender.com`.

Without PR previews there is no preview URL. Fall back to serving the exact publish directory locally and health-checking that:

```bash
python3 -m http.server -d <PUBLISH_DIR> 8000
```

## Phase 4.5 — health check

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
```

2xx/3xx → promote. 4xx/5xx or empty → stop and read the build log in the dashboard, or `render logs`.

**Also probe the first stylesheet the page references** — a 200 on `/` with a 404 on the CSS is a filename-capitalisation bug, and the root probe alone would call that green.

## Phase 5 — prod promotion

A push to the configured branch triggers the deploy:

```bash
git push
render deploys create <SERVICE_ID>    # or trigger manually
```

**Cost note:** free to deploy, no credit card. The constraint is **5 GB/month of outbound bandwidth**, then $0.15/GB. Verify before promoting a site that expects traffic: `https://render.com/docs/outbound-bandwidth`

## Phase 6 — post-deploy

```bash
curl -sSL -o /dev/null -w "%{http_code}" "https://<SERVICE>.onrender.com"
```

**Rollback:** the dashboard keeps rollbacks on the free plan, **limited to the two previous deploys**. *Service → Deploys → the deploy you want → Rollback.* Beyond two, redeploy an earlier commit.

**Logs:**

```bash
render logs
```

Free-plan log streams are available; retention is short.

## Custom domain

Full detail in `references/custom-domain.md`.

- **Apex** — `ANAME`/`ALIAS` → `<SERVICE>.onrender.com`, or an `A` record → `216.24.57.1`.
- **`www`** — `CNAME` → `<SERVICE>.onrender.com`.
- **Remove any `AAAA` records** while configuring DNS. Render is IPv4-only and a stale AAAA makes the site unreachable for IPv6 clients in a way that looks random.

## Common pitfalls

- **5 GB/month.** The number changed and most guides online still quote 100 GB. Check it, say it, and don't put a marketing site here without a plan for the overage.
- **`type: web` + `runtime: static`.** Getting one of the two wrong produces a service that tries to run a web process and fails with no obvious message.
- **`staticPublishPath` is the folder containing `index.html`**, not the repo root — `./dist`, `./public`, `./_site`.
- **Two custom domains included.** A third costs money, which is surprising on a "free" plan.
- **IPv4 only** — leftover `AAAA` records break the site intermittently.
- **No drag-and-drop.** Render always deploys from a repo; someone with just a folder needs git first, or a different target.
