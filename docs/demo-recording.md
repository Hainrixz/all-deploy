# Recording the `/all-deploy` demo

A 20–30s GIF embedded at the top of the README converts a reader into a user faster than any amount of docs. This guide is a recipe for capturing one.

**[English](#english)  ·  [Español](#español)**

---

## English

### What to record

A full **full-auto deploy of a Next.js starter to Vercel** is the highest-impact demo because it exercises every phase in under a minute:

1. You type `/all-deploy auto` in Claude Code.
2. Detect → Audit → Target ranking → Phase 3.5 → Preview → Health check → Prod.
3. The final production URL appears.

Keep it under 30 seconds. Trim anything longer than that in post.

### Recommended tools

| Tool | macOS | Linux | Output |
|---|---|---|---|
| **asciinema + svg-term-cli** | `brew install asciinema && npm i -g svg-term-cli` | `apt install asciinema` | SVG (small, crisp) |
| **LICEcap** | [licecap.com](https://www.cockos.com/licecap/) | via Wine or alt | GIF |
| **Kap** (recommended) | `brew install --cask kap` | — | GIF / MP4 |
| **ttygif** | `brew install ttygif` | `apt install ttygif` | GIF from terminal |

For README embedding, **MP4 → GIF via `gifski`** gives the smallest file with acceptable quality:
```bash
# Record with Kap → export MP4, then:
brew install gifski
gifski --fps 15 --width 900 --quality 80 -o demo.gif input.mp4
```

Target: **under 2 MB**. GIFs above that slow the README render and look unprofessional.

### Setup (before recording)

1. **Fresh Next.js starter in a throwaway dir:**
   ```bash
   cd ~/Desktop
   npx create-next-app@latest demo-app --typescript --app --no-src-dir --no-tailwind --no-eslint --import-alias "@/*"
   cd demo-app
   ```

2. **Link to a scratch Vercel project:**
   ```bash
   vercel link
   ```
   Pick personal scope, create new project, default answers. This avoids the "first-time" interactive prompts appearing in the recording.

3. **Run the audit once manually to make sure it's clean:**
   ```bash
   python3 ~/.claude/skills/all-deploy/scripts/audit.py . --skip-cve
   ```
   Fix any findings before recording.

4. **Size your terminal window:** 900–1000 px wide, 500–600 px tall. Wider is cinematic but pushes file size up.

5. **Font:** 14–16 pt monospace. Smaller looks jittery in a GIF; larger overflows the README column.

### The recording

Start Claude Code in the `demo-app` directory. Hit record. Then:

1. **Pause ~1s** on the blank prompt (gives viewers time to register the starting state).
2. Type: `/all-deploy auto`
3. Let the skill run. The interesting moments:
   - Phase 1 detection table.
   - Phase 2 audit "clean" result.
   - Phase 3 target ranking with Vercel at the top.
   - Phase 4 preview URL appearing.
   - Phase 4.5 curl 200 response.
   - Phase 5 "prod promotion in 5 seconds" countdown.
   - Phase 6 final production URL.
4. **Pause ~1s** on the final production URL so it sticks.
5. Stop recording.

### Framing tips

- **Cut dead air.** Most recorders produce 10+ seconds of blank terminal between steps. In post, trim those down to 0.5–1s max.
- **Speed up the slow bits.** `vercel` upload/build takes ~30–60s. Cut to a 2–3s timelapse with a small "⏩ ~45s" overlay if you can.
- **Don't zoom mid-clip.** Fixed framing reads better as a GIF.
- **Blur your account info** if the Vercel scope name appears. One blur pass in QuickTime / iMovie / DaVinci Resolve.
- **Caption the prod gate.** Add a one-line text overlay during the 5-second ESC window: *"Press ESC to abort — or wait 5s for prod."*

### Embedding in the README

Once you have `demo.gif` (or a Vercel-hosted MP4), add to the top of `README.md`, right under the title block:

```markdown
<div align="center">

![all-deploy demo](docs/demo.gif)

</div>
```

Commit the GIF at `docs/demo.gif`. GitHub will render it inline.

If the GIF is above 10 MB, GitHub refuses to inline it — host the MP4 on a CDN (Cloudflare R2, Vercel Blob, YouTube as fallback) and use an `<img>` tag with `src="https://cdn.../demo.gif"`.

### A/B variants worth recording

Make three short clips and embed the best, keep the rest on YouTube:

1. **Full-auto happy path** (the one above) — converts skeptics.
2. **Audit catches a committed `.env`** — shows the safety value.
3. **Step-by-step mode** — demonstrates the alternative UX for cautious users.

---

## Español

### Qué grabar

Un **deploy full-auto de un starter de Next.js a Vercel** es el demo de mayor impacto porque ejercita cada fase en menos de un minuto:

1. Escribes `/all-deploy auto` en Claude Code.
2. Detect → Audit → Ranking de targets → Fase 3.5 → Preview → Health check → Prod.
3. Aparece la URL final de producción.

Mantenlo bajo 30 segundos. Recorta cualquier cosa más larga en post.

### Herramientas recomendadas

| Herramienta | macOS | Linux | Salida |
|---|---|---|---|
| **asciinema + svg-term-cli** | `brew install asciinema && npm i -g svg-term-cli` | `apt install asciinema` | SVG (ligero, crujiente) |
| **LICEcap** | [licecap.com](https://www.cockos.com/licecap/) | vía Wine o alternativa | GIF |
| **Kap** (recomendada) | `brew install --cask kap` | — | GIF / MP4 |
| **ttygif** | `brew install ttygif` | `apt install ttygif` | GIF desde terminal |

Para embeber en el README, **MP4 → GIF con `gifski`** da el archivo más pequeño con calidad aceptable:
```bash
# Graba con Kap → exporta MP4, luego:
brew install gifski
gifski --fps 15 --width 900 --quality 80 -o demo.gif input.mp4
```

Objetivo: **menos de 2 MB**. Arriba de eso, el README se ralentiza y se ve poco profesional.

### Setup (antes de grabar)

1. **Starter fresco de Next.js en un directorio desechable:**
   ```bash
   cd ~/Desktop
   npx create-next-app@latest demo-app --typescript --app --no-src-dir --no-tailwind --no-eslint --import-alias "@/*"
   cd demo-app
   ```

2. **Linkea a un proyecto Vercel scratch:**
   ```bash
   vercel link
   ```
   Elige scope personal, crea proyecto nuevo, respuestas default. Así evitas los prompts interactivos de primera vez en la grabación.

3. **Corre el audit una vez manualmente para asegurar que está limpio:**
   ```bash
   python3 ~/.claude/skills/all-deploy/scripts/audit.py . --skip-cve
   ```
   Arregla cualquier finding antes de grabar.

4. **Dimensiona tu ventana de terminal:** 900–1000 px de ancho, 500–600 px de alto. Más ancho se ve cinematográfico pero aumenta el peso.

5. **Fuente:** 14–16 pt monoespaciada. Más chico se ve trémulo en GIF; más grande desborda la columna del README.

### La grabación

Arranca Claude Code en el directorio `demo-app`. Dale record. Después:

1. **Pausa ~1s** en el prompt en blanco (le da al espectador tiempo de registrar el estado inicial).
2. Escribe: `/all-deploy auto`
3. Deja que el skill corra. Momentos interesantes:
   - Tabla de detección de Fase 1.
   - Resultado "clean" del audit de Fase 2.
   - Ranking de targets de Fase 3 con Vercel arriba.
   - URL de preview apareciendo en Fase 4.
   - Respuesta 200 del curl en Fase 4.5.
   - Countdown "promoción a prod en 5 segundos" de Fase 5.
   - URL final de producción de Fase 6.
4. **Pausa ~1s** en la URL final de producción para que se quede.
5. Para la grabación.

### Tips de framing

- **Corta el aire muerto.** La mayoría de grabadores producen 10+ segundos de terminal en blanco entre pasos. En post, recórtalos a 0.5–1s máx.
- **Acelera lo lento.** El upload/build de `vercel` toma ~30–60s. Córtalo a un timelapse de 2–3s con un overlay "⏩ ~45s" si puedes.
- **No hagas zoom a mitad del clip.** El framing fijo se lee mejor como GIF.
- **Difumina tu info de cuenta** si aparece el nombre del scope de Vercel. Un blur en QuickTime / iMovie / DaVinci Resolve.
- **Añade caption en el gate de prod.** Un overlay de una línea durante la ventana de 5 segundos ESC: *"Presiona ESC para abortar — o espera 5s para prod."*

### Embeber en el README

Una vez que tengas `demo.gif` (o un MP4 hosteado en Vercel), agrega arriba del `README.md`, justo bajo el bloque de título:

```markdown
<div align="center">

![demo de all-deploy](docs/demo.gif)

</div>
```

Commitea el GIF en `docs/demo.gif`. GitHub lo renderiza inline.

Si el GIF pesa más de 10 MB, GitHub se niega a inlinearlo — hostea el MP4 en un CDN (Cloudflare R2, Vercel Blob, YouTube como fallback) y usa un tag `<img>` con `src="https://cdn.../demo.gif"`.

### Variantes A/B que vale la pena grabar

Haz tres clips cortos y embebe el mejor, deja los otros en YouTube:

1. **Happy path full-auto** (el de arriba) — convierte a escépticos.
2. **El audit atrapa un `.env` commiteado** — muestra el valor de seguridad.
3. **Modo paso a paso** — demuestra la UX alternativa para usuarios cautelosos.
