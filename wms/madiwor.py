"""Madiwor Integration Adapter.

Stato verificato (ottobre 2026): Madiwor NON espone API (confermato da Gabriele con Madiwor) e non
risultano webhook. Restano, nell'ordine richiesto dalla specifica:
  3. esportazioni strutturate ufficiali  → `StructuredExportSource` (formato colonne DA CONFIGURARE
     su un export reale: nessun nome di colonna è inventato, la mappa arriva da configurazione);
  4. scheda lavoro PDF generata da Madiwor → `PdfJobSheetSource`: legge solo le ancore già
     verificate dall'app "Etichette Anima" (#numero, CUSTOMER, SPECIFICATIONS), assegna una
     confidenza a ogni campo e mette in quarantena il documento se manca un campo obbligatorio.

Tutto converge su `MadiworJob` (modello normalizzato) e su `import_job`, che è idempotente:
stesso contenuto → nessuna modifica; contenuto cambiato → nuova versione, ricalcolo solo delle
prenotazioni non ancora consumate; commessa annullata → rilascio prenotazioni, storico intatto.
"""
from __future__ import annotations

import datetime as dt
import re
import uuid
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Callable, Protocol

from psycopg.types.json import Jsonb

from . import engine
from .engine import D, SYSTEM_ACTOR, BusinessRuleError, canonical_hash
from .errors import IntegrationAuthError

NS_IMPORT = uuid.UUID("6b0c3a52-7f0e-4b7e-9a7c-2f5d1c9b4e01")
FASI_VALIDE = {"STAMPA", "STAMPA_A_CALDO", "VERNICIATURA", "RILIEVO", "SECONDA_STAMPA", "FUSTELLATURA",
               "RIFINITURA", "RIBOBINATURA", "CONTROLLO", "IMBALLAGGIO"}


@dataclass
class MaterialeRichiesto:
    descrizione: str                 # testo esatto Madiwor
    larghezza_mm: Decimal | None
    metri: Decimal                   # metratura prevista dalla commessa


@dataclass
class MadiworJob:
    external_id: str
    cliente_nome: str
    sales_order_id: str | None = None
    cliente_ref: str | None = None
    articolo: str | None = None
    descrizione: str | None = None
    quantita: int | None = None
    data_consegna: dt.date | None = None
    stato: str = "ATTIVA"            # ATTIVA | ANNULLATA
    materiali: list[MaterialeRichiesto] = field(default_factory=list)
    fasi: list[dict] = field(default_factory=list)   # [{"fase": "STAMPA", "macchina": "CX3S"}, ...]
    specifiche: dict = field(default_factory=dict)

    def normalized(self) -> dict:
        d = asdict(self)
        d["data_consegna"] = self.data_consegna.isoformat() if self.data_consegna else None
        for m in d["materiali"]:
            m["larghezza_mm"] = str(D(m["larghezza_mm"])) if m["larghezza_mm"] is not None else None
            m["metri"] = str(D(m["metri"]))
        return d


class JobSource(Protocol):
    kind: str

    def fetch(self) -> list[MadiworJob]: ...


