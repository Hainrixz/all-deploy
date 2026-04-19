# Pre-deploy audit checklist

Every check performed by `scripts/audit.py`, with the "what," "why," and "how to fix." Use this to explain audit failures to the user, or to walk through checks manually.

Severity levels:
- **critical** — blocks the deploy. Must be resolved (or audit flag added) before Phase 4.
- **warn** — surfaced but does not block. Fix when convenient.

---

## Secret checks

### `secret.env-tracked` (critical)

**What:** Any of `.env`, `.env.local`, `.env.production`, `.env.development`, `.env.staging`, `.env.test` is tracked by git.

**Why:** Committed env files leak credentials to anyone with read access to the repo, forever, in the git history.

**Fix:**
1. `git rm --cached <file>` — remove from the index while keeping the local file.
2. Add to `.gitignore`.
3. **Rotate every value in the file** — assume they're already compromised.
4. Rewrite history with `trufflehog git file://.` or `git-filter-repo --path <file> --invert-paths` to purge the file from all prior commits.

Allowed env files: `.env.example`, `.env.sample`, `.env.vault` (dotenv-vault encrypted), `.envrc` (direnv).

### `secret.<pattern>` (critical, one per pattern per file)

**What:** A known credential pattern matches in a non-binary, non-allowlisted source file. Patterns covered:
- AWS access key (`AKIA...`)
- Stripe live/test/publishable keys (`sk_live_`, `sk_test_`, `pk_live_`)
- OpenAI keys (`sk-...` 48 chars; `sk-proj-...`)
- Anthropic keys (`sk-ant-api03-...`)
- GitHub tokens (`ghp_`, `github_pat_`, `gho_`)
- Google API keys (`AIza...`), OAuth tokens (`ya29.`)
- Slack tokens (`xoxb-`, `xoxp-`)
- SSH private key blocks (`-----BEGIN ... PRIVATE KEY-----`)
- JWTs (`eyJ...eyJ...` three-part)

**Why:** Any of these in a tracked source file means the credential is shared with every repo viewer.

**Fix:** Same as `secret.env-tracked` — remove from source, rotate the credential, rewrite history, and load via environment variable instead.

**Note:** audit reports all distinct pattern types per file (no single-per-file dedup), so a `.env.production` containing AWS + Stripe + DB URL surfaces all three in one run.

---

## Git-hygiene checks

### `gitignore.missing` (critical)

`.gitignore` does not exist. Even if the repo is currently clean, future commits will leak. Create one covering `.env`, `node_modules`, `__pycache__`, `dist`, `.next`, `.venv`, `.vercel`.

### `gitignore.incomplete` (warn, one per missing entry)

`.gitignore` exists but omits a recommended entry. Append the entries listed in the finding.

### `git.dirty` (critical)

Tracked files have uncommitted changes (detected via `git diff-index --quiet HEAD --`, which correctly ignores untracked files). Deploying from a dirty tree makes rollback harder — if prod breaks and you `git checkout HEAD~1`, the dirty changes are lost.

**Fix options:**
- `git add` + `git commit` the changes.
- `git stash` to set aside and restore post-deploy.
- Re-run audit with `--allow-dirty` to proceed anyway.

### `git.untracked` (warn)

Untracked files exist. Not a block — common during iteration — but worth noting. Normal for the recovery flow where the audit has just asked the user to create a new `.env.example`.

### `git.remote.missing` (critical, skippable via `--skip-remote`)

`git remote -v` returns empty. Cloud deploys expect a remote. Add one with `git remote add origin <url>`. Skip this check for docker-vps deploys that don't use a remote.

---

## Lockfile checks

### `lockfile.missing.node` (critical)

`package.json` exists but no lockfile (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, or `bun.lockb`). Installs on the remote will pull non-reproducible versions — deploy-time builds may succeed locally and fail in prod.

**Fix:** run `npm install` / `pnpm install` / `yarn` / `bun install` locally and commit the generated lockfile.

### `lockfile.missing.python` (warn)

Python project (`pyproject.toml` or `Pipfile`) exists but no lockfile. Pinned `requirements.txt` also counts.

