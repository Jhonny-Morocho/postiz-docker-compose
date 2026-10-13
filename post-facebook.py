"""Modulo para publicar y programar videos en Facebook, Instagram y TikTok a traves de Postiz.

Procesa multiples carpetas de Dropbox, identificando dinamicamente:
- El DJ / Proveedor correspondiente a cada video
- El Genero musical de cada tema
- Los metadatos de BPM y version (Edit / Remix)

Programa las publicaciones cada 30 minutos a traves de las 3 redes sociales:
- Facebook: Post de video y Story
- Instagram: Reel y Story
- TikTok: Post de video directo
"""

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

INTERVALO_MINUTOS = 30
POSTIZ_URL_BASE = os.environ.get("POSTIZ_URL", "http://localhost:4007/api/public/v1")
CANAL_FACEBOOK_DEFECTO = "cmux7ue880001nz8dp1z3y4da"
ARCHIVO_HISTORIAL = Path(__file__).with_name("publicados.json")
MODO_SIMULACION = "--dry" in sys.argv

CARPETAS_DROPBOX_PREDETERMINADAS = [
    r"C:\Users\Usuario iTC\Dropbox\VIDEOS-PUBLICIDAD-PROEDITS\dj-jordan-medina-productos-halloween-con-audio",
    r"C:\Users\Usuario iTC\Dropbox\VIDEOS-PUBLICIDAD-PROEDITS\dj-jordan-medina-productos-halloween-verano-bruja-con-audio",
    r"C:\Users\Usuario iTC\Dropbox\VIDEOS-PUBLICIDAD-PROEDITS\dj-nikel-the-skpt-productos-halloween-con-audio",
    r"C:\Users\Usuario iTC\Dropbox\VIDEOS-PUBLICIDAD-PROEDITS\top20-reggaeton-halloween-2026-10-05",
    r"C:\Users\Usuario iTC\Dropbox\VIDEOS-PUBLICIDAD-PROEDITS\dj-deyzer-nuevos-con-audio",
]

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
    "sl.u.AGwjaH7NuoHEHLW4VXWArX99y2R94Tl_KfUreDbQUB7ntLROpQdZiRQHAk0vW3XSAbhgQBvanTCY-VFVFS_hx6Jk_begNuN2hHLFRsZLjbC5IF_D4opQc7h_6fAZ_E0qf2GAceu-QQgId5NFWWon-dOqoRUoKrI5OZsnS_XoaQAVLXxhD35yLac6I2-q0tY5blu3ozxHlwO-tlUX_wpPIqhU6Eyg9lMkpE2xFufjyNigkEw7g19vWe7PDsQ392cdQj6WDuW2Wuz5k3vA-x1IMecUFXaguLTuPp5mGqIczwccy9Tc525TyhoZCw45xXSvxMHHj2RLnB8oQ4S3TDpfMbcg2O7pQ_l7ph-xsMeJZX0l0tQEczkYHRRPm6UFm8W9Bg73nqZkmu34JDf1ouWyMFDgZoNKisXvBhX0b_VmawPff6RkUFqv-WTDecump7ZNpGc3B5SIO1QudK4SCVG3G-uEEbnBYv4OkBomvfbFg1cOA1pmb60oc65Qzcms4s7r-c2mSVxfL5uJE933Jh8AfQFcwaQFe1m1Om80B9DTx-wZxACls_Q52mH9kaybT-whTvuKRiGw96tMu396dbOlHCmoMON5sEVxQcLJMEJfDB-vQp8_3yOdkrS4r65SOco6BFS8c2Gdkpgje-1A8cs-K4YF4UKSUFk-Gmjm7PZCas1tdEXR8ciFsbXrex3hL3gttCZxmRGtbSmkJpPGXbtFG2MiMNCxOc0AX2GysISgoBC_SwaAuMINpKkt9DiKSIHUZ9wCBACh89ag-M-l0_iGHylhibmk84knZJxr1J53yS6ugkeu2FFKz13Rmb582vPvkRRYWUrrvDLN0E-Lx0b05DgiLV2X9onb3nR5RxW4fIyKNpzLfa_ksVFiKuA8L4x9w9uISC53GEScugCU2TJAK-LPumvxMH4t1M8GA49lVK5Za9NCZrclW5a7jsVIK1LLy5CJSJlFZGRuOFQ2aCFcYHMHqUtfDmKt3ZyyeXUdbD-LAevfccqeo38KE3DzZr0OYWU5pK0E9RO3NLmSmg7lc4B9qSVesxlhh49Qx-dMI6rvzf8ldLujjTwk2uYCtikMAAAltsk60COdVF_AdUEwYkiqpZC_2He2w0oeeHG1u0nL4oB4_vGl8H0NenD07v_v5iaVWkBenFDXAI0YVJtN9vD1d26lUch8gyMdSn8XUycnvrDsCD25E3I4VEI4soew8CJwHqdDuv5jf7jOuw9XyfKHTbnDlhLayxsEC6Qtg8v3-E0XKN0O6U00_3OdNTFEBsGQpo5NY6qBSeqq4lznDJhwkEZarAQFHuHjiSqd6R5HMc1U19T_NbEj1HkaY-JjyRw"
)


