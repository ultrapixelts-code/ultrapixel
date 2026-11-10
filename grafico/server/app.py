"""UltraPixel — grafico AI online.
Il cliente scrive e carica foto/logo; Claude (API) capisce il brief e disegna le proposte con lo strumento `mostra_proposte`,
che le rende con grafico.py (progetto.py). Il cliente sceglie una proposta e la invia a UltraPixel dal modulo (lead.php) con il file di stampa.

Variabili d'ambiente: ANTHROPIC_API_KEY (obbligatoria), MODEL (default claude-sonnet-5-5), LEAD_ENDPOINT, MAX_TURNI, MAX_SESSIONI_ORA.
Le sessioni stanno in memoria (un solo processo): al riavvio del servizio si perdono, come una conversazione chiusa.
"""
import base64, io, json, os, re, sys, threading, time, uuid
from flask import Flask, Response, jsonify, request, send_from_directory, abort

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import progetto  # noqa: E402

MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")
MAX_TURNI = int(os.environ.get("MAX_TURNI", "20"))
MAX_SESSIONI_ORA = int(os.environ.get("MAX_SESSIONI_ORA", "8"))
LEAD_ENDPOINT = os.environ.get("LEAD_ENDPOINT", "https://ultrapixel.it/backend/api/lead.php")
SYSTEM = open(os.path.join(HERE, "prompt.md"), encoding="utf-8").read()

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 14 * 1024 * 1024
S, IPS, LOCK = {}, {}, threading.Lock()

TOOL = {
    "name": "mostra_proposte",
    "description": "Disegna e mostra al cliente da 1 a 3 proposte di etichetta sul suo contenitore. Restituisce un'immagine di controllo e gli avvisi di impaginazione.",
    "input_schema": {"type": "object", "required": ["proposte"], "properties": {"proposte": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
        "type": "object", "required": ["nome", "concetto", "formato", "materiale", "contenitore", "elementi"],
        "properties": {"nome": {"type": "string"}, "concetto": {"type": "string"},
                       "formato": {"type": "object", "properties": {"w": {"type": "number"}, "h": {"type": "number"}, "forma": {"type": "string"}, "raggio": {"type": "number"}}},
                       "materiale": {"type": "string"}, "foil": {"type": "string"},
                       "contenitore": {"type": "object", "properties": {"tipo": {"type": "string"}, "colore": {"type": "string"}, "tappo": {"type": "string"}, "d": {"type": "number"}, "h": {"type": "number"}, "liquido": {"type": "string"}}},
                       "elementi": {"type": "array", "items": {"type": "object"}}}}}}},
}

def client():
    import anthropic
    return anthropic.Anthropic()

def png_controllo(items):
    """Etichette piatte affiancate (e il contenitore della prima) in un PNG per lo sguardo del modello."""
    import resvg_py
    from PIL import Image
    ims = []
    for it in items:
        for key, w in (("piatta", 520), ("contenitore", 300)):
            try:
                ims.append(Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=it[key], width=w)))).convert("RGB"))
            except Exception:
                pass
    if not ims:
        return None
    H = max(i.height for i in ims); out = Image.new("RGB", (sum(i.width for i in ims) + 16 * (len(ims) + 1), H + 32), (233, 231, 225)); x = 16
    for i in ims:
        out.paste(i, (x, 16 + H - i.height)); x += i.width + 16
    if out.width > 2400:
        out = out.resize((2400, int(out.height * 2400 / out.width)))
    b = io.BytesIO(); out.save(b, "JPEG", quality=80); return base64.b64encode(b.getvalue()).decode()

def esegui_strumento(sess, inp):
    props = (inp.get("proposte") or [])[:3]; out, testo = [], []
    for n, p in enumerate(props):
        pid = uuid.uuid4().hex[:10]
        try:
            r = progetto.anteprime(p, sess.get("logo"), k=f"p{n}")
        except Exception as ex:
            testo.append(f"Proposta {n+1} ({p.get('nome', '')}): errore {type(ex).__name__}, non disegnata."); continue
        sess["proposte"][pid] = {"p": p, "r": r, "t": time.time()}
        out.append({"id": pid, "nome": str(p.get("nome", ""))[:60], "concetto": str(p.get("concetto", ""))[:300], "spec": r["spec"]})
        testo.append(f"Proposta {n+1} «{p.get('nome', '')}»: " + ("avvisi: " + "; ".join(r["avvisi"]) if r["avvisi"] else "nessun avviso") + ".")
    sess["ultime"] = out
    content = [{"type": "text", "text": "\n".join(testo) or "Nessuna proposta disegnata."}]
    img = png_controllo([sess["proposte"][o["id"]]["r"] for o in out]) if out else None
    if img:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img}})
    return content

def pota(messages):
    """Toglie le immagini di controllo dai turni passati (costano e non servono più)."""
    for m in messages[:-2]:
        if m["role"] == "user" and isinstance(m["content"], list):
            for c in m["content"]:
                if c.get("type") == "tool_result" and isinstance(c.get("content"), list):
                    c["content"] = [x for x in c["content"] if x.get("type") != "image"] or [{"type": "text", "text": "ok"}]

