---
name: publish-website
description: >
  Puts a web page on the internet for free, with no terminal and no paid
  plan — a folder of HTML/CSS/JS, or a page Claude just built. Checks the
  page for the things that silently break it once it's live (wrong filename,
  broken image paths, capitalisation that works on your computer and 404s on
  the host, API keys left in the JavaScript), then walks through publishing
  it on Cloudflare Pages, Netlify, GitHub Pages or Render, and connecting a
  custom domain. Use when the user says "publish my website", "put my page
  online", "deploy my HTML", "host my site for free", "sube mi página web",
  "publicar mi página", "quiero subir mi página a internet", "dónde subo mi
  HTML", "hosting gratis", "free hosting", "custom domain", "dominio propio",
  or has a web page and doesn't know where to put it. For a web app, an API
  or anything with a backend, use /all-deploy instead.
---

# publish-website

Takes a web page from a folder on someone's computer to a public URL, for free, without assuming they have a terminal, a GitHub account, or any money.

Reply in the user's language. Most people reaching this skill are not developers — no jargon without a half-line explanation, and never a command without saying what it does.

## What this skill is not for

If the project has a backend — a database, a login, a server that runs code, an API — stop and say so: *"this isn't a static page, it needs a server."* Point at `/all-deploy`, which handles apps and APIs with a full pre-deploy audit. Trying to squeeze an app onto a static host wastes the user's afternoon.

Signals it's an app, not a page: `package.json` with a `start` script, `requirements.txt`, `Dockerfile`, `main.py`, anything that talks about a port.

## Step 1 — Find the page

Locate what's actually being published: a folder, a single `.html` file, or files Claude generated earlier in this conversation. Confirm the folder that will be uploaded — the one holding the home page.

**The home page must be named exactly `index.html`, lowercase.** Every host serves that name at `/`; `mi-pagina.html` or `Index.html` gives a 404 at the site root. This is the single most common reason a first deploy appears broken. If it's named something else, offer the rename and show it before doing it:

```
mv mi-pagina.html index.html
```

If the site has a build step (Astro, Hugo, Jekyll, Eleventy, MkDocs, Docusaurus, Next with `output: 'export'`), the folder to publish is the build output — `dist/`, `public/`, `_site/`, `site/`, `build/`, `out/` — not the project root. Get this right before anything else; it's the field people fill in wrong in the host's dashboard.

## Step 2 — Check the page

Run the bundled checker if a terminal is available:

```
python3 scripts/static_check.py <folder>
```

If there's no shell — Cowork, or the user just doesn't have one — do the same checks by reading the files. Every one of these breaks a page *after* it goes live, which is why they're worth catching first:

1. **`index.html` at the root of the folder** — otherwise the site root 404s.
2. **Capitalisation of file paths.** `<img src="imagenes/foto.png">` when the file is actually `Imagenes/Foto.PNG`. This works on Mac and Windows — their filesystems ignore capitals — and 404s on every host, which run Linux. The images just don't appear and nothing says why. Compare each `src`/`href` against the real filename, letter by letter.
3. **Paths that point at the user's computer** — `file:///Users/...`, `C:\Users\...`. Usually from dragging an image into the HTML. Blank for everyone else.
4. **References to files that aren't in the folder.**
5. **API keys or passwords in the HTML or JavaScript.** Everything uploaded to a static host is public — there is no such thing as a hidden file. Stripe `pk_` keys and referrer-restricted Google Maps keys are designed to be public and are fine; anything else must come out and be rotated.
6. **Heavy images.** Anything over a few MB means a long wait on phone data.
7. **`<title>`, description, and social preview tags.** Without them the browser tab shows a filename and sharing the link on WhatsApp or Slack produces a blank card that reads as broken. Worth 60 seconds:

```html
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your page name</title>
<meta name="description" content="One sentence about the page.">
<meta property="og:title" content="Your page name">
<meta property="og:description" content="One sentence about the page.">
<meta property="og:image" content="https://your-site/preview.png">
```

Fix items 1–5 before publishing. Show every change before making it — these are the user's files.

## Step 3 — Three questions, asked together

Ask all three at once, not one at a time:

1. **Do you have a GitHub account?** (If they don't know what that is, the answer is no, and that's fine.)
2. **Will you want to change the page later, or is this a one-time thing?**
3. **Do you have your own domain (miempresa.com), or is a free address fine (mipagina.pages.dev)?**

And one more that decides more than any of them:

4. **Is anyone being paid in connection with this page?** Built it for a client, charging for it, selling something on it, running ads? This removes two of the five options outright — see `references/hosts.md`.

## Step 4 — Pick the host

