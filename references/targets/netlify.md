# Target: Netlify

Best for a static site that needs a contact form with no backend — Netlify Forms is free and is the one feature none of the other four match. Also the easiest drag-and-drop path. Free subdomain, free TLS, deploy previews on every branch.

> **The free plan is a credit budget, not a bandwidth allowance, and it has a hard floor.** 300 credits/month, no rollover. A **production deploy costs 15 credits**, bandwidth 20 credits/GB, web requests 2 credits per 10,000. When the balance hits zero, Netlify's wording is: *"all of your web projects (sites/apps) are paused and visitors to your web projects will find a `Site not available` page."* That is roughly 20 production deploys a month **and nothing else**, or ~15 GB of traffic. Say this out loud before someone puts a client's site here. Deploy previews and branch deploys are free.

## Phase 3.5 — prerequisites

```bash
netlify --version
netlify status                        # must print an account — if not, ! netlify login
```

If the CLI is missing: `! npm install -g netlify-cli`

**No-CLI path.** `https://app.netlify.com/drop` — drag the publish folder, a zip, or a single HTML file. No account needed **to deploy**, but the quickstart states the result *"is protected with a temporary password until you claim it"*, and claiming means signing up. So the honest framing is: *publishing is account-free, showing it to anyone is not.* Don't promise a public URL without a signup.

## Link to existing project vs create new

Check for `.netlify/state.json` first. If present, the folder is already linked to a site — reuse it and skip linking.

```bash
netlify link                          # link this folder to an existing site
netlify init                          # create the site and wire up continuous deployment
```

`.netlify/` should be gitignored.

## Phase 4 — env delivery

**For a static site: skip this phase entirely.** Netlify serves whatever is in the publish directory, publicly. A build-time variable is inlined into the bundle. See `references/static-sites.md`.

If the project has Netlify Functions, those run server-side and take real values:

```bash
netlify env:set <KEY> <value>
netlify env:list
```

Never log the values. Only the keys.

## Phase 4 — preview deploy

```bash
netlify deploy --dir=<PUBLISH_DIR>              # draft deploy — this is the DEFAULT
netlify deploy --dir=<PUBLISH_DIR> --no-build   # when the files are already built
```

`netlify deploy` creates a **draft** unless you pass `--prod`. That default is the right way round, and it means the preview step costs nothing against the credit budget.

The draft URL is printed as `Website Draft URL: https://<hash>--<site>.netlify.app`:

```bash
netlify deploy --dir=<PUBLISH_DIR> 2>&1 | tee /tmp/netlify-preview.log
PREVIEW_URL=$(grep -oE 'https://[a-z0-9-]+--[a-z0-9-]+\.netlify\.app' /tmp/netlify-preview.log | tail -1)
```

Useful extras: `--alias <NAME>` for a stable preview URL, `--message "..."` to label the deploy in the dashboard, `--json` for machine-readable output.

## Phase 4.5 — health check

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
```

2xx/3xx → promote. 4xx/5xx or empty → stop; run `netlify logs --source deploy --since 1h`.

**Also probe the first stylesheet the page references** — a 200 on `/` with a 404 on the CSS is what a filename-capitalisation bug looks like live, and the root probe alone would call that green.

## Phase 5 — prod promotion

```bash
netlify deploy --prod --dir=<PUBLISH_DIR>
```

**Cost note:** this is the call that spends **15 credits**, out of 300 per month. Ten deploys in an afternoon while tweaking a heading is half the month's budget. For iteration, use draft deploys — they're free — and promote once. Current pricing: `https://www.netlify.com/pricing/`

## Phase 6 — post-deploy

```bash
curl -sSL -o /dev/null -w "%{http_code}" "https://<SITE_NAME>.netlify.app"
netlify status
```

**Rollback:** there is no `netlify rollback` command. From the dashboard: *Deploys → pick a previous successful deploy → **Publish deploy**.* Netlify documents it as *"This doesn't trigger a new deploy but instead publishes a previous atomic deploy that is still available to you. Rollbacks are instantaneous."* Instant, free, and it does not consume a production-deploy credit.

**Logs:**

```bash
netlify logs --source deploy --since 7d
netlify logs --source functions --since 24h
netlify logs --follow
```

Note the flag form. The older `netlify logs:deploy` subcommand style has been replaced by `--source`.

## Custom domain

Full detail in `references/custom-domain.md`. With external DNS:

- **Apex** — `ALIAS`/`ANAME`/flattened `CNAME` at `@` → `apex-loadbalancer.netlify.com`. If the provider supports none of those, an `A` record at `@` → `75.2.60.5`.
- **`www`** — `CNAME` → `<SITE_NAME>.netlify.app`.

## Common pitfalls

- **Running out of credits pauses the site.** Not throttles — pauses, with a "Site not available" page. This is the single most important thing to tell someone putting a client's site here.
- **`netlify deploy` without `--prod` is a draft.** People run it, see a URL, share it, and wonder why the custom domain shows the old site.
- **`--no-build` when you already built.** Without it Netlify may try to run a build command it detected and fail on a folder that has no build.
- **A Drop deploy is not public until claimed.** The URL works for you and is password-protected for everyone else.
- **Netlify Forms needs the form to exist at build time** — a `netlify` attribute on a `<form>` in the deployed HTML. Forms injected by JavaScript after load are not detected.
- **A `.env` in the publish folder gets uploaded and served.** The static audit blocks on this.
- **Free-plan credits do not roll over** and there is no way to buy a partial top-up — the next step is a paid plan.