def realizar_peticion_http(
    url, cuerpo, token_autorizacion, permitir_409=False, metodo="POST", max_reintentos=5
):
    """Ejecuta una solicitud HTTP JSON con reintentos ante limite de tasa (429)."""
    datos_binarios = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    cabeceras = {
        "Content-Type": "application/json",
        "Authorization": token_autorizacion,
    }

    for intento in range(max_reintentos + 1):
        solicitud = urllib.request.Request(
            url, data=datos_binarios, headers=cabeceras, method=metodo
        )
        try:
            with urllib.request.urlopen(solicitud, timeout=60) as respuesta:
                return json.load(respuesta)
        except urllib.error.HTTPError as error:
            if permitir_409 and error.code == 409:
                return json.loads(error.read().decode("utf-8"))

            if error.code == 429 and intento < max_reintentos:
                segundos_espera = 3 * (intento + 1)
                print(
                    f"      Limite 429 alcanzado. Esperando {segundos_espera}s para reintentar..."
                )
                time.sleep(segundos_espera)
                continue

            mensaje_error = error.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"Error {error.code} en {url}: {mensaje_error}")


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


def obtener_enlace_directo_dropbox(ruta_relativa_dropbox, token_dropbox):
    """Genera o reutiliza un enlace publico directo de descarga desde Dropbox."""
    cuerpo_creacion = {
        "path": ruta_relativa_dropbox,
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
        cuerpo_lista = {"path": ruta_relativa_dropbox, "direct_only": True}
        respuesta_existente = realizar_peticion_http(
            "https://api.dropboxapi.com/2/sharing/list_shared_links",
            cuerpo=cuerpo_lista,
            token_autorizacion=f"Bearer {token_dropbox}",
        )
        enlace = respuesta_existente["links"][0]["url"]

    return enlace.replace("dl=0", "raw=1")


def deducir_dj_desde_carpeta(nombre_carpeta):
    """Deduce el nombre formal del DJ segun el nombre de la carpeta contenedora."""
    carpeta_min = nombre_carpeta.lower()

    if "jordan-medina" in carpeta_min:
        return "DJ Jordan Medina"
    if "nikel" in carpeta_min:
        return "DJ Nikel The Skpt"
    if "deyzer" in carpeta_min:
        return "DJ Deyzer"
    if "top20" in carpeta_min or "top-20" in carpeta_min:
        return "ProEditsClub"

    partes = [p.capitalize() for p in nombre_carpeta.replace("-", " ").split()]
    return " ".join(partes[:3])


def obtener_nombre_dj(fila_datos, nombre_carpeta):
    """Obtiene y normaliza el nombre del DJ a partir del CSV o de la carpeta."""
    dj_directo = (
        fila_datos.get("dj")
        or fila_datos.get("proveedor")
        or fila_datos.get("artista")
        or ""
    ).strip()

    if dj_directo:
        if dj_directo.islower():
            dj_directo = dj_directo.title()
        if not dj_directo.lower().startswith("dj ") and not dj_directo.lower().startswith("proedits"):
            return f"DJ {dj_directo}"
        return dj_directo

    return deducir_dj_desde_carpeta(nombre_carpeta)


def deducir_genero_musical(fila_datos, nombre_carpeta):
    """Obtiene el genero musical a partir del CSV o del contexto de la carpeta."""
    genero_directo = (
        fila_datos.get("genero")
        or fila_datos.get("genre")
        or fila_datos.get("categoria")
        or fila_datos.get("subgenero")
        or ""
    ).strip()

    if genero_directo:
        return genero_directo.title()

    carpeta_min = nombre_carpeta.lower()
    if "reggaeton" in carpeta_min:
        return "Reggaeton"
    if "halloween" in carpeta_min:
        return "Halloween Special"
    if "cumbia" in carpeta_min:
        return "Cumbia"
    if "salsa" in carpeta_min:
        return "Salsa"

    return "Open Format"


def extraer_metadatos_producto(producto_cadena):
    """Extrae titulo del tema, version del edit y BPM a partir del formato estandar."""
    cadena_limpia = producto_cadena.strip()
    patron = re.match(r"^(\d+)\s*BPM\s*-\s*(.+?)\s*\((.+)\)\s*$", cadena_limpia)

    if not patron:
        return cadena_limpia, "", ""

    bpm, tema, edit = patron.groups()
    return " ".join(tema.split()), edit.strip(), bpm


def generar_contenido_texto(fila_datos, nombre_carpeta):
    """Genera la descripcion estructurada y personalizada segun DJ y Genero."""
    producto = fila_datos.get("producto", fila_datos.get("titulo", ""))
    enlace_web = fila_datos.get("link", fila_datos.get("url", ""))
    tema, edit, bpm = extraer_metadatos_producto(producto)

    nombre_dj = obtener_nombre_dj(fila_datos, nombre_carpeta)
    genero = deducir_genero_musical(fila_datos, nombre_carpeta)

    elementos_detalle = [x for x in (edit, f"{bpm} BPM" if bpm else "", genero) if x]
    linea_detalle = " · ".join(elementos_detalle)

    etiqueta_dj = re.sub(r"[^a-zA-Z0-9]", "", nombre_dj)
    etiqueta_genero = re.sub(r"[^a-zA-Z0-9]", "", genero)

    parrafos = [
        f"🔥 NUEVO UPDATE de {nombre_dj.upper()} 🔥",
        "",
        f"🎧 {tema}",
    ]

    if linea_detalle:
        parrafos.append(f"📦 {linea_detalle}")

    parrafos.extend([
        "",
        f"Ya está disponible este tremendo material de {nombre_dj} ({genero}) en ProEditsClub. "
        "Edits exclusivos listos para la cabina, con intros limpias y BPM exacto para tus mezclas.",
        "",
        "👉 Escúchalo y descárgalo ahora en:",
        enlace_web,
        "",
        f"#ProEditsClub #{etiqueta_dj} #{etiqueta_genero} #DJ #Remix #Edits2026 #DJLife",
    ])

    return "".join(f"<p>{linea}</p>" for linea in parrafos)


def generar_titulo_publicacion(fila_datos, nombre_carpeta):
    """Genera el titulo conciso para publicaciones en redes sociales."""
    producto = fila_datos.get("producto", fila_datos.get("titulo", ""))
    tema, _, bpm = extraer_metadatos_producto(producto)
    nombre_dj = obtener_nombre_dj(fila_datos, nombre_carpeta)
    sufijo_bpm = f" ({bpm} BPM)" if bpm else ""
    return f"Nuevo update {nombre_dj} - {tema}{sufijo_bpm}"[:250]


def construir_configuracion_red(red, tipo_publicacion, fila_datos, nombre_carpeta):
    """Construye las opciones especificas segun la red social de destino."""
    configuracion = {"__type": red, "post_type": tipo_publicacion}

    if red == "facebook" and tipo_publicacion == "post":
        configuracion["title"] = generar_titulo_publicacion(fila_datos, nombre_carpeta)

    if red == "instagram":
        configuracion["collaborators"] = []

    if red == "tiktok":
        configuracion["privacy_level"] = "PUBLIC_TO_EVERYONE"
        configuracion["content_posting_method"] = "DIRECT_POST"
        configuracion["duet"] = False
        configuracion["stitch"] = False
        configuracion["comment"] = True
        configuracion["autoAddMusic"] = "no"
        configuracion["brand_content_toggle"] = False
        configuracion["brand_organic_toggle"] = False
        configuracion["video_made_with_ai"] = False

    return configuracion


def cargar_historial_publicados(ruta_archivo):
    """Carga los identificadores de publicaciones previas para evitar duplicados."""
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


def buscar_archivo_csv(ruta_carpeta):
    """Localiza el archivo CSV dentro de la carpeta indicada."""
    archivo_estandar = ruta_carpeta / "ids-y-links.csv"
    if archivo_estandar.exists():
        return archivo_estandar

    candidatos_csv = list(ruta_carpeta.glob("*.csv"))
    if candidatos_csv:
        return candidatos_csv[0]

    return None


def recolectar_tareas_de_todas_las_carpetas(rutas_carpetas):
    """Lee todas las carpetas configuradas y consolida la lista global de tareas."""
    lista_global = []

    for ruta_texto in rutas_carpetas:
        carpeta_obj = Path(ruta_texto)
        if not carpeta_obj.exists():
            print(f"AVISO: No se encontro la carpeta local: {carpeta_obj.name}")
            continue

        archivo_csv = buscar_archivo_csv(carpeta_obj)
        if not archivo_csv:
            print(f"AVISO: No hay archivo CSV en: {carpeta_obj.name}")
            continue

        nombre_carpeta = carpeta_obj.name
        with open(archivo_csv, encoding="utf-8-sig", newline="") as flujo:
            filas = list(csv.DictReader(flujo))

        for fila in filas:
            nombre_video = fila.get("video", fila.get("archivo", ""))
            if not nombre_video:
                continue

            nombre_video_norm = normalizar_nombre_archivo_video(nombre_video)
            ruta_dropbox = f"/VIDEOS-PUBLICIDAD-PROEDITS/{nombre_carpeta}/{nombre_video_norm}"

            lista_global.append({
                "fila": fila,
                "nombre_carpeta": nombre_carpeta,
                "nombre_video": nombre_video_norm,
                "ruta_dropbox": ruta_dropbox,
            })

    return lista_global


def filtrar_tareas_pendientes(tareas_totales, redes_disponibles, historial):
    """Filtra y agrupa unicamente los destinos que faltan por publicar."""
    pendientes = []

    for tarea in tareas_totales:
        nombre_video = tarea["nombre_video"]
        carpeta = tarea["nombre_carpeta"]

        faltantes = []
        for destino in DESTINOS_PUBLICACION:
            clave_destino = destino[0]
            red = destino[1]

            if red not in redes_disponibles:
                continue

            clave_con_carpeta = f"{carpeta}/{nombre_video}|{clave_destino}"
            clave_simple = f"{nombre_video}|{clave_destino}"

            if clave_con_carpeta in historial or clave_simple in historial:
                continue

            faltantes.append(destino)

        if faltantes:
            pendientes.append((tarea, faltantes))

    return pendientes


def calcular_fecha_publicacion(tiempo_base, indice_video):
    """Calcula la fecha de publicacion espaciada exactamente cada 30 minutos."""
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
    nombre_carpeta,
    clave_destino,
    url_video,
    tipo_envio,
    fecha_envio,
):
    """Construye y envia la peticion de creacion/programacion hacia Postiz."""
    tiene_texto = tipo_publicacion == "post"
    nombre_dj = obtener_nombre_dj(fila, nombre_carpeta)
    contenido = (
        generar_contenido_texto(fila, nombre_carpeta)
        if tiene_texto
        else f"<p>🔥 Nuevo update {nombre_dj} · ProEditsClub</p>"
    )

    numero_identificador = fila.get("numero") or fila.get("id") or "1"
    ajustes_red = construir_configuracion_red(red, tipo_publicacion, fila, nombre_carpeta)

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

    for indice, (tarea, destinos_faltantes) in enumerate(pendientes):
        fila = tarea["fila"]
        nombre_video = tarea["nombre_video"]
        carpeta = tarea["nombre_carpeta"]
        ruta_dropbox = tarea["ruta_dropbox"]

        fecha_programada, tipo_envio = calcular_fecha_publicacion(tiempo_inicio, indice)
        destinos_nombres = ", ".join(d[0] for d in destinos_faltantes)
        nombre_dj = obtener_nombre_dj(fila, carpeta)
        genero = deducir_genero_musical(fila, carpeta)

        print(
            f"{indice + 1:>2}. [{carpeta}] {nombre_video} ({nombre_dj} · {genero}) -> {tipo_envio} "
            f"{fecha_programada.astimezone():%d/%m %H:%M} [{destinos_nombres}]"
        )

        if MODO_SIMULACION:
            continue

        url_video_dropbox = obtener_enlace_directo_dropbox(ruta_dropbox, token_dropbox)

        for clave_destino, red, post_type, _ in destinos_faltantes:
            canal_id, _ = redes_activas[red]
            try:
                enviar_publicacion_postiz(
                    clave_postiz=clave_postiz,
                    canal_id=canal_id,
                    red=red,
                    tipo_publicacion=post_type,
                    fila=fila,
                    nombre_carpeta=carpeta,
                    clave_destino=clave_destino,
                    url_video=url_video_dropbox,
                    tipo_envio=tipo_envio,
                    fecha_envio=fecha_programada,
                )
                clave_registro = f"{carpeta}/{nombre_video}|{clave_destino}"
                historial.add(clave_registro)
                guardar_historial_publicados(ARCHIVO_HISTORIAL, historial)
                print(f"      ok {clave_destino}")
                time.sleep(1.5)
            except Exception as error_envio:
                print(f"      FALLO {clave_destino}: {error_envio}")


