
## Watch the Tutorial for docker-compose install:
[https://m.youtube.com/watch?v=A6CjAmJOWvA&t=5s](https://m.youtube.com/watch?v=A6CjAmJOWvA&t=5s)

## Warning
If you are upgrading from Postiz old version, please make sure you update your docker compose, you can read more here:
https://docs.postiz.com/installation/migration

### Configuration uses environment variables

The docker containers for Postiz are entirely configured with environment variables.

- **Option A** - environment variables in your `docker-compose.yml` file
- **Option B** - environment variables in a `postiz.env` file mounted in `/config` for the Postiz container only
- **Option C** - environment variables in a `.env` file next to your `docker-compose.yml` file (not recommended).

... or a mixture of the above options!

There is a [configuration reference](https://docs.postiz.com/configuration/reference) page with a list
of configuration settings.

Setup:
```
git clone https://github.com/gitroomhq/postiz-docker-compose
```

Then run:
```
docker compose up
```

Wait for it to load:

Open your website on https://localhost:4007

---

# Configuración de este fork (Jhonny-Morocho)

Fork de `gitroomhq/postiz-docker-compose` con dos añadidos: **deploy a producción en Dokploy** y un **script de publicación masiva** de videos (Dropbox → Postiz → Facebook / Instagram / TikTok).

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `docker-compose.yaml` | Dev local (`http://localhost:4007`, `NOT_SECURED=true`). |
| `docker-compose.prod.yaml` | Producción en Dokploy. Sin puertos al host, secretos por variables, red `dokploy-network`. |
| `.env.example` | Plantilla de variables para la pestaña *Environment* de Dokploy. |
| `dynamicconfig/` | Config de Temporal, montada por ambos compose. |
| `post-facebook.py` | Script de publicación/programación masiva. |
| `publicados.json` | Historial de destinos ya publicados (evita duplicados). |
| `post.json` | Payload de ejemplo para la API pública de Postiz. |

## Stack

`postiz` (app, puerto interno 5000) · `postiz-postgres` (PG 17) · `postiz-redis` · Temporal (`temporal`, `temporal-postgresql`, `temporal-elasticsearch`). Postiz no arranca hasta que Postgres, Redis y Temporal estén *healthy* (primer arranque ≈ 2–3 min; Elasticsearch pide 1–2 GB de RAM, servidor recomendado ≥ 4 GB).

## Deploy en Dokploy

1. Dominio: registro DNS A → IP del servidor.
2. *Create Service → Compose*, provider **GitHub**, repo `postiz-docker-compose`, rama `main`, **Compose Path `./docker-compose.prod.yaml`**.
3. *Environment*: pegar `.env.example` con valores reales, en formato `CLAVE=valor` sin comentarios ni comillas, y pulsar **Save**.
   - `MAIN_URL`: tu dominio con `https://`.
   - `POSTGRES_PASSWORD` / `TEMPORAL_DB_PASSWORD`: contraseñas de las bases; en local eran `postiz-password` y `temporal`.
   - `JWT_SECRET`: clave que firma las sesiones; no viene de ningún sitio, se inventa. Mínimo 32 caracteres, sin espacios, `$` ni `#`. Cambiarla cierra las sesiones pero no pierde datos. Generarla con:
     - PowerShell: `-join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })`
     - Git Bash / Linux: `openssl rand -hex 32`
4. *Domains*: host = tu dominio, servicio `postiz`, puerto `5000`, HTTPS + Let's Encrypt.
5. *Deploy*. Crear la cuenta y luego poner `DISABLE_REGISTRATION=true` y redeploy.
6. Actualizar las redirect URIs OAuth en Meta y TikTok al nuevo dominio.

Trigger *On Push*: cada push a `main` redespliega. Datos persistentes en volúmenes nombrados (`postgres-volume`, `postiz-uploads`, etc.); no usar `docker compose down -v`.

## Script `post-facebook.py`

Recorre carpetas de Dropbox con videos `.mp4` + un CSV, deduce DJ, género, BPM y versión (Edit/Remix) y programa en Postiz **una publicación cada 30 min** (`INTERVALO_MINUTOS`):

| Destino | Red | Tipo |
|---|---|---|
| `fb_post` / `fb_story` | Facebook | video / story |
| `ig_reel` / `ig_story` | Instagram | reel / story |
| `tiktok_video` | TikTok | video |

- Historial: clave `"<video>|<destino>"` (con carpeta) en `publicados.json`; solo se envía lo pendiente. Reintenta ante 429.
- Uso: `python post-facebook.py` (real) · `python post-facebook.py --dry` (simulación, no envía).
- Variables: `POSTIZ_API_KEY`, `DROPBOX_TOKEN`, `POSTIZ_URL` (por defecto `http://localhost:4007/api/public/v1`; para producción apuntar a `https://tu.dominio/api/public/v1`).
- Las carpetas viven en `CARPETAS_DROPBOX_PREDETERMINADAS` (rutas locales de Windows).
- ⚠️ El script trae tokens de Postiz y Dropbox como valor por defecto en el código y el `docker-compose.yaml` de dev trae secretos de Facebook/TikTok. Están en el historial de git: **rotarlos** y usar solo variables de entorno.
