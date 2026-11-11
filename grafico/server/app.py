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
    sess["_disegnato"] = True
    props = (inp.get("proposte") or [])[:3]; out = []; testo = illustra(sess, props)
    for n, p in enumerate(props):
        pid = uuid.uuid4().hex[:10]
        try:
            r = progetto.anteprime(p, sess.get("logo"), k=f"p{n}", illustrazioni=sess.get("ill"))
        except Exception as ex:
            testo.append(f"Proposta {n+1} ({p.get('nome', '')}): errore {type(ex).__name__}, non disegnata."); continue
        sess["proposte"][pid] = {"p": p, "r": r, "t": time.time()}
        out.append({"id": pid, "nome": str(p.get("nome", ""))[:60], "concetto": str(p.get("concetto", ""))[:300], "spec": r["spec"], "p": p})
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
    "account": {"it": "Per usare lo studio accedi o registra la tua azienda.", "en": "To use the studio, sign in or register your company.", "fr": "Pour utiliser le studio, connectez-vous ou enregistrez votre entreprise.", "de": "Um das Studio zu nutzen, melden Sie sich an oder registrieren Sie Ihr Unternehmen."},
    "pagamento": {"it": "Hai usato i giri gratuiti. Per continuare a modificare le proposte sblocca altri giri, oppure scegli una proposta: la inviamo a UltraPixel e ti prepariamo il preventivo.",
                  "en": "You have used your free rounds. To keep editing, unlock more rounds, or choose a proposal: we send it to UltraPixel and prepare your quote.",
                  "fr": "Vous avez utilisé vos tours gratuits. Pour continuer à modifier, débloquez d'autres tours, ou choisissez une proposition : nous l'envoyons à UltraPixel et préparons votre devis.",
                  "de": "Sie haben Ihre kostenlosen Runden genutzt. Um weiter zu ändern, schalten Sie weitere Runden frei, oder wählen Sie einen Vorschlag: Wir senden ihn an UltraPixel und erstellen Ihr Angebot."},
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

SESS_DIR = os.environ.get("SESS_DIR", "")   # con un disco persistente di Render (es. /data/sessioni) le conversazioni sopravvivono a riavvii e aggiornamenti

def salva(sid, sess):
    if not SESS_DIR:
        return
    try:
        os.makedirs(SESS_DIR, exist_ok=True); tmp = os.path.join(SESS_DIR, sid + ".tmp")
        data = {k: v for k, v in sess.items() if k != "busy"}
        data["proposte"] = {k: {"p": v["p"], "t": v.get("t", 0)} for k, v in sess["proposte"].items()}   # le anteprime si ridisegnano quando servono
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, os.path.join(SESS_DIR, sid + ".json"))
    except Exception as ex:
        app.logger.error("sessione non salvata: %s", ex)

def carica(sid):
    if not SESS_DIR or not re.match(r"^[0-9a-f]{32}$", sid or ""):
        return None
    try:
        with open(os.path.join(SESS_DIR, sid + ".json")) as f:
            sess = json.load(f)
        sess["busy"] = False
        if sess.get("logo"):
            sess["logo"] = tuple(sess["logo"])
        return sess
    except Exception:
        return None

def proposta(sess, pid):
    """La proposta con le sue anteprime (ridisegnate se la sessione è stata ricaricata dal disco)."""
    pr = sess and sess["proposte"].get(pid)
    if pr and "r" not in pr:
        pr["r"] = progetto.anteprime(pr["p"], sess.get("logo"), k="d" + pid[:4], illustrazioni=sess.get("ill"))
    return pr

