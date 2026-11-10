"""Illustrazioni generate con il modello immagini di OpenAI e preparate per la stampa.

- genera(descrizione, stile, per_lavorazione): chiama l'API Images (OPENAI_API_KEY, IMAGE_MODEL) e restituisce un PNG.
  Il prompt è costruito qui, con regole fisse: nessun testo, nessuna cornice, soggetto isolato, adatto a un'etichetta.
- prepara(png, per_lavorazione): {"png": data URL, "ratio": w/h, "vettore": (paths, w, h) | None}.
  Per foil e rilievo il disegno diventa vettoriale (potrace): l'oro e il rilievo vogliono forme nette, non pixel.
"""
import base64, io, json, os, urllib.request
import numpy as np
from PIL import Image

MODELLI = [m for m in [os.environ.get("IMAGE_MODEL", "").strip(), "gpt-image-2.5-flare", "gpt-image-2", "gpt-image-1.5", "gpt-image-1"] if m]
STILI = {
    "incisione": "fine engraving / etching illustration, crisp black linework with cross-hatching, vintage botanical plate quality",
    "acquerello": "delicate watercolor illustration, soft washes, subtle paper texture inside the shapes, refined and premium",
    "linea": "elegant single-weight line art, clean continuous lines, minimal, generous negative space",
    "pittura": "painterly gouache illustration, rich but harmonious colors, artisanal and premium",
    "piatta": "flat vector-style illustration, few solid colors, clean shapes, contemporary",
}
LAVORAZIONE = ("pure black and white artwork only: solid black shapes and bold lines on a plain white background, no grays, no gradients, "
               "no thin hairlines, no textures, shapes thick enough to be hot-foil stamped or embossed")

def prompt(descrizione, stile, colori, per_lavorazione, riempi=False, zona=""):
    s = STILI.get(stile, stile if isinstance(stile, str) and len(stile) > 12 else STILI["incisione"])
    if riempi:
        return (f"Full-bleed artwork for a premium product label, filling the entire frame edge to edge: {descrizione.strip()[:700]}. Style: {s}. "
                + (f"Color palette: {colori.strip()[:200]}. " if colori else "")
                + (f"Keep a calm, uncluttered area {zona} where typography will be placed later. " if zona else "")
                + "Strong, distinctive composition worthy of an award-winning label designer; no generic clip-art look. Absolutely no text, no letters, no numbers, no logos, no frame, no border, no mockup, no bottle: only the flat artwork.")
    base = (f"Illustration for a premium product label: {descrizione.strip()[:500]}. Style: {s}. "
            "Single isolated subject, centered, nothing cut off at the edges. Absolutely no text, no letters, no numbers, no logos, "
            "no frame, no border, no background scenery unless the description asks for it.")
    if per_lavorazione:
        return base + " " + LAVORAZIONE
    return base + (f" Color palette: {colori.strip()[:200]}." if colori else "") + " Transparent background."

def _post(model, p, size, transparent):
    body = {"model": model, "prompt": p, "size": size, "n": 1, "quality": os.environ.get("IMAGE_QUALITY", "medium")}
    if transparent:
        body["background"] = "transparent"
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        j = json.load(r)
    d = j["data"][0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    with urllib.request.urlopen(d["url"], timeout=60) as r:
        return r.read()

def genera(descrizione, stile="incisione", colori="", per_lavorazione=False, formato="quadrato", riempi=False, zona=""):
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("manca OPENAI_API_KEY")
    size = {"verticale": "1024x1536", "orizzontale": "1536x1024"}.get(formato, "1024x1024")
    p = prompt(descrizione, stile, colori, per_lavorazione, riempi, zona); err = None
    for m in MODELLI:
        for transparent in ((False,) if (per_lavorazione or riempi) else (True, False)):
            try:
                return _post(m, p, size, transparent)
            except urllib.error.HTTPError as e:
                err = f"{m}: {e.code} {e.read()[:200]!r}"
                if e.code in (401, 429):   # chiave sbagliata o credito/limite: inutile provare altri modelli
                    raise RuntimeError(err)
            except Exception as e:
                err = f"{m}: {e}"
    raise RuntimeError(err or "generazione non riuscita")

def _trasparente(im):
    """Se il modello ha messo uno sfondo chiaro uniforme, lo rende trasparente."""
    im = im.convert("RGBA"); a = np.array(im).astype(np.int16)
    if (a[..., 3] < 250).mean() > .05:     # è già trasparente
        return im
    bg = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)[:3]
    if bg.mean() < 200:
        return im
    dist = np.abs(a[..., :3] - bg).sum(-1)
    a[..., 3] = np.clip((dist - 12) * 6, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")

def _ritaglia(im):
    bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    if bb:
        pad = 8; bb = (max(0, bb[0]-pad), max(0, bb[1]-pad), min(im.width, bb[2]+pad), min(im.height, bb[3]+pad)); im = im.crop(bb)
    return im

def vettorializza(im, lato=900, modo="nero"):
    """modo nero: le parti scure diventano tracciati (disegni per foil/rilievo); modo sagoma: tutta la figura (rilievo sotto un'illustrazione a colori)."""
    import potrace
    g = im.convert("RGBA"); s = min(1, lato / max(g.size)); g = g.resize((max(1, int(g.width * s)), max(1, int(g.height * s))))
    a = np.array(g).astype(np.int16); lum = (a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11)
    nero = (a[..., 3] > 128) if modo == "sagoma" else ((lum < 128) & (a[..., 3] > 128))
    pl = potrace.Bitmap(~nero).trace(turdsize=6, alphamax=1.0, opticurve=True, opttolerance=0.25)
    out = []
    for c in pl:
        p = c.start_point; d = f"M{p.x:.1f} {p.y:.1f}"
        for sg in c.segments:
            if sg.is_corner:
                d += f"L{sg.c.x:.1f} {sg.c.y:.1f}L{sg.end_point.x:.1f} {sg.end_point.y:.1f}"
            else:
                d += f"C{sg.c1.x:.1f} {sg.c1.y:.1f} {sg.c2.x:.1f} {sg.c2.y:.1f} {sg.end_point.x:.1f} {sg.end_point.y:.1f}"
        out.append(d + "Z")
    return ("".join(out), g.width, g.height)

def chiave(el):
    import hashlib
    per_lav = el.get("livello", "stampa") != "stampa"
    return hashlib.sha1(json.dumps([el.get("descrizione", ""), el.get("stile", ""), el.get("colori", ""), per_lav, el.get("formato", ""), bool(el.get("riempi")), el.get("zona", "")], ensure_ascii=False).encode()).hexdigest()[:16]

def prepara(png, per_lavorazione=False, sagoma=False, riempi=False):
    im = Image.open(io.BytesIO(png))
    if riempi:   # a tutta etichetta: niente scontorno, JPEG per tenere leggero il file
        im = im.convert("RGB"); b = io.BytesIO(); im.save(b, "JPEG", quality=88)
        return {"png": "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode(), "ratio": im.width / im.height, "vettore": None, "sagoma": None}
    im = _ritaglia(_trasparente(im))
    if max(im.size) > 1400:
        s = 1400 / max(im.size); im = im.resize((int(im.width * s), int(im.height * s)))
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return {"png": "data:image/png;base64," + base64.b64encode(b.getvalue()).decode(), "ratio": im.width / im.height,
            "vettore": vettorializza(im) if per_lavorazione else None, "sagoma": vettorializza(im, modo="sagoma") if sagoma else None}
