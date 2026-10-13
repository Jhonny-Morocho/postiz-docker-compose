"""Modulo para publicar y programar videos en Facebook, Instagram y TikTok a traves de Postiz.

Publica los videos definidos en un archivo CSV alojados en Dropbox hacia:
- Facebook: Publicacion de video y Story
- Instagram: Reel (Publicacion de video) y Story
- TikTok: Publicacion de video

El primer video se publica de inmediato y los siguientes se programan cada 30 minutos.
"""

import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

INTERVALO_MINUTOS = 30
POSTIZ_URL_BASE = os.environ.get("POSTIZ_URL", "http://localhost:4007/api/public/v1")
CANAL_FACEBOOK_DEFECTO = "cmux7ue880001nz8dp1z3y4da"
CARPETA_VIDEOS = Path(
    os.environ.get(
        "CARPETA",
        r"C:\Users\Usuario iTC\Dropbox\VIDEOS-PUBLICIDAD-PROEDITS\dj-deyzer-nuevos-con-audio",
    )
)
RUTA_DROPBOX_BASE = os.environ.get(
    "DROPBOX_PATH",
    "/VIDEOS-PUBLICIDAD-PROEDITS/dj-deyzer-nuevos-con-audio",
)
ARCHIVO_HISTORIAL = Path(__file__).with_name("publicados.json")
MODO_SIMULACION = "--dry" in sys.argv

DESTINOS_PUBLICACION = [
    ("fb_post", "facebook", "post", True),
    ("fb_story", "facebook", "story", False),
    ("ig_reel", "instagram", "post", True),
    ("ig_story", "instagram", "story", False),
    ("tiktok_video", "tiktok", "post", True),
]

TOKEN_POSTIZ_POR_DEFECTO = (
    "cf8920774d1eab8b801a6b1126bbc8cb711975170065f1afdb7566c20fbbb8c2"
)
TOKEN_DROPBOX_POR_DEFECTO = (
    "sl.u.AGyMDgW958vf2s9VHW4t0T_qhp-1jGYdaM9yp8-01Jd6mbY1DJ47cHbnZDNpWgQaaTHSTmnBB1ZITpWBomMRkWVV6tptHmGebAzvssFOrj2syqIvUNaiabalLFy5l9pKkhTGv1jDLb-FEk5PVYCPg-BWdrmAI1_OTg-j642iqKsQj8dgeYzhyrVZsSNQBuLNioCHBR15QFJAht7ekJyhFCOcxiXnuzHqnAaCFsT7WIAH5LoPK3zinAsjQjJmtUE8PR_uXsBket6eOw7klINHd9X6rLt9bIjBV1vypyMvegG4XgMaBn8DbyZreVUV800aIcC32Ysot4CMkViqW-VlKUIzopqnMyW5mCOrUrraOKdvOCDeq_CFow4hlLlJm9b78n6768QBpmI_43am51kUM9nTxRr3LPgGRM41-qLSLWZVSW0xnzOPt4kn2hs6MKCgKmifbpGTXZD12Li3NQiMnRpIjfC-Yc00uZTs7_7SHdwS_tzL_cRsqTM0p2M9In50NYUOv7WMPksvudS5OfCgMX5uS51ukepCsfzj1qn8ZBYixuLlC7BVUAz8ltgjbXGXpvuC8QfKo-ntgZEDKeIJj7_tJSvdwbhvgjr_4YmoJiMgqw1_GJl65QwdOm5x5DXLK95zGo7VPiO66w1j657YBijMwhWRL_2nlWWkyKDjn3F5w8xoEevHmf0U6HaBA8BiNQBriC_EhxpJYeByMqjJjIqMtuV9gZ9IQ4vk4BpfJsGkeCkd4uXQN89HBU4ci0w86r99EH2cm5nLOL4ngF76vub7Ug6zz6kB--3rADHChxShM9sqLBt8uCAgVOaiAnbHtKs9CJOdloFHngtiUvpUxUR6tWTP4YlF02X179lzB1V-FX4bcqJKhNw_X3Pdyr37RtVDwA8KskUIFwDQf3kIBCNVB39f_lnYvqJj3gecozV31ON-qhr4FmMMMy79bflqnKy55Ztgm2bDTFUyfyQZYiRoIDTG_iZ5mzUrg_xhvhrTrupDQJoJSYBnBryNQYJIDNpT8ltvUPwXHQee86UddSlCunQjWnbV4k6racWU-OIdnQa8BfpdnbqFt-e7GQfcwi8CsXYkMQnntT0atwAvHl2iAVYU4EN5vUzsJexEIeeR1kG1AObRJABhglZ7inP2OpXzIygKcO7ESPDgSjIYJfiC08AusWEADJ9056_oxEsia5fRmmHRoGcXEBYFTEWuUhogurAz5zzet174h0_qDBTY6FcRsSQNj8C9zYaXlWuDafnYcY95D9kiDgTvGMbxlyZlB7kSgY6BX_4DUFyHRQPBSJCRUv8nQiOTnP9XgqyJnyPkYVrJJmDagRgww84Ns0k"
)


