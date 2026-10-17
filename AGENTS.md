# AGENTS.md

Guía para agentes de IA (Claude Code, Codex, etc.) que trabajen en este repo. Detalle completo en `README.md`.

## Qué es
Fork de `gitroomhq/postiz-docker-compose` (remote `upstream`; `origin` = Jhonny-Morocho). Contiene:
1. Compose de dev (`docker-compose.yaml`) y de producción para **Dokploy** (`docker-compose.prod.yaml`).
2. `post-facebook.py`: publica videos de Dropbox en FB/IG/TikTok vía la API pública de Postiz.

## Reglas
- **Producción = `docker-compose.prod.yaml`**. Sin `container_name`, sin `ports:` (Traefik de Dokploy enruta a `postiz:5000`), red externa `dokploy-network`. Todo secreto va como `${VAR}`; si agregas una variable, añádela también a `.env.example`.
- No pongas secretos reales en archivos versionados. Los que ya están (tokens en `post-facebook.py`, FB/TikTok en `docker-compose.yaml`) deben rotarse, no replicarse.
- `docker-compose.yaml` es solo local (`NOT_SECURED=true`, puertos al host). No lo uses para producción.
- No borres volúmenes (`down -v`): contienen Postgres, uploads y Temporal.
- `publicados.json` es estado del script: no lo regeneres ni lo vacíes (causaría publicaciones duplicadas).
- Commits en inglés, estilo imperativo corto (ver `git log`). El script y sus identificadores están en español: respeta ese idioma.

## Verificar cambios
- Compose: `docker compose -f docker-compose.prod.yaml config` (con variables exportadas o un `.env` temporal fuera de git).
- Script: `python post-facebook.py --dry` (nunca ejecutarlo sin `--dry` sin que el usuario lo pida; publica en redes reales).

## Script — puntos clave
- Entrada: carpetas en `CARPETAS_DROPBOX_PREDETERMINADAS` (cada una con `.mp4` + CSV); salida: posts programados cada 30 min en los destinos de `DESTINOS_PUBLICACION`.
- Env: `POSTIZ_API_KEY`, `DROPBOX_TOKEN`, `POSTIZ_URL`.
- Deducción de DJ/género/BPM: `deducir_dj_desde_carpeta`, `deducir_genero_musical`, `extraer_metadatos_producto`.
- Idempotencia: `cargar_historial_publicados` / `filtrar_tareas_pendientes` con claves `video|destino`.