# ---------------------------------------------------------------------------
# Sorgente 3: esportazione strutturata (CSV/JSON) con mappa colonne da configurazione
# ---------------------------------------------------------------------------
@dataclass
class StructuredExportSource:
    """Righe già lette (es. da csv.DictReader) + mappa {campo_normalizzato: nome_colonna_export}.

    Campi richiesti dalla mappa: external_id, cliente_nome, materiale, metri.
    La mappa NON ha valori di default: va compilata guardando un export Madiwor reale."""
    rows: list[dict]
    column_map: dict[str, str]
    fetcher: Callable[[], list[dict]] | None = None   # es. download autorizzato; può sollevare IntegrationAuthError
    kind: str = "EXPORT_STRUTTURATO"

    REQUIRED = ("external_id", "cliente_nome", "materiale", "metri")

    def fetch(self) -> list[MadiworJob]:
        missing = [k for k in self.REQUIRED if k not in self.column_map]
        if missing:
            raise BusinessRuleError("Mappa colonne export incompleta: " + ", ".join(missing), code="MAPPA_INCOMPLETA")
        rows = self.fetcher() if self.fetcher else self.rows
        out = []
        cm = self.column_map
        for r in rows:
            def g(k):
                col = cm.get(k)
                v = r.get(col) if col else None
                return v.strip() if isinstance(v, str) else v
            fasi = [{"fase": f.strip().upper()} for f in (g("fasi") or "").split("|") if f.strip()]
            out.append(MadiworJob(
                external_id=str(g("external_id")), cliente_nome=g("cliente_nome"),
                sales_order_id=g("sales_order_id"), articolo=g("articolo"), descrizione=g("descrizione"),
                quantita=int(g("quantita")) if g("quantita") else None,
                data_consegna=_parse_date(g("data_consegna")),
                stato="ANNULLATA" if str(g("stato") or "").upper() in ("ANNULLATA", "CANCELLED", "CANCELED") else "ATTIVA",
                materiali=[MaterialeRichiesto(g("materiale"), D(g("larghezza_mm")) if g("larghezza_mm") else None,
                                              D(g("metri")))],
                fasi=fasi))
        return out


def _parse_date(v) -> dt.date | None:
    if not v:
        return None
    if isinstance(v, dt.date):
        return v
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(str(v), fmt).date()
        except ValueError:
            continue
    raise BusinessRuleError(f"Data non riconosciuta: {v}", code="DATO_NON_VALIDO")


# ---------------------------------------------------------------------------
# Sorgente 4: scheda lavoro PDF (testo già estratto), con confidenza e quarantena
# ---------------------------------------------------------------------------
@dataclass
class PdfExtraction:
    job: MadiworJob | None
    confidenza: dict[str, float]
    mancanti: list[str]
    da_quarantena: bool


class PdfJobSheetSource:
    """Estrazione da testo della scheda lavoro.

    Ancore verificate sul formato reale (app Etichette Anima): numero produzione "#NNNN",
    blocchi CUSTOMER e SPECIFICATIONS, SKU numerici nella tabella SPECIFICATIONS.
    Materiale, larghezza carta e metratura: le etichette dei campi sono passate in `field_patterns`
    perché non sono ancora state verificate su un PDF reale. Senza quei campi → quarantena."""
    kind = "PDF"
    SOGLIA = 0.9

    def __init__(self, text: str, document_ref: str, field_patterns: dict[str, str] | None = None):
        self.text = text
        self.document_ref = document_ref
        self.field_patterns = field_patterns or {}

    def extract(self) -> PdfExtraction:
        t = self.text
        conf: dict[str, float] = {}
        vals: dict[str, str] = {}
        nums = re.findall(r"#\s*(\d{1,8})\b", t)
        if len(set(nums)) == 1:
            vals["external_id"], conf["external_id"] = nums[0], 1.0
        elif nums:
            vals["external_id"], conf["external_id"] = nums[0], 0.4   # più numeri: ambiguo
        m = re.search(r"CUSTOMER\s*\n\s*(?:\d+\s*-\s*)?(.+)", t)
        if m:
            vals["cliente_nome"], conf["cliente_nome"] = m.group(1).strip(), 0.95
        for key, pattern in self.field_patterns.items():
            found = re.findall(pattern, t, flags=re.IGNORECASE | re.MULTILINE)
            if len(found) == 1:
                vals[key], conf[key] = (found[0] if isinstance(found[0], str) else found[0][0]).strip(), 0.95
            elif found:
                vals[key], conf[key] = str(found[0]).strip(), 0.5
        required = ["external_id", "cliente_nome", "materiale", "metri"]
        mancanti = [k for k in required if k not in vals]
        bassi = [k for k in required if k in vals and conf[k] < self.SOGLIA]
        if mancanti or bassi:
            return PdfExtraction(None, conf, mancanti + [f"{b} (incerto)" for b in bassi], True)
        try:
            job = MadiworJob(
                external_id=vals["external_id"], cliente_nome=vals["cliente_nome"],
                articolo=vals.get("articolo"), quantita=int(vals["quantita"].replace(".", "")) if vals.get("quantita") else None,
                data_consegna=_parse_date(vals.get("data_consegna")),
                materiali=[MaterialeRichiesto(vals["materiale"],
                                              D(vals["larghezza_mm"]) if vals.get("larghezza_mm") else None,
                                              D(vals["metri"]))])
        except BusinessRuleError as e:
            return PdfExtraction(None, conf, [e.message], True)
        return PdfExtraction(job, conf, [], False)


