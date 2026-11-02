"""UltraPixel — anteprima "Scopri quanto costa la tua etichetta".

Serve il sito statico di questo ramo e due chiamate:
  POST /api/quote/analyze   foto o PDF dell'etichetta -> misura stimata, materiale, lavorazioni riconosciute
  POST /api/quote/price     misura + quantità + materiale + lavorazioni -> prezzo "a partire da"

Il calcolo resta qui sul server: al browser arrivano solo i prezzi, mai tariffe o formule.
Le immagini non vengono salvate: restano in memoria per la durata della richiesta.
"""
import base64, io, json, math, os, re, time, urllib.request, urllib.error
from collections import defaultdict, deque
from flask import Flask, abort, jsonify, request, send_from_directory

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

# ------------------------------------------------------------------ motore di costo
# Copia fedele di avviamentoProgressivoOre / battuteForRow / computeCost del "Docket Etichette"
# (claude/docket-pricing-engine.js nel progetto, artifact version 1789562730-5859). Se il motore cambia là, va riallineato qui.
RATES = dict(rClic=0.15, rXeikon=70.0, rGaranzia=25.0, rVernice=15.0, rRifinitura=60.0, rVarie=40.0, rLamina=0.65,
             vXeikon=600.0, vRifinituraSolo=4500.0, vRifinituraExtra=3000.0, vRifinituraEntrambe=2500.0,
             avviamentoMl=50.0, avviamentoVerniceMl=25.0)
LARGHEZZA_XEIKON_MM, LARGHEZZA_UTILE_MM, GUTTER_MM = 330.0, 310.0, 3.0

# Materiali proposti al cliente -> voce e prezzo del listino materiali (claude/preventivatore-materiali-prezzi.md)
MATERIALS = {
    "coated":   ("Fasson MC PRIMECOAT FSC S2045N", 0.37),
    "wine":     ("HGWINE PREMIUM FSC", 0.81),
    "textured": ("MARTELE BLANC PLUS", 1.30),
    "pp_white": ("PP60 TOP WHITE", 0.52),
    "pp_clear": ("PP60 TOP CLEAR", 0.55),
}
QTY_MIN, QTY_MAX = 250, 500000


def avviamento_ore(q):
    if q <= 1000:
        m = 10 + q * (10 / 1000)
    elif q < 10000:
        m = 20 + (q - 1000) * (40 / 9000)
    else:
        m = 60
    return m / 60


def compute_cost(qty, c):
    avv = avviamento_ore(qty)
    righe = math.ceil(qty / c["pose"])
    metri_tiratura = righe * (c["H"] + c["gutter"]) / 1000
    extra_lamina = max(0, c["numLamina"] - 1) if c["hasLamina"] else 0
    passaggi = 1 + 1 + extra_lamina
    metri_tot = metri_tiratura + passaggi * c["avviamentoMl"] + (c["avviamentoVerniceMl"] if c["hasVernice"] else 0)
    mq = metri_tot * (LARGHEZZA_XEIKON_MM / 1000)          # fustella esistente: bobina a piena larghezza Xeikon
    carta = mq * c["matPrice"]
    clic = metri_tot * c["rClic"]
    ore_x = avv + metri_tot / c["vXeikon"]
    xeikon = ore_x * c["rXeikon"]
    garanzia = ore_x * c["rGaranzia"]
    vel = c["vRifinituraEntrambe"] if (c["hasLamina"] and c["hasBraille"]) else c["vRifinituraExtra"] if (c["hasLamina"] or c["hasBraille"]) else c["vRifinituraSolo"]
    battute = math.ceil(righe / max(1, c["righeFustella"]))
    pass_rif = max(1, c["numLamina"]) if c["hasLamina"] else 1
    ore_r = pass_rif * (avv + battute / vel)
    rifinitura = ore_r * c["rRifinitura"]
    varie = (ore_x + ore_r) * c["rVarie"]
    vernice = ore_x * c["rVernice"] if c["hasVernice"] else 0
    lamina = (c["W"] * c["H"] / 1e6) * qty * c["coperturaLamina"] * c["numLamina"] * c["rLamina"] if c["hasLamina"] else 0
    return carta + clic + xeikon + garanzia + vernice + rifinitura + varie + lamina