def realizar_peticion_http(url, cuerpo, token_autorizacion, permitir_409=False, metodo="POST"):
    """Ejecuta una solicitud HTTP JSON y retorna la respuesta decodificada."""
    datos_binarios = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    cabeceras = {
        "Content-Type": "application/json",
        "Authorization": token_autorizacion,
    }
    solicitud = urllib.request.Request(url, data=datos_binarios, headers=cabeceras, method=metodo)

    try:
        with urllib.request.urlopen(solicitud, timeout=60) as respuesta:
            return json.load(respuesta)
    except urllib.error.HTTPError as error:
        if permitir_409 and error.code == 409:
            return json.loads(error.read().decode("utf-8"))
        mensaje_error = error.read().decode("utf-8", errors="replace")[:400]
        raise SystemExit(f"Error {error.code} en {url}: {mensaje_error}")


def obtener_canales_activos(llave_postiz):
    """Consulta en Postiz las integraciones activas para Facebook, Instagram y TikTok."""
    canales_mapeados = {}

    if MODO_SIMULACION and not llave_postiz:
        return {
            "facebook": (CANAL_FACEBOOK_DEFECTO, "facebook"),
            "instagram": ("id-instagram-simulado", "instagram"),
            "tiktok": ("id-tiktok-simulado", "tiktok"),
        }

    integraciones = realizar_peticion_http(
        f"{POSTIZ_URL_BASE}/integrations",
        cuerpo=None,
        token_autorizacion=llave_postiz,
        metodo="GET",
    )

    for item in integraciones:
        if item.get("disabled"):
            continue

        identificador = (item.get("identifier") or item.get("providerIdentifier") or "").lower()

        if "facebook" in identificador and "facebook" not in canales_mapeados:
            canales_mapeados["facebook"] = (item["id"], "facebook")
        elif "instagram" in identificador and "instagram" not in canales_mapeados:
            canales_mapeados["instagram"] = (item["id"], "instagram")
        elif "tiktok" in identificador and "tiktok" not in canales_mapeados:
            canales_mapeados["tiktok"] = (item["id"], "tiktok")

    canales_mapeados.setdefault("facebook", (CANAL_FACEBOOK_DEFECTO, "facebook"))
    return canales_mapeados


def normalizar_nombre_archivo_video(nombre_video):
    """Asegura la extension .mp4 en el nombre de archivo si no esta presente."""
    nombre_limpio = nombre_video.strip()
    if not nombre_limpio.lower().endswith(".mp4"):
        return f"{nombre_limpio}.mp4"
    return nombre_limpio