def quarantine(conn, source: str, document_ref: str, errore: str, payload: dict, confidence: float | None = None):
    conn.execute("""INSERT INTO wms.integration_errors(source, document_ref, errore, confidence, payload)
                    VALUES (%s,%s,%s,%s,%s)""",
                 (source, document_ref, errore, confidence, Jsonb(engine._jsonable(payload))))
    conn.execute("""INSERT INTO wms.sync_events(source, external_id, entity, esito, dettagli)
                    VALUES (%s,%s,'JOB','QUARANTENA',%s)""", (source, document_ref, Jsonb({"errore": errore})))


# ---------------------------------------------------------------------------
# Import idempotente
# ---------------------------------------------------------------------------
def resolve_material(conn, descr: str):
    r = conn.execute("SELECT id FROM wms.materials WHERE lower(descrizione_madiwor)=lower(%s) AND stato='ATTIVO'",
                     (descr.strip(),)).fetchone()
    if r:
        return r["id"]
    a = conn.execute("""SELECT entity_id FROM wms.barcode_aliases WHERE namespace='MADIWOR_MATERIALE'
                        AND entity_type='MATERIAL' AND lower(code)=lower(%s)""", (descr.strip(),)).fetchall()
    return a[0]["entity_id"] if len(a) == 1 else None