def price_from(w, h, qty, material, varnish, foil, relief, foil_cov):
    """Prezzo ricorrente più basso reale per questa etichetta: fustella già disponibile, orientamento che rende di più sulla bobina,
    nessuna attrezzatura nuova, trasporto e IVA esclusi."""
    best = None
    for W, H in {(w, h), (h, w)}:
        if W + GUTTER_MM > LARGHEZZA_UTILE_MM:
            continue
        c = dict(RATES, W=W, H=H, gutter=GUTTER_MM, pose=int(LARGHEZZA_UTILE_MM // (W + GUTTER_MM)), righeFustella=1,
                 matPrice=MATERIALS[material][1], hasVernice=bool(varnish), hasLamina=foil > 0, numLamina=max(1, foil),
                 hasBraille=bool(relief), coperturaLamina=foil_cov)
        t = compute_cost(qty, c)
        best = t if best is None or t < best else best
    return best


# ------------------------------------------------------------------ limiti d'uso (in memoria, per indirizzo)
HITS = defaultdict(deque)


def limited(kind, n, seconds):
    ip = (request.headers.get("X-Forwarded-For", request.remote_addr or "") or "").split(",")[0].strip()
    q = HITS[(kind, ip)]; now = time.time()
    while q and q[0] < now - seconds:
        q.popleft()
    if len(q) >= n:
        return True
    q.append(now)
    return False


def num(v, lo, hi, default=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return x if lo <= x <= hi and math.isfinite(x) else default


@app.post("/api/quote/price")
def api_price():
    if limited("price", 240, 3600):
        return jsonify(error="rate"), 429
    d = request.get_json(silent=True) or {}
    w, h, qty = num(d.get("w"), 10, 1000), num(d.get("h"), 10, 1000), num(d.get("qty"), QTY_MIN, QTY_MAX)
    mat = d.get("material") if d.get("material") in MATERIALS else "coated"
    if not w or not h:
        return jsonify(error="size"), 400
    if not qty:
        return jsonify(error="qty", min=QTY_MIN, max=QTY_MAX), 400
    foil = int(num(d.get("foil"), 0, 2, 0)); cov = num(d.get("foil_cov"), 0.03, 0.8, 0.2)
    args = (round(w), round(h))
    rest = (mat, bool(d.get("varnish")), foil, bool(d.get("relief")), cov)
    qty = int(qty); total = price_from(*args, qty, *rest)
    if total is None:
        return jsonify(error="toolarge"), 400
    steps = sorted({q for q in (qty, _nice(qty * 2), _nice(qty * 5)) if q <= QTY_MAX})
    table = []
    for q in steps:
        t = price_from(*args, q, *rest)
        table.append({"qty": q, "total": math.ceil(t), "per1000": round(t / q * 1000, 2)})
    return jsonify(total=math.ceil(total), per1000=round(total / qty * 1000, 2), table=table,
                   config={"w": args[0], "h": args[1], "qty": qty, "material": mat, "varnish": rest[1], "foil": foil, "relief": rest[3]})


def _nice(q):
    m = 10 ** max(2, int(math.log10(q)) - 1)
    return int(round(q / m) * m)


# ------------------------------------------------------------------ lettura dell'immagine
VISION_PROMPT = """You are a label-printing estimator. The image shows a product label (photographed on a bottle/jar/pack, photographed flat, or a print-ready artwork file).
Return ONLY a JSON object, no prose, with these keys:
- "is_label": true if a product label is clearly visible, else false
- "width_mm", "height_mm": your best estimate of the real size of the main (front) label in millimetres, as integers. Use the container as a scale reference when visible (a standard 0.75 l wine bottle is about 75 mm in diameter and 300 mm tall; a 0.33 l beer bottle about 60 mm; a 0.5 l olive-oil bottle about 60 mm; a 212 ml jar about 65 mm). A label wrapping a cylinder is wider than it looks.
- "size_confidence": "high" if a clear scale reference is visible, "medium" if the container type is recognisable, "low" if the label is shown alone with no reference
- "container": short description of what the label is on, or "none"
- "material": one of "coated" (white smooth coated paper), "wine" (uncoated/natural matt wine paper), "textured" (visibly embossed, laid or felt-marked premium paper), "pp_white" (white plastic film), "pp_clear" (transparent film, the container shows through)
- "hot_foil": number of distinct metallic hot-foil colours you can see (0, 1 or 2). Count only truly reflective metallic areas, not yellow or grey ink.
- "foil_coverage": fraction of the label area covered by foil, 0 to 1
- "relief": true if you see embossing, raised tactile varnish or screen-printed gloss relief
- "varnish": true unless the surface is clearly raw unprotected paper
- "notes": one short sentence on what you are unsure about
If you cannot tell a value, give your most likely guess; never leave keys out."""


def call_vision(jpeg_bytes):
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None
    body = {"model": os.environ.get("QUOTE_VISION_MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 500,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(jpeg_bytes).decode()}},
                {"type": "text", "text": VISION_PROMPT}]}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        out = json.loads(r.read())
    text = "".join(b.get("text", "") for b in out.get("content", []))
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else None


def clean(v):
    """Keep only expected, bounded values from the model's answer."""
    if not isinstance(v, dict):
        return None
    mat = v.get("material") if v.get("material") in MATERIALS else "coated"
    conf = v.get("size_confidence") if v.get("size_confidence") in ("high", "medium", "low") else "low"
    return {"is_label": bool(v.get("is_label", True)), "w": num(v.get("width_mm"), 10, 600), "h": num(v.get("height_mm"), 10, 600),
            "size_confidence": conf, "material": mat, "foil": int(num(v.get("hot_foil"), 0, 2, 0)), "foil_cov": num(v.get("foil_coverage"), 0.03, 0.8, 0.2),
            "relief": bool(v.get("relief")), "varnish": bool(v.get("varnish", True))}


DIE_NAMES = re.compile(r"die|fustell|cut|kiss|stanz|d[eé]coupe|troquel|crease|contour|thru", re.I)


def label_box(doc, page):
    """Size of the label inside a print file. The die line wins over the page: a stroked, unfilled outline drawn in the
    usual die colours (green or magenta) or while the file declares a spot colour named like a die. Then trim box, art box, page."""
    pr = page.rect; cands = []
    try:
        spots = " ".join(doc.xref_object(x) for x in range(1, doc.xref_length()) if "/Separation" in (doc.xref_object(x) or ""))
        has_die_spot = bool(DIE_NAMES.search(" ".join(re.findall(r"/Separation\s*/([^\s/\[]+)", spots))))
        for d in page.get_drawings():
            c, r = d.get("color"), d.get("rect")
            if d.get("type") != "s" or not c or not r or (d.get("width") or 0) > 2.5:
                continue
            if r.width < 28 or r.height < 28 or (r.width > pr.width * .985 and r.height > pr.height * .985):
                continue                                         # under 1 cm, or the page frame itself
            rr, g, b = c[:3]
            green = g > .45 and g - rr > .25 and g - b > .15
            magenta = rr > .7 and b > .4 and g < .35
            if max(rr, g, b) > .97 and min(rr, g, b) > .97:
                continue                                         # white strokes are never the die
            if green or magenta or has_die_spot:
                cands.append(((2 if green or magenta else 1), r.width * r.height, r))
    except Exception:
        cands = []
    if cands:
        return max(cands, key=lambda x: (x[0], x[1]))[2], "die"
    for name in ("trimbox", "artbox"):
        b = getattr(page, name)
        if b.width > 1 and (abs(b.width - pr.width) > 1 or abs(b.height - pr.height) > 1):
            return b, name
    return pr, "page"


@app.post("/api/quote/analyze")
def api_analyze():
    if limited("analyze", 12, 3600) or limited("analyze-day", 30, 86400):
        return jsonify(error="rate"), 429
    f = request.files.get("file")
    if not f:
        return jsonify(error="nofile"), 400
    data = f.read(); kind = "photo"; exact = None; src = ""
    try:
        if data[:5] == b"%PDF-":
            import pymupdf as fitz
            doc = fitz.open(stream=data, filetype="pdf"); page = doc[0]
            box, src = label_box(doc, page)
            exact = (round(box.width / 72 * 25.4), round(box.height / 72 * 25.4)); kind = "pdf"
            clip = (box + (-9, -9, 9, 9)) & page.rect          # a little air around the label, never the whole sheet
            z = 1400 / max(clip.width, clip.height)
            data = page.get_pixmap(matrix=fitz.Matrix(z, z), clip=clip, alpha=False).tobytes("jpeg")
        else:
            from PIL import Image, ImageOps
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB"); im.thumbnail((1600, 1600))
            b = io.BytesIO(); im.save(b, "JPEG", quality=85); data = b.getvalue()
    except Exception:
        return jsonify(error="badfile"), 400
    res = {"kind": kind, "recognised": False}
    if kind == "pdf":
        res["preview"] = "data:image/jpeg;base64," + base64.b64encode(data).decode()
    try:
        v = clean(call_vision(data))
    except Exception as ex:
        app.logger.warning("vision failed: %s", type(ex).__name__); v = None
    if v:
        res.update(v, recognised=True)
    if exact:
        res.update(w=exact[0], h=exact[1], size_confidence="die" if src == "die" else "exact")
    return jsonify(res)


@app.get("/api/quote/status")
def api_status():
    return jsonify(vision=bool(os.environ.get("ANTHROPIC_API_KEY")))


# ------------------------------------------------------------------ chiamate dai siti pubblicati altrove
ALLOWED_ORIGINS = set(filter(None, os.environ.get("QUOTE_ORIGINS", "https://ultrapixel.it,https://www.ultrapixel.it,https://ultrapixel.fr,https://www.ultrapixel.fr").split(",")))


@app.after_request
def cors(resp):
    o = request.headers.get("Origin", "")
    if request.path.startswith("/api/") and o in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = o; resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"; resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Max-Age"] = "86400"
    return resp


@app.route("/api/<path:_p>", methods=["OPTIONS"])
def preflight(_p):
    return ("", 204)


# ------------------------------------------------------------------ sito statico
BLOCKED = ("server/", "content/", "src/", ".git", "build.py", "requirements.txt", "README.md", "render.yaml")


@app.get("/")
@app.get("/<path:p>")
def static_site(p=""):
    if p.startswith(BLOCKED) or p.endswith((".py", ".pyc")) or "/." in "/" + p:
        abort(404)
    full = os.path.join(ROOT, p)
    if os.path.isdir(full):
        if p and not p.endswith("/"):
            from flask import redirect
            return redirect("/" + p + "/", 301)
        p = os.path.join(p, "index.html")
    if not os.path.isfile(os.path.join(ROOT, p)):
        return send_from_directory(ROOT, "404.html"), 404
    return send_from_directory(ROOT, p)
