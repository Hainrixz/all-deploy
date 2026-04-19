# Contributing to `/all-deploy`

**[English](#english)  ·  [Español](#español)**

---

## English

Thanks for your interest in contributing. This skill is part of the [Tododeia](https://tododeia.com) community — built by [@soyenriquerocha](https://instagram.com/soyenriquerocha), maintained collaboratively.

### Good first contributions

| Type | Where | Size |
|---|---|---|
| **Add a deploy target** (Netlify, Fly, Modal, Render, HF Spaces, Cloudflare Pages) | `references/targets/<target>.md` | ~150–200 lines |
| **Extend secret patterns** (new API key format — Anthropic, OpenAI, etc.) | `scripts/audit.py` `SECRET_PATTERNS` dict | 1–2 lines + a test fixture |
| **Improve framework detection** | `references/project-types.md` + `SKILL.md` Phase 1 | 1 table row |
| **Improve Spanish copy in the README or CONTRIBUTING** | `README.md`, `CONTRIBUTING.md` | varies |
| **Fix a documented CLI staleness** (Railway / Vercel syntax changed) | Relevant `references/targets/*.md` | 1–2 lines |

### Dev setup

```bash
git clone https://github.com/Hainrixz/all-deploy.git
cd all-deploy

# Symlink into your Claude Code skills directory so changes are live immediately:
ln -s "$(pwd)" ~/.claude/skills/all-deploy
```

Every edit to `SKILL.md`, `scripts/`, `references/`, or `assets/` is visible in Claude Code on the next invocation. No rebuild needed.

### Running tests

```bash
# Validate SKILL.md frontmatter + structure:
python3 tests/validate_skill.py .

# Syntax-check scripts:
python3 -m py_compile scripts/audit.py scripts/env_extract.py

# Run audit fixtures:
python3 -m pytest tests/ -v
```

CI runs the same checks on every pull request (see `.github/workflows/ci.yml`).

### Adding a new deploy target

The target reference is a playbook. Follow the structure used by the four existing references (`references/targets/vercel.md`, `railway.md`, `docker-vps.md`, `cloudflared-tunnel.md`):

1. **Phase 3.5 — Prerequisites** — CLI install + auth command (`! <cmd>`).
2. **Link existing vs create new** — how to reuse a linked project.
3. **Phase 4 — Env delivery** — the exact CLI to push env vars.
4. **Phase 4 — Preview deploy** — the command + how to parse the preview URL from stdout.
5. **Phase 4.5 — Health check** — the curl probe (or equivalent for non-HTTP targets).
6. **Phase 5 — Prod promotion** — the command + cost notes.
7. **Phase 6 — Post-deploy** — rollback command + log-tail command.
8. **Common pitfalls** — things that bite users.

Keep it under ~200 lines. Don't wrap the target CLI in a custom script — document the real command so users can read and verify (Hard Rule 5).

Also update `references/project-types.md` and the target-selection rubric in `SKILL.md` so the new target gets ranked when signals match.

### Extending audit checks

`scripts/audit.py` uses a strict Finding pattern:

```python
self.findings.append(Finding(
    "critical",                     # or "warn"
    "check.name",                   # dotted short identifier
    "Human-readable description.",
    fix="Exact steps the user should take.",
    location="path/to/offending/file",  # optional
))
```

When adding a check:
- **Exit code 1** on any `critical` finding.
- **Never** print secret values — only the pattern name and file path.
- Add a fixture test under `tests/test_audit.py` that confirms the check fires on bad input and passes clean input.

### Pull request checklist

Before opening a PR, confirm:

- [ ] `python3 tests/validate_skill.py .` passes.
- [ ] `python3 -m pytest tests/` passes.
- [ ] You've updated `SKILL.md`, the relevant reference, and any impacted template — all three stay in sync.
- [ ] No hardcoded paths (use skill-relative references).
- [ ] No secrets in commits (check `git log -p` before pushing).
- [ ] README / CONTRIBUTING updated if behavior changes.

### Commit message convention

Short imperative:
```
feat(targets): add Netlify reference
fix(audit): correct OpenAI key regex for sk-proj keys
docs(readme): fix install path in Spanish section
```

### Need help?

- Open an issue — bugs and target requests have templates.
- Join the [Tododeia community](https://tododeia.com).
- Ping [@soyenriquerocha](https://instagram.com/soyenriquerocha) on Instagram.

---

## Español

Gracias por tu interés en contribuir. Este skill es parte de la comunidad [Tododeia](https://tododeia.com) — creado por [@soyenriquerocha](https://instagram.com/soyenriquerocha), mantenido en colaboración.

### Buenas primeras contribuciones

| Tipo | Dónde | Tamaño |
|---|---|---|
| **Agregar un target de deploy** (Netlify, Fly, Modal, Render, HF Spaces, Cloudflare Pages) | `references/targets/<target>.md` | ~150–200 líneas |
| **Extender patrones de secretos** (nuevo formato de API key) | `scripts/audit.py` dict `SECRET_PATTERNS` | 1–2 líneas + un fixture |
| **Mejorar detección de frameworks** | `references/project-types.md` + `SKILL.md` Fase 1 | 1 fila de tabla |
| **Mejorar la copia en español del README o CONTRIBUTING** | `README.md`, `CONTRIBUTING.md` | variable |
| **Corregir un comando de CLI desactualizado** (Railway / Vercel cambió sintaxis) | `references/targets/*.md` relevante | 1–2 líneas |

### Setup de desarrollo

```bash
git clone https://github.com/Hainrixz/all-deploy.git
cd all-deploy

# Symlink al directorio de skills de Claude Code para ver cambios en vivo:
ln -s "$(pwd)" ~/.claude/skills/all-deploy
```

Cada edición a `SKILL.md`, `scripts/`, `references/`, o `assets/` es visible en Claude Code en la siguiente invocación. No hay paso de build.

### Correr los tests

```bash
# Validar frontmatter + estructura de SKILL.md:
python3 tests/validate_skill.py .

# Syntax-check de scripts:
python3 -m py_compile scripts/audit.py scripts/env_extract.py

# Correr fixtures del audit:
python3 -m pytest tests/ -v
```

CI corre los mismos checks en cada pull request (ver `.github/workflows/ci.yml`).

### Agregar un target nuevo

La referencia del target es un playbook. Sigue la estructura de las cuatro existentes (`references/targets/vercel.md`, `railway.md`, `docker-vps.md`, `cloudflared-tunnel.md`):

1. **Fase 3.5 — Prerrequisitos** — comando de instalación del CLI + auth (`! <cmd>`).
2. **Linkear existente vs crear nuevo** — cómo reusar un proyecto ya linkeado.
3. **Fase 4 — Entrega de env** — el comando exacto para empujar env vars.
4. **Fase 4 — Preview deploy** — el comando + cómo parsear la URL de preview del stdout.
5. **Fase 4.5 — Health check** — la probe con curl (o equivalente para targets no-HTTP).
6. **Fase 5 — Promoción a prod** — el comando + notas de costo.
7. **Fase 6 — Post-deploy** — comando de rollback + comando de log-tail.
8. **Problemas comunes** — cosas que muerden a los usuarios.

Mantén bajo ~200 líneas. No envuelvas el CLI en un script propio — documenta el comando real para que los usuarios puedan leerlo y verificarlo (Regla dura 5).

También actualiza `references/project-types.md` y el ranking de selección de target en `SKILL.md` para que el nuevo target aparezca cuando las señales coincidan.

### Extender checks del audit

`scripts/audit.py` usa un patrón estricto de Finding:

```python
self.findings.append(Finding(
    "critical",                     # o "warn"
    "check.name",                   # identificador corto con puntos
    "Descripción legible para humanos.",
    fix="Pasos exactos que el usuario debe seguir.",
    location="path/to/offending/file",  # opcional
))
```

Al agregar un check:
- **Exit code 1** con cualquier finding `critical`.
- **Nunca** imprimir valores de secretos — solo el nombre del patrón y la ruta del archivo.
- Agrega un fixture de test bajo `tests/test_audit.py` que confirme que el check dispara con input malo y pasa con input limpio.

### Checklist de pull request

Antes de abrir un PR, confirma:

- [ ] `python3 tests/validate_skill.py .` pasa.
- [ ] `python3 -m pytest tests/` pasa.
- [ ] Actualizaste `SKILL.md`, la referencia relevante, y el template afectado — los tres quedan en sync.
- [ ] No hay paths hardcodeados (usa referencias relativas al skill).
- [ ] No hay secretos en los commits (revisa `git log -p` antes de pushear).
- [ ] README / CONTRIBUTING actualizado si el comportamiento cambia.

### Convención de commits

Imperativo corto:
```
feat(targets): agregar referencia de Netlify
fix(audit): corregir regex de OpenAI para keys sk-proj
docs(readme): arreglar ruta de instalación en la sección en español
```

### ¿Necesitas ayuda?

- Abre un issue — bugs y solicitudes de target tienen templates.
- Únete a la [comunidad Tododeia](https://tododeia.com).
- Escríbeme a [@soyenriquerocha](https://instagram.com/soyenriquerocha) en Instagram.
