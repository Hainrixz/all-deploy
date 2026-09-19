# `publish-website`

**Puts a web page on the internet, free, without a terminal.**

A companion to [`/all-deploy`](../README.md) for the other half of the question. `/all-deploy` deploys apps, APIs and agents and assumes you have a terminal. This one is for the person who has a folder with `index.html` in it and wants it online.

It checks the page first — for the things that break it *after* it's live, which are not the things people expect — then walks through publishing it on Cloudflare Pages, Netlify, GitHub Pages or Render, and connecting a custom domain.

**[English](#english) · [Español](#español)**

---

## English

### What it checks before publishing

Seven things, and every one of them is invisible until the page is already live:

- **The home page is named `index.html`.** Hosts serve that name at `/`. `mi-pagina.html` gives a 404 at the site root.
- **Capitalisation in file paths.** `<img src="imagenes/foto.png">` when the file is `Imagenes/Foto.PNG` works on Mac and Windows — their filesystems ignore capitals — and 404s on every host, which run Linux. The images just vanish and nothing in any log says why. This is the one that catches the most people.
- **Paths pointing at your computer** — `file:///Users/...`, `C:\Users\...`. Usually from dragging an image into the HTML.
- **References to files that aren't in the folder.**
- **API keys in the HTML or JavaScript.** Everything a static host serves is public — a private repo changes nothing. Publishable keys (Stripe `pk_`, restricted Google Maps) are fine and flagged as a note; real credentials block.
- **Oversized images.**
- **Missing `<title>` and social preview tags** — without them, sharing the link on WhatsApp shows a blank card that reads as broken.

### Which host it picks

The question that decides it is one most guides skip: **is anyone being paid in connection with this page?**

Vercel's free plan counts *"receiving payment to create, update, or host the site"* as commercial usage — so a client's page is out even if the page sells nothing. GitHub Pages bars sites *"primarily directed at facilitating commercial transactions."* That single question reorders the list more than any technical comparison.

| Situation | Host |
|---|---|
| Client's page, or anyone was paid | Cloudflare Pages |
| Needs a contact form, no backend | Netlify |
| Portfolio, docs, demo, personal | GitHub Pages |
| Personal project on Next/React/Astro | Vercel |
| Online right now, no account | Netlify Drop |

### Install

**Cowork** — package this folder as a `.plugin` file and install it from the Cowork desktop app.

**Claude Code** — copy the skill in directly:

```bash
git clone https://github.com/Hainrixz/all-deploy.git /tmp/all-deploy
cp -R /tmp/all-deploy/cowork-plugin/skills/publish-website ~/.claude/skills/
```

Then say *"publish my website"*, *"sube mi página"*, or anything close to it.

### What it deliberately doesn't do

- **Never buys a domain or creates an account for you.** It shows the steps and the cost; you decide.
- **Never installs or logs into a CLI on your behalf.**
- **Never changes your files without showing you the change first.**
- **Never claims a static page can keep a secret**, because it can't — and says what to do instead.

### Not for apps

A backend, a login, a database, an API? That's `/all-deploy`, which runs a full pre-deploy audit. This skill says so and hands you over rather than wasting your afternoon.

---

## Español

### Qué revisa antes de publicar

Siete cosas, y todas son invisibles hasta que la página ya está en línea:

- **Que la página principal se llame `index.html`.** Los hosts sirven ese nombre exacto en `/`. Con `mi-pagina.html`, la raíz del sitio da 404.
- **Mayúsculas en las rutas de archivos.** `<img src="imagenes/foto.png">` cuando el archivo es `Imagenes/Foto.PNG` funciona en Mac y Windows —sus sistemas de archivos ignoran mayúsculas— y da 404 en cualquier host, porque todos corren Linux. Las imágenes simplemente desaparecen y ningún log dice por qué. Esta es la que atrapa a más gente.
- **Rutas que apuntan a tu computadora** — `file:///Users/...`, `C:\Users\...`. Casi siempre por arrastrar una imagen al HTML.
- **Referencias a archivos que no están en la carpeta.**
- **Llaves de API en el HTML o el JavaScript.** Todo lo que sirve un host estático es público — que el repo sea privado no cambia nada. Las llaves publicables (Stripe `pk_`, Google Maps restringida) están bien y salen como aviso; las credenciales de verdad bloquean.
- **Imágenes demasiado pesadas.**
- **Falta de `<title>` y de tags de previsualización** — sin eso, compartir el link por WhatsApp muestra una tarjeta en blanco que se ve rota.

### Cómo elige el host

La pregunta que lo decide es la que casi ninguna guía hace: **¿a alguien le están pagando por esta página?**

El plan gratis de Vercel cuenta como uso comercial *"recibir pago por crear, actualizar u hospedar el sitio"* — así que la página de un cliente queda fuera aunque no venda nada. GitHub Pages prohíbe los sitios *"dirigidos principalmente a facilitar transacciones comerciales"*. Esa sola pregunta reordena la lista más que cualquier comparación técnica.

| Caso | Host |
|---|---|
| Página de un cliente, o te pagaron | Cloudflare Pages |
| Necesita formulario de contacto, sin backend | Netlify |
| Portafolio, docs, demo, personal | GitHub Pages |
| Proyecto personal en Next/React/Astro | Vercel |
| En línea ya, sin cuenta | Netlify Drop |

### Instalación

**Cowork** — empaqueta esta carpeta como archivo `.plugin` e instálalo desde la app de escritorio de Cowork.

**Claude Code** — copia la skill directo:

```bash
git clone https://github.com/Hainrixz/all-deploy.git /tmp/all-deploy
cp -R /tmp/all-deploy/cowork-plugin/skills/publish-website ~/.claude/skills/
```

Después dile *"sube mi página"*, *"publica mi página web"*, o algo parecido.

### Qué NO hace a propósito

- **Nunca compra un dominio ni crea una cuenta por ti.** Te muestra los pasos y el costo; tú decides.
- **Nunca instala ni inicia sesión en un CLI por ti.**
- **Nunca cambia tus archivos sin enseñarte antes el cambio.**
- **Nunca dice que una página estática puede guardar un secreto**, porque no puede — y te dice qué hacer en su lugar.

### No es para apps

¿Backend, login, base de datos, API? Eso es `/all-deploy`, que corre un audit completo antes de desplegar. Esta skill te lo dice y te pasa para allá en vez de hacerte perder la tarde.

---

MIT · Creado por **Enrique Rocha** para la comunidad [Tododeia](https://tododeia.com) · [@soyenriquerocha](https://instagram.com/soyenriquerocha)
