# Free static hosting — which one, and why

Five hosts will put a web page online for free, keep it there, give it HTTPS and let you point your own domain at it. They are not interchangeable. Read this in Phase 3, before presenting candidates.

Verified against provider documentation on 2026-09-19. Limits and terms drift — every playbook links its provider's live page, and nothing here should be quoted back to a user as permanent.

## The question that decides it

**"Is anyone being paid in connection with this page?"**

Ask it first, because it eliminates two of the five outright, and it is not obvious — two hosts restrict commercial use, and one of them defines it far more broadly than people expect.

| Host | Commercial use | The actual wording |
|---|---|---|
| **Cloudflare Pages** | **Allowed** | No commercial restriction in the free plan terms |
| **Netlify** | **Allowed** | No commercial restriction; the constraint is the credit budget |
| **Render** | **Allowed** | No commercial restriction; the constraint is 5 GB/month |
| **GitHub Pages** | **Restricted** | *"not intended for or allowed to be used as a free web-hosting service to run your online business, e-commerce site, or any other website that is **primarily directed at** either facilitating commercial transactions or providing commercial software as a service (SaaS)"* |
| **Vercel (Hobby)** | **Prohibited** | *"Commercial usage is defined as any Deployment that is used for the purpose of financial gain of **anyone** involved in **any part of the production** of the project, **including a paid employee or consultant writing the code**"* |

Two consequences worth stating plainly to the user:

- **Vercel Hobby is out the moment someone is paid to build the page** — even if the page itself sells nothing, carries no ads and takes no payments. Vercel lists *"receiving payment to create, update, or host the site"* as commercial usage. Asking for donations is explicitly **not** commercial.
- **GitHub Pages is softer.** "Primarily directed at" means a brochure or portfolio site for a business is generally fine; a storefront, a checkout, or a SaaS app is not.

## The comparison

| | Cloudflare Pages | Netlify | GitHub Pages | Render | Vercel (Hobby) |
|---|---|---|---|---|---|
| Free subdomain | `*.pages.dev` | `*.netlify.app` | `*.github.io` | `*.onrender.com` | `*.vercel.app` |
| Custom domain | Yes, 100/project | Yes | Yes | Yes, **2** on free | Yes, 50/project |
| Free TLS | Yes | Yes | Yes | Yes | Yes |
| Push-to-deploy from GitHub | Yes (dashboard setup) | Yes | Native | Yes | Yes |
| Works with **no** git repo | Yes (direct upload) | Yes (Drop) | No | No | Yes (CLI) |
| Preview deploys | Unlimited | Free (don't cost credits) | **None** | PR previews | Yes |
| Bandwidth | Not published; static requests *"free and unlimited"* | 20 credits/GB out of 300/mo | 100 GB/mo (**soft**) | **5 GB/mo**, then $0.15/GB | 100 GB/mo |
| Hard stop when exceeded | — | **Site paused**, "Site not available" | Soft limit | Billed overage | Feature cut off ~30 days |
| Rollback | Dashboard only | Dashboard, instant | `git revert` | Dashboard, last 2 only | `vercel rollback` |
| Notable extra | Unlimited static requests | **Forms, free** | Zero new accounts | — | Zero-config frameworks |

## Choosing

| Situation | Pick | Why |
|---|---|---|
| A client's page, or anyone was paid | **Cloudflare Pages** | The only one with no commercial restriction *and* no spend cliff |
| Needs a contact form, no backend | **Netlify** | Netlify Forms is free and nothing else on this list matches it |
| Portfolio, docs, demo, personal | **GitHub Pages** | No new account, no new dashboard, it's already where the code is |
| Built with Next / React / Astro, personal project | **Vercel** | Zero-config — but not if money is involved anywhere |
| Wants it online in the next two minutes, no account | **Netlify Drop** | With the caveat below |
| Low-traffic internal or personal site, already on Render | **Render** | Fine at that scale; 5 GB goes fast otherwise |

### Two caveats to state out loud

- **Netlify Drop publishes without an account, but the result is not public.** Netlify's quickstart: *"your project URL is protected with a temporary password until you claim it."* Claiming means signing up. So the honest version is "you can publish without an account, but to show it to anyone you'll need one."
- **Netlify's free plan pauses the site when credits run out.** 300 credits/month, a production deploy costs 15, bandwidth 20/GB, nothing rolls over. Roughly 20 deploys *and nothing else*. For a site somebody is relying on, that is a real risk — say so before recommending it.

## The domain is not free

Every one of the five gives you a free subdomain and free TLS, and every one lets you attach a domain you already own at no extra hosting cost. **None of them registers a domain for you on a free plan.** Expect **$10–15 USD/year** at Cloudflare Registrar (sold at cost), Namecheap or Porkbun.

The split worth drawing for someone who has never done this:

```
Hosting:  free      https://mi-proyecto.pages.dev
Domain:   ~$12/yr   https://miempresa.com        <- this is the part you pay for
```

Vercel's free-first-year domain offer exists but is **Pro-only**, and explicitly not available during the Pro trial.

DNS records per host: `custom-domain.md`.

## Also worth knowing (not shipped as targets)

- **Cloudflare Workers with static assets** — Cloudflare's own recommendation for new projects: *"Start new projects with Workers."* Same free static-asset serving as Pages. Covered at the bottom of the all-deploy skill's Cloudflare Pages playbook.
- **Deno Deploy** — generous free tier and a notably high custom-domain allowance. No commercial-use restriction found. A reasonable sixth option if the others don't fit.
- **Surge.sh** — the shortest path that exists if you live in a terminal: `surge ./dist my-name.surge.sh`. Redirects, password protection and CORS are paid.
- **Bunny.net is not free.** It is an excellent cheap CDN (~$0.01/GB, $1/month minimum), but it does not belong in a free-tier comparison and shouldn't be offered as one.

## What none of them can do

A static host serves files. It does not run code on the server. That means the page **cannot**:

- take a payment, or hold any key that could take one
- store what a visitor typed anywhere
- send an email
- keep a secret of any kind — see SKILL.md, step 2

Each of those has a real answer that keeps the site static (a form service, a payment link, a third-party widget), and at some point the honest answer is that it isn't a static site any more and needs the normal `/all-deploy` app pipeline. Say which one applies rather than letting someone discover the limit after launch.
