# Pointing your own domain at a free static host

The hosting is free. The domain is not. This file covers the part where people get stuck: which DNS record to create, where, and why the site is still not working twenty minutes later.

Verified against provider documentation on 2026-09-19. Record targets change — confirm against the host's dashboard, which always shows the current value for your specific project.

## Buy the domain first

None of the five free static hosts registers a domain on a free plan. Expect **$10–15 USD/year**. Reasonable registrars: **Cloudflare Registrar** (sells at wholesale cost, no markup, but requires using Cloudflare DNS), **Porkbun**, **Namecheap**.

Never buy on the user's behalf. Show them where and what it costs, and let them do it.

## Apex vs `www` — the thing nobody explains

```
miempresa.com          <- the apex (also called root, naked, or bare domain)
www.miempresa.com      <- a subdomain
```

DNS was designed so a subdomain can be a `CNAME` pointing at another name, and the apex **cannot** — the apex has to hold records the zone itself needs, and a CNAME is not allowed to coexist with them. That single rule is why every host has one easy answer for `www` and a fiddlier one for the apex.

Three ways hosts work around it:

1. **Flattened CNAME / ALIAS / ANAME** — a provider-side fake CNAME at the apex. Cloudflare, Netlify and Render all support this. Best option when available, because the target can change without you touching DNS.
2. **Plain `A` records** — a fixed IP list. What GitHub Pages uses. Works everywhere, but if the host ever changes IPs, your site goes down until you update them.
3. **Redirect** — point the apex at `www` (or the reverse) and serve from one canonical name. Pick one and redirect the other; serving both is bad for SEO and confusing to debug.

## Records per host

Create these at your **DNS provider** (wherever the domain's nameservers point — the registrar, or Cloudflare if you moved them there), then add the domain in the host's dashboard. Both halves are required: the DNS record routes traffic, and the dashboard entry tells the host to answer for that name and issue a certificate for it.

### Cloudflare Pages

| Purpose | Type | Name | Value |
|---|---|---|---|
| Apex | — | — | The domain must be on **Cloudflare nameservers**; Cloudflare creates the flattened CNAME itself when you add the custom domain |
| `www` | `CNAME` | `www` | `<PROJECT>.pages.dev` |

There is no A-record path for the apex. If the domain is registered elsewhere, move its nameservers to Cloudflare (free) or use `www` only.

### Netlify (external DNS)

| Purpose | Type | Name | Value |
|---|---|---|---|
| Apex, preferred | `ALIAS` / `ANAME` / flattened `CNAME` | `@` (or empty) | `apex-loadbalancer.netlify.com` |
| Apex, fallback | `A` | `@` (or empty) | `75.2.60.5` |
| `www` | `CNAME` | `www` | `<SITE>.netlify.app` |

Use the `A` record only if the provider supports none of ALIAS/ANAME/flattened CNAME.

### GitHub Pages

| Purpose | Type | Name | Value |
|---|---|---|---|
| Apex | `A` | `@` | `185.199.108.153` |
| Apex | `A` | `@` | `185.199.109.153` |
| Apex | `A` | `@` | `185.199.110.153` |
| Apex | `A` | `@` | `185.199.111.153` |
| Apex (IPv6) | `AAAA` | `@` | `2606:50c0:8000::153` |
| Apex (IPv6) | `AAAA` | `@` | `2606:50c0:8001::153` |
| Apex (IPv6) | `AAAA` | `@` | `2606:50c0:8002::153` |
| Apex (IPv6) | `AAAA` | `@` | `2606:50c0:8003::153` |
| `www` | `CNAME` | `www` | `<USERNAME>.github.io` |

**All four A records, not one.** And the `www` CNAME points at `<USERNAME>.github.io` — **without the repository name appended**. Adding `/repo` or `username.github.io/repo` is the single most common GitHub Pages misconfiguration.

GitHub Pages also needs a `CNAME` file at the repo root containing the bare domain. The Pages settings UI creates and commits it for you; if you add it by hand, it holds one line and no protocol:

```
miempresa.com
```

Check DNS from GitHub's side: `gh api repos/{owner}/{repo}/pages/health`

### Render

| Purpose | Type | Name | Value |
|---|---|---|---|
| Apex, preferred | `ANAME` / `ALIAS` | `@` | `<SERVICE>.onrender.com` |
| Apex, fallback | `A` | `@` | `216.24.57.1` |
| `www` | `CNAME` | `www` | `<SERVICE>.onrender.com` |

**Delete any `AAAA` records** on the domain. Render is IPv4-only, and a leftover AAAA makes the site fail for IPv6 clients in a way that looks intermittent and random. Free plan includes **2** custom domains.

### Vercel

Vercel's dashboard prints the exact record for your project when you add the domain — use what it shows rather than a value memorised from a guide, because it varies by account and region. `www` is always a `CNAME`.

## After you add the records

Three waits, in order. People give up during the second one.

1. **DNS propagation** — usually minutes, up to 48 hours in the worst case, and mostly determined by the TTL of whatever record was there before. Check what the world actually sees, not what your browser cached:
   ```bash
   dig +short miempresa.com
   dig +short www.miempresa.com
   ```
2. **Certificate issuance** — the host requests a TLS certificate only *after* DNS resolves to it. Expect a few minutes; up to an hour is normal. During this window the site is reachable over HTTP and throws a certificate warning over HTTPS. **This is not a broken deploy.** Do not start changing records.
3. **Enforce HTTPS** — once the certificate is issued, turn on the host's "always use HTTPS" / "enforce HTTPS" toggle. On GitHub Pages it is a checkbox in *Settings → Pages* that stays greyed out until the certificate exists.

```bash
curl -sSL -o /dev/null -w "%{http_code}\n" https://miempresa.com
curl -sSL -o /dev/null -w "%{http_code}\n" https://www.miempresa.com
```

Both should return 2xx or 3xx. A 3xx on one of them is correct if you set up the apex↔`www` redirect.

## Common failures

- **Certificate warning right after setup.** Almost always waiting on issuance, not a misconfiguration. Wait an hour before touching anything.
- **`www` works, apex doesn't** — no ALIAS/ANAME support at the provider and no A records added. Use the fallback IP, or move DNS to a provider that supports ALIAS.
- **Apex works, `www` doesn't** — the CNAME is missing, or the host's dashboard only has the apex registered. Add both names in the dashboard, not just the one.
- **A stale `A` record from an old host** still in the zone. Delete everything pointing at the previous setup; two conflicting A records means traffic goes to both, at random.
- **Cloudflare proxy (orange cloud) in front of a non-Cloudflare host.** Usually fine, sometimes causes a redirect loop when the host also forces HTTPS. If the loop appears, set Cloudflare's SSL mode to **Full (strict)** or switch the record to DNS-only (grey cloud).
- **Editing DNS at the registrar when the nameservers point somewhere else.** The records have to live wherever the nameservers point. Check with `dig +short NS miempresa.com` before editing anything.
- **Forgetting the dashboard half.** A perfect DNS record with no matching custom domain in the host's project gets you the host's generic 404, not your site.