def ip():
    return (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()

@app.get("/")
def home():
    return send_from_directory(os.path.join(HERE, "static"), "index.html")

@app.get("/static/<path:f>")
def static_f(f):
    return send_from_directory(os.path.join(HERE, "static"), f)

@app.get("/health")
def health():
    return {"ok": True, "chiave": bool(os.environ.get("ANTHROPIC_API_KEY")), "model": MODEL}

@app.post("/api/chat")
def chat():
    d = request.get_json(force=True, silent=True) or {}
    sid = d.get("sid") or ""
    with LOCK:
        now = time.time()
        for k in [k for k, v in S.items() if now - v["t"] > 6 * 3600]:
            S.pop(k, None)
        sess = S.get(sid)
        if not sess:
            a = [t for t in IPS.get(ip(), []) if now - t < 3600]
            if len(a) >= MAX_SESSIONI_ORA:
                return jsonify(error="troppe", msg="Hai aperto molte conversazioni nell'ultima ora: riprova più tardi o scrivici a info@ultrapixel.it."), 429
            IPS[ip()] = a + [now]; sid = uuid.uuid4().hex
            sess = S[sid] = {"messages": [], "logo": None, "proposte": {}, "ultime": [], "turni": 0, "t": now, "busy": False}
        if sess["busy"]:
            return jsonify(error="occupato", msg="Sto ancora lavorando alla risposta precedente."), 409
        if sess["turni"] >= MAX_TURNI:
            return jsonify(error="limite", msg="Abbiamo raggiunto il limite di questa conversazione: scegli una proposta o scrivici a info@ultrapixel.it."), 429
        sess["busy"] = True; sess["turni"] += 1; sess["t"] = now
    try:
        text = str(d.get("text", ""))[:3000].strip()
        content = []
        for im in (d.get("images") or [])[:4]:
            data = str(im.get("data", "")); mt = im.get("type") if im.get("type") in ("image/jpeg", "image/png", "image/webp") else "image/jpeg"
            if not data or len(data) > 4_000_000 or not re.match(r"^[A-Za-z0-9+/=]+$", data[:200]):
                continue
            content.append({"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}})
            if im.get("logo"):
                ratio = float(im.get("ratio") or 1) or 1
                sess["logo"] = (f"data:{mt};base64,{data}", max(.1, min(10, ratio)))
                content.append({"type": "text", "text": "(Questa immagine è il logo del cliente: usalo con l'elemento logo.)"})
        if not text and not content:
            return jsonify(error="vuoto"), 400
        content.append({"type": "text", "text": text or "(immagini allegate)"})
        msgs = sess["messages"]; msgs.append({"role": "user", "content": content})
        sess["ultime"] = []; reply = ""; c = client()
        for _ in range(4):
            res = c.messages.create(model=MODEL, max_tokens=12000, system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                                    tools=[TOOL], messages=msgs)
            msgs.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in res.content]})
            uses = [b for b in res.content if b.type == "tool_use"]
            reply = "\n".join(b.text for b in res.content if b.type == "text").strip()
            if not uses:
                break
            results = [{"type": "tool_result", "tool_use_id": u.id, "content": esegui_strumento(sess, u.input)} for u in uses]
            msgs.append({"role": "user", "content": results})
        else:
            msgs.append({"role": "user", "content": [{"type": "text", "text": "(Rispondi ora al cliente in poche frasi, senza altri strumenti.)"}]})
            res = c.messages.create(model=MODEL, max_tokens=1500, system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}], messages=msgs, tools=[TOOL], tool_choice={"type": "none"})
            msgs.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in res.content]})
            reply = "\n".join(b.text for b in res.content if b.type == "text").strip()
        pota(msgs)
        return jsonify(sid=sid, reply=reply, proposte=sess["ultime"], turni_rimasti=MAX_TURNI - sess["turni"])
    except Exception as ex:
        app.logger.exception("chat")
        # la conversazione resta coerente: tolgo il turno incompleto
        while sess["messages"] and sess["messages"][-1]["role"] != "user":
            sess["messages"].pop()
        if sess["messages"]:
            sess["messages"].pop()
        return jsonify(sid=sid, error="server", msg="Qualcosa non ha funzionato. Riprova tra poco."), 500
    finally:
        sess["busy"] = False

@app.get("/api/file/<sid>/<pid>/<kind>.svg")
def file(sid, pid, kind):
    sess = S.get(sid); pr = sess and sess["proposte"].get(pid)
    if not pr or kind not in ("contenitore", "piatta", "stampa"):
        abort(404)
    headers = {"Cache-Control": "private, max-age=3600"}
    if kind == "stampa":
        headers["Content-Disposition"] = f'attachment; filename="etichetta-{re.sub(r"[^a-z0-9]+", "-", pr["p"].get("nome", "proposta").lower())[:40]}.svg"'
    return Response(pr["r"][kind], mimetype="image/svg+xml", headers=headers)

@app.get("/api/riepilogo/<sid>/<pid>")
def riepilogo(sid, pid):
    """Testo che accompagna la richiesta: proposta scelta, specifica e brief del cliente."""
    sess = S.get(sid); pr = sess and sess["proposte"].get(pid)
    if not pr:
        abort(404)
    brief = []
    for m in sess["messages"]:
        if m["role"] == "user" and isinstance(m["content"], list):
            t = " ".join(c.get("text", "") for c in m["content"] if c.get("type") == "text" and not c.get("text", "").startswith("("))
            if t.strip():
                brief.append("- " + t.strip()[:600])
    p = pr["p"]
    lines = ["[Grafico AI dal sito] Proposta scelta: " + str(p.get("nome", "")), "Concetto: " + str(p.get("concetto", "")), ""] + pr["r"]["spec"] + \
            ["Contenitore: " + json.dumps(p.get("contenitore", {}), ensure_ascii=False), "Logo caricato: " + ("sì" if sess.get("logo") else "no"), "", "Messaggi del cliente:"] + brief[:12]
    return jsonify(testo="\n".join(lines)[:4800], endpoint=LEAD_ENDPOINT)

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 8080)), debug=False)
