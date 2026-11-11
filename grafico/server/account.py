"""Account aziendali per lo studio: registrazione con dati di fatturazione, accesso con codice via mail, conteggio dei giri.

- I dati stanno in SQLite sul disco di Render (ACC_DB, di default accanto alle sessioni: /data/account.db).
- Accesso senza password: si riceve un codice di 6 cifre via mail (SMTP_*). Senza SMTP configurato il codice
  viene restituito alla pagina ("modalità prova"): da usare solo finché lo studio con account è sulla pagina /prova.
- Partita IVA UE verificata con VIES (registro europeo): se valida, ragione sociale e indirizzo vengono dal registro.
"""
import hashlib, json, os, re, secrets, smtplib, sqlite3, threading, time, urllib.request
from email.message import EmailMessage

_SESS = os.environ.get("SESS_DIR", "")
DB = os.environ.get("ACC_DB") or (os.path.join(os.path.dirname(_SESS.rstrip("/")), "account.db") if _SESS else os.path.join(os.path.dirname(__file__), "account.db"))
GIRI_GRATIS = int(os.environ.get("GIRI_GRATIS", "2"))
UE = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "XI"}
_L = threading.Lock()

def _db():
    c = sqlite3.connect(DB, timeout=10); c.row_factory = sqlite3.Row
    return c

def init():
    os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    with _L, _db() as c:
        c.executescript("""
        create table if not exists account(id integer primary key, email text unique not null, referente text, ragione text, piva text, paese text,
          indirizzo text, cap text, citta text, sdi text, pec text, telefono text, piva_ok integer default 0, vies text,
          creato real, verificato real, giri_usati integer default 0, giri_extra integer default 0, ultimo real, lingua text);
        create table if not exists codice(email text primary key, h text, scade real, tentativi integer default 0, inviati text);
        create table if not exists token(h text primary key, account integer, creato real, visto real);
        """)

def _h(s):
    return hashlib.sha256(s.encode()).hexdigest()

def pulisci_piva(paese, piva):
    p = re.sub(r"[^A-Za-z0-9]", "", piva or "").upper()
    if p[:2] == paese or (paese == "EL" and p[:2] == "GR"):
        p = p[2:]
    return p

def vies(paese, piva):
    """(valida: True/False/None se il registro non risponde, ragione, indirizzo)"""
    if paese not in UE:
        return None, "", ""
    try:
        with urllib.request.urlopen(f"https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{paese}/vat/{piva}", timeout=12) as r:
            j = json.load(r)
        if j.get("userError") not in ("VALID", "INVALID"):
            return None, "", ""
        nome = (j.get("name") or "").strip(); ind = (j.get("address") or "").strip()
        return bool(j.get("isValid")), ("" if nome in ("---", "") else nome), ("" if ind in ("---", "") else re.sub(r"\s*\n\s*", ", ", ind).strip(", "))
    except Exception:
        return None, "", ""

def smtp_ok():
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASS"))

def invia_mail(a, oggetto, testo):
    m = EmailMessage(); m["From"] = os.environ.get("SMTP_FROM") or os.environ["SMTP_USER"]; m["To"] = a; m["Subject"] = oggetto; m.set_content(testo)
    porta = int(os.environ.get("SMTP_PORT", "465"))
    if porta == 465:
        s = smtplib.SMTP_SSL(os.environ["SMTP_HOST"], porta, timeout=20)
    else:
        s = smtplib.SMTP(os.environ["SMTP_HOST"], porta, timeout=20); s.starttls()
    with s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(m)

OGG = {"it": "Il tuo codice per UltraPixel Studio", "en": "Your UltraPixel Studio code", "fr": "Votre code UltraPixel Studio", "de": "Ihr Code für UltraPixel Studio"}
TXT = {"it": "Ciao,\n\nil tuo codice di accesso a UltraPixel Studio è: {c}\n\nVale 15 minuti. Se non l'hai chiesto tu, ignora questa mail.\n\nUltraPixel – etichette su misura\nhttps://ultrapixel.it",
       "en": "Hello,\n\nyour UltraPixel Studio access code is: {c}\n\nIt is valid for 15 minutes. If you did not request it, please ignore this email.\n\nUltraPixel – custom labels\nhttps://ultrapixel.it",
       "fr": "Bonjour,\n\nvotre code d'accès à UltraPixel Studio est : {c}\n\nIl est valable 15 minutes. Si vous ne l'avez pas demandé, ignorez cet e-mail.\n\nUltraPixel – étiquettes sur mesure\nhttps://ultrapixel.fr",
       "de": "Hallo,\n\nIhr Zugangscode für UltraPixel Studio lautet: {c}\n\nEr ist 15 Minuten gültig. Falls Sie ihn nicht angefordert haben, ignorieren Sie diese E-Mail.\n\nUltraPixel – Etiketten nach Maß\nhttps://ultrapixel.it"}

