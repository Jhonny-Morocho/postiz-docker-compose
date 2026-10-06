"""Publica los videos de una carpeta de Dropbox via Postiz en:
   - Facebook: post de video + historia
   - Instagram: reel (post) + historia   (si el canal de Instagram esta conectado en Postiz)

El 1er video sale ya; los demas se programan cada CADA_MIN minutos.
Uso:  python publicar_videos.py --dry   (solo muestra, no envia nada)
      python publicar_videos.py         (publica de verdad)
Requiere variables de entorno: POSTIZ_API_KEY y DROPBOX_TOKEN.

Si lo vuelves a correr, solo envia lo que falta (lo ya enviado queda en publicados.json).
"""
import csv, json, os, re, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

CARPETA = Path(os.environ.get("CARPETA", r"C:\Users\Usuario iTC\Dropbox\VIDEOS-PUBLICIDAD-PROEDITS\dj-jordan-medina-productos-halloween-con-audio"))
RUTA_DROPBOX = "/VIDEOS-PUBLICIDAD-PROEDITS/dj-jordan-medina-productos-halloween-con-audio"
POSTIZ = os.environ.get("POSTIZ_URL", "http://localhost:4007/api/public/v1")
CANAL_FB = "cmux7ue880001nz8dp1z3y4da"  # Proeditsclub (Facebook) - por si no se detecta solo
CADA_MIN = 30
HECHOS = Path(__file__).with_name("publicados.json")  # evita duplicar si lo corres de nuevo
DRY = "--dry" in sys.argv

# Que se publica por cada video: (clave, red, post_type, lleva_texto)
DESTINOS = [
    ("fb_post",  "facebook",  "post",  True),
    ("fb_story", "facebook",  "story", False),
    ("ig_reel",  "instagram", "post",  True),   # en Instagram un video "post" sale como Reel
    ("ig_story", "instagram", "story", False),
]


def api(url, body, token, ok_409=False, method="POST"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data, {"Content-Type": "application/json", "Authorization": token}, method=method)
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        if ok_409 and e.code == 409:
            return json.loads(e.read())
        raise SystemExit(f"Error {e.code} en {url}: {e.read().decode()[:400]}")


def canales(postiz_key):
    """Busca en Postiz los canales de Facebook e Instagram -> {'facebook': (id, tipo), 'instagram': (id, tipo)}"""
    encontrados = {}
    if DRY and not postiz_key:
        return {"facebook": (CANAL_FB, "facebook"), "instagram": ("(id-instagram)", "instagram")}
    lista = api(f"{POSTIZ}/integrations", None, postiz_key, method="GET")
    for c in lista:
        ident = (c.get("identifier") or c.get("providerIdentifier") or "").lower()
        if c.get("disabled"):
            continue
        if ident == "facebook" and "facebook" not in encontrados:
            encontrados["facebook"] = (c["id"], ident)
        elif ident.startswith("instagram") and "instagram" not in encontrados:
            encontrados["instagram"] = (c["id"], ident)
    encontrados.setdefault("facebook", (CANAL_FB, "facebook"))
    return encontrados


def enlace_directo(archivo, token):
    ruta = f"{RUTA_DROPBOX}/{archivo}"
    r = api("https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings",
            {"path": ruta, "settings": {"requested_visibility": "public"}},
            "Bearer " + token, ok_409=True)
    url = r.get("url")
    if not url:  # ya existia un enlace: lo reutiliza
        r = api("https://api.dropboxapi.com/2/sharing/list_shared_links",
                {"path": ruta, "direct_only": True}, "Bearer " + token)
        url = r["links"][0]["url"]
    return url.replace("dl=0", "raw=1")


def partes(fila):
    """'100 BPM - Artista - Tema (INTRO OUTRO DSK DJ X FT. DJ JORDAN MEDINA 2026)' -> (tema, edit, bpm)"""
    p = fila["producto"].strip()
    m = re.match(r"^(\d+)\s*BPM\s*-\s*(.+?)\s*\((.+)\)\s*$", p)
    if not m:
        return p, "", ""
    bpm, tema, edit = m.groups()
    return " ".join(tema.split()), edit.strip(), bpm


def texto(fila):
    tema, edit, bpm = partes(fila)
    detalle = " · ".join(x for x in (edit, f"{bpm} BPM" if bpm else "") if x)
    lineas = ["🔥 NUEVO UPDATE de DJ JORDAN MEDINA 🔥", "",
              "🎧 " + tema] + ([detalle] if detalle else []) + ["",
              "Ya está disponible el nuevo update de DJ Jordan Medina en ProEditsClub. "
              "Edits listos para la cabina, con intros limpias y BPM exacto para tus mezclas.", "",
              "👉 Escúchalo y descárgalo aquí:", fila["link"], "",
              "#ProEditsClub #DJJordanMedina #DJ #Remix #Edits2026 #DJLife"]
    return "".join(f"<p>{l}</p>" for l in lineas)


def titulo(fila):
    tema, _, bpm = partes(fila)
    return (f"Nuevo update DJ Jordan Medina - {tema}" + (f" ({bpm} BPM)" if bpm else ""))[:250]


def ajustes(red, tipo_red, post_type, fila):
    s = {"__type": tipo_red, "post_type": post_type}
    if red == "facebook" and post_type == "post":
        s["title"] = titulo(fila)
    if red == "instagram":
        s["collaborators"] = []
    return s