@engine.command("IMPORTA_COMMESSA", roles=set())
def cmd_importa_commessa(tx: engine.Tx, p: dict) -> dict:
    conn = tx.conn
    j = p["job"]
    norm_hash = p["hash"]
    ext = str(j["external_id"])
    for f in j.get("fasi") or []:
        if f["fase"] not in FASI_VALIDE:
            raise BusinessRuleError(f"Fase sconosciuta: {f['fase']}", code="FASE_SCONOSCIUTA")
    existing = conn.execute("SELECT * FROM wms.production_jobs WHERE external_madiwor_id=%s FOR UPDATE", (ext,)).fetchone()
    if existing and existing["source_hash"] == norm_hash:
        conn.execute("INSERT INTO wms.sync_events(source, external_id, entity, esito, payload_hash) VALUES "
                     "(%s,%s,'JOB','INVARIATO',%s)", (p["source"], ext, norm_hash))
        return {"esito": "INVARIATO", "messaggio": f"Commessa {ext} già aggiornata", "job_id": existing["id"]}

    stato = "ANNULLATA" if j.get("stato") == "ANNULLATA" else None
    specs = {**(j.get("specifiche") or {}), "fasi": j.get("fasi") or []}
    if existing:
        if existing["stato"] == "ANNULLATA" and stato is None:
            raise BusinessRuleError(f"Commessa {ext} annullata: una riattivazione va gestita a mano", code="COMMESSA_ANNULLATA")
        conn.execute("""UPDATE wms.production_jobs SET sales_order_id=%s, cliente_ref=%s, cliente_nome=%s, articolo_codice=%s,
                        descrizione=%s, quantita_ordinata=%s, data_consegna=%s, specifiche=%s, source_kind=%s, source_hash=%s,
                        source_version=source_version+1, last_synced_at=now(), stato=coalesce(%s, stato) WHERE id=%s""",
                     (j.get("sales_order_id"), j.get("cliente_ref"), j["cliente_nome"], j.get("articolo"), j.get("descrizione"),
                      j.get("quantita"), j.get("data_consegna"), Jsonb(specs), p["source"], norm_hash, stato, existing["id"]))
        job_id = existing["id"]
        esito = "ANNULLATO" if stato else "AGGIORNATO"
    else:
        job_id = conn.execute(
            """INSERT INTO wms.production_jobs(external_madiwor_id, sales_order_id, cliente_ref, cliente_nome, articolo_codice,
                 descrizione, quantita_ordinata, data_consegna, stato, specifiche, source_kind, source_hash)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (ext, j.get("sales_order_id"), j.get("cliente_ref"), j["cliente_nome"], j.get("articolo"), j.get("descrizione"),
             j.get("quantita"), j.get("data_consegna"), stato or "APERTA", Jsonb(specs), p["source"], norm_hash)).fetchone()["id"]
        esito = "CREATO"
        for i, f in enumerate(j.get("fasi") or [], start=1):
            conn.execute("INSERT INTO wms.job_phases(job_id, seq, fase, macchina) VALUES (%s,%s,%s,%s)",
                         (job_id, i * 10, f["fase"], f.get("macchina")))

    job = engine.get_job(conn, job_id)
    rilasciati = Decimal("0")
    if job["stato"] == "ANNULLATA":
        for res in conn.execute("SELECT * FROM wms.material_reservations WHERE job_id=%s AND status='ATTIVA' "
                                "ORDER BY id FOR UPDATE", (job_id,)).fetchall():
            rilasciati += engine._release(tx, res, causale="Commessa annullata in Madiwor")
        conn.execute("INSERT INTO wms.sync_events(source, external_id, entity, esito, payload_hash) VALUES "
                     "(%s,%s,'JOB','ANNULLATO',%s)", (p["source"], ext, norm_hash))
        return {"esito": "ANNULLATO", "job_id": job_id, "rilasciati_metri": rilasciati,
                "messaggio": f"Commessa {ext} annullata: liberati {rilasciati} m prenotati"}

    # fabbisogni: confronto per (descrizione materiale, larghezza)
    wanted = {(m["descrizione"].strip(), D(m["larghezza_mm"]) if m.get("larghezza_mm") is not None else None): D(m["metri"])
              for m in j.get("materiali") or []}
    current = conn.execute("SELECT * FROM wms.production_job_materials WHERE job_id=%s AND attiva FOR UPDATE",
                           (job_id,)).fetchall()
    non_risolti = []
    for jm in current:
        key = (jm["material_label_source"].strip(),
               D(jm["larghezza_richiesta_mm"]) if jm["larghezza_richiesta_mm"] is not None else None)
        if key not in wanted:
            # specifica materiale cambiata: la riga vecchia si disattiva, si liberano solo le prenotazioni non consumate
            for res in conn.execute("SELECT * FROM wms.material_reservations WHERE job_material_id=%s AND status='ATTIVA' "
                                    "FOR UPDATE", (jm["id"],)).fetchall():
                rilasciati += engine._release(tx, res, causale="Specifica materiale cambiata in Madiwor")
            conn.execute("UPDATE wms.production_job_materials SET attiva=false WHERE id=%s", (jm["id"],))
        else:
            metri = wanted.pop(key)
            if metri != D(jm["metri_teorici"]):
                conn.execute("UPDATE wms.production_job_materials SET metri_teorici=%s WHERE id=%s", (metri, jm["id"]))
                jm2 = engine._get_jm(conn, jm["id"])
                excess = D(jm2["metri_prenotati"]) - engine.remaining_need(jm2)
                for res in conn.execute("SELECT * FROM wms.material_reservations WHERE job_material_id=%s AND status='ATTIVA' "
                                        "ORDER BY created_at DESC FOR UPDATE", (jm["id"],)).fetchall():
                    if excess <= 0:
                        break
                    q = engine._release(tx, res, excess, causale="Quantità ridotta in Madiwor")
                    excess -= q
                    rilasciati += q
    for (descr, w), metri in wanted.items():
        mid = resolve_material(conn, descr)
        if mid is None:
            non_risolti.append(descr)
        row = conn.execute("""SELECT id FROM wms.production_job_materials WHERE job_id=%s AND material_label_source=%s
                              AND larghezza_richiesta_mm IS NOT DISTINCT FROM %s""", (job_id, descr, w)).fetchone()
        if row:   # riga tornata uguale a una versione precedente: si riattiva
            conn.execute("UPDATE wms.production_job_materials SET attiva=true, metri_teorici=%s, material_id=%s WHERE id=%s",
                         (metri, mid, row["id"]))
        else:
            conn.execute("""INSERT INTO wms.production_job_materials(job_id, material_id, material_label_source,
                            larghezza_richiesta_mm, metri_teorici) VALUES (%s,%s,%s,%s,%s)""", (job_id, mid, descr, w, metri))
    fabb = conn.execute("""SELECT material_label_source, larghezza_richiesta_mm, metri_teorici FROM wms.production_job_materials
                           WHERE job_id=%s AND attiva""", (job_id,)).fetchall()
    conn.execute("UPDATE wms.production_jobs SET fabbisogno_teorico=%s WHERE id=%s",
                 (Jsonb(engine._jsonable({"materiali": fabb, "nota": "metratura come indicata dalla commessa Madiwor"})), job_id))
    for descr in non_risolti:
        conn.execute("""INSERT INTO wms.integration_errors(source, document_ref, errore, payload, in_quarantena)
                        VALUES (%s,%s,%s,%s,false)""",
                     (p["source"], ext, f"Materiale non associato in anagrafica: {descr}", Jsonb({"materiale": descr})))
        tx.warnings.append(f"Materiale '{descr}' non associato: serve l'associazione in anagrafica (nessuna sostituzione automatica)")
    conn.execute("INSERT INTO wms.sync_events(source, external_id, entity, esito, payload_hash) VALUES (%s,%s,'JOB',%s,%s)",
                 (p["source"], ext, esito, norm_hash))
    return {"esito": esito, "job_id": job_id, "messaggio": f"Commessa {ext}: {esito.lower()}",
            "materiali_non_risolti": non_risolti, "rilasciati_metri": rilasciati}


def import_job(conn, job: MadiworJob, source_kind: str, auto_reserve: bool = True) -> dict:
    """Import idempotente: l'event_id deriva da (commessa, contenuto). Lo stesso documento importato
    due volte, o un retry dopo un timeout, non produce nessuna scrittura in più."""
    norm = job.normalized()
    h = canonical_hash(norm)
    prev = conn.execute("SELECT source_hash FROM wms.production_jobs WHERE external_madiwor_id=%s",
                        (str(job.external_id),)).fetchone()
    # l'identità dell'operazione è la transizione "versione precedente → nuova": un retry della stessa
    # transizione è un duplicato, mentre un ritorno a un contenuto già visto viene applicato davvero.
    event_id = uuid.uuid5(NS_IMPORT, f"{job.external_id}:{prev['source_hash'] if prev else '-'}->{h}")
    actor = engine.Actor(user_id=None, role_code="SISTEMA", role_level=100, fonte="MADIWOR")
    res = engine.execute(conn, actor, event_id, "IMPORTA_COMMESSA", {"job": norm, "hash": h, "source": source_kind})
    if auto_reserve and res.get("esito") in ("CREATO", "AGGIORNATO") and not res.get("duplicato"):
        try:
            res["prenotazione"] = engine.execute(conn, actor, uuid.uuid5(event_id, "auto-reserve"), "PRENOTA_AUTOMATICA",
                                                 {"job_id": str(res["job_id"])})
        except BusinessRuleError as e:
            res["prenotazione"] = e.to_dict()
    return res


def sync_once(conn, source: JobSource) -> dict:
    """Un giro di sincronizzazione: errori di credenziali e documenti ambigui non bloccano nulla,
    finiscono in integration_errors. Nessuna scrittura parziale: ogni commessa è una transazione."""
    try:
        jobs = source.fetch()
    except IntegrationAuthError as e:
        with conn.transaction():
            quarantine(conn, source.kind, "fetch", f"Credenziali non valide: {e.message}", {})
        return {"esito": "ERRORE_CREDENZIALI", "importate": 0}
    report = {"esito": "OK", "importate": 0, "invariate": 0, "errori": []}
    for j in jobs:
        try:
            r = import_job(conn, j, source.kind)
            report["invariate" if r["esito"] == "INVARIATO" or r.get("duplicato") else "importate"] += 1
        except BusinessRuleError as e:
            with conn.transaction():
                quarantine(conn, source.kind, j.external_id, e.message, j.normalized())
            report["errori"].append({"commessa": j.external_id, "errore": e.message})
    return report