def obtener_enlace_directo_dropbox(nombre_archivo, token_dropbox):
    """Genera o reutiliza un enlace publico directo de descarga desde Dropbox."""
    archivo_normalizado = normalizar_nombre_archivo_video(nombre_archivo)
    ruta_archivo = f"{RUTA_DROPBOX_BASE.rstrip('/')}/{archivo_normalizado.lstrip('/')}"
    cuerpo_creacion = {
        "path": ruta_archivo,
        "settings": {"requested_visibility": "public"},
    }

    respuesta = realizar_peticion_http(
        "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings",
        cuerpo=cuerpo_creacion,
        token_autorizacion=f"Bearer {token_dropbox}",
        permitir_409=True,
    )

    enlace = respuesta.get("url")
    if not enlace:
        cuerpo_lista = {"path": ruta_archivo, "direct_only": True}
        respuesta_existente = realizar_peticion_http(
            "https://api.dropboxapi.com/2/sharing/list_shared_links",
            cuerpo=cuerpo_lista,
            token_autorizacion=f"Bearer {token_dropbox}",
        )
        enlace = respuesta_existente["links"][0]["url"]

    return enlace.replace("dl=0", "raw=1")


def extraer_metadatos_producto(producto_cadena):
    """Extrae titulo del tema, version del edit y BPM a partir del formato estandar."""
    cadena_limpia = producto_cadena.strip()
    patron = re.match(r"^(\d+)\s*BPM\s*-\s*(.+?)\s*\((.+)\)\s*$", cadena_limpia)

    if not patron:
        return cadena_limpia, "", ""

    bpm, tema, edit = patron.groups()
    return " ".join(tema.split()), edit.strip(), bpm


def obtener_nombre_proveedor(fila_datos):
    """Obtiene y normaliza el nombre del proveedor o DJ para el contenido."""
    proveedor_crudo = (
        fila_datos.get("proveedor")
        or fila_datos.get("dj")
        or fila_datos.get("artista")
        or "Deyzer"
    ).strip()

    if not proveedor_crudo:
        return "Deyzer"

    return proveedor_crudo.title() if proveedor_crudo.islower() else proveedor_crudo


def obtener_nombre_artistico(proveedor):
    """Retorna el nombre con prefijo DJ si aun no lo contiene."""
    if proveedor.lower().startswith("dj "):
        return proveedor
    return f"DJ {proveedor}"


def generar_contenido_texto(fila_datos):
    """Genera el cuerpo HTML enriquecido para la descripcion de la publicacion."""
    producto = fila_datos.get("producto", "")
    enlace_web = fila_datos.get("link", fila_datos.get("url", ""))
    tema, edit, bpm = extraer_metadatos_producto(producto)
    proveedor = obtener_nombre_proveedor(fila_datos)
    nombre_dj = obtener_nombre_artistico(proveedor)

    partes_detalle = [texto for texto in (edit, f"{bpm} BPM" if bpm else "") if texto]
    linea_detalle = " · ".join(partes_detalle)

    etiqueta_proveedor = re.sub(r"[^a-zA-Z0-9]", "", proveedor)
    etiqueta_dj = re.sub(r"[^a-zA-Z0-9]", "", nombre_dj)

    parrafos = [
        f"🔥 NUEVO UPDATE de {nombre_dj.upper()} 🔥",
        "",
        f"🎧 {tema}",
    ]

    if linea_detalle:
        parrafos.append(linea_detalle)

    parrafos.extend([
        "",
        f"Ya está disponible el nuevo update de {nombre_dj} en ProEditsClub. "
        "Edits listos para la cabina, con intros limpias y BPM exacto para tus mezclas.",
        "",
        "👉 Escúchalo y descárgalo aquí:",
        enlace_web,
        "",
        f"#ProEditsClub #{etiqueta_proveedor} #{etiqueta_dj} #DJ #Remix #Edits2026 #DJLife",
    ])

    return "".join(f"<p>{linea}</p>" for linea in parrafos)