def main():
    hechos = set(json.loads(HECHOS.read_text())) if HECHOS.exists() else set()
    # compatibilidad: la version anterior guardaba solo el nombre del video (= post de Facebook ya enviado)
    hechos = {h if "|" in h else f"{h}|fb_post" for h in hechos}

    postiz_key = 'cf8920774d1eab8b801a6b1126bbc8cb711975170065f1afdb7566c20fbbb8c2'
    dropbox = 'sl.u.AGyMDgW958vf2s9VHW4t0T_qhp-1jGYdaM9yp8-01Jd6mbY1DJ47cHbnZDNpWgQaaTHSTmnBB1ZITpWBomMRkWVV6tptHmGebAzvssFOrj2syqIvUNaiabalLFy5l9pKkhTGv1jDLb-FEk5PVYCPg-BWdrmAI1_OTg-j642iqKsQj8dgeYzhyrVZsSNQBuLNioCHBR15QFJAht7ekJyhFCOcxiXnuzHqnAaCFsT7WIAH5LoPK3zinAsjQjJmtUE8PR_uXsBket6eOw7klINHd9X6rLt9bIjBV1vypyMvegG4XgMaBn8DbyZreVUV800aIcC32Ysot4CMkViqW-VlKUIzopqnMyW5mCOrUrraOKdvOCDeq_CFow4hlLlJm9b78n6768QBpmI_43am51kUM9nTxRr3LPgGRM41-qLSLWZVSW0xnzOPt4kn2hs6MKCgKmifbpGTXZD12Li3NQiMnRpIjfC-Yc00uZTs7_7SHdwS_tzL_cRsqTM0p2M9In50NYUOv7WMPksvudS5OfCgMX5uS51ukepCsfzj1qn8ZBYixuLlC7BVUAz8ltgjbXGXpvuC8QfKo-ntgZEDKeIJj7_tJSvdwbhvgjr_4YmoJiMgqw1_GJl65QwdOm5x5DXLK95zGo7VPiO66w1j657YBijMwhWRL_2nlWWkyKDjn3F5w8xoEevHmf0U6HaBA8BiNQBriC_EhxpJYeByMqjJjIqMtuV9gZ9IQ4vk4BpfJsGkeCkd4uXQN89HBU4ci0w86r99EH2cm5nLOL4ngF76vub7Ug6zz6kB--3rADHChxShM9sqLBt8uCAgVOaiAnbHtKs9CJOdloFHngtiUvpUxUR6tWTP4YlF02X179lzB1V-FX4bcqJKhNw_X3Pdyr37RtVDwA8KskUIFwDQf3kIBCNVB39f_lnYvqJj3gecozV31ON-qhr4FmMMMy79bflqnKy55Ztgm2bDTFUyfyQZYiRoIDTG_iZ5mzUrg_xhvhrTrupDQJoJSYBnBryNQYJIDNpT8ltvUPwXHQee86UddSlCunQjWnbV4k6racWU-OIdnQa8BfpdnbqFt-e7GQfcwi8CsXYkMQnntT0atwAvHl2iAVYU4EN5vUzsJexEIeeR1kG1AObRJABhglZ7inP2OpXzIygKcO7ESPDgSjIYJfiC08AusWEADJ9056_oxEsia5fRmmHRoGcXEBYFTEWuUhogurAz5zzet174h0_qDBTY6FcRsSQNj8C9zYaXlWuDafnYcY95D9kiDgTvGMbxlyZlB7kSgY6BX_4DUFyHRQPBSJCRUv8nQiOTnP9XgqyJnyPkYVrJJmDagRgww84Ns0k'
    if not DRY and not (postiz_key and dropbox):
        raise SystemExit("Faltan POSTIZ_API_KEY y/o DROPBOX_TOKEN.")

    redes = canales(postiz_key)
    print("Canales:", ", ".join(f"{k} -> {v[0]}" for k, v in redes.items()))
    if "instagram" not in redes:
        print("AVISO: no hay canal de Instagram conectado en Postiz; solo se publicara en Facebook.")

    with open(CARPETA / "ids-y-links.csv", encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))

    pendientes = []
    for fila in filas:
        faltan = [d for d in DESTINOS if d[1] in redes and f"{fila['video']}|{d[0]}" not in hechos]
        if faltan:
            pendientes.append((fila, faltan))
    if not pendientes:
        raise SystemExit("No hay nada pendiente.")

    inicio = datetime.now(timezone.utc)
    for i, (fila, faltan) in enumerate(pendientes):
        fecha = inicio + timedelta(minutes=CADA_MIN * i)
        tipo = "now" if i == 0 else "schedule"
        print(f"{i+1:>2}. {fila['video']}  ->  {tipo}  {fecha.astimezone():%d/%m %H:%M}  [{', '.join(d[0] for d in faltan)}]")
        if DRY:
            continue
        video = enlace_directo(fila["video"], dropbox)
        for clave, red, post_type, con_texto in faltan:
            canal_id, tipo_red = redes[red]
            contenido = texto(fila) if con_texto else "<p>🔥 Nuevo update DJ Jordan Medina · ProEditsClub</p>"
            api(f"{POSTIZ}/posts", {
                "type": tipo, "date": fecha.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "shortLink": False, "tags": [],
                "posts": [{"integration": {"id": canal_id},
                           "value": [{"content": contenido,
                                      "image": [{"id": f"{fila['numero']}-{clave}", "path": video}]}],
                           "settings": ajustes(red, tipo_red, post_type, fila)}]}, postiz_key)
            hechos.add(f"{fila['video']}|{clave}")
            HECHOS.write_text(json.dumps(sorted(hechos), indent=1))
            print(f"      ok {clave}")
    print("Listo." if not DRY else "(simulacion: no se envio nada)")


main()