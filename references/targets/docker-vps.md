# Target: Docker + SSH VPS

Self-hosted deployment to a Linux server you control. Good for stateful workloads, multi-service compose stacks, workloads with custom system deps, or when you've already got a VPS.

Assumes: a Linux VPS with `docker` + `docker compose` installed, SSH access via key (not password), a non-root user with docker-group membership.

## Phase 3.5 — prerequisites

```bash
# Local:
docker --version                                    # confirm docker CLI (for build)
ssh -o BatchMode=yes -o ConnectTimeout=5 user@host true   # confirm key auth works

# Remote (via ssh):
ssh user@host 'docker --version && docker compose version'
```

If SSH fails: point the user at their SSH config (`~/.ssh/config`) and key setup. Do not attempt automated key provisioning.

## Project shape

Expect either:

- **Single-service:** `Dockerfile` at the project root. Run as `docker run` or `docker compose up`.
- **Multi-service stack:** `docker-compose.yml` at the root defining `app`, optional `db`, `redis`, `nginx`, etc.

If neither is present, scaffold from `assets/templates/`:
- `assets/templates/Dockerfile.node` — for Node apps.
- `assets/templates/Dockerfile.python` — for Python apps.
- `assets/templates/docker-compose.example.yml` — starting point.

**Show the diff before applying** per Hard Rule 6.

## Phase 4 — build + transfer + deploy

The typical flow:

### Option A — build on the VPS (simplest)

```bash
# Sync project to the host (excluding git/node_modules/etc.):
rsync -az --delete \
  --exclude=.git --exclude=node_modules --exclude=.venv \
  --exclude=dist --exclude=.next --exclude=.vercel \
  ./ user@host:/app/

# Push env:
scp .env.production user@host:/app/.env

# Build + start:
ssh user@host 'cd /app && docker compose up -d --build --pull=always'
```

### Option B — build locally, push image

```bash
# Build:
docker build -t myapp:$(git rev-parse --short HEAD) .

# Tag for a registry (Docker Hub, GHCR, or your private one):
docker tag myapp:<sha> ghcr.io/<user>/myapp:<sha>
docker push ghcr.io/<user>/myapp:<sha>

# Pull + run on the VPS:
ssh user@host "docker pull ghcr.io/<user>/myapp:<sha> && docker tag ghcr.io/<user>/myapp:<sha> myapp:latest && cd /app && docker compose up -d"
```

Option B keeps secrets (build-time tokens) off the VPS and makes rollback to a prior image one `docker tag` away.

### Env delivery

Docker Compose reads env from:
1. The `environment:` block in `docker-compose.yml` (hardcoded).
2. A `.env` file next to `docker-compose.yml` (variable substitution).
3. Host shell env.

Typical production layout:
```yaml
# docker-compose.yml (committed)
services:
  app:
    image: myapp:latest
    restart: unless-stopped
    ports: ["3000:3000"]
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - STRIPE_SECRET=${STRIPE_SECRET}
```

```
# .env (NEVER committed — scp'd to the host)
DATABASE_URL=postgres://...
STRIPE_SECRET=sk_live_...
```

Verify env is wired:
```bash
ssh user@host 'cd /app && docker compose config | grep -v "password\|secret\|key" | head -30'
```

(`docker compose config` prints the fully-resolved compose — redact secrets before reviewing.)

## Phase 4.5 — health check

If you know the port + path the service exposes:
```bash
PREVIEW_URL="http://<host-or-ip>:<port>"
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
```

If the service is behind a reverse proxy (Caddy, nginx, Traefik), hit the proxy's hostname:
```bash
PREVIEW_URL="https://<your-domain>"
curl -sSL -o /dev/null -w "%{http_code}" "$PREVIEW_URL"
```

For compose stacks, confirm all services are healthy:
```bash
ssh user@host 'cd /app && docker compose ps'
# STATUS column should show "Up" or "healthy" for every service.
```

## Phase 5 — prod promotion

For docker-vps, there is typically no "preview vs prod" split on a single VPS — the deploy IS prod. The safeguard is:

1. **Deploy to a staging stack first** if the VPS has the capacity (docker-compose with a different project name / port).
2. Confirm health.
3. Deploy to the production stack.

For single-VPS single-env flows, Phase 4.5 health check is the gate. The Phase 5 "5-second pause" still applies — after confirming preview health, give the user the chance to abort before the compose-up that replaces the current container.

## Phase 6 — post-deploy

```bash
ssh user@host 'cd /app && docker compose ps && docker compose logs --tail=50 app'
```

**Rollback:**
```bash
# If you used tagged images (Option B above):
ssh user@host 'cd /app && docker tag myapp:<previous-sha> myapp:latest && docker compose up -d --no-deps app'

# If you built on the VPS:
# Re-rsync from a prior git SHA:
git checkout <previous-sha>
rsync -az --delete ... user@host:/app/
ssh user@host 'cd /app && docker compose up -d --build'
git checkout -
```

**Logs:**
```bash
ssh user@host 'cd /app && docker compose logs -f app'
```

## Common pitfalls

- **`.env` file not on the host:** containers start, silently use empty strings, app crashes at first request. `scp .env` before `docker compose up -d`.
- **Permission issues:** the user running docker must be in the `docker` group, or use `sudo docker`. `usermod -aG docker $USER` + logout/login.
- **Disk full:** old Docker images accumulate. Periodic `docker system prune -af` on the VPS.
- **Firewall:** the port exposed in `docker-compose.yml` must also be open in the VPS firewall (`ufw allow 3000`, etc.) and the cloud provider's security group.
- **No reverse proxy + no HTTPS:** production traffic should terminate TLS at a proxy (Caddy is simplest). Not covered in v1 — document the need but don't configure it automatically.
- **Backups:** volumes (`/var/lib/docker/volumes/...`) are not backed up by default. For DB volumes, set up `pg_dump` + rsync-to-backup-host.