def generar_titulo_publicacion(fila_datos):
    """Genera el titulo corto para publicaciones de video en Facebook."""
    producto = fila_datos.get("producto", "")
    tema, _, bpm = extraer_metadatos_producto(producto)
    nombre_dj = obtener_nombre_artistico(obtener_nombre_proveedor(fila_datos))
    sufijo_bpm = f" ({bpm} BPM)" if bpm else ""
    return f"Nuevo update {nombre_dj} - {tema}{sufijo_bpm}"[:250]


def construir_configuracion_red(red, tipo_publicacion, fila_datos):
    """Construye el diccionario de opciones especificas segun la red y el tipo de contenido."""
    configuracion = {"__type": red, "post_type": tipo_publicacion}

    if red == "facebook" and tipo_publicacion == "post":
        configuracion["title"] = generar_titulo_publicacion(fila_datos)

    if red == "instagram":
        configuracion["collaborators"] = []

    if red == "tiktok":
        configuracion["privacy_level"] = "PUBLIC_TO_EVERYONE"
        configuracion["content_posting_method"] = "DIRECT_POST"
        configuracion["duet"] = False
        configuracion["stitch"] = False
        configuracion["comment"] = True
        configuracion["brand_content_toggle"] = False
        configuracion["brand_organic_toggle"] = False
        configuracion["video_made_with_ai"] = False

    return configuracion


def cargar_historial_publicados(ruta_archivo):
    """Carga los identificadores de publicaciones previas para evitar duplicidad."""
    if not ruta_archivo.exists():
        return set()

    datos = json.loads(ruta_archivo.read_text(encoding="utf-8"))
    return {item if "|" in item else f"{item}|fb_post" for item in datos}


def guardar_historial_publicados(ruta_archivo, historial_set):
    """Persiste en disco el registro ordenado de publicaciones procesadas."""
    ruta_archivo.write_text(
        json.dumps(sorted(historial_set), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def cargar_registros_csv(ruta_directorio):
    """Lee el archivo CSV de productos y videos desde la ruta configurada."""
    archivo_csv = ruta_directorio / "ids-y-links.csv"
    if not archivo_csv.exists():
        raise SystemExit(f"No se encontro el archivo CSV requerido en: {archivo_csv}")

    with open(archivo_csv, encoding="utf-8-sig", newline="") as flujo:
        return list(csv.DictReader(flujo))


def filtrar_tareas_pendientes(registros, redes_disponibles, historial):
    """Determina que videos y formatos faltan por publicar en los canales configurados."""
    pendientes = []

    for fila in registros:
        nombre_video = fila.get("video", "")
        faltantes = [
            destino
            for destino in DESTINOS_PUBLICACION
            if destino[1] in redes_disponibles
            and f"{nombre_video}|{destino[0]}" not in historial
        ]

        if faltantes:
            pendientes.append((fila, faltantes))

    return pendientes


def calcular_fecha_publicacion(tiempo_base, indice_video):
    """Calcula la marca de tiempo de publicacion espaciada cada 30 minutos."""
    delta = timedelta(minutes=INTERVALO_MINUTOS * indice_video)
    fecha_calculada = tiempo_base + delta
    tipo_envio = "now" if indice_video == 0 else "schedule"
    return fecha_calculada, tipo_envio


def enviar_publicacion_postiz(
    clave_postiz,
    canal_id,
    red,
    tipo_publicacion,
    fila,
    clave_destino,
    url_video,
    tipo_envio,
    fecha_envio,
):
    """Construye y envia la peticion de creacion/programacion hacia Postiz."""
    tiene_texto = tipo_publicacion == "post"
    nombre_dj = obtener_nombre_artistico(obtener_nombre_proveedor(fila))
    contenido = (
        generar_contenido_texto(fila)
        if tiene_texto
        else f"<p>🔥 Nuevo update {nombre_dj} · ProEditsClub</p>"
    )

    numero_identificador = fila.get("numero") or fila.get("id") or "1"
    ajustes_red = construir_configuracion_red(red, tipo_publicacion, fila)

    payload = {
        "type": tipo_envio,
        "date": fecha_envio.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": canal_id},
                "value": [
                    {
                        "content": contenido,
                        "image": [
                            {
                                "id": f"{numero_identificador}-{clave_destino}",
                                "path": url_video,
                            }
                        ],
                    }
                ],
                "settings": ajustes_red,
            }
        ],
    }

    realizar_peticion_http(f"{POSTIZ_URL_BASE}/posts", payload, clave_postiz)


