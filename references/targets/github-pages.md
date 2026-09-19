# Target: GitHub Pages

Best for a portfolio, documentation, a demo or a personal site when the code already lives on GitHub — no new account, no new dashboard, no CLI to install. Free `*.github.io` subdomain, free TLS, custom domains supported.

> **Read the commercial restriction before choosing this target.** GitHub's wording: *"GitHub Pages is not intended for or allowed to be used as a free web-hosting service to run your online business, e-commerce site, or any other website that is primarily directed at either facilitating commercial transactions or providing commercial software as a service (SaaS)."* Note **"primarily directed at"** — a brochure site for a business is generally fine; a storefront or a SaaS app is not. Also explicitly prohibited: *"sensitive transactions like sending passwords or credit card numbers."* If the site takes payments, choose Cloudflare Pages.

> **This is the one static target that requires a git repo and a remote.** The audit enforces it here and skips it everywhere else — run the audit with `--target github-pages`.

## Phase 3.5 — prerequisites

```bash
gh --version
gh auth status                        # must show a logged-in account — if not, ! gh auth login
git remote -v                         # must point at a GitHub remote
```

If `gh` is missing: `! brew install gh`

**No-CLI path.** Everything here is doable at github.com: create the repo, *Add file → Upload files*, drag the folder in, commit, then *Settings → Pages → Source: Deploy from a branch*. Offer this whenever the user has no terminal. It is the only free host where the browser path also gives you push-to-update.

## Repo + branch setup

If there is no repo yet, show the commands and **confirm before creating anything on the user's account** — this publishes code under their name:

```bash
git init -b main
git add -A && git commit -m "Initial site"
gh repo create <NAME> --public --source=. --push
```

Publishing source. GitHub's current recommendation for a plain static site is the **branch**, not Actions: *"If you do not need any control over the build process for your site, we recommend that you publish your site when changes are pushed to a specific branch."* Actions is for a non-Jekyll build, or when you don't want compiled output committed.

```bash
# Branch-based (recommended for plain HTML)
gh api repos/{owner}/{repo}/pages -X POST \
  --field source.branch=main \
  --field source.path=/            # or /docs

# GitHub Actions as the build source instead
gh api repos/{owner}/{repo}/pages -X PUT -f build_type=workflow

# Read the current config
gh api repos/{owner}/{repo}/pages
```

There is **no `gh pages` command**. Pages is driven entirely through `gh api`. `build_type` takes exactly two values: `legacy` (branch) and `workflow` (Actions).

## Phase 4 — env delivery

**Skip. There is nothing to deliver to.** A branch-published site is the contents of a folder in a public repo — every byte is readable on github.com before it is ever served. If the page needs a secret, it needs a server. See `references/static-sites.md`.

Actions-built sites can read repository secrets at build time, but any value inlined into the output is still public. Same rule.

## Phase 4 — publish (there is no preview)

**One branch = one site.** GitHub Pages has no preview environment and no staging URL. This is the honest gap against Cloudflare Pages and Netlify, and it changes how the skill's preview gate is satisfied.

Serve the exact publish directory locally and health-check that instead — no install needed, it ships with Python:

```bash
python3 -m http.server -d <PUBLISH_DIR> 8000
```

Then publish:

```bash
git add -A && git commit -m "Publish site" && git push
```

The build takes 30–90 seconds after the push.

```bash
gh api repos/{owner}/{repo}/pages/builds/latest --jq '.status, .error.message'
```

## Phase 4.5 — health check

```bash
PROD_URL="https://<USERNAME>.github.io/<REPO>/"       # project site
# or: PROD_URL="https://<USERNAME>.github.io/"        # user site (repo named <USERNAME>.github.io)
curl -sSL -o /dev/null -w "%{http_code}" "$PROD_URL"
```

Expect a 404 for the first couple of minutes after enabling Pages — that is the build, not a failure. Re-probe before concluding anything.

**Also probe the first stylesheet.** On a *project* site the page lives under `/<REPO>/`, so a `/style.css` reference resolves to the domain root and 404s while the page itself returns 200. That is the most common GitHub Pages bug and the root probe hides it.

## Phase 5 — prod promotion

There is no promotion step. The push *is* production. Make sure the local health check passed and the user has said yes before the push, because there is no green-preview state to fall back to.

**Cost note:** free, with documented limits — source repo *"recommended limit of 1 GB"*, published site *"may be no larger than 1 GB"*, a **soft** bandwidth limit of 100 GB/month and a **soft** limit of 10 builds/hour. Both bandwidth and builds are explicitly soft. Current limits: `https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits`

## Phase 6 — post-deploy

**Rollback:** revert the commit and push.

```bash
git revert <bad-sha> && git push
```

**Logs / status:**

```bash
gh api repos/{owner}/{repo}/pages/builds/latest
gh run list --workflow=pages-build-deployment      # when built via Actions
gh api repos/{owner}/{repo}/pages/health           # DNS check for a custom domain
```

## `.nojekyll` — when it's required

GitHub Pages runs Jekyll over a branch-published site, and Jekyll **skips any file or directory whose name starts with an underscore**. A site with `_next/`, `_assets/` or `_images/` will serve its HTML fine and 404 every stylesheet and script — the page renders as unstyled text and nothing in the build log says why.

```bash
touch <PUBLISH_DIR>/.nojekyll
```

It must be at the root of the published directory; one in a subfolder is ignored. Not needed when publishing through an Actions workflow that uploads an artifact — that path never runs Jekyll. The static audit flags this, but only with `--target github-pages`.

## Custom domain

Add a `CNAME` file at the repo root containing the bare domain — the Pages settings UI creates it for you. Full DNS detail in `references/custom-domain.md`.

- **Apex** — all four `A` records (`185.199.108.153`, `.109.153`, `.110.153`, `.111.153`) and, for IPv6, all four `AAAA` (`2606:50c0:8000::153` through `8003::153`).
- **`www`** — `CNAME` → `<USERNAME>.github.io`, **without the repository name appended.** This is the single most common misconfiguration.

## Common pitfalls

- **`/style.css` breaks on a project site.** The site root is `username.github.io/repo/`, not `username.github.io/`. Use relative paths. The static audit flags root-relative references under `--target github-pages`.
- **Underscore folders vanish without `.nojekyll`.** Silent, total, and invisible in the build log.
- **The `www` CNAME must not include the repo name.**
- **No preview environment.** One branch, one site. Check locally first.
- **A public repo means the source is public**, including anything you forgot to delete. This is not the target for a client's unpublished work.
- **Enabling Pages on a brand-new repo 404s for a minute or two.** Don't diagnose a DNS problem that is actually a build in progress.
- **`gh api` needs `{owner}/{repo}` substituted** — `gh` fills those placeholders from the current repo, so run it inside the checkout.