| Situation | Host | Why |
|---|---|---|
| Client's page, or anyone was paid | **Cloudflare Pages** | The only free option with no commercial restriction and no spending cliff |
| Needs a contact form, no backend | **Netlify** | Netlify Forms is free; nothing else here matches it |
| Portfolio, docs, demo, personal | **GitHub Pages** | No new account if they're already on GitHub |
| Personal project built with Next/React/Astro | **Vercel** | Zero-config — but not if money is involved |
| Wants it online right now, no account | **Netlify Drop** | See the caveat below |

**Two things to say out loud before choosing:**

- **Vercel's free plan forbids commercial use, and the definition is broad.** It counts *"receiving payment to create, update, or host the site"* — so a client's page is out even if the page itself sells nothing.
- **Netlify Drop publishes without an account, but the result isn't public.** The URL is password-protected until it's "claimed", and claiming means signing up.

Full comparison, free-tier limits and the exact terms: `references/hosts.md`.

## Step 5 — Publish

Give browser steps by default. Offer commands only if the user has a terminal and wants them.

### Cloudflare Pages — browser

1. Sign up free at `dash.cloudflare.com`.
2. **Workers & Pages → Create → Pages**.
3. To upload a folder: **Upload assets**, name the project, drag the folder in, **Deploy site**.
4. To connect GitHub instead: **Connect to Git**, authorize, pick the repo and branch, then set:
   - **Build command:** leave **empty** for a plain HTML page.
   - **Build output directory:** `/` for a plain page, or the build folder (`dist`, `public`, `_site`).
5. The page is live at `<project>.pages.dev`.

### Netlify — browser

1. Drag the folder onto `app.netlify.com/drop`. It deploys immediately.
2. Sign up to claim it — until then the URL is password-protected.
3. To connect GitHub: **Add new site → Import an existing project**, pick the repo, leave the build command empty for a plain page, set the publish directory.
4. Live at `<site>.netlify.app`.

**Warn about the credit budget:** the free plan is 300 credits a month, a production deploy costs 15, and when they run out the site is *paused* — visitors see "Site not available." Fine for a personal page; a real risk for a client's.

### GitHub Pages — browser

1. At github.com: **New repository**, public.
2. **Add file → Upload files**, drag the folder in, **Commit changes**.
3. **Settings → Pages → Source: Deploy from a branch → `main` / root → Save.**
4. Live at `<username>.github.io/<repo>/` in about a minute. It 404s at first — that's the build, not a failure.

Two traps specific to GitHub Pages:
- Paths starting with `/` break here. The site lives under `/<repo>/`, so `/style.css` goes to the wrong place. Use relative paths (`style.css`).
- If any folder name starts with `_`, add an empty file called `.nojekyll` at the root, or every stylesheet and script silently 404s.

### Commands, if they have a terminal

```bash
# Cloudflare Pages
npx wrangler login
npx wrangler pages deploy <folder> --project-name <name> --branch=main

# Netlify
netlify login
netlify deploy --dir=<folder>            # draft first — free
netlify deploy --prod --dir=<folder>     # this one costs 15 credits
```

## Step 6 — Check it actually works

Open the URL. Then check what a quick glance misses: **the page can load while its stylesheet doesn't.** Open the site and confirm it looks like it did locally — right fonts, images present, layout intact. If it appears as plain unstyled text, it's almost always a capitalisation mismatch (Step 2, item 2) or a `/`-prefixed path on GitHub Pages.

## Step 7 — Custom domain, if they want one

**Be clear about the money:** the hosting is free and stays free. The domain is not — around **$10–15 USD a year**, bought separately at Cloudflare Registrar (sold at cost), Porkbun or Namecheap. None of these hosts includes a domain.

Never buy anything on their behalf. Show what to do and let them do it.

The DNS records per host, apex vs `www`, and what to expect while waiting for the certificate: `references/custom-domain.md`.

## Step 8 — Hand it over

Give them, in plain language:

1. **The URL.**
2. **How to change the page later** — for a folder upload, re-upload it (and keep a copy of what's live, since that's the only way back); for a GitHub-connected site, edit and commit, and it redeploys itself.
3. **What this page can't do**, with the real alternative for each — because finding out after launch is worse:

| They'll want | The answer that keeps it static |
|---|---|
| A contact form | Netlify Forms (free), Formspree, or an embedded Google Form |
| To take payments | A Stripe Payment Link or a Gumroad button — hosted checkout, not code on the page |
| To save what visitors type | A form service. Storing it yourself means a backend |
| To send email | The form service's notification, never from the page itself |
| A login | Not a static page any more — that's `/all-deploy` |

## Bundled files

- `references/hosts.md` — the five free hosts compared, with free-tier limits and the exact commercial-use terms.
- `references/custom-domain.md` — DNS records per host, apex vs `www`, and the waiting.
- `scripts/static_check.py` — the checks from Step 2, deterministic, when a terminal is available.