def ripristina(sess, r):
    """Il servizio si è riavviato e la sessione è persa: il browser rimanda la conversazione (testi, proposte, logo) e la ricostruiamo."""
    storia = []
    for m in (r.get("storia") or [])[-30:]:
        chi = "Cliente" if m.get("r") == "u" else "Grafico"
        storia.append(f"{chi}: {str(m.get('t', ''))[:1500]}")
    props = [x for x in (r.get("proposte") or [])[:3] if isinstance(x, dict) and isinstance(x.get("p"), dict)]
    lg = r.get("logo") or {}
    if lg.get("data") and re.match(r"^[A-Za-z0-9+/=]+$", str(lg["data"])[:200]) and len(lg["data"]) < 4_000_000:
        mt = lg.get("type") if lg.get("type") in ("image/jpeg", "image/png", "image/webp") else "image/png"
        sess["logo"] = (f"data:{mt};base64,{lg['data']}", max(.1, min(10, float(lg.get("ratio") or 1))))
    rimappa = {}
    for x in props:
        try:
            pid = uuid.uuid4().hex[:10]; rr_ = progetto.anteprime(x["p"], sess.get("logo"), k="r" + pid[:4], illustrazioni=sess.get("ill"))
            sess["proposte"][pid] = {"p": x["p"], "r": rr_, "t": time.time()}; rimappa[str(x.get("id", ""))] = pid
        except Exception:
            pass
    testo = ("(La conversazione riprende dopo un riavvio del servizio: il cliente non deve accorgersene. Ecco cosa ci siamo detti finora:)\n" + "\n".join(storia) +
             "\n(Ultime proposte mostrate al cliente, nel linguaggio di disegno: partine da qui per le modifiche, mantenendo testi, formato e contenitore. "
             "Le illustrazioni AI già generate non sono più disponibili: se servono, rigenerale con la stessa descrizione.)\n" + json.dumps([x["p"] for x in props], ensure_ascii=False)[:40000])
    return testo, rimappa

# ——— foto realistiche: generate in sottofondo dopo le proposte, il browser le chiede finché non sono pronte ———
MAX_FOTO = int(os.environ.get("MAX_FOTO", "12"))   # foto per conversazione
FOTO_POOL = ThreadPoolExecutor(3)
FOTO = {}   # pid -> {"stato": "corso"|"ok"|"errore", "jpg": bytes}

def _foto_path(pid):
    return os.path.join(SESS_DIR, "foto", pid + ".jpg") if SESS_DIR else ""

def _png(svg, **kw):
    import resvg_py
    return bytes(resvg_py.svg_to_bytes(svg_string=svg, **kw))

def avvia_foto(sess, pid):
    if pid in FOTO or not os.environ.get("OPENAI_API_KEY") or (_foto_path(pid) and os.path.exists(_foto_path(pid))):
        return
    if sess.get("n_foto", 0) >= MAX_FOTO:
        return
    pr = proposta(sess, pid)
    if not pr:
        return
    sess["n_foto"] = sess.get("n_foto", 0) + 1; FOTO[pid] = {"stato": "corso"}
    def lavora():
        try:
            jpg = immagini.foto(_png(pr["r"]["piatta"], width=1024), _png(pr["r"]["contenitore"], width=640), pr["p"].get("contenitore"), pr["r"].get("spec"))
            FOTO[pid] = {"stato": "ok", "jpg": jpg}
            if SESS_DIR:
                os.makedirs(os.path.dirname(_foto_path(pid)), exist_ok=True)
                with open(_foto_path(pid), "wb") as f:
                    f.write(jpg)
        except Exception as ex:
            app.logger.error("foto %s: %s", pid, ex); FOTO[pid] = {"stato": "errore"}
    FOTO_POOL.submit(lavora)