**Fix:** `uv lock` / `poetry lock` / `pipenv lock`, or pin in `requirements.txt`.

---

## Env-var completeness

### `env.example.missing` (critical)

Code reads env vars (detected by `scripts/env_extract.py`), but neither `.env.example` nor `.env.sample` exists. New contributors can't configure the project, and there's no manifest for which vars to set on the remote.

**Fix:** create `.env.example` with all keys listed in the finding. Leave values empty (`KEY=`) or use placeholder text.

### `env.example.incomplete` (critical)

`.env.example` (or `.env.sample`) exists but is missing keys the code reads. Deploy will succeed but the app will crash at runtime on missing config.

**Fix:** append the missing keys.

---

## Start-command checks

### `start-command.missing.node` (warn)

`package.json` has no `start`, `dev`, or `build` script. Most hosts run `npm start` by default; without it, the remote has no idea how to launch the service.

**Fix:** add `"scripts": { "start": "node server.js" }` (or the equivalent for your framework).

### `start-command.missing.python` (warn)

Python project with no `[project.scripts]`, no `Procfile`, and no `main.py` with `__main__` or an HTTP framework instance.

**Fix (Railway-style):** add a `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Or declare an entry point in `pyproject.toml`:
```toml
[project.scripts]
myapp = "myapp.main:app"
```

---

## Runtime-version pinning

### `runtime.missing.node` (warn)

Neither `.nvmrc`, `.node-version`, nor `engines.node` in `package.json`. Remote picks an unknown version; your local 22.x might deploy as a 18.x and hit syntax errors.

**Fix:** `echo 'lts/*' > .nvmrc` or set `"engines": { "node": ">=20" }` in `package.json`.

### `runtime.missing.python` (warn)

Neither `.python-version` nor `requires-python` in `pyproject.toml`.

**Fix:** `echo '3.12' > .python-version` or add `requires-python = ">=3.11"` under `[project]` in `pyproject.toml`.

---

## Runtime binding

### `port-binding.localhost-only` (warn)

Source binds `localhost` / `127.0.0.1` without any `0.0.0.0` binding. Works locally; fails on Railway, Fly, and any Docker container.

**Fix:** bind to `0.0.0.0`. For Python: `uvicorn main:app --host 0.0.0.0 --port $PORT`. For Node: `server.listen(process.env.PORT, "0.0.0.0")`.

---

## Known-CVE checks

### `cve.npm.critical` (critical)

`npm audit --production --audit-level=high --json` reports one or more critical-severity vulnerabilities in runtime dependencies.

**Fix:** `npm audit fix`, or manually upgrade the vulnerable package(s). If the fix isn't available, evaluate the impact and decide whether to proceed with `--skip-cve`.

### `cve.npm.high` (warn)

High-severity vulnerabilities. Fix when convenient.

### `cve.python` (critical)

`pip-audit` reports one or more vulnerable Python packages. Python vulnerabilities are treated as critical (pip-audit's default threshold is already conservative).

**Fix:** upgrade the listed packages. Run `pip-audit` without `--format json` to see details. Use `--skip-cve` to bypass if you've evaluated the risk.

---

## Manual checks (not in audit.py)

### Git-history secret scan (recommended — not automated)

The audit scans **tracked files** only. Secrets that were committed in prior commits and later removed still live in history. Before publishing a repo publicly, run one of:

```
trufflehog git file://.
git-secrets --scan-history
git log -p -S 'sk_' -S 'AKIA' -S 'ghp_' -- .
```

If you find leaked secrets in history, rewrite with `git-filter-repo --replace-text` and **rotate every affected credential**.

### Healthcheck endpoint (recommended)

Long-running services benefit from a `/health` or `/healthz` endpoint that returns 200. Railway and Fly can use it for auto-restart; the preview-URL probe in Phase 4.5 uses the root URL by default — if your root redirects or requires auth, configure Phase 4.5 to probe the health endpoint instead.

### Free-tier limits (target-specific)

Each target reference documents current free-tier caps. Not an audit check (limits change).
