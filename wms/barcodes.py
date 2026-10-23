"""Barcode Recognition Engine.

Regole:
- I codici generati da UltraPixel OS hanno un prefisso esplicito (namespace), solo lettere
  maiuscole e cifre, così non dipendono dal layout tastiera dello scanner (niente trattini o
  simboli che una pistola in modalità tastiera US su PC italiano trasformerebbe):
      UPR000123  bobina        UPC000045  collo
      UPS000007  spedizione    UPL...     ubicazione (codice libero dopo il prefisso)
      UPW330     larghezza in mm (risposta al ricevimento, pulsante o cartellino)
      UPQ0..UPQ3 quanto resta sulla bobina a fine lavoro (finita, 1/4, 2/4, 3/4): cartellino in macchina
- I codici numerici esterni (commessa Madiwor, articolo, codice fornitore) NON sono riconosciuti
  dalla lunghezza: si cercano nel database. Se lo stesso codice corrisponde a più entità il
  risultato è AMBIGUO e serve contesto + conferma.
- GS1-128 (etichette fornitore con separatore FNC1/GS): si leggono solo gli Application
  Identifier standard (01 GTIN, 10 lotto, 21 seriale, 311n lunghezza in metri, 37 quantità).
- QR con URL: accettati solo dominio e percorso configurati in wms.settings. Il sistema non apre
  MAI l'URL: estrae l'identificativo e lo cerca nel proprio database.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from urllib.parse import urlsplit

INTERNAL = {
    "UPR": "ROLL",
    "UPC": "PACKAGE",
    "UPS": "SHIPMENT",
    "UPL": "LOCATION",
    "UPB": "BADGE",
}
INTERNAL_RE = re.compile(r"^(UPR|UPC|UPS)(\d{6})$|^(UPL|UPB)([A-Z0-9]{1,30})$")
QUARTI_RE = re.compile(r"^UPQ([0-4])$")
LARGHEZZA_RE = re.compile(r"^UPW(\d{2,4})$")
QUARTI_LABEL = {0: "Finita", 1: "1/4", 2: "2/4", 3: "3/4", 4: "Intera"}
GS = "\x1d"


@dataclass
class Candidate:
    tipo: str              # JOB, ROLL, PACKAGE, SHIPMENT, LOCATION, MATERIAL, FINISHED_PRODUCT, USER
    id: object
    etichetta: str
    fonte: str             # INTERNO, MADIWOR, ALIAS, GS1
    extra: dict = field(default_factory=dict)


@dataclass
class Recognition:
    raw: str
    normalized: str
    stato: str             # RICONOSCIUTO, AMBIGUO, SCONOSCIUTO, NON_VALIDO
    candidati: list[Candidate] = field(default_factory=list)
    gs1: dict = field(default_factory=dict)
    motivo: str | None = None

    @property
    def unico(self) -> Candidate | None:
        return self.candidati[0] if self.stato == "RICONOSCIUTO" else None


def normalize(raw: str) -> str:
    s = unicodedata.normalize("NFKC", raw or "")
    # FNC1 può arrivare come GS, come "]C1" (identificatore AIM) o come carattere ~ a seconda dello scanner
    s = s.replace("\r", "").replace("\n", "").replace("\t", "")
    if s.startswith("]C1") or s.startswith("]Q3") or s.startswith("]d2"):
        s = s[3:]
    return s.strip()


def printable(s: str) -> str:
    """Versione sicura da registrare/mostrare: caratteri di controllo resi visibili (\\x1d per GS)."""
    return "".join(c if c.isprintable() else f"\\x{ord(c):02x}" for c in (s or ""))[:512]


# --- GS1 --------------------------------------------------------------------
_FIXED = {"00": 18, "01": 14, "02": 14, "11": 6, "13": 6, "15": 6, "17": 6}
_VAR = {"10": 20, "21": 20, "37": 8}


def parse_gs1(s: str) -> dict | None:
    """Parser minimo GS1 element string. Ritorna None se non è GS1 valido."""
    if not (s.startswith("01") or s.startswith("02") or s.startswith("00")) or len(s) < 16:
        return None
    out, i = {}, 0
    try:
        while i < len(s):
            if s[i] == GS:
                i += 1
                continue
            ai2 = s[i:i + 2]
            if ai2 in _FIXED:
                ln = _FIXED[ai2]
                val = s[i + 2:i + 2 + ln]
                if len(val) != ln or not val.isdigit():
                    return None
                out[ai2] = val
                i += 2 + ln
            elif ai2 in _VAR:
                j = s.find(GS, i + 2)
                j = len(s) if j == -1 else j
                val = s[i + 2:j]
                if not val or len(val) > _VAR[ai2]:
                    return None
                out[ai2] = val
                i = j
            elif s[i:i + 3] in ("311", "312") and i + 4 <= len(s):
                dec = int(s[i + 3])
                val = s[i + 4:i + 10]
                if len(val) != 6 or not val.isdigit():
                    return None
                # 311n lunghezza, 312n larghezza: entrambe in metri
                out[s[i:i + 3]] = Decimal(val) / (Decimal(10) ** dec)
                i += 10
            else:
                return None
    except (ValueError, IndexError):
        return None
    if "01" in out and not _gtin_ok(out["01"]):
        return None
    return out


def _gtin_ok(g: str) -> bool:
    digits = [int(c) for c in g]
    check = digits[-1]
    s = sum(d * (3 if (len(digits) - 1 - idx) % 2 == 1 else 1) for idx, d in enumerate(digits[:-1]))
    return (10 - s % 10) % 10 == check


# --- QR ---------------------------------------------------------------------
def parse_qr_url(conn, s: str) -> tuple[str | None, str | None]:
    """(identificativo, errore). Solo domini/percorsi esplicitamente ammessi."""
    try:
        u = urlsplit(s)
    except ValueError:
        return None, "QR non leggibile"
    if u.scheme not in ("http", "https") or not u.hostname:
        return None, "QR con indirizzo non valido"
    from .engine import setting
    domini = [d.lower() for d in (setting(conn, "qr_domini_ammessi", []) or [])]
    if u.hostname.lower() not in domini:
        return None, f"QR di un dominio non ammesso ({u.hostname})"
    for pattern in setting(conn, "qr_percorsi_commessa", []) or []:
        m = re.fullmatch(pattern, u.path + (("?" + u.query) if u.query else ""))
        if m and m.groupdict().get("commessa"):
            return m.group("commessa"), None
    return None, "QR Madiwor con formato non ancora configurato"


# --- Riconoscimento ---------------------------------------------------------
def recognize(conn, raw: str) -> Recognition:
    s = normalize(raw)
    if not s:
        return Recognition(raw, s, "NON_VALIDO", motivo="Lettura vuota")
    if len(s) > 512 or any(ord(c) < 32 and c != GS for c in s):
        return Recognition(raw, printable(s), "NON_VALIDO", motivo="Lettura non valida")

    if s.lower().startswith(("http://", "https://")):
        ident, err = parse_qr_url(conn, s)
        if err:
            return Recognition(raw, s, "NON_VALIDO", motivo=err)
        rec = recognize(conn, ident)
        rec.raw = raw
        rec.candidati = [c for c in rec.candidati if c.tipo == "JOB"]
        rec.stato = "RICONOSCIUTO" if len(rec.candidati) == 1 else ("SCONOSCIUTO" if not rec.candidati else "AMBIGUO")
        return rec

    su = s.upper()
    q = QUARTI_RE.match(su)
    if q:
        n = int(q.group(1))
        return Recognition(raw, su, "RICONOSCIUTO", candidati=[Candidate("QUARTI", n, QUARTI_LABEL[n], "INTERNO")])
    w = LARGHEZZA_RE.match(su)
    if w:
        mm = int(w.group(1))
        return Recognition(raw, su, "RICONOSCIUTO", candidati=[Candidate("LARGHEZZA", mm, f"{mm} mm", "INTERNO")])
    m = INTERNAL_RE.match(su)
    if m:
        prefix = m.group(1) or m.group(3)
        return _internal(conn, raw, su, INTERNAL[prefix])
    if su.startswith(("UPR", "UPC", "UPS", "UPL", "UPB", "UPQ", "UPW")):
        return Recognition(raw, su, "NON_VALIDO", motivo="Codice interno malformato")

    gs1 = parse_gs1(s)
    if gs1:
        cands = []
        if "01" in gs1:
            cands = _aliases(conn, gs1["01"], namespaces=("GTIN", "FORNITORE"))
        rec = Recognition(raw, s, "RICONOSCIUTO" if len(cands) == 1 else ("AMBIGUO" if cands else "SCONOSCIUTO"),
                          candidati=cands, gs1={k: (str(v) if isinstance(v, Decimal) else v) for k, v in gs1.items()})
        if not cands:
            rec.motivo = "GTIN non associato a nessun materiale"
        return rec

    cands: list[Candidate] = []
    for r in conn.execute("SELECT id, external_madiwor_id, cliente_nome, stato FROM wms.production_jobs "
                          "WHERE external_madiwor_id=%s", (s,)).fetchall():
        cands.append(Candidate("JOB", r["id"], f"Commessa {r['external_madiwor_id']} — {r['cliente_nome']}", "MADIWOR",
                               {"stato": r["stato"]}))
    for r in conn.execute("SELECT id, external_sku_id, versione, descrizione FROM wms.finished_products "
                          "WHERE external_sku_id=%s", (s,)).fetchall():
        cands.append(Candidate("FINISHED_PRODUCT", r["id"], f"Articolo {r['external_sku_id']} v{r['versione']}", "MADIWOR"))
    cands += _aliases(conn, s)
    for r in conn.execute("SELECT id, display_name FROM wms.users WHERE badge_code=%s AND active", (s,)).fetchall():
        cands.append(Candidate("USER", r["id"], r["display_name"], "INTERNO"))
    stato = "RICONOSCIUTO" if len(cands) == 1 else ("AMBIGUO" if cands else "SCONOSCIUTO")
    return Recognition(raw, s, stato, candidati=cands, motivo=None if cands else "Codice sconosciuto")


def _aliases(conn, code: str, namespaces: tuple[str, ...] | None = None) -> list[Candidate]:
    q = """SELECT a.*, m.descrizione AS mat_descr FROM wms.barcode_aliases a
           LEFT JOIN wms.materials m ON a.entity_type='MATERIAL' AND m.id=a.entity_id
           WHERE a.code=%s"""
    args: list = [code]
    if namespaces:
        q += " AND a.namespace = ANY(%s)"
        args.append(list(namespaces))
    out = []
    for r in conn.execute(q, args).fetchall():
        label = r["mat_descr"] or r["code"]
        tipo = {"MATERIAL": "MATERIAL", "FINISHED_PRODUCT": "FINISHED_PRODUCT", "LOCATION": "LOCATION",
                "SUPPLIER": "SUPPLIER"}[r["entity_type"]]
        out.append(Candidate(tipo, r["entity_id"], label, "ALIAS",
                             {"namespace": r["namespace"], "identifica_unita": r["identifica_unita"],
                              "metri_dichiarati": r["metri_dichiarati"]}))
    return out


def _internal(conn, raw: str, code: str, tipo: str) -> Recognition:
    if tipo == "ROLL":
        r = conn.execute("""SELECT r.id, r.barcode, r.stato, m.descrizione FROM wms.material_rolls r
                            JOIN wms.materials m ON m.id=r.material_id WHERE r.barcode=%s""", (code,)).fetchone()
        label = r and f"Bobina {r['barcode']} — {r['descrizione']}"
    elif tipo == "PACKAGE":
        r = conn.execute("SELECT id, barcode, stato FROM wms.finished_goods_packages WHERE barcode=%s", (code,)).fetchone()
        label = r and f"Collo {r['barcode']}"
    elif tipo == "SHIPMENT":
        r = conn.execute("SELECT id, barcode, cliente_nome, stato FROM wms.shipments WHERE barcode=%s", (code,)).fetchone()
        label = r and f"Spedizione {r['barcode']} — {r['cliente_nome']}"
    elif tipo == "LOCATION":
        r = conn.execute("SELECT id, codice, tipo AS stato FROM wms.warehouse_locations WHERE barcode=%s", (code,)).fetchone()
        label = r and f"Ubicazione {r['codice']}"
    else:  # BADGE
        r = conn.execute("SELECT id, display_name, 'ATTIVO' AS stato FROM wms.users WHERE badge_code=%s AND active",
                         (code,)).fetchone()
        label = r and r["display_name"]
        tipo = "USER"
    if not r:
        return Recognition(raw, code, "SCONOSCIUTO", motivo=f"{code}: codice interno non presente in archivio")
    return Recognition(raw, code, "RICONOSCIUTO", [Candidate(tipo, r["id"], label, "INTERNO", {"stato": r["stato"]})])