def procesar_cola_publicaciones(pendientes, redes_activas, clave_postiz, token_dropbox, historial):
    """Itera y programa cada video pendiente respetando el intervalo de 30 minutos."""
    tiempo_inicio = datetime.now(timezone.utc)

    for indice, (fila, destinos_faltantes) in enumerate(pendientes):
        nombre_video = fila.get("video", "")
        fecha_programada, tipo_envio = calcular_fecha_publicacion(tiempo_inicio, indice)
        destinos_nombres = ", ".join(d[0] for d in destinos_faltantes)

        print(
            f"{indice + 1:>2}. {nombre_video} -> {tipo_envio} "
            f"{fecha_programada.astimezone():%d/%m %H:%M} [{destinos_nombres}]"
        )

        if MODO_SIMULACION:
            continue

        url_video_dropbox = obtener_enlace_directo_dropbox(nombre_video, token_dropbox)

        for clave_destino, red, post_type, _ in destinos_faltantes:
            canal_id, _ = redes_activas[red]
            enviar_publicacion_postiz(
                clave_postiz=clave_postiz,
                canal_id=canal_id,
                red=red,
                tipo_publicacion=post_type,
                fila=fila,
                clave_destino=clave_destino,
                url_video=url_video_dropbox,
                tipo_envio=tipo_envio,
                fecha_envio=fecha_programada,
            )

            historial.add(f"{nombre_video}|{clave_destino}")
            guardar_historial_publicados(ARCHIVO_HISTORIAL, historial)
            print(f"      ok {clave_destino}")


def main():
    """Punto de entrada principal del flujo de publicacion."""
    historial = cargar_historial_publicados(ARCHIVO_HISTORIAL)

    clave_postiz = os.environ.get("POSTIZ_API_KEY", TOKEN_POSTIZ_POR_DEFECTO)
    token_dropbox = os.environ.get("DROPBOX_TOKEN", TOKEN_DROPBOX_POR_DEFECTO)

    if not MODO_SIMULACION and not (clave_postiz and token_dropbox):
        raise SystemExit("Faltan POSTIZ_API_KEY y/o DROPBOX_TOKEN.")

    redes_activas = obtener_canales_activos(clave_postiz)
    print("Canales configurados:", ", ".join(f"{k} -> {v[0]}" for k, v in redes_activas.items()))

    if "instagram" not in redes_activas:
        print("AVISO: No hay canal de Instagram conectado en Postiz; omitiendo publicaciones en Instagram.")

    if "tiktok" not in redes_activas:
        print("AVISO: No hay canal de TikTok conectado en Postiz; omitiendo publicaciones en TikTok.")

    filas = cargar_registros_csv(CARPETA_VIDEOS)
    pendientes = filtrar_tareas_pendientes(filas, redes_activas, historial)

    if not pendientes:
        print("No hay tareas pendientes por publicar.")
        return

    procesar_cola_publicaciones(
        pendientes=pendientes,
        redes_activas=redes_activas,
        clave_postiz=clave_postiz,
        token_dropbox=token_dropbox,
        historial=historial,
    )

    if MODO_SIMULACION:
        print("(Simulacion completada: no se envio ninguna peticion)")
    else:
        print("Proceso de publicacion y programacion finalizado con exito.")


if __name__ == "__main__":
    main()