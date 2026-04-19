# Target: cloudflared tunnel

Expose a locally-running service to a public URL via Cloudflare's tunnel. No server, no deploy — just a connection from your machine outbound to Cloudflare.

Two modes:
- **Quick tunnel** — zero config, random `trycloudflare.com` URL. For demos, testing webhooks, grabbing a preview URL in seconds. Not for prod.
- **Named tunnel** — persistent, bound to a Cloudflare account, optionally wired to a custom domain. For longer-lived demos or hobby prod.

## Phase 3.5 — prerequisites

```bash
cloudflared --version          # >= 2024.x
```

If missing:
- macOS: `! brew install cloudflared`
- Linux: see `https://pkg.cloudflare.com/`.

For named tunnels:
```bash
cloudflared tunnel list        # empty + prompts login if not authenticated
# If not authenticated:
! cloudflared tunnel login     # opens browser
```

## Quick tunnel (zero config)

Start the local server first (in its own terminal / tool call):
```bash
npm run dev                    # or uvicorn main:app --reload --port 8000, etc.
```

Then in another shell:
```bash
cloudflared tunnel --url http://localhost:8000
```

cloudflared prints a URL line like:
```
+-------------------------------------------------------+
|  Your quick tunnel has been created! Visit it at:     |
|  https://<random-subdomain>.trycloudflare.com         |
+-------------------------------------------------------+
```

Parse:
```bash
TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cloudflared.log | tail -1)
```

Use this as `$PREVIEW_URL` for the health check:
```bash
curl -sSL -o /dev/null -w "%{http_code}" "$TUNNEL_URL"
```

Quick tunnels are **ephemeral** — they die when `cloudflared` exits, and the URL is new each time. Good for: one-off demos, webhook testing (Stripe, GitHub webhooks), screen-sharing a local dev server.

## Named tunnel (persistent)

Create once:
```bash
cloudflared tunnel create all-deploy-demo
# generates a tunnel ID and a credentials JSON at ~/.cloudflared/<tunnel-id>.json
```

Wire to a hostname (requires you own a domain on Cloudflare):
```bash
cloudflared tunnel route dns all-deploy-demo demo.yourdomain.com
```

Write a config:
```yaml
# ~/.cloudflared/config.yml
tunnel: all-deploy-demo
credentials-file: /Users/you/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: demo.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

Run:
```bash
cloudflared tunnel run all-deploy-demo
```

The tunnel is up at `https://demo.yourdomain.com` whenever `cloudflared` is running on your machine.

## Run-locally mode integration

`/all-deploy` run-locally starts the dev server in the foreground (Phases 0, 1, scoped 2, then start). If the user asks to also expose it:

1. Keep the dev server running (already the case).
2. Start `cloudflared tunnel --url http://localhost:<port>` in a separate background task.
3. Extract the trycloudflare URL and surface it.

This is the one place cloud-deploy and run-locally modes meet — a user running locally can share a public URL without committing to a host.

## Phase 4.5 — health check

```bash
curl -sSL -o /dev/null -w "%{http_code}" "$TUNNEL_URL"
```

2xx/3xx → the tunnel is passing traffic correctly.

If the curl fails but `curl http://localhost:8000` works, the issue is usually:
- cloudflared exited (check the log).
- Local service isn't actually listening on the expected port.
- An upstream Cloudflare issue (rare).

## Phase 5 — "prod promotion"

For a quick tunnel, there is no prod. For a named tunnel, the tunnel IS the prod URL — no separate step. The "prod gate" for cloudflared is:

1. Confirm `$TUNNEL_URL` returns 2xx.
2. Share the URL.

If this is being used for webhook reception (Stripe, GitHub), also verify the webhook target has been updated to the tunnel URL on the remote service.

## Phase 6 — post-deploy

- Traffic is only routed while `cloudflared` runs. If the user's laptop sleeps or loses network, the tunnel drops.
- For longer-term exposure, move to Vercel or Railway instead.

## Common pitfalls

- **Quick tunnels are unauthenticated.** Anyone with the URL can hit your local service. For anything sensitive, use a named tunnel with Cloudflare Access policies.
- **Rate limits on the free plan.** Quick tunnels and free Cloudflare accounts have QPS and bandwidth caps. Not suitable for real traffic.
- **Tunnels expose everything at the configured host/port.** If your dev server has an admin panel on `/admin` with no auth, the tunnel exposes it too. Add auth before tunneling a dev server that has admin routes.
- **HMR / WebSockets:** Vite/Next.js HMR uses WebSockets. Cloudflare tunnels support WebSockets, but some dev servers bind the HMR port separately — the tunnel only forwards the main port. HMR may not work over the tunnel.
- **`cloudflared` exits when its parent shell ends.** For longer sessions, run under `nohup`, `tmux`, or `launchctl`.

## When to choose cloudflared over a real deploy

Use cloudflared when:
- You need a URL for <24h (demo, test webhook, mobile device on your home wifi).
- You don't want to deploy yet — you want to iterate locally but share a URL.
- The project isn't ready for audit (no lockfile, secrets still in code, etc.) — cloudflared bypasses the cloud-deploy audit since it's a local exposure.

Use Vercel/Railway/docker-vps when:
- The URL should survive your laptop closing.
- Real users will hit the service.
- You need env vars, logs, rollback, and the other production affordances.