def manda_codice(email, lingua):
    """Crea e invia il codice. Restituisce (ok, codice_se_modalita_prova, errore)."""
    now = time.time()
    with _L, _db() as c:
        r = c.execute("select inviati from codice where email=?", (email,)).fetchone()
        inv = [t for t in json.loads(r["inviati"] or "[]") if now - t < 3600] if r else []
        if len(inv) >= 5:
            return False, None, "troppi"
        cod = f"{secrets.randbelow(10**6):06d}"
        c.execute("insert or replace into codice(email,h,scade,tentativi,inviati) values(?,?,?,0,?)", (email, _h(email + cod), now + 900, json.dumps(inv + [now])))
    if not smtp_ok():
        return True, cod, None
    try:
        invia_mail(email, OGG.get(lingua, OGG["en"]), TXT.get(lingua, TXT["en"]).format(c=cod))
        return True, None, None
    except Exception as ex:
        return False, None, "mail: " + str(ex)[:120]

def verifica_codice(email, cod):
    now = time.time()
    with _L, _db() as c:
        r = c.execute("select * from codice where email=?", (email,)).fetchone()
        if not r or r["scade"] < now or r["tentativi"] >= 6:
            return None, False
        if r["h"] != _h(email + re.sub(r"\D", "", cod or "")):
            c.execute("update codice set tentativi=tentativi+1 where email=?", (email,)); return None, False
        c.execute("delete from codice where email=?", (email,))
        if not c.execute("select id from account where email=?", (email,)).fetchone():
            return None, False
        a = c.execute("select id, verificato from account where email=?", (email,)).fetchone()
        nuovo = not a["verificato"]
        c.execute("update account set verificato=coalesce(verificato,?), ultimo=? where id=?", (now, now, a["id"]))
        t = secrets.token_hex(24); c.execute("insert into token(h,account,creato,visto) values(?,?,?,?)", (_h(t), a["id"], now, now))
        return t, nuovo

def da_token(t):
    if not t or len(t) > 100:
        return None
    with _L, _db() as c:
        r = c.execute("select a.* from token t join account a on a.id=t.account where t.h=? and t.creato>?", (_h(t), time.time() - 180 * 86400)).fetchone()
        return dict(r) if r else None

def esci(t):
    with _L, _db() as c:
        c.execute("delete from token where h=?", (_h(t or ""),))

def per_email(email):
    with _L, _db() as c:
        r = c.execute("select * from account where email=?", (email,)).fetchone()
        return dict(r) if r else None

def salva(d):
    """Crea o aggiorna (se non ancora verificato) l'account. d già validato."""
    with _L, _db() as c:
        r = c.execute("select id, verificato from account where email=?", (d["email"],)).fetchone()
        campi = ["referente", "ragione", "piva", "paese", "indirizzo", "cap", "citta", "sdi", "pec", "telefono", "piva_ok", "vies", "lingua"]
        if r and r["verificato"]:
            return r["id"], False   # esiste già: si entra col codice, i dati non si sovrascrivono da qui
        if r:
            c.execute("update account set " + ",".join(f"{k}=?" for k in campi) + " where id=?", [d.get(k) for k in campi] + [r["id"]]); return r["id"], True
        cur = c.execute("insert into account(email," + ",".join(campi) + ",creato) values(?," + ",".join("?" * len(campi)) + ",?)", [d["email"]] + [d.get(k) for k in campi] + [time.time()])
        return cur.lastrowid, True

def giri(a):
    """(usati, disponibili totali)"""
    return a.get("giri_usati") or 0, GIRI_GRATIS + (a.get("giri_extra") or 0)

def conta_giro(aid):
    with _L, _db() as c:
        c.execute("update account set giri_usati=giri_usati+1, ultimo=? where id=?", (time.time(), aid))

def aggiungi_giri(email, n):
    with _L, _db() as c:
        c.execute("update account set giri_extra=giri_extra+? where email=?", (int(n), email))
        r = c.execute("select * from account where email=?", (email,)).fetchone()
        return dict(r) if r else None

def elenco():
    with _L, _db() as c:
        return [dict(r) for r in c.execute("select * from account order by creato desc limit 300")]

def pubblico(a):
    u, tot = giri(a)
    return {"email": a["email"], "ragione": a["ragione"], "referente": a["referente"], "paese": a["paese"], "piva": a["piva"],
            "giri_usati": u, "giri_totali": tot, "giri_rimasti": max(0, tot - u)}
