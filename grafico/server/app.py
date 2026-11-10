"""UltraPixel — grafico AI online.
Il cliente scrive e carica foto/logo; Claude (API) capisce il brief e disegna le proposte con lo strumento `mostra_proposte`,
che le rende con grafico.py (progetto.py). Il cliente sceglie una proposta e la invia a UltraPixel dal modulo (lead.php) con il file di stampa.

Variabili d'ambiente: ANTHROPIC_API_KEY (obbligatoria), MODEL (default claude-sonnet-5-5), LEAD_ENDPOINT, MAX_TURNI, MAX_SESSIONI_ORA.
Le sessioni stanno in memoria (un solo processo): al riavvio del servizio si perdono, come una conversazione chiusa.
"""
import base64, io, json, os, re, sys, threading, time, uuid
from flask import Flask, Response, jsonify, request, send_from_directory, abort

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import progetto, immagini  # noqa: E402
from concurrent.futures import ThreadPoolExecutor

MODEL = os.environ.get("MODEL", "claude-opus-5-5")
MAX_TURNI = int(os.environ.get("MAX_TURNI", "20"))
MAX_SESSIONI_ORA = int(os.environ.get("MAX_SESSIONI_ORA", "8"))
MAX_IMMAGINI = int(os.environ.get("MAX_IMMAGINI", "9"))   # illustrazioni generate per conversazione
LEAD_ENDPOINT = os.environ.get("LEAD_ENDPOINT", "https://ultrapixel.it/backend/api/lead.php")
SYSTEM = open(os.path.join(HERE, "prompt.md"), encoding="utf-8").read().replace("ESEMPI_JSON", open(os.path.join(HERE, "esempi.json"), encoding="utf-8").read())

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

def STATO():
    return ("Illustrazioni AI (immagine_ai): ATTIVE, al massimo " + str(MAX_IMMAGINI) + " per conversazione.") if os.environ.get("OPENAI_API_KEY") else "Illustrazioni AI (immagine_ai): NON attive, non usarle."

def client():
    import anthropic
    return anthropic.Anthropic()

def png_controllo(items):  # piatte grandi per poter giudicare i dettagli
    """Etichette piatte affiancate (e il contenitore della prima) in un PNG per lo sguardo del modello."""
    import resvg_py
    from PIL import Image
    ims = []
    for it in items:
        for key, w in (("piatta", 640), ("contenitore", 300)):
            try:
                ims.append(Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=it[key], width=w)))).convert("RGB"))
            except Exception:
                pass
    if not ims:
        return None
    H = max(i.height for i in ims); out = Image.new("RGB", (sum(i.width for i in ims) + 16 * (len(ims) + 1), H + 32), (233, 231, 225)); x = 16
    for i in ims:
        out.paste(i, (x, 16 + H - i.height)); x += i.width + 16
    if out.width > 2800:
        out = out.resize((2800, int(out.height * 2800 / out.width)))
    b = io.BytesIO(); out.save(b, "JPEG", quality=80); return base64.b64encode(b.getvalue()).decode()

CHECK = ("\n\nOra guarda l'immagine come un direttore artistico. Checklist: 1) sembra il lavoro di un grafico professionista o una clipart? "
         "2) gerarchia chiara (marchio, prodotto, diciture) e corpi leggibili? 3) allineamenti e spazi coerenti, niente vuoti casuali o elementi schiacciati? "
         "4) sembra un template (immagine sopra, fascia sotto, nome centrato in bastoni)? ogni direzione ha un'idea forte e un linguaggio visivo riconoscibile, e le tre sono davvero diverse? 5) lavorazioni sensate e stampabili? 6) il contenitore somiglia a quello del cliente? "
         "Se anche un punto non è all'altezza, correggi le proposte e richiama mostra_proposte. Altrimenti rispondi al cliente.")

def illustra(sess, props):
    """Genera (in parallelo) le illustrazioni richieste dalle proposte che non sono già pronte. Restituisce le note per il modello."""
    if not os.environ.get("OPENAI_API_KEY"):
        return ["Illustrazioni AI non attive su questo servizio: non usare immagine_ai."] if any(e.get("tipo") == "immagine_ai" for p in props for e in (p.get("elementi") or [])) else []
    cache = sess.setdefault("ill", {}); job = {}
    for p in props:
        for e in (p.get("elementi") or []):
            if e.get("tipo") == "immagine_ai" and str(e.get("descrizione", "")).strip():
                k = immagini.chiave(e)
                if k not in cache and k not in job:
                    job[k] = e
    note = []
    resto = MAX_IMMAGINI - sess.get("n_img", 0)
    if len(job) > max(0, min(4, resto)):
        note.append(f"Limite illustrazioni: ne genero {max(0, min(4, resto))} su {len(job)} richieste; riusa quelle già fatte (stessa descrizione e stile).")
        job = dict(list(job.items())[:max(0, min(4, resto))])
    def one(k, e):
        lav = e.get("livello", "stampa") != "stampa"
        rp = bool(e.get("riempi")) and not lav
        png = immagini.genera(str(e.get("descrizione")), e.get("stile", "incisione"), str(e.get("colori", "")), lav, e.get("formato", "quadrato"), rp, str(e.get("zona", ""))[:80])
        return k, immagini.prepara(png, per_lavorazione=lav, sagoma=not lav and not rp, riempi=rp)
    if job:
        sess["n_img"] = sess.get("n_img", 0) + len(job)
        with ThreadPoolExecutor(max_workers=4) as ex:
            for fut in [ex.submit(one, k, e) for k, e in job.items()]:
                try:
                    k, a = fut.result(); cache[k] = a
                except Exception as err:
                    app.logger.error("illustrazione non generata: %s", err); note.append("Un'illustrazione non è stata generata: usa un'alternativa.")
    return note

def esegui_strumento(sess, inp, giro=0):
    props = (inp.get("proposte") or [])[:3]; out = []; testo = illustra(sess, props)
    for n, p in enumerate(props):
        pid = uuid.uuid4().hex[:10]
        try:
            r = progetto.anteprime(p, sess.get("logo"), k=f"p{n}", illustrazioni=sess.get("ill"))
        except Exception as ex:
            testo.append(f"Proposta {n+1} ({p.get('nome', '')}): errore {type(ex).__name__}, non disegnata."); continue
        sess["proposte"][pid] = {"p": p, "r": r, "t": time.time()}
        out.append({"id": pid, "nome": str(p.get("nome", ""))[:60], "concetto": str(p.get("concetto", ""))[:300], "spec": r["spec"]})
        testo.append(f"Proposta {n+1} «{p.get('nome', '')}»: " + ("avvisi: " + "; ".join(r["avvisi"]) if r["avvisi"] else "nessun avviso") + ".")
    # una correzione può ridisegnare solo alcune proposte: le altre di questo turno restano visibili
    nuovi = {o["nome"] for o in out}
    sess["ultime"] = [o for o in sess.get("ultime", []) if o["nome"] not in nuovi] + out
    sess["ultime"] = sess["ultime"][-3:]
    content = [{"type": "text", "text": ("\n".join(testo) or "Nessuna proposta disegnata.") + (CHECK if giro == 0 else "\n\nUltima revisione possibile: correggi solo errori evidenti, poi rispondi.")}]
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

MSG = {
    "troppe": {"it": "Hai aperto molte conversazioni nell'ultima ora: riprova più tardi o scrivici a info@ultrapixel.it.", "en": "You have opened many conversations in the last hour: please try later or write to info@ultrapixel.it.",
               "fr": "Vous avez ouvert beaucoup de conversations ces dernières heures : réessayez plus tard ou écrivez à info@ultrapixel.it.", "de": "Sie haben in der letzten Stunde viele Gespräche gestartet: bitte später erneut versuchen oder an info@ultrapixel.it schreiben."},
    "occupato": {"it": "Sto ancora lavorando alla risposta precedente.", "en": "I am still working on the previous answer.", "fr": "Je travaille encore sur la réponse précédente.", "de": "Ich arbeite noch an der vorherigen Antwort."},
    "limite": {"it": "Abbiamo raggiunto il limite di questa conversazione: scegli una proposta o scrivici a info@ultrapixel.it.", "en": "This conversation has reached its limit: choose a proposal or write to info@ultrapixel.it.",
               "fr": "Cette conversation a atteint sa limite : choisissez une proposition ou écrivez à info@ultrapixel.it.", "de": "Dieses Gespräch hat sein Limit erreicht: wählen Sie einen Vorschlag oder schreiben Sie an info@ultrapixel.it."},
    "server": {"it": "Qualcosa non ha funzionato. Riprova tra poco.", "en": "Something went wrong. Please try again shortly.", "fr": "Un problème est survenu. Réessayez dans un instant.", "de": "Etwas ist schiefgelaufen. Bitte gleich noch einmal versuchen."},
}
def msg(k, d):
    l = str(d.get("lang", "it"))[:2]
    return MSG[k].get(l, MSG[k]["en"])

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
    return {"ok": True, "chiave": bool(os.environ.get("ANTHROPIC_API_KEY")), "model": MODEL, "immagini": bool(os.environ.get("OPENAI_API_KEY"))}

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
                return jsonify(error="troppe", msg=msg("troppe", d)), 429
            IPS[ip()] = a + [now]; sid = uuid.uuid4().hex
            sess = S[sid] = {"messages": [], "logo": None, "proposte": {}, "ultime": [], "turni": 0, "t": now, "busy": False}
        if sess["busy"]:
            return jsonify(error="occupato", msg=msg("occupato", d)), 409
        if sess["turni"] >= MAX_TURNI:
            return jsonify(error="limite", msg=msg("limite", d)), 429
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
        giro = 0
        for _ in range(4):
            res = c.messages.create(model=MODEL, max_tokens=12000, system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}, {"type": "text", "text": STATO() + " Lingua della pagina del cliente: " + str(d.get("lang", "it"))[:2] + " (rispondi comunque nella lingua in cui scrive il cliente)."}],
                                    tools=[TOOL], messages=msgs)
            msgs.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in res.content]})
            uses = [b for b in res.content if b.type == "tool_use"]
            reply = "\n".join(b.text for b in res.content if b.type == "text").strip()
            if not uses:
                break
            results = [{"type": "tool_result", "tool_use_id": u.id, "content": esegui_strumento(sess, u.input, giro)} for u in uses]; giro += 1
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
        return jsonify(sid=sid, error="server", msg=msg("server", d)), 500
    finally:
        sess["busy"] = False

@app.get("/api/file/<sid>/<pid>/<kind>.svg")
def file(sid, pid, kind):
    sess = S.get(sid); pr = sess and sess["proposte"].get(pid)
    if not pr or kind not in ("contenitore", "piatta"):   # il file di stampa non si scarica: va solo a UltraPixel
        abort(404)
    return Response(pr["r"][kind], mimetype="image/svg+xml", headers={"Cache-Control": "private, max-age=3600"})

SELF_ORIGIN = os.environ.get("SELF_ORIGIN", "https://ultrapixel-grafico.onrender.com")

@app.post("/api/invia")
def invia():
    """Il cliente sceglie una proposta: il server manda a UltraPixel (lead.php -> info@) dati, riepilogo e file di stampa."""
    import urllib.request
    d = request.get_json(force=True, silent=True) or {}
    sess = S.get(d.get("sid", "")); pr = sess and sess["proposte"].get(d.get("pid", ""))
    if not pr:
        return jsonify(error="sessione", msg="La conversazione è scaduta: ricarica la pagina."), 404
    f = {k: str(d.get(k, "")).strip()[:300] for k in ("name", "company", "email", "country", "qty", "phone", "notes", "lang", "utm_source", "utm_medium", "utm_campaign", "referrer")}
    if not f["name"] or not f["company"] or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", f["email"]):
        return jsonify(error="campi"), 400
    if sess.get("inviate", 0) >= 3:
        return jsonify(error="limite", msg="Hai già inviato le tue scelte: ti rispondiamo presto."), 429
    testo = riepilogo_testo(sess, pr) + f"\n\nQuantità: {f['qty']}" + (f"\nTelefono: {f['phone']}" if f["phone"] else "") + (f"\nNote: {f['notes'][:1500]}" if f["notes"] else "")
    fields = {"name": f["name"], "company": f["company"], "email": f["email"], "country": f["country"], "sector": "other", "request_type": "label-design-ai",
              "message": testo[:4900], "lang": f["lang"] or "it", "source_page": SELF_ORIGIN + "/", "landing_page": "/", "referrer": f["referrer"],
              "utm_source": f["utm_source"], "utm_medium": f["utm_medium"], "utm_campaign": f["utm_campaign"], "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "website": ""}
    b = uuid.uuid4().hex; body = b""
    for k, v in fields.items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    nome = re.sub(r"[^a-z0-9]+", "-", str(pr["p"].get("nome", "proposta")).lower()).strip("-")[:40] or "proposta"
    body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="etichetta-{nome}.svg"\r\nContent-Type: image/svg+xml\r\n\r\n').encode() + pr["r"]["stampa"].encode() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(LEAD_ENDPOINT, data=body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={b}", "Origin": SELF_ORIGIN, "Accept": "application/json", "User-Agent": "UltraPixel-grafico"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            ok = r.status == 200
    except Exception as ex:
        app.logger.error("invio lead fallito: %s", ex); ok = False
    if not ok:
        return jsonify(error="invio", msg="Invio non riuscito. Riprova o scrivici a info@ultrapixel.it."), 502
    sess["inviate"] = sess.get("inviate", 0) + 1
    return jsonify(ok=True)

@app.post("/api/pacchetto")
def pacchetto():
    """Il firewall di Keliweb blocca le richieste che partono dai server di Render: l'invio a lead.php lo fa il browser del cliente.
    Dopo che il cliente ha lasciato i suoi dati, il server gli consegna una volta sola testo di riepilogo e file di stampa da inoltrare."""
    d = request.get_json(force=True, silent=True) or {}
    sess = S.get(d.get("sid", "")); pr = sess and sess["proposte"].get(d.get("pid", ""))
    if not pr:
        return jsonify(error="sessione", msg="La conversazione è scaduta: ricarica la pagina."), 404
    if sess.get("inviate", 0) >= 3:
        return jsonify(error="limite", msg="Hai già inviato le tue scelte: ti rispondiamo presto."), 429
    if not str(d.get("name", "")).strip() or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(d.get("email", ""))):
        return jsonify(error="campi"), 400
    sess["inviate"] = sess.get("inviate", 0) + 1
    nome = re.sub(r"[^a-z0-9]+", "-", str(pr["p"].get("nome", "proposta")).lower()).strip("-")[:40] or "proposta"
    return jsonify(testo=riepilogo_testo(sess, pr), svg=pr["r"]["stampa"], filename=f"etichetta-{nome}.svg", endpoint=LEAD_ENDPOINT)

def riepilogo_testo(sess, pr):
    brief = []
    for m in sess["messages"]:
        if m["role"] == "user" and isinstance(m["content"], list):
            t = " ".join(c.get("text", "") for c in m["content"] if c.get("type") == "text" and not c.get("text", "").startswith("("))
            if t.strip():
                brief.append("- " + t.strip()[:600])
    p = pr["p"]
    lines = ["[Grafico AI dal sito] Proposta scelta: " + str(p.get("nome", "")), "Concetto: " + str(p.get("concetto", "")), ""] + pr["r"]["spec"] + \
            ["Contenitore: " + json.dumps(p.get("contenitore", {}), ensure_ascii=False), "Logo caricato: " + ("sì" if sess.get("logo") else "no"), "", "Messaggi del cliente:"] + brief[:12]
    return "\n".join(lines)[:4000]

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 8080)), debug=False)
