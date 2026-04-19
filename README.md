<div align="center">

# `/all-deploy`

**The Claude Code skill that deploys any project to the internet — with a strict safety audit built in.**

🌐 [tododeia.com](https://tododeia.com)  ·  📸 [@soyenriquerocha](https://instagram.com/soyenriquerocha)  ·  📦 [Latest release](https://github.com/Hainrixz/all-deploy/releases/latest)

**[English](#english)  ·  [Español](#español)**

</div>

---

## English

### What it does

One command — `/all-deploy` — takes your project from "it runs on my laptop" to "it's live on the internet."

It walks through six phases every time:

1. **Detects** your framework (Next.js, FastAPI, Docker, static site — whatever you have).
2. **Audits** your code for leaked secrets, missing config, vulnerable dependencies, and other deploy blockers.
3. **Picks the best host** (Vercel, Railway, Docker+VPS, or a cloudflared tunnel).
4. **Deploys a preview first** and curls the URL to confirm the app actually works.
5. **Promotes to production** only after the preview is green (with a 5-second ESC window, or an explicit "yes" if you chose step-by-step).
6. **Hands you the rollback and log commands** so you're not stranded if something breaks later.

A **run-locally** mode runs the same audit and then starts the app on your own machine, optionally exposed through a cloudflared tunnel for a temporary public URL.

### Install (30 seconds)

```bash
git clone https://github.com/Hainrixz/all-deploy.git ~/.claude/skills/all-deploy
```

That's it. `/all-deploy` now works inside Claude Code.

To update later: `cd ~/.claude/skills/all-deploy && git pull`

Prefer a single-file install? Download `all-deploy.skill` from the [Releases page](https://github.com/Hainrixz/all-deploy/releases/latest) and use Claude Code's skill installer.

### Usage

Inside Claude Code, say any of these:

| You say | What happens |
|---|---|
| `/all-deploy` | Starts deploy. Asks if you want full-auto or step-by-step. |
| `/all-deploy auto` | Full-auto. Audit → preview → prod with a 5-second ESC window before prod. |
| `/all-deploy step` | Step-by-step. Confirms each phase with you. |
| `/all-deploy local` | Runs the app on your machine instead of deploying. |
| `deploy this` / `ship this` / `push to prod` / `get this online` | Natural language also triggers the skill. |

### Supported targets (v1)

| Target | Best for |
|---|---|
| **Vercel** | Next.js, Vite, Astro, Remix, Nuxt, SvelteKit, static sites |
| **Railway** | FastAPI, Flask, Express, Python workers, agent loops, MCP HTTP servers |
| **Docker + SSH VPS** | Self-hosted, stateful apps, multi-service `docker compose` stacks |
| **cloudflared tunnel** | Local dev exposure, quick demos, webhook testing |

More targets (Netlify, Fly, Modal, Cloudflare Pages) are coming — [open an issue](https://github.com/Hainrixz/all-deploy/issues) to vote for yours.

### Safety — 8 hard rules

The skill ships with 8 non-negotiable rules. The short version:

1. Never bypass the audit.
2. Never deploy to prod before a green preview.
3. Never print, log, or commit secrets.
4. Never auto-install or auto-login CLIs — always hands you the command.
5. Never hide deploy commands inside wrapper scripts.
6. Never modify your code without showing the diff first.
7. Never deploy from a dirty git tree without your permission.
8. "Wait" always wins — any hesitation aborts.

Full rules and workflow in [SKILL.md](SKILL.md).

### Requirements

- **macOS or Linux.** Windows users: install under WSL2.
- **Git**, **Python 3.8+**, and the CLI of the target you choose (Vercel, Railway, `cloudflared`, or SSH + Docker). The skill tells you exactly which one's missing and how to install it.
- **Claude Code** (CLI, desktop, web, or an IDE extension).

### Author & community

Built by **Enrique Rocha** · [@soyenriquerocha](https://instagram.com/soyenriquerocha) · for the **Tododeia** community.

🌐 **[tododeia.com](https://tododeia.com)** — join the community, find more tools, see what we're building together.

### Contributing

Issues and pull requests welcome. Good starter contributions:

- Add a new target under `references/targets/` (Netlify, Fly, Modal, Cloudflare Pages, Render, etc.).
- Extend the secret patterns or audit checks in `scripts/audit.py`.
- Improve framework detection in `references/project-types.md`.

Keep references under ~200 lines and match the existing layout (prereqs → env delivery → preview → health check → prod → rollback + logs).

### License

MIT — see [LICENSE](LICENSE). Use it, fork it, ship it commercially, anything — just keep the copyright notice.

---

## Español

### Qué hace

Un solo comando — `/all-deploy` — lleva tu proyecto de *"corre en mi laptop"* a *"está en vivo en internet"*.

Sigue seis fases cada vez:

1. **Detecta** tu framework (Next.js, FastAPI, Docker, sitio estático — lo que tengas).
2. **Audita** tu código buscando secretos filtrados, configuración faltante, dependencias con vulnerabilidades y otros bloqueadores.
3. **Elige el mejor host** (Vercel, Railway, Docker+VPS, o un túnel cloudflared).
4. **Despliega primero una preview** y verifica la URL con curl para confirmar que la app funciona.
5. **Promociona a producción** solo después de que la preview esté verde (con ventana de 5 segundos para ESC, o un "sí" explícito si elegiste paso a paso).
6. **Te deja los comandos de rollback y logs** para que no quedes varado si algo falla más adelante.

El modo **run-locally** corre el mismo audit y luego inicia la app en tu propia máquina, opcionalmente expuesta por un túnel cloudflared para una URL pública temporal.

### Instalación (30 segundos)

```bash
git clone https://github.com/Hainrixz/all-deploy.git ~/.claude/skills/all-deploy
```

Listo. `/all-deploy` ya funciona dentro de Claude Code.

Para actualizar después: `cd ~/.claude/skills/all-deploy && git pull`

¿Prefieres instalar un solo archivo? Descarga `all-deploy.skill` desde la [página de Releases](https://github.com/Hainrixz/all-deploy/releases/latest) y úsalo con el instalador de skills de Claude Code.

### Uso

Dentro de Claude Code, di cualquiera de estos:

| Tú dices | Qué pasa |
|---|---|
| `/all-deploy` | Inicia el deploy. Pregunta si quieres modo automático o paso a paso. |
| `/all-deploy auto` | Automático. Audit → preview → prod con 5 segundos para cancelar con ESC. |
| `/all-deploy step` | Paso a paso. Confirma cada fase contigo. |
| `/all-deploy local` | Corre la app en tu máquina en vez de desplegarla. |
| `despliega esto` / `mándalo a prod` / `paso a paso` / `ponlo online` | El lenguaje natural también dispara el skill. |

### Targets soportados (v1)

| Target | Ideal para |
|---|---|
| **Vercel** | Next.js, Vite, Astro, Remix, Nuxt, SvelteKit, sitios estáticos |
| **Railway** | FastAPI, Flask, Express, workers de Python, agentes, servidores MCP HTTP |
| **Docker + SSH VPS** | Self-hosted, apps con estado, stacks `docker compose` multi-servicio |
| **cloudflared tunnel** | Exponer dev local, demos rápidas, pruebas de webhook |

Vienen más targets (Netlify, Fly, Modal, Cloudflare Pages) — [abre un issue](https://github.com/Hainrixz/all-deploy/issues) para votar por el tuyo.

### Seguridad — 8 reglas duras

El skill viene con 8 reglas no negociables. Versión corta:

1. Nunca omitir el audit.
2. Nunca desplegar a prod sin una preview verde.
3. Nunca imprimir, loggear ni commitear secretos.
4. Nunca auto-instalar ni auto-loggear CLIs — siempre te da el comando a ti.
5. Nunca esconder comandos de deploy en scripts envolventes.
6. Nunca modificar tu código sin mostrarte el diff primero.
7. Nunca hacer deploy desde un tree de git sucio sin tu permiso.
8. "Espera" siempre gana — cualquier duda aborta.

Reglas completas y flujo en [SKILL.md](SKILL.md).

### Requisitos

- **macOS o Linux.** Windows: instala bajo WSL2.
- **Git**, **Python 3.8+**, y el CLI del target que elijas (Vercel, Railway, `cloudflared`, o SSH + Docker). El skill te avisa exactamente cuál falta y cómo instalarlo.
- **Claude Code** (CLI, desktop, web, o una extensión de IDE).

### Autor y comunidad

Creado por **Enrique Rocha** · [@soyenriquerocha](https://instagram.com/soyenriquerocha) · para la comunidad **Tododeia**.

🌐 **[tododeia.com](https://tododeia.com)** — únete a la comunidad, encuentra más herramientas, mira lo que estamos construyendo juntos.

### Contribuir

Issues y pull requests son bienvenidos. Buenas contribuciones iniciales:

- Agregar un target nuevo bajo `references/targets/` (Netlify, Fly, Modal, Cloudflare Pages, Render, etc.).
- Extender los patrones de secretos o checks del audit en `scripts/audit.py`.
- Mejorar la detección de frameworks en `references/project-types.md`.

Mantén las referencias bajo ~200 líneas y sigue el layout existente (prereqs → entrega de env → preview → health check → prod → rollback + logs).

### Licencia

MIT — ver [LICENSE](LICENSE). Úsalo, forkealo, véndelo comercialmente, lo que sea — solo mantén el aviso de copyright.