@app.get("/api/foto/<sid>/<pid>.jpg")
def foto(sid, pid):
    if not re.match(r"^[0-9a-f]{10}$", pid or ""):
        abort(404)
    f = FOTO.get(pid) or {}
    if f.get("stato") == "ok":
        return Response(f["jpg"], mimetype="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})
    fp = _foto_path(pid)
    if fp and os.path.exists(fp):
        return send_from_directory(os.path.dirname(fp), pid + ".jpg", mimetype="image/jpeg", max_age=86400)
    if f.get("stato") == "corso":
        return jsonify(stato="corso"), 202
    if f.get("stato") == "errore":
        return jsonify(stato="errore"), 404
    sess = S.get(sid) or carica(sid)
    if sess and sid not in S:
        S[sid] = sess
    if not sess or pid not in sess["proposte"]:
        abort(404)
    avvia_foto(sess, pid)
    return (jsonify(stato="corso"), 202) if pid in FOTO else (jsonify(stato="limite"), 404)

# ——— accesso riservato a UltraPixel: elenco delle conversazioni salvate (per recuperare una proposta) ———
ADMIN_SHA = os.environ.get("ADMIN_SHA", "db603ca7607c90b069f3427503cc827475c2970636a4b0060b905cc26a59f5b2")

@app.get("/api/admin/sessioni")
def admin_sessioni():
    import hashlib
    k = request.args.get("k", "")
    if not k or hashlib.sha256(k.encode()).hexdigest() != ADMIN_SHA:
        abort(404)
    out = []
    for fn in sorted(os.listdir(SESS_DIR) if SESS_DIR and os.path.isdir(SESS_DIR) else [], key=lambda f: -os.path.getmtime(os.path.join(SESS_DIR, f)))[:60]:
        if not fn.endswith(".json"):
            continue
        try:
            s = json.load(open(os.path.join(SESS_DIR, fn)))
        except Exception:
            continue
        primo = next((b.get("text", "") for m in s.get("messages", []) if m.get("role") == "user" for b in (m["content"] if isinstance(m["content"], list) else [{"text": m["content"]}]) if isinstance(b, dict) and b.get("type", "text") == "text"), "")
        out.append({"sid": fn[:-5], "agg": os.path.getmtime(os.path.join(SESS_DIR, fn)), "primo": primo[:300],
                    "proposte": [{"pid": pid, "nome": v["p"].get("nome"), "t": v.get("t"), "foto": bool(_foto_path(pid) and os.path.exists(_foto_path(pid)))} for pid, v in s.get("proposte", {}).items()]})
    return jsonify(out)

import account, urllib.request, urllib.error
account.init()
COOKIE = "up_t"
def acc_corrente():
    return account.da_token(request.cookies.get(COOKIE, ""))

def ip():
    return (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()

@app.get("/")
def home():
    return send_from_directory(os.path.join(HERE, "static"), "index.html")

@app.get("/prova")
def prova():   # versione di prova con il brief guidato (stessa pagina: lo script vede /prova e mostra le schede)
    return send_from_directory(os.path.join(HERE, "static"), "index.html")

# ——— brief guidato: dalle risposte a schede l'AI scrive il brief come lo scriverebbe un grafico ———
BRIEF_MODEL = os.environ.get("BRIEF_MODEL", "claude-sonnet-5-5")
BRIEF_IPS = {}
SETTORI = open(os.path.join(os.path.dirname(HERE), "settori.md"), encoding="utf-8").read()
LINGUA = {"it": "italiano", "en": "English", "fr": "français", "de": "Deutsch"}

@app.post("/api/brief")
def brief():
    d = request.get_json(force=True, silent=True) or {}
    now = time.time(); a = [t for t in BRIEF_IPS.get(ip(), []) if now - t < 3600]
    if len(a) >= 20:
        return jsonify(error="limite"), 429
    BRIEF_IPS[ip()] = a + [now]
    risposte = json.dumps(d.get("risposte") or {}, ensure_ascii=False)[:6000]
    lg = d.get("lang") if d.get("lang") in LINGUA else "it"
    istr = ("Sei l'art director di UltraPixel, stampatore di etichette premium. Un cliente ha compilato un brief guidato a schede. "
            "Scrivi il brief di progetto per il grafico, in " + LINGUA[lg] + ", chiaro e professionale, in testo semplice (niente markdown, niente #, niente asterischi): ogni sezione inizia con un titoletto in MAIUSCOLO, gli elenchi con il trattino. Sezioni: "
            "Prodotto e cliente; Contenitore e formato; Testi obbligatori (riportali ESATTAMENTE come scritti dal cliente, tra virgolette; non inventare nomi, annate, gradazioni o volumi); "
            "Testi mancanti (le diciture obbligatorie per il settore che il cliente non ha dato: elencale come 'da definire', senza inventarle); "
            "Stile e atmosfera (traduci le scelte in indicazioni visive concrete: riferimenti, tipografia, palette, composizione, cosa evitare); "
            "Materiale e lavorazioni (solo quelle fattibili da UltraPixel); Allegati. "
            "Massimo 250 parole. Niente premesse, niente saluti: solo il brief.\n\nRegole di settore e limiti di stampa:\n" + SETTORI)
    try:
        res = client().messages.create(model=BRIEF_MODEL, max_tokens=4000, system=istr,
                                       messages=[{"role": "user", "content": "Risposte del cliente (JSON):\n" + risposte}])
        return jsonify(brief="\n".join(b.text for b in res.content if b.type == "text").strip())
    except Exception as ex:
        app.logger.exception("brief")
        return jsonify(error="server", msg=str(ex)[:200]), 500

@app.get("/static/<path:f>")
def static_f(f):
    return send_from_directory(os.path.join(HERE, "static"), f)

@app.get("/health")
def health():
    return {"ok": True, "chiave": bool(os.environ.get("ANTHROPIC_API_KEY")), "model": MODEL, "immagini": bool(os.environ.get("OPENAI_API_KEY"))}

# ——— account aziendali ———
REG_IPS = {}
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[A-Za-z]{2,}$")

def _lim(store, n):
    now = time.time(); a = [t for t in store.get(ip(), []) if now - t < 3600]
    if len(a) >= n:
        return False
    store[ip()] = a + [now]; return True

def _risposta_codice(ok, cod, err, email, extra=None):
    if not ok:
        return jsonify(error="codice", msg=err or ""), 429 if err == "troppi" else 502
    j = {"ok": True, "email": email, **(extra or {})}
    if cod:
        j["prova_codice"] = cod   # SMTP non configurato: modalità prova
    return jsonify(j)

@app.post("/api/account/vies")
def acc_vies():
    d = request.get_json(force=True, silent=True) or {}
    paese = str(d.get("paese", "")).upper()[:2]; piva = account.pulisci_piva(paese, d.get("piva"))
    if not _lim(REG_IPS, 40) or not piva:
        return jsonify(valida=None)
    v, nome, ind = account.vies(paese, piva)
    return jsonify(valida=v, ragione=nome, indirizzo=ind, piva=piva)

@app.post("/api/account/registra")
def acc_registra():
    d = request.get_json(force=True, silent=True) or {}
    if not _lim(REG_IPS, 40):
        return jsonify(error="troppe"), 429
    email = str(d.get("email", "")).strip().lower()[:120]; lg = d.get("lang") if d.get("lang") in ("it", "en", "fr", "de") else "en"
    if not EMAIL_RE.match(email):
        return jsonify(error="email"), 400
    esiste = account.per_email(email)
    if esiste and esiste.get("verificato"):
        ok, cod, err = account.manda_codice(email, lg)
        return _risposta_codice(ok, cod, err, email, {"esiste": True})
    paese = str(d.get("paese", "")).upper()[:2]; piva = account.pulisci_piva(paese, d.get("piva"))
    f = {k: str(d.get(k, "")).strip()[:200] for k in ("referente", "ragione", "indirizzo", "cap", "citta", "sdi", "pec", "telefono")}
    if not re.match(r"^[A-Z]{2}$", paese) or len(piva) < 5 or not f["referente"]:
        return jsonify(error="campi"), 400
    v, nome, ind = account.vies(paese, piva)
    if v is False:
        return jsonify(error="piva"), 400
    f["ragione"] = f["ragione"] or nome
    if not f["indirizzo"] and ind:
        f["indirizzo"] = ind
    if not f["ragione"] or (not ind and not (f["indirizzo"] and f["citta"])):
        return jsonify(error="campi"), 400
    if paese == "IT" and not (re.match(r"^[A-Za-z0-9]{7}$", f["sdi"]) or EMAIL_RE.match(f["pec"])):
        return jsonify(error="sdi"), 400
    account.salva({"email": email, **f, "paese": paese, "piva": piva, "piva_ok": 1 if v else 0, "lingua": lg,
                   "vies": json.dumps({"ragione": nome, "indirizzo": ind}, ensure_ascii=False) if v else None})
    ok, cod, err = account.manda_codice(email, lg)
    return _risposta_codice(ok, cod, err, email)

@app.post("/api/account/accedi")
def acc_accedi():
    d = request.get_json(force=True, silent=True) or {}
    email = str(d.get("email", "")).strip().lower()[:120]
    if not _lim(REG_IPS, 40):
        return jsonify(error="troppe"), 429
    a = account.per_email(email)
    if not a:
        return jsonify(error="nessuno"), 404
    ok, cod, err = account.manda_codice(email, d.get("lang") or a.get("lingua") or "en")
    return _risposta_codice(ok, cod, err, email)

@app.post("/api/account/verifica")
def acc_verifica():
    d = request.get_json(force=True, silent=True) or {}
    email = str(d.get("email", "")).strip().lower()[:120]
    t, nuovo = account.verifica_codice(email, str(d.get("codice", "")))
    if not t:
        return jsonify(error="codice"), 400
    a = account.da_token(t)
    r = jsonify(ok=True, account=account.pubblico(a), nuovo=nuovo,
                lead=({"testo": "Nuova azienda registrata allo studio AI:\n" + "\n".join(f"{k}: {a.get(k) or ''}" for k in ("ragione", "referente", "email", "telefono", "paese", "piva", "indirizzo", "cap", "citta", "sdi", "pec"))
                       + f"\nPartita IVA verificata VIES: {'sì' if a.get('piva_ok') else 'no / non UE'}", "endpoint": LEAD_ENDPOINT} if nuovo else None))
    r.set_cookie(COOKIE, t, max_age=180 * 86400, httponly=True, secure=True, samesite="Lax")
    return r

@app.get("/api/account/me")
def acc_me():
    a = acc_corrente()
    return jsonify(account=account.pubblico(a) if a else None)

@app.post("/api/account/esci")
def acc_esci():
    account.esci(request.cookies.get(COOKIE, "")); r = jsonify(ok=True); r.delete_cookie(COOKIE); return r

@app.post("/api/admin/immagine")
def admin_immagine():
    """Genera un'immagine (per le grafiche del sito, es. l'ingresso): solo con la chiave riservata."""
    import hashlib, base64 as b64
    d = request.get_json(force=True, silent=True) or {}
    k = d.get("k", "")
    if not k or hashlib.sha256(k.encode()).hexdigest() != ADMIN_SHA:
        abort(404)
    body = {"model": d.get("model") or immagini.MODELLI[0], "prompt": d["prompt"], "size": d.get("size", "1024x1536"), "n": 1, "quality": d.get("quality", "high")}
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            j = json.load(r)
        return jsonify(b64=j["data"][0].get("b64_json"), model=body["model"])
    except urllib.error.HTTPError as e:
        return jsonify(error=e.code, msg=e.read()[:400].decode("utf-8", "replace"), model=body["model"]), 502

@app.get("/api/admin/account")
def admin_account():
    import hashlib
    k = request.args.get("k", "")
    if not k or hashlib.sha256(k.encode()).hexdigest() != ADMIN_SHA:
        abort(404)
    if request.args.get("email") and request.args.get("giri"):
        return jsonify(account.aggiungi_giri(request.args["email"].lower(), int(request.args["giri"])))
    return jsonify(account.elenco())

@app.post("/api/chat")
def chat():
    d = request.get_json(force=True, silent=True) or {}
    sid = d.get("sid") or ""
    with LOCK:
        now = time.time()
        for k in [k for k, v in S.items() if now - v["t"] > 6 * 3600]:
            S.pop(k, None)
        if SESS_DIR and os.path.isdir(SESS_DIR):   # privacy: conversazioni cancellate dopo 30 giorni
            for fn in os.listdir(SESS_DIR):
                fp = os.path.join(SESS_DIR, fn)
                try:
                    if now - os.path.getmtime(fp) > 30 * 86400:
                        os.remove(fp)
                except OSError:
                    pass
        sess = S.get(sid) or carica(sid)
        if sess:
            S[sid] = sess
        elif sid and not d.get("ripristino"):
            return jsonify(error="persa"), 410   # il browser rimanda la conversazione con "ripristino"
        if not sess:
            a = [t for t in IPS.get(ip(), []) if now - t < 3600]
            if len(a) >= MAX_SESSIONI_ORA:
                return jsonify(error="troppe", msg=msg("troppe", d)), 429
            IPS[ip()] = a + [now]; vecchio = sid; sid = uuid.uuid4().hex
            sess = S[sid] = {"messages": [], "logo": None, "proposte": {}, "ultime": [], "turni": 0, "t": now, "busy": False}
        if sess["busy"]:
            return jsonify(error="occupato", msg=msg("occupato", d)), 409
        acc = acc_corrente()
        if os.environ.get("REQUIRE_ACCOUNT", "1") != "0" and not acc:   # lo studio si usa solo da registrati
            return jsonify(error="account", msg=msg("account", d)), 401
        if acc:
            u, tot = account.giri(acc)
            if u >= tot:
                return jsonify(error="pagamento", msg=msg("pagamento", d), account=account.pubblico(acc)), 402
            sess["acc"] = acc["id"]
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
        rimappa = {}
        if d.get("ripristino") and not sess["messages"]:
            prima, rimappa = ripristina(sess, d["ripristino"]); sess["turni"] += len(d["ripristino"].get("storia") or []) // 2
            content.insert(0, {"type": "text", "text": prima})
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
        salva(sid, sess)
        for o in sess["ultime"]:
            avvia_foto(sess, o["id"])
        info = None
        if sess.pop("_disegnato", False) and sess.get("acc"):
            account.conta_giro(sess["acc"])
        a2 = acc_corrente()
        if a2:
            info = account.pubblico(a2)
        return jsonify(sid=sid, reply=reply, proposte=sess["ultime"], turni_rimasti=MAX_TURNI - sess["turni"], rimappa=rimappa, account=info)
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
    sess = S.get(sid) or carica(sid); pr = proposta(sess, pid)
    if sess and sid not in S:
        S[sid] = sess
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
    sess = S.get(d.get("sid", "")) or carica(d.get("sid", "")); pr = proposta(sess, d.get("pid", ""))
    if not pr:
        return jsonify(error="sessione", msg="La conversazione è scaduta: ricarica la pagina."), 404
    if sess.get("inviate", 0) >= 3:
        return jsonify(error="limite", msg="Hai già inviato le tue scelte: ti rispondiamo presto."), 429
    acc = acc_corrente()
    if acc:   # cliente registrato: i dati li abbiamo già
        for k, ka in (("name", "referente"), ("email", "email"), ("company", "ragione"), ("country", "paese"), ("phone", "telefono")):
            d[k] = d.get(k) or acc.get(ka) or ""
    if not str(d.get("name", "")).strip() or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(d.get("email", ""))):
        return jsonify(error="campi"), 400
    sess["inviate"] = sess.get("inviate", 0) + 1; salva(d.get("sid", ""), sess)
    nome = re.sub(r"[^a-z0-9]+", "-", str(pr["p"].get("nome", "proposta")).lower()).strip("-")[:40] or "proposta"
    pid = d.get("pid", "")
    for _ in range(45):   # la foto è ancora in preparazione: la aspettiamo un po', così arriva insieme al file
        if (FOTO.get(pid) or {}).get("stato") != "corso":
            break
        time.sleep(2)
    jpg = (FOTO.get(pid) or {}).get("jpg")
    if not jpg and _foto_path(pid) and os.path.exists(_foto_path(pid)):
        jpg = open(_foto_path(pid), "rb").read()
    import zipfile
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"etichetta-{nome}.svg", pr["r"]["stampa"])
        if jpg:
            zf.writestr(f"rendering-{nome}.jpg", jpg)
        try:
            zf.writestr(f"anteprima-contenitore-{nome}.png", _png(pr["r"]["contenitore"], width=800))
            zf.writestr(f"anteprima-etichetta-{nome}.png", _png(pr["r"]["piatta"], width=1200))
        except Exception as ex:
            app.logger.error("anteprime zip: %s", ex)
    fisc = ("\n\nDATI DI FATTURAZIONE (account studio)\n" + "\n".join(f"{k}: {acc.get(k) or ''}" for k in ("ragione", "referente", "email", "telefono", "piva", "paese", "indirizzo", "cap", "citta", "sdi", "pec"))
            + f"\nP.IVA verificata VIES: {'sì' if acc.get('piva_ok') else 'no'} · giri usati: {acc.get('giri_usati')}") if acc else ""
    testo = riepilogo_testo(sess, pr) + fisc + "\n\nNello ZIP: file di stampa (SVG a livelli)" + (", rendering realistico visto dal cliente (JPG)" if jpg else "") + ", anteprime PNG."
    return jsonify(testo=testo, zip=base64.b64encode(z.getvalue()).decode(), zipname=f"ultrapixel-{nome}.zip",
                   svg=pr["r"]["stampa"], filename=f"etichetta-{nome}.svg", endpoint=LEAD_ENDPOINT)

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