def main():
    """Punto de entrada principal para el procesamiento multicarpetas."""
    historial = cargar_historial_publicados(ARCHIVO_HISTORIAL)

    clave_postiz = os.environ.get("POSTIZ_API_KEY", TOKEN_POSTIZ_POR_DEFECTO)
    token_dropbox = os.environ.get("DROPBOX_TOKEN", TOKEN_DROPBOX_POR_DEFECTO)

    if not MODO_SIMULACION and not (clave_postiz and token_dropbox):
        raise SystemExit("Faltan POSTIZ_API_KEY y/o DROPBOX_TOKEN.")

    redes_activas = obtener_canales_activos(clave_postiz)
    print("Canales conectados:", ", ".join(f"{k} -> {v[0]}" for k, v in redes_activas.items()))

    if "instagram" not in redes_activas:
        print("AVISO: No hay canal de Instagram conectado; se omitira Instagram.")
    if "tiktok" not in redes_activas:
        print("AVISO: No hay canal de TikTok conectado; se omitira TikTok.")
    if "facebook" not in redes_activas:
        print("AVISO: No hay canal de Facebook conectado; se omitira Facebook.")

    tareas_totales = recolectar_tareas_de_todas_las_carpetas(CARPETAS_DROPBOX_PREDETERMINADAS)
    print(f"Total de videos detectados en todas las carpetas: {len(tareas_totales)}")

    pendientes = filtrar_tareas_pendientes(tareas_totales, redes_activas, historial)

    if not pendientes:
        print("No hay tareas pendientes por publicar.")
        return

    print(f"Videos con publicaciones pendientes: {len(pendientes)}")

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
        print("Proceso de publicacion y programacion multicarpetas finalizado.")


if __name__ == "__main__":
    main()