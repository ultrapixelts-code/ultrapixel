"""Warehouse Transaction Engine.

Unico punto da cui passano tutte le modifiche di giacenza.

Regole:
- ogni comando ha un event_id generato dal client: un retry con lo stesso event_id restituisce
  il risultato già registrato e non scrive nulla (idempotenza);
- ogni comando gira in una sola transazione: o tutto o niente;
- le righe toccate vengono bloccate (SELECT ... FOR UPDATE) in ordine stabile → niente corse
  tra due operatori sulla stessa bobina;
- ogni variazione di giacenza produce un movimento nel registro append-only
  `wms.inventory_movements`; le tabelle bobine/colli sono proiezioni di quel registro;
- una prenotazione NON è un consumo; una stima NON diventa mai consumo da sola.

Unità usate nel registro:
  'm'      metri fisici di una bobina (verificati)
  'm_ris'  metri riservati su una bobina (dimensione "prenotazioni")
  'pz'     etichette in un collo (giacenza prodotto finito)
  'pz_prod' / 'pz_conf'  etichette prodotte / dichiarate conformi in un lotto
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable

import psycopg
from psycopg.types.json import Jsonb

from .errors import BusinessRuleError, Forbidden, IdempotencyConflict, NotFound

TWO = Decimal("0.01")
LEVEL_RESPONSABILE = 30


def D(x: Any) -> Decimal:
    if x is None:
        raise BusinessRuleError("Valore numerico mancante", code="DATO_MANCANTE")
    try:
        return Decimal(str(x).replace(",", ".")).quantize(TWO, rounding=ROUND_HALF_UP)
    except Exception as exc:  # noqa: BLE001
        raise BusinessRuleError(f"Valore numerico non valido: {x!r}", code="DATO_NON_VALIDO") from exc


def as_uuid(x: Any, what: str = "id") -> uuid.UUID:
    if isinstance(x, uuid.UUID):
        return x
    try:
        return uuid.UUID(str(x))
    except Exception as exc:  # noqa: BLE001
        raise BusinessRuleError(f"{what} non valido", code="DATO_NON_VALIDO") from exc


def canonical_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def _jsonable(obj: Any) -> Any:
    return json.loads(json.dumps(obj, default=lambda o: str(o) if not isinstance(o, Decimal) else float(o)))


# ---------------------------------------------------------------------------
# Attore e transazione
# ---------------------------------------------------------------------------
@dataclass
class Actor:
    user_id: uuid.UUID | None
    role_code: str
    role_level: int
    device_id: uuid.UUID | None = None
    postazione: str | None = None
    device_location_id: uuid.UUID | None = None
    fonte: str = "UI"
    offline: bool = False
    client_ts: dt.datetime | None = None


SYSTEM_ACTOR = Actor(user_id=None, role_code="SISTEMA", role_level=100, fonte="SISTEMA")


@dataclass
class Tx:
    conn: psycopg.Connection
    actor: Actor
    event_id: uuid.UUID
    command_type: str
    n: int = 0
    warnings: list[str] = field(default_factory=list)

    def move(self, tipo: str, entity_type: str, entity_id: uuid.UUID, quantita: Decimal | int = 0,
             um: str = "m", origine=None, destinazione=None, commessa=None, causale=None,
             reference=None, reversal_of=None, metadata: dict | None = None) -> int:
        self.n += 1
        mv_event = uuid.uuid5(self.event_id, f"mv{self.n}")
        row = self.conn.execute(
            """INSERT INTO wms.inventory_movements
               (event_id, command_event_id, tipo_movimento, entity_type, entity_id, quantita, unita_misura,
                origine_id, destinazione_id, commessa_id, operatore_id, device_id, fonte, causale,
                reference_id, reversal_of, metadata)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (mv_event, self.event_id, tipo, entity_type, entity_id, quantita, um, origine, destinazione,
             commessa, self.actor.user_id, self.actor.device_id, self.actor.fonte, causale, reference,
             reversal_of, Jsonb(_jsonable(metadata or {}))),
        ).fetchone()
        return row["id"]

    def audit(self, azione: str, entita: str, entita_id, prima=None, dopo=None, motivo=None):
        self.conn.execute(
            """INSERT INTO wms.audit_logs(actor_type, actor_id, azione, entita, entita_id, prima, dopo, motivo)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            ("SISTEMA" if self.actor.user_id is None else "UTENTE", str(self.actor.user_id or self.actor.role_code),
             azione, entita, str(entita_id), Jsonb(_jsonable(prima)) if prima is not None else None,
             Jsonb(_jsonable(dopo)) if dopo is not None else None, motivo),
        )


# ---------------------------------------------------------------------------
# Registro comandi
# ---------------------------------------------------------------------------
@dataclass
class CommandSpec:
    handler: Callable[[Tx, dict], dict]
    roles: set[str] | None  # None = tutti i ruoli operativi


HANDLERS: dict[str, CommandSpec] = {}
PROD = {"OPERATORE_PRODUZIONE"}
SPED = {"OPERATORE_SPEDIZIONE"}
ALL_OPS = PROD | SPED


def command(name: str, roles: set[str] | None = None):
    def deco(fn):
        HANDLERS[name] = CommandSpec(fn, roles)
        return fn
    return deco


def _authorize(actor: Actor, spec: CommandSpec, name: str):
    if actor.role_level >= LEVEL_RESPONSABILE:
        return
    if spec.roles is not None and actor.role_code not in spec.roles:
        raise Forbidden(f"Il ruolo {actor.role_code} non può eseguire {name}", code="RUOLO_NON_AUTORIZZATO")


def execute(conn: psycopg.Connection, actor: Actor, event_id: Any, command_type: str, payload: dict) -> dict:
    """Esegue un comando in modo idempotente e atomico."""
    spec = HANDLERS.get(command_type)
    if spec is None:
        raise BusinessRuleError(f"Comando sconosciuto: {command_type}", code="COMANDO_SCONOSCIUTO")
    _authorize(actor, spec, command_type)
    event_id = as_uuid(event_id, "event_id")
    payload = payload or {}
    phash = canonical_hash({"t": command_type, "p": payload})

    def run() -> dict:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (str(event_id),))
        prev = conn.execute("SELECT command_type, payload_hash, result FROM wms.commands WHERE event_id=%s",
                            (event_id,)).fetchone()
        if prev:
            if prev["payload_hash"] != phash:
                raise IdempotencyConflict("Questo event_id è già stato usato per un'altra operazione")
            res = dict(prev["result"])
            res["duplicato"] = True
            return res
        tx = Tx(conn, actor, event_id, command_type)
        result = spec.handler(tx, payload)
        result = _jsonable(result)
        result.setdefault("esito", "OK")
        if tx.warnings:
            result["avvisi"] = tx.warnings
        result["event_id"] = str(event_id)
        result["comando"] = command_type
        conn.execute(
            """INSERT INTO wms.commands(event_id, command_type, payload_hash, payload, result,
                                         operatore_id, device_id, client_ts, offline)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (event_id, command_type, phash, Jsonb(_jsonable(payload)), Jsonb(result), actor.user_id,
             actor.device_id, actor.client_ts, actor.offline),
        )
        result["duplicato"] = False
        return result

    # Se esiste già una transazione aperta (scansione, import) questa diventa un savepoint:
    # un errore annulla solo il comando, non l'evento di scansione che lo ha generato.
    try:
        with conn.transaction():
            return run()
    except psycopg.errors.IntegrityError as exc:
        diag = getattr(exc.diag, "constraint_name", None) or ""
        raise BusinessRuleError("Operazione rifiutata: lo stato è cambiato nel frattempo, rileggi e riprova",
                                code="VINCOLO_DB", vincolo=diag) from exc


# ---------------------------------------------------------------------------
# Lettura con blocco
# ---------------------------------------------------------------------------
def setting(conn, key: str, default=None):
    r = conn.execute("SELECT value FROM wms.settings WHERE key=%s", (key,)).fetchone()
    return r["value"] if r else default


def get_roll(conn, roll_id, lock=True) -> dict:
    r = conn.execute("SELECT * FROM wms.material_rolls WHERE id=%s" + (" FOR UPDATE" if lock else ""),
                     (as_uuid(roll_id, "bobina"),)).fetchone()
    if not r:
        raise NotFound("Bobina non trovata", code="BOBINA_NON_TROVATA")
    return r


def get_job(conn, job_id, lock=True) -> dict:
    r = conn.execute("SELECT * FROM wms.production_jobs WHERE id=%s" + (" FOR UPDATE" if lock else ""),
                     (as_uuid(job_id, "commessa"),)).fetchone()
    if not r:
        raise NotFound("Commessa non trovata", code="COMMESSA_NON_TROVATA")
    return r


def get_location(conn, loc_id) -> dict:
    r = conn.execute("SELECT * FROM wms.warehouse_locations WHERE id=%s", (as_uuid(loc_id, "ubicazione"),)).fetchone()
    if not r:
        raise NotFound("Ubicazione non trovata", code="UBICAZIONE_NON_TROVATA")
    if r["stato"] != "ATTIVA":
        raise BusinessRuleError(f"Ubicazione {r['codice']} non attiva", code="UBICAZIONE_NON_ATTIVA")
    return r


def next_code(conn, counter: str, prefix: str) -> str:
    v = conn.execute("UPDATE wms.counters SET value=value+1 WHERE name=%s RETURNING value", (counter,)).fetchone()
    return f"{prefix}{v['value']:06d}"


def material_compatibility(conn, required_material_id, roll_material_id, cliente_ref=None) -> str | None:
    """Ritorna il tipo di compatibilità oppure None. Solo equivalenze esplicite e validate."""
    if required_material_id is None:
        return None
    if str(required_material_id) == str(roll_material_id):
        return "IDENTICO"
    eq = conn.execute(
        """SELECT compatibility_type, constraints FROM wms.material_equivalences
           WHERE material_id=%s AND compatible_material_id=%s AND active""",
        (required_material_id, roll_material_id),
    ).fetchone()
    if not eq:
        return None
    clienti = (eq["constraints"] or {}).get("solo_clienti")
    if clienti and cliente_ref not in clienti:
        return None
    return eq["compatibility_type"]


def width_ok(conn, roll_width: Decimal, required: Decimal | None) -> bool:
    if required is None:
        return True
    tol = D(setting(conn, "tolleranza_larghezza_mm", 0))
    return abs(D(roll_width) - D(required)) <= tol


def remaining_need(jm: dict) -> Decimal:
    """Metri ancora da consumare secondo la commessa (teorico − consumato misurato − consumo stimato)."""
    return max(Decimal("0"), D(jm["metri_teorici"]) - D(jm["metri_consumati"]) - D(jm["metri_consumo_stimato"]))


def roll_available(roll: dict) -> Decimal:
    if roll["stato"] != "DISPONIBILE":
        return Decimal("0")
    return D(roll["metri_residui"]) - D(roll["metri_riservati"])


def _roll_update(conn, roll_id, **fields):
    sets = ", ".join(f"{k}=%s" for k in fields) + ", version=version+1"
    conn.execute(f"UPDATE wms.material_rolls SET {sets} WHERE id=%s", (*fields.values(), roll_id))


def _locate_default(tx: Tx, payload: dict, key: str = "ubicazione_id", tipo_fallback: str | None = None):
    loc_id = payload.get(key) or tx.actor.device_location_id
    if not loc_id and tipo_fallback:
        r = tx.conn.execute("SELECT id FROM wms.warehouse_locations WHERE tipo=%s AND stato='ATTIVA' ORDER BY codice LIMIT 1",
                            (tipo_fallback,)).fetchone()
        loc_id = r["id"] if r else None
    if not loc_id:
        raise BusinessRuleError("Scansiona un'ubicazione", code="UBICAZIONE_MANCANTE")
    return get_location(tx.conn, loc_id)


# ---------------------------------------------------------------------------
# Ricevimento
# ---------------------------------------------------------------------------
@command("RICEVI_BOBINA", roles=PROD | SPED)
def cmd_ricevi_bobina(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    mat = conn.execute("SELECT * FROM wms.materials WHERE id=%s", (as_uuid(p.get("material_id"), "materiale"),)).fetchone()
    if not mat:
        raise NotFound("Materiale non trovato", code="MATERIALE_NON_TROVATO")
    if mat["stato"] != "ATTIVO":
        raise BusinessRuleError(f"Materiale {mat['codice_interno']} non attivo", code="MATERIALE_NON_ATTIVO")
    larghezza = p.get("larghezza_mm") or mat["larghezza_mm"]
    if larghezza is None:
        raise BusinessRuleError("Manca la larghezza della bobina", code="DATO_MANCANTE", campi=["larghezza_mm"])
    larghezza = D(larghezza)
    metri = D(p.get("metri")) if p.get("metri") is not None else None
    if metri is None:
        raise BusinessRuleError("Mancano i metri della bobina", code="DATO_MANCANTE", campi=["metri"])
    if metri <= 0 or larghezza <= 0:
        raise BusinessRuleError("Metri e larghezza devono essere maggiori di zero", code="DATO_NON_VALIDO")
    origine = p.get("origine_metratura", "FORNITORE")
    if origine not in ("FORNITORE", "MISURA"):
        raise BusinessRuleError("Origine metratura non valida", code="DATO_NON_VALIDO")
    n = int(p.get("numero_bobine", 1))
    if not 1 <= n <= 50:
        raise BusinessRuleError("Numero bobine fuori intervallo (1-50)", code="DATO_NON_VALIDO")
    loc = _locate_default(tx, p, tipo_fallback="RICEVIMENTO")
    costo = D(p["costo_per_m"]) if p.get("costo_per_m") is not None else mat["costo_per_um"]
    out = []
    for _ in range(n):
        barcode = next_code(conn, "ROLL", "UPR")
        r = conn.execute(
            """INSERT INTO wms.material_rolls(barcode, material_id, lotto_fornitore, larghezza_mm, metri_iniziali,
                 metri_residui, ubicazione_id, stato, costo_per_m, origine_dato_metratura, ultima_verifica)
               VALUES (%s,%s,%s,%s,%s,%s,%s,'DISPONIBILE',%s,%s, CASE WHEN %s='MISURA' THEN now() END)
               RETURNING id, barcode""",
            (barcode, mat["id"], p.get("lotto_fornitore"), larghezza, metri, metri, loc["id"], costo, origine, origine),
        ).fetchone()
        tx.move("RICEVIMENTO", "ROLL", r["id"], metri, "m", destinazione=loc["id"],
                causale=p.get("documento_fornitore") or "Ricevimento",
                metadata={"lotto": p.get("lotto_fornitore"), "origine_metratura": origine,
                          "codice_letto": p.get("codice_letto")})
        out.append({"id": r["id"], "barcode": r["barcode"], "metri": metri, "larghezza_mm": larghezza})
    sugg = suggest_location(conn, mat["id"], exclude=loc["id"])
    return {"messaggio": f"Ricevut{'a' if n == 1 else 'e'} {n} bobin{'a' if n == 1 else 'e'} {mat['descrizione']}",
            "bobine": out, "ubicazione": loc["codice"], "ubicazione_suggerita": sugg,
            "stampa": [{"tipo": "bobina", "id": b["id"]} for b in out]}


def suggest_location(conn, material_id, exclude=None) -> dict | None:
    r = conn.execute(
        """SELECT l.id, l.codice, count(*) AS n FROM wms.material_rolls r
           JOIN wms.warehouse_locations l ON l.id=r.ubicazione_id
           WHERE r.material_id=%s AND r.stato IN ('DISPONIBILE','DA_VERIFICARE') AND l.tipo='SCAFFALE'
             AND l.stato='ATTIVA' AND l.id IS DISTINCT FROM %s
           GROUP BY l.id, l.codice ORDER BY n DESC, l.codice LIMIT 1""",
        (material_id, exclude)).fetchone()
    if r:
        return {"id": r["id"], "codice": r["codice"], "motivo": f"già {r['n']} bobine dello stesso materiale"}
    return None


# ---------------------------------------------------------------------------
# Spostamenti
# ---------------------------------------------------------------------------
@command("SPOSTA_BOBINA", roles=ALL_OPS)
def cmd_sposta_bobina(tx: Tx, p: dict) -> dict:
    roll = get_roll(tx.conn, p.get("roll_id"))
    dest = get_location(tx.conn, p.get("destinazione_id"))
    if roll["stato"] not in ("DISPONIBILE", "DA_VERIFICARE", "QUARANTENA"):
        raise BusinessRuleError(f"Bobina {roll['barcode']} in stato {roll['stato']}: non spostabile",
                                code="STATO_NON_VALIDO")
    if dest["tipo"] == "MACCHINA":
        raise BusinessRuleError("Per portare una bobina in macchina scansiona prima la commessa",
                                code="USA_ASSEGNAZIONE")
    if roll["ubicazione_id"] == dest["id"]:
        return {"esito": "INVARIATO", "messaggio": f"{roll['barcode']} è già in {dest['codice']}"}
    tx.move("SPOSTAMENTO", "ROLL", roll["id"], 0, "m", origine=roll["ubicazione_id"], destinazione=dest["id"])
    _roll_update(tx.conn, roll["id"], ubicazione_id=dest["id"])
    return {"messaggio": f"{roll['barcode']} → {dest['codice']}", "bobina": roll["barcode"], "ubicazione": dest["codice"]}


# ---------------------------------------------------------------------------
# Prenotazioni
# ---------------------------------------------------------------------------
def _get_jm(conn, jm_id, lock=True) -> dict:
    r = conn.execute("SELECT * FROM wms.production_job_materials WHERE id=%s" + (" FOR UPDATE" if lock else ""),
                     (as_uuid(jm_id, "fabbisogno"),)).fetchone()
    if not r:
        raise NotFound("Riga fabbisogno non trovata", code="FABBISOGNO_NON_TROVATO")
    return r


def _check_job_active(job: dict):
    if job["stato"] in ("ANNULLATA", "COMPLETATA", "SOSPESA"):
        raise BusinessRuleError(f"Commessa {job['external_madiwor_id']} {job['stato'].lower()}",
                                code=f"COMMESSA_{job['stato']}")


def _check_roll_for_job(conn, roll: dict, jm: dict, job: dict) -> str:
    comp = material_compatibility(conn, jm["material_id"], roll["material_id"], job["cliente_ref"])
    if comp is None:
        req = conn.execute("SELECT descrizione FROM wms.materials WHERE id=%s", (jm["material_id"],)).fetchone()
        got = conn.execute("SELECT descrizione FROM wms.materials WHERE id=%s", (roll["material_id"],)).fetchone()
        raise BusinessRuleError(
            f"Materiale sbagliato: serve {req['descrizione'] if req else jm['material_label_source']}, "
            f"la bobina è {got['descrizione']}", code="MATERIALE_NON_COMPATIBILE")
    if not width_ok(conn, roll["larghezza_mm"], jm["larghezza_richiesta_mm"]):
        raise BusinessRuleError(
            f"Larghezza sbagliata: serve {D(jm['larghezza_richiesta_mm'])} mm, la bobina è {D(roll['larghezza_mm'])} mm",
            code="LARGHEZZA_NON_COMPATIBILE")
    return comp


def _reserve(tx: Tx, job: dict, jm: dict, roll: dict, qty: Decimal, causale="Prenotazione") -> dict:
    conn = tx.conn
    existing = conn.execute(
        "SELECT * FROM wms.material_reservations WHERE job_material_id=%s AND roll_id=%s AND status='ATTIVA' FOR UPDATE",
        (jm["id"], roll["id"])).fetchone()
    if existing:
        res_id = existing["id"]
        conn.execute("UPDATE wms.material_reservations SET quantity=quantity+%s WHERE id=%s", (qty, res_id))
    else:
        res_id = conn.execute(
            """INSERT INTO wms.material_reservations(job_id, job_material_id, roll_id, quantity)
               VALUES (%s,%s,%s,%s) RETURNING id""", (job["id"], jm["id"], roll["id"], qty)).fetchone()["id"]
    _roll_update(conn, roll["id"], metri_riservati=D(roll["metri_riservati"]) + qty)
    conn.execute("UPDATE wms.production_job_materials SET metri_prenotati=metri_prenotati+%s WHERE id=%s", (qty, jm["id"]))
    tx.move("PRENOTAZIONE", "ROLL", roll["id"], qty, "m_ris", commessa=job["id"], reference=res_id, causale=causale)
    roll["metri_riservati"] = D(roll["metri_riservati"]) + qty
    jm["metri_prenotati"] = D(jm["metri_prenotati"]) + qty
    return {"reservation_id": res_id, "bobina": roll["barcode"], "metri": qty}


def _release(tx: Tx, res: dict, qty: Decimal | None = None, causale="Rilascio prenotazione",
             final_status="RILASCIATA") -> Decimal:
    """Riduce (o chiude) una prenotazione attiva. Non tocca i metri fisici."""
    conn = tx.conn
    roll = get_roll(conn, res["roll_id"])
    q = D(res["quantity"]) if qty is None else min(D(qty), D(res["quantity"]))
    if q <= 0:
        return Decimal("0")
    left = D(res["quantity"]) - q
    if left == 0:
        conn.execute("UPDATE wms.material_reservations SET quantity=%s, status=%s, closed_at=now() WHERE id=%s",
                     (D(res["quantity"]), final_status, res["id"]))
    else:
        conn.execute("UPDATE wms.material_reservations SET quantity=%s WHERE id=%s", (left, res["id"]))
    _roll_update(conn, roll["id"], metri_riservati=D(roll["metri_riservati"]) - q)
    conn.execute("UPDATE wms.production_job_materials SET metri_prenotati=metri_prenotati-%s WHERE id=%s",
                 (q, res["job_material_id"]))
    tx.move("RILASCIO_PRENOTAZIONE", "ROLL", roll["id"], -q, "m_ris", commessa=res["job_id"],
            reference=res["id"], causale=causale)
    return q


def to_reserve(jm: dict) -> Decimal:
    return max(Decimal("0"), remaining_need(jm) - D(jm["metri_prenotati"]))


@command("PRENOTA", roles=ALL_OPS)
def cmd_prenota(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    jm = _get_jm(conn, p.get("job_material_id"))
    job = get_job(conn, jm["job_id"])
    _check_job_active(job)
    if not jm["attiva"] or jm["material_id"] is None:
        raise BusinessRuleError("Fabbisogno non attivo o materiale non risolto", code="FABBISOGNO_NON_VALIDO")
    roll = get_roll(conn, p.get("roll_id"))
    if roll["stato"] != "DISPONIBILE":
        raise BusinessRuleError(f"Bobina {roll['barcode']} in stato {roll['stato']}", code="BOBINA_NON_DISPONIBILE")
    _check_roll_for_job(conn, roll, jm, job)
    da_prenotare = to_reserve(jm)
    qty = D(p["metri"]) if p.get("metri") is not None else min(da_prenotare, roll_available(roll))
    if qty <= 0:
        raise BusinessRuleError("Niente da prenotare: fabbisogno già coperto o bobina vuota", code="NIENTE_DA_PRENOTARE")
    if qty > roll_available(roll):
        raise BusinessRuleError(f"Metratura insufficiente: disponibili {roll_available(roll)} m su {roll['barcode']}",
                                code="BOBINA_INSUFFICIENTE")
    if qty > da_prenotare:
        raise BusinessRuleError(f"Prenotazione oltre il fabbisogno (restano da prenotare {da_prenotare} m)",
                                code="PRENOTAZIONE_ECCEDENTE")
    r = _reserve(tx, job, jm, roll, qty)
    return {"messaggio": f"Prenotati {qty} m su {roll['barcode']} per commessa {job['external_madiwor_id']}", **r}


@command("RILASCIA_PRENOTAZIONE", roles=ALL_OPS)
def cmd_rilascia(tx: Tx, p: dict) -> dict:
    res = tx.conn.execute("SELECT * FROM wms.material_reservations WHERE id=%s FOR UPDATE",
                          (as_uuid(p.get("reservation_id"), "prenotazione"),)).fetchone()
    if not res or res["status"] != "ATTIVA":
        raise BusinessRuleError("Prenotazione non attiva", code="PRENOTAZIONE_NON_ATTIVA")
    q = _release(tx, res, causale=p.get("causale") or "Rilascio manuale")
    return {"messaggio": f"Rilasciati {q} m", "metri": q}


@command("PRENOTA_AUTOMATICA", roles=ALL_OPS)
def cmd_prenota_automatica(tx: Tx, p: dict) -> dict:
    from .optimizer import choose_rolls  # import locale: evita cicli
    conn = tx.conn
    job = get_job(conn, p.get("job_id"))
    _check_job_active(job)
    out, mancanze = [], []
    jms = conn.execute("SELECT * FROM wms.production_job_materials WHERE job_id=%s AND attiva ORDER BY id FOR UPDATE",
                       (job["id"],)).fetchall()
    for jm in jms:
        if jm["material_id"] is None:
            mancanze.append({"materiale": jm["material_label_source"], "motivo": "materiale non risolto"})
            continue
        need = to_reserve(jm)
        if need <= 0:
            continue
        plan = choose_rolls(conn, jm, job, need)
        for step in plan["scelte"]:
            roll = get_roll(conn, step["roll_id"])
            q = min(D(step["metri"]), roll_available(roll), to_reserve(jm))
            if q <= 0:
                continue
            r = _reserve(tx, job, jm, roll, q, causale="Prenotazione automatica")
            out.append({**r, "motivo": step["motivo"]})
        short = to_reserve(jm)
        if short > 0:
            mancanze.append({"materiale": jm["material_label_source"], "mancano_metri": short,
                             "alternative_con_taglio": plan.get("con_taglio", [])})
    if mancanze:
        tx.warnings.append("Materiale insufficiente per la commessa " + job["external_madiwor_id"])
    return {"messaggio": f"Commessa {job['external_madiwor_id']}: {len(out)} prenotazioni",
            "prenotazioni": out, "mancanze": mancanze}


# ---------------------------------------------------------------------------
# Produzione: assegnazione bobina, chiusura, verifica
# ---------------------------------------------------------------------------
def _match_jm_for_roll(conn, job: dict, roll: dict) -> dict:
    jms = conn.execute("SELECT * FROM wms.production_job_materials WHERE job_id=%s AND attiva ORDER BY id FOR UPDATE",
                       (job["id"],)).fetchall()
    if not jms:
        raise BusinessRuleError("La commessa non ha fabbisogni materiali", code="FABBISOGNO_ASSENTE")
    last_err = None
    for jm in jms:
        if jm["material_id"] is None:
            continue
        try:
            comp = _check_roll_for_job(conn, roll, jm, job)
            return {**jm, "_comp": comp}
        except BusinessRuleError as e:
            last_err = e
    if last_err:
        raise last_err
    raise BusinessRuleError("Materiale della commessa non ancora risolto in anagrafica", code="FABBISOGNO_NON_VALIDO")


@command("ASSEGNA_BOBINA", roles=PROD)
def cmd_assegna_bobina(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    job = get_job(conn, p.get("job_id"))
    _check_job_active(job)
    roll = get_roll(conn, p.get("roll_id"))
    machine = _locate_default(tx, p, key="location_id")
    if machine["tipo"] != "MACCHINA":
        raise BusinessRuleError("Questa postazione non è una macchina", code="POSTAZIONE_NON_MACCHINA")
    stato = roll["stato"]
    if stato == "IN_PRODUZIONE":
        other = conn.execute("SELECT external_madiwor_id FROM wms.production_jobs WHERE id=%s",
                             (roll["assigned_job_id"],)).fetchone()
        raise BusinessRuleError(f"Bobina già in produzione sulla commessa {other['external_madiwor_id'] if other else '?'}",
                                code="BOBINA_GIA_IN_USO")
    if stato == "ESAURITA":
        raise BusinessRuleError(f"Bobina {roll['barcode']} esaurita", code="BOBINA_ESAURITA")
    if stato == "DA_VERIFICARE":
        raise BusinessRuleError(f"Bobina {roll['barcode']}: misura prima i metri residui", code="BOBINA_DA_VERIFICARE")
    if stato != "DISPONIBILE":
        raise BusinessRuleError(f"Bobina {roll['barcode']} in stato {stato}", code="BOBINA_NON_DISPONIBILE")
    jm = _match_jm_for_roll(conn, job, roll)
    comp = jm.pop("_comp")

    mine = conn.execute(
        "SELECT * FROM wms.material_reservations WHERE job_material_id=%s AND roll_id=%s AND status='ATTIVA' FOR UPDATE",
        (jm["id"], roll["id"])).fetchone()
    mine_q = D(mine["quantity"]) if mine else Decimal("0")
    free_for_us = D(roll["metri_residui"]) - (D(roll["metri_riservati"]) - mine_q)
    if free_for_us <= 0:
        jobs = conn.execute(
            """SELECT DISTINCT j.external_madiwor_id FROM wms.material_reservations r
               JOIN wms.production_jobs j ON j.id=r.job_id WHERE r.roll_id=%s AND r.status='ATTIVA'""",
            (roll["id"],)).fetchall()
        raise BusinessRuleError("Bobina riservata ad altre commesse: " + ", ".join(j["external_madiwor_id"] for j in jobs),
                                code="RISERVATA_ALTRA_COMMESSA")
    need = remaining_need(jm)
    target = min(need, free_for_us)
    if target > mine_q:
        _reserve(tx, job, jm, roll, target - mine_q, causale="Prenotazione all'assegnazione")
    # le prenotazioni della stessa riga su altre bobine non montate vengono ridotte se non più necessarie
    others = conn.execute(
        """SELECT r.* FROM wms.material_reservations r JOIN wms.material_rolls b ON b.id=r.roll_id
           WHERE r.job_material_id=%s AND r.roll_id<>%s AND r.status='ATTIVA' AND b.stato='DISPONIBILE'
           ORDER BY r.quantity DESC FOR UPDATE OF r""", (jm["id"], roll["id"])).fetchall()
    jm_now = _get_jm(conn, jm["id"])
    excess = D(jm_now["metri_prenotati"]) - need
    for o in others:
        if excess <= 0:
            break
        excess -= _release(tx, o, excess, causale="Montata un'altra bobina")
    if free_for_us < need:
        tx.warnings.append(f"Metratura insufficiente: mancano {need - free_for_us} m, servirà un'altra bobina")
    a = conn.execute(
        """INSERT INTO wms.roll_assignments(job_id, job_material_id, roll_id, location_id, metri_inizio)
           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
        (job["id"], jm["id"], roll["id"], machine["id"], D(roll["metri_residui"]))).fetchone()
    tx.move("ASSEGNAZIONE", "ROLL", roll["id"], 0, "m", origine=roll["ubicazione_id"], destinazione=machine["id"],
            commessa=job["id"], reference=a["id"],
            metadata={"metri_inizio": roll["metri_residui"], "compatibilita": comp})
    _roll_update(conn, roll["id"], stato="IN_PRODUZIONE", assigned_job_id=job["id"], ubicazione_id=machine["id"])
    if job["stato"] == "APERTA":
        conn.execute("UPDATE wms.production_jobs SET stato='IN_PRODUZIONE' WHERE id=%s", (job["id"],))
    msg = f"Bobina {roll['barcode']} montata su {machine['codice']} per commessa {job['external_madiwor_id']}"
    if comp != "IDENTICO":
        msg += f" (materiale equivalente approvato: {comp})"
    return {"messaggio": msg, "assignment_id": a["id"], "bobina": roll["barcode"],
            "commessa": job["external_madiwor_id"], "metri_inizio": roll["metri_residui"], "compatibilita": comp}


def _close_consumption(tx: Tx, a: dict, roll: dict, residui: Decimal, scarto: Decimal, tipo: str, dest_id=None):
    """Trasforma un montaggio in consumo verificato (misura o dato macchina)."""
    conn = tx.conn
    inizio = D(a["metri_inizio"])
    if residui < 0 or residui > inizio:
        raise BusinessRuleError(f"Misura incoerente: a inizio lavoro la bobina aveva {inizio} m", code="MISURA_INCOERENTE")
    consumo = inizio - residui
    if scarto < 0 or scarto > consumo:
        raise BusinessRuleError(f"Scarto ({scarto} m) maggiore del consumo ({consumo} m)", code="MISURA_INCOERENTE")
    utilizzati = consumo - scarto
    # le prenotazioni della commessa su questa bobina si chiudono: il consumo reale le sostituisce
    for res in conn.execute("SELECT * FROM wms.material_reservations WHERE job_material_id=%s AND roll_id=%s "
                            "AND status='ATTIVA' FOR UPDATE", (a["job_material_id"], roll["id"])).fetchall():
        _release(tx, res, causale="Chiusura bobina", final_status="CONSUMATA")
    roll = get_roll(conn, roll["id"])
    if utilizzati > 0:
        tx.move("CONSUMO", "ROLL", roll["id"], -utilizzati, "m", commessa=a["job_id"], reference=a["id"],
                metadata={"tipo_dato": tipo})
    if scarto > 0:
        tx.move("SCARTO", "ROLL", roll["id"], -scarto, "m", commessa=a["job_id"], reference=a["id"],
                metadata={"tipo_dato": tipo})
    if residui < D(roll["metri_riservati"]):
        # se altre commesse avevano prenotato più del residuo reale, la parte eccedente va rilasciata
        over = D(roll["metri_riservati"]) - residui
        tx.warnings.append(f"Residuo reale inferiore alle prenotazioni di altre commesse: rilasciati {over} m")
        for res in conn.execute("SELECT * FROM wms.material_reservations WHERE roll_id=%s AND status='ATTIVA' "
                                "ORDER BY created_at DESC FOR UPDATE", (roll["id"],)).fetchall():
            if over <= 0:
                break
            over -= _release(tx, res, over, causale="Residuo reale inferiore al previsto")
        roll = get_roll(conn, roll["id"])
    nuovo_stato = "ESAURITA" if residui == 0 else "DISPONIBILE"
    ubic = None if residui == 0 else (dest_id or roll["ubicazione_id"])
    if dest_id and residui > 0 and dest_id != roll["ubicazione_id"]:
        tx.move("RIENTRO", "ROLL", roll["id"], 0, "m", origine=roll["ubicazione_id"], destinazione=dest_id,
                commessa=a["job_id"])
    _roll_update(conn, roll["id"], metri_residui=residui, metri_stimati=None, stato=nuovo_stato,
                 assigned_job_id=None, ubicazione_id=ubic,
                 origine_dato_metratura="MISURA" if tipo == "MISURATO" else "CALCOLATO", ultima_verifica=dt.datetime.now(dt.timezone.utc))
    conn.execute("""UPDATE wms.production_job_materials
                    SET metri_consumati=metri_consumati+%s, metri_scarto=metri_scarto+%s WHERE id=%s""",
                 (utilizzati, scarto, a["job_material_id"]))
    conn.execute("""UPDATE wms.roll_assignments SET stato='CHIUSA', metri_fine=%s, consumo_tipo=%s,
                    metri_utilizzati=%s, metri_scarto=%s, fine_at=now() WHERE id=%s""",
                 (residui, tipo, utilizzati, scarto, a["id"]))
    return {"consumo": consumo, "utilizzati": utilizzati, "scarto": scarto, "residui": residui, "stato_bobina": nuovo_stato}


@command("CHIUDI_BOBINA", roles=PROD)
def cmd_chiudi_bobina(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    roll = get_roll(conn, p.get("roll_id"))
    a = conn.execute("SELECT * FROM wms.roll_assignments WHERE roll_id=%s AND stato='IN_CORSO' FOR UPDATE",
                     (roll["id"],)).fetchone()
    if not a:
        raise BusinessRuleError(f"Bobina {roll['barcode']} non è montata su nessuna commessa", code="NESSUN_MONTAGGIO")
    scarto = D(p.get("metri_scarto", 0))
    dest = get_location(conn, p["destinazione_id"])["id"] if p.get("destinazione_id") else None
    if p.get("metri_residui") is not None:
        r = _close_consumption(tx, a, roll, D(p["metri_residui"]), scarto, "MISURATO", dest)
        return {"messaggio": f"{roll['barcode']}: consumati {r['utilizzati']} m, scarto {r['scarto']} m, "
                             f"residuo {r['residui']} m (misurato)", **r}
    if p.get("consumo_macchina") is not None:
        consumo = D(p["consumo_macchina"])
        r = _close_consumption(tx, a, roll, D(a["metri_inizio"]) - consumo, scarto, "MACCHINA", dest)
        return {"messaggio": f"{roll['barcode']}: consumo da macchina {consumo} m, residuo {r['residui']} m", **r}
    # nessuna misura: stima dichiarata, NON trasformata in consumo
    jm = _get_jm(conn, a["job_material_id"])
    stima = min(D(a["metri_inizio"]), remaining_need(jm))
    conn.execute("UPDATE wms.production_job_materials SET metri_consumo_stimato=metri_consumo_stimato+%s WHERE id=%s",
                 (stima, jm["id"]))
    conn.execute("""UPDATE wms.roll_assignments SET stato='DA_VERIFICARE', consumo_tipo='STIMATO',
                    metri_utilizzati=%s, fine_at=now() WHERE id=%s""", (stima, a["id"]))
    _roll_update(conn, roll["id"], stato="DA_VERIFICARE", metri_stimati=D(a["metri_inizio"]) - stima,
                 origine_dato_metratura="STIMA")
    tx.audit("STIMA_CONSUMO", "ROLL", roll["id"], dopo={"stima_consumo": stima, "metri_inizio": a["metri_inizio"]},
             motivo="Chiusura senza misura")
    return {"esito": "AVVISO", "stima_consumo": stima, "metri_stimati": D(a["metri_inizio"]) - stima,
            "messaggio": f"{roll['barcode']}: consumo STIMATO {stima} m (non definitivo). Misura i metri residui."}


@command("VERIFICA_METRATURA", roles=ALL_OPS)
def cmd_verifica_metratura(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    roll = get_roll(conn, p.get("roll_id"))
    misura = D(p.get("metri_misurati"))
    if misura < 0:
        raise BusinessRuleError("Misura negativa", code="DATO_NON_VALIDO")
    if roll["stato"] == "DA_VERIFICARE":
        a = conn.execute("SELECT * FROM wms.roll_assignments WHERE roll_id=%s AND stato='DA_VERIFICARE' FOR UPDATE",
                         (roll["id"],)).fetchone()
        if a:
            stima = D(a["metri_utilizzati"] or 0)
            conn.execute("UPDATE wms.production_job_materials SET metri_consumo_stimato=metri_consumo_stimato-%s WHERE id=%s",
                         (stima, a["job_material_id"]))
            r = _close_consumption(tx, a, roll, misura, D(p.get("metri_scarto", 0)), "MISURATO",
                                   get_location(conn, p["destinazione_id"])["id"] if p.get("destinazione_id") else None)
            return {"messaggio": f"{roll['barcode']}: misurati {misura} m, consumo reale {r['consumo']} m "
                                 f"(stima era {stima} m)", "stima_precedente": stima, **r}
    if roll["stato"] not in ("DISPONIBILE", "QUARANTENA"):
        raise BusinessRuleError(f"Bobina in stato {roll['stato']}: misura non applicabile", code="STATO_NON_VALIDO")
    if misura == D(roll["metri_residui"]):
        tx.move("VERIFICA_METRATURA", "ROLL", roll["id"], 0, "m", causale="Misura confermata")
        _roll_update(conn, roll["id"], origine_dato_metratura="MISURA", ultima_verifica=dt.datetime.now(dt.timezone.utc))
        return {"messaggio": f"{roll['barcode']}: {misura} m confermati"}
    return _rettifica(tx, roll, misura, p.get("causale") or "Verifica metratura")


def _rettifica(tx: Tx, roll: dict, nuovi: Decimal, causale: str) -> dict:
    conn = tx.conn
    if not causale or not str(causale).strip():
        raise BusinessRuleError("La rettifica richiede una causale", code="CAUSALE_MANCANTE")
    if roll["stato"] in ("IN_PRODUZIONE", "TAGLIATA", "ANNULLATA", "DA_VERIFICARE"):
        raise BusinessRuleError(f"Bobina in stato {roll['stato']}: rettifica non consentita", code="STATO_NON_VALIDO")
    if nuovi < 0:
        raise BusinessRuleError("Giacenza negativa non ammessa", code="GIACENZA_NEGATIVA")
    delta = nuovi - D(roll["metri_residui"])
    if delta == 0:
        return {"esito": "INVARIATO", "messaggio": "Nessuna differenza"}
    soglia = D(setting(conn, "soglia_rettifica_metri", 50))
    if abs(delta) > soglia and tx.actor.role_level < LEVEL_RESPONSABILE:
        raise Forbidden(f"Rettifica di {delta} m oltre soglia {soglia} m: serve il responsabile di magazzino",
                        code="RICHIEDE_AUTORIZZAZIONE")
    if roll["stato"] == "ESAURITA" and tx.actor.role_level < LEVEL_RESPONSABILE:
        raise Forbidden("Riattivare una bobina esaurita richiede il responsabile", code="RICHIEDE_AUTORIZZAZIONE")
    if nuovi < D(roll["metri_riservati"]):
        raise BusinessRuleError("La nuova giacenza è inferiore ai metri prenotati: rilascia prima le prenotazioni",
                                code="PRENOTAZIONI_SUPERANO")
    tx.move("RETTIFICA", "ROLL", roll["id"], delta, "m", causale=causale,
            metadata={"prima": roll["metri_residui"], "dopo": nuovi})
    stato = "ESAURITA" if nuovi == 0 else ("DISPONIBILE" if roll["stato"] == "ESAURITA" else roll["stato"])
    _roll_update(conn, roll["id"], metri_residui=nuovi, stato=stato, origine_dato_metratura="MISURA",
                 ultima_verifica=dt.datetime.now(dt.timezone.utc),
                 ubicazione_id=None if nuovi == 0 else roll["ubicazione_id"])
    return {"messaggio": f"{roll['barcode']}: rettifica {delta:+} m ({causale})", "delta": delta}


@command("RETTIFICA", roles=ALL_OPS)
def cmd_rettifica(tx: Tx, p: dict) -> dict:
    roll = get_roll(tx.conn, p.get("roll_id"))
    return _rettifica(tx, roll, D(p.get("metri_nuovi")), p.get("causale"))


@command("TAGLIA_BOBINA", roles=PROD)
def cmd_taglia_bobina(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    parent = get_roll(conn, p.get("roll_id"))
    if parent["stato"] != "DISPONIBILE":
        raise BusinessRuleError(f"Bobina in stato {parent['stato']}: non tagliabile", code="STATO_NON_VALIDO")
    if D(parent["metri_riservati"]) > 0:
        raise BusinessRuleError("La bobina ha prenotazioni attive: rilasciale prima del taglio", code="PRENOTAZIONI_ATTIVE")
    figlie = p.get("figlie") or []
    if len(figlie) < 1:
        raise BusinessRuleError("Indica almeno una bobina figlia", code="DATO_MANCANTE")
    pw, pl = D(parent["larghezza_mm"]), D(parent["metri_residui"])
    area_tot = Decimal("0")
    for f in figlie:
        w, l = D(f.get("larghezza_mm")), D(f.get("metri"))
        if w <= 0 or l <= 0 or w > pw or l > pl:
            raise BusinessRuleError(f"Figlia {w} mm × {l} m incompatibile con la madre {pw} mm × {pl} m",
                                    code="TAGLIO_NON_VALIDO")
        area_tot += w * l
    if area_tot > pw * pl:
        raise BusinessRuleError("Le figlie superano la superficie della bobina madre", code="TAGLIO_NON_VALIDO")
    sfrido_mm_m = pw * pl - area_tot
    dest = get_location(conn, p["destinazione_id"])["id"] if p.get("destinazione_id") else parent["ubicazione_id"]
    tx.move("TAGLIO_USCITA", "ROLL", parent["id"], -pl, "m", origine=parent["ubicazione_id"],
            metadata={"sfrido_mm_x_m": sfrido_mm_m, "figlie": len(figlie)})
    _roll_update(conn, parent["id"], metri_residui=0, stato="TAGLIATA", ubicazione_id=None)
    out = []
    for f in figlie:
        w, l = D(f["larghezza_mm"]), D(f["metri"])
        bc = next_code(conn, "ROLL", "UPR")
        costo = (D(parent["costo_per_m"]) * w / pw).quantize(Decimal("0.0001")) if parent["costo_per_m"] is not None else None
        r = conn.execute(
            """INSERT INTO wms.material_rolls(barcode, material_id, lotto_fornitore, parent_roll_id, larghezza_mm,
                 metri_iniziali, metri_residui, ubicazione_id, stato, costo_per_m, origine_dato_metratura)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'DISPONIBILE',%s,'CALCOLATO') RETURNING id, barcode""",
            (bc, parent["material_id"], parent["lotto_fornitore"], parent["id"], w, l, l, dest, costo)).fetchone()
        tx.move("TAGLIO_INGRESSO", "ROLL", r["id"], l, "m", destinazione=dest, reference=parent["id"],
                metadata={"madre": parent["barcode"]})
        out.append({"id": r["id"], "barcode": r["barcode"], "larghezza_mm": w, "metri": l})
    return {"messaggio": f"{parent['barcode']} tagliata in {len(out)} bobine", "figlie": out,
            "sfrido_mm_x_m": sfrido_mm_m, "stampa": [{"tipo": "bobina", "id": o["id"]} for o in out]}


@command("BLOCCA_BOBINA", roles=set())
def cmd_blocca(tx: Tx, p: dict) -> dict:
    roll = get_roll(tx.conn, p.get("roll_id"))
    if roll["stato"] not in ("DISPONIBILE", "DA_VERIFICARE"):
        raise BusinessRuleError(f"Bobina in stato {roll['stato']}", code="STATO_NON_VALIDO")
    if not p.get("causale"):
        raise BusinessRuleError("Serve una causale", code="CAUSALE_MANCANTE")
    tx.move("BLOCCO", "ROLL", roll["id"], 0, "m", causale=p["causale"], metadata={"stato_prima": roll["stato"]})
    _roll_update(tx.conn, roll["id"], stato="QUARANTENA")
    return {"messaggio": f"{roll['barcode']} bloccata: {p['causale']}"}


@command("SBLOCCA_BOBINA", roles=set())
def cmd_sblocca(tx: Tx, p: dict) -> dict:
    roll = get_roll(tx.conn, p.get("roll_id"))
    if roll["stato"] != "QUARANTENA":
        raise BusinessRuleError("Bobina non bloccata", code="STATO_NON_VALIDO")
    tx.move("SBLOCCO", "ROLL", roll["id"], 0, "m", causale=p.get("causale") or "Sblocco")
    _roll_update(tx.conn, roll["id"], stato="DISPONIBILE" if D(roll["metri_residui"]) > 0 else "ESAURITA")
    return {"messaggio": f"{roll['barcode']} sbloccata"}


# ---------------------------------------------------------------------------
# Fasi di lavorazione, lotti, controllo qualità
# ---------------------------------------------------------------------------
def _phases(conn, job_id):
    return conn.execute("SELECT * FROM wms.job_phases WHERE job_id=%s ORDER BY seq FOR UPDATE", (job_id,)).fetchall()


@command("COMPLETA_FASE", roles=PROD)
def cmd_completa_fase(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    job = get_job(conn, p.get("job_id"))
    _check_job_active(job)
    phases = _phases(conn, job["id"])
    target = next((f for f in phases if f["fase"] == p.get("fase") and f["stato"] != "COMPLETATA"), None)
    if not target:
        raise BusinessRuleError(f"Fase {p.get('fase')} non prevista o già completata", code="FASE_NON_VALIDA")
    if target["fase"] in ("CONTROLLO", "IMBALLAGGIO"):
        raise BusinessRuleError("Controllo e imballaggio si chiudono con le loro operazioni", code="FASE_NON_VALIDA")
    prev = [f for f in phases if f["seq"] < target["seq"] and f["stato"] != "COMPLETATA"]
    if prev:
        raise BusinessRuleError("Prima completa: " + ", ".join(f["fase"] for f in prev), code="FASE_PRECEDENTE_APERTA")
    q = int(p["quantita_out"]) if p.get("quantita_out") is not None else None
    conn.execute("""UPDATE wms.job_phases SET stato='COMPLETATA', quantita_out=%s, macchina=coalesce(%s, macchina),
                    completata_at=now(), completata_da=%s WHERE id=%s""",
                 (q, p.get("macchina"), tx.actor.user_id, target["id"]))
    tx.audit("FASE_COMPLETATA", "JOB", job["id"], dopo={"fase": target["fase"], "quantita_out": q})
    nxt = next((f["fase"] for f in phases if f["seq"] > target["seq"] and f["stato"] != "COMPLETATA"), None)
    return {"messaggio": f"Commessa {job['external_madiwor_id']}: {target['fase']} completata", "prossima_fase": nxt}


@command("RILAVORA_FASE", roles=PROD)
def cmd_rilavora_fase(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    job = get_job(conn, p.get("job_id"))
    _check_job_active(job)
    phases = _phases(conn, job["id"])
    target = next((f for f in phases if f["fase"] == p.get("fase")), None)
    if not target or target["fase"] in ("CONTROLLO", "IMBALLAGGIO"):
        raise BusinessRuleError("Fase non valida per rilavorazione", code="FASE_NON_VALIDA")
    if not p.get("causale"):
        raise BusinessRuleError("Serve una causale di rilavorazione", code="CAUSALE_MANCANTE")
    conn.execute("UPDATE wms.job_phases SET stato='RILAVORAZIONE' WHERE id=%s", (target["id"],))
    conn.execute("UPDATE wms.job_phases SET stato='DA_FARE', completata_at=NULL WHERE job_id=%s AND seq>%s "
                 "AND fase IN ('CONTROLLO') ", (job["id"], target["seq"]))
    conn.execute("UPDATE wms.job_phases SET stato='DA_FARE', completata_at=NULL WHERE job_id=%s AND seq>%s "
                 "AND fase NOT IN ('CONTROLLO','IMBALLAGGIO')", (job["id"], target["seq"]))
    tx.audit("RILAVORAZIONE", "JOB", job["id"], dopo={"fase": target["fase"]}, motivo=p["causale"])
    return {"messaggio": f"Commessa {job['external_madiwor_id']}: {target['fase']} da rilavorare"}


def _production_done(phases) -> bool:
    return all(f["stato"] == "COMPLETATA" for f in phases if f["fase"] not in ("CONTROLLO", "IMBALLAGGIO"))


def ensure_finished_product(conn, job: dict) -> dict:
    sku = job["articolo_codice"]
    if not sku:
        raise BusinessRuleError("La commessa non indica il codice articolo", code="ARTICOLO_MANCANTE")
    ver = str((job["specifiche"] or {}).get("versione") or "1")
    fp = conn.execute("SELECT * FROM wms.finished_products WHERE external_sku_id=%s AND versione=%s", (sku, ver)).fetchone()
    if fp:
        return fp
    return conn.execute(
        """INSERT INTO wms.finished_products(external_sku_id, versione, cliente_ref, codice_articolo, descrizione, specifiche)
           VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (external_sku_id, versione) DO UPDATE SET descrizione=EXCLUDED.descrizione
           RETURNING *""",
        (sku, ver, job["cliente_ref"], sku, job["descrizione"], Jsonb({"formato": (job["specifiche"] or {}).get("formato")}))
    ).fetchone()


@command("REGISTRA_PRODUZIONE", roles=PROD)
def cmd_registra_produzione(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    job = get_job(conn, p.get("job_id"))
    _check_job_active(job)
    phases = _phases(conn, job["id"])
    if not phases:
        raise BusinessRuleError("La commessa non ha fasi definite", code="FASI_ASSENTI")
    if not _production_done(phases):
        aperte = [f["fase"] for f in phases if f["stato"] != "COMPLETATA" and f["fase"] not in ("CONTROLLO", "IMBALLAGGIO")]
        raise BusinessRuleError("Lavorazioni ancora aperte: " + ", ".join(aperte), code="LAVORAZIONI_APERTE")
    q = int(p.get("quantita") or 0)
    if q <= 0:
        raise BusinessRuleError("Quantità prodotta mancante", code="DATO_MANCANTE")
    fp = ensure_finished_product(conn, job)
    n = conn.execute("SELECT count(*) AS n FROM wms.production_lots WHERE production_job_id=%s", (job["id"],)).fetchone()["n"]
    codice = f"L{job['external_madiwor_id']}-{n + 1}"
    lot = conn.execute(
        """INSERT INTO wms.production_lots(codice, production_job_id, finished_product_id, quantita_prodotta)
           VALUES (%s,%s,%s,%s) RETURNING *""", (codice, job["id"], fp["id"], q)).fetchone()
    tx.move("PRODUZIONE", "LOT", lot["id"], q, "pz_prod", commessa=job["id"])
    conn.execute("UPDATE wms.job_phases SET stato='DA_FARE' WHERE job_id=%s AND fase='CONTROLLO'", (job["id"],))
    return {"messaggio": f"Lotto {codice}: {q} etichette prodotte, in attesa di controllo", "lotto": codice,
            "lot_id": lot["id"]}


@command("CONTROLLO_QUALITA", roles=PROD)
def cmd_controllo(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    lot = conn.execute("SELECT * FROM wms.production_lots WHERE id=%s FOR UPDATE",
                       (as_uuid(p.get("lot_id"), "lotto"),)).fetchone()
    if not lot:
        raise NotFound("Lotto non trovato", code="LOTTO_NON_TROVATO")
    if lot["stato_qualita"] not in ("IN_ATTESA", "RILAVORAZIONE"):
        raise BusinessRuleError(f"Lotto già controllato ({lot['stato_qualita']})", code="LOTTO_GIA_CONTROLLATO")
    conf, scarti = int(p.get("conformi", -1)), int(p.get("scarti", -1))
    if conf < 0 or scarti < 0 or conf + scarti != lot["quantita_prodotta"]:
        raise BusinessRuleError(f"Conformi + scarti devono essere uguali alle {lot['quantita_prodotta']} prodotte",
                                code="QUANTITA_INCOERENTE")
    esito = "APPROVATO" if conf > 0 else "RESPINTO"
    conn.execute("""UPDATE wms.production_lots SET quantita_conforme=%s, quantita_scartata=%s, stato_qualita=%s
                    WHERE id=%s""", (conf, scarti, esito, lot["id"]))
    tx.move("CONTROLLO_QUALITA", "LOT", lot["id"], conf, "pz_conf", commessa=lot["production_job_id"],
            metadata={"scarti": scarti, "esito": esito, "nota": p.get("nota")})
    pending = conn.execute("SELECT count(*) AS n FROM wms.production_lots WHERE production_job_id=%s "
                           "AND stato_qualita IN ('IN_ATTESA','RILAVORAZIONE')", (lot["production_job_id"],)).fetchone()["n"]
    if pending == 0:
        conn.execute("UPDATE wms.job_phases SET stato='COMPLETATA', completata_at=now(), completata_da=%s "
                     "WHERE job_id=%s AND fase='CONTROLLO'", (tx.actor.user_id, lot["production_job_id"]))
    return {"messaggio": f"Lotto {lot['codice']}: {conf} conformi, {scarti} scarti ({esito})", "esito_qualita": esito}


@command("CONFEZIONA", roles=PROD | SPED)
def cmd_confeziona(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    lot = conn.execute("SELECT * FROM wms.production_lots WHERE id=%s FOR UPDATE",
                       (as_uuid(p.get("lot_id"), "lotto"),)).fetchone()
    if not lot:
        raise NotFound("Lotto non trovato", code="LOTTO_NON_TROVATO")
    if lot["stato_qualita"] != "APPROVATO":
        raise BusinessRuleError("Il lotto non ha superato il controllo qualità", code="LOTTO_NON_APPROVATO")
    q = int(p.get("quantita") or 0)
    residuo = lot["quantita_conforme"] - lot["quantita_confezionata"]
    if q <= 0 or q > residuo:
        raise BusinessRuleError(f"Quantità non valida: confezionabili {residuo}", code="QUANTITA_NON_VALIDA")
    loc = _locate_default(tx, p, tipo_fallback="SCAFFALE")
    bc = next_code(conn, "PACKAGE", "UPC")
    pkg = conn.execute(
        """INSERT INTO wms.finished_goods_packages(barcode, lotto_id, quantita, ubicazione_id)
           VALUES (%s,%s,%s,%s) RETURNING id, barcode""", (bc, lot["id"], q, loc["id"])).fetchone()
    conn.execute("UPDATE wms.production_lots SET quantita_confezionata=quantita_confezionata+%s WHERE id=%s", (q, lot["id"]))
    tx.move("CONFEZIONAMENTO", "PACKAGE", pkg["id"], q, "pz", destinazione=loc["id"], commessa=lot["production_job_id"],
            reference=lot["id"])
    tot = conn.execute(
        """SELECT coalesce(sum(quantita_conforme - quantita_confezionata),0) AS da_conf,
                  count(*) FILTER (WHERE stato_qualita IN ('IN_ATTESA','RILAVORAZIONE')) AS in_attesa
           FROM wms.production_lots WHERE production_job_id=%s""", (lot["production_job_id"],)).fetchone()
    if tot["da_conf"] == 0 and tot["in_attesa"] == 0:
        conn.execute("UPDATE wms.job_phases SET stato='COMPLETATA', completata_at=now() WHERE job_id=%s AND fase='IMBALLAGGIO'",
                     (lot["production_job_id"],))
    return {"messaggio": f"Collo {bc}: {q} etichette (lotto {lot['codice']})", "collo": bc, "package_id": pkg["id"],
            "ubicazione": loc["codice"], "stampa": [{"tipo": "collo", "id": pkg["id"]}]}


# ---------------------------------------------------------------------------
# Spedizioni
# ---------------------------------------------------------------------------
def _get_pkg(conn, pkg_id) -> dict:
    r = conn.execute(
        """SELECT p.*, l.finished_product_id, l.production_job_id, l.stato_qualita, l.codice AS lotto
           FROM wms.finished_goods_packages p JOIN wms.production_lots l ON l.id=p.lotto_id
           WHERE p.id=%s FOR UPDATE OF p""", (as_uuid(pkg_id, "collo"),)).fetchone()
    if not r:
        raise NotFound("Collo non trovato", code="COLLO_NON_TROVATO")
    return r


@command("CREA_SPEDIZIONE", roles=set())
def cmd_crea_spedizione(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    ext = p.get("external_madiwor_ref")
    if ext:
        ex = conn.execute("SELECT id, barcode FROM wms.shipments WHERE external_madiwor_ref=%s", (ext,)).fetchone()
        if ex:
            return {"esito": "INVARIATO", "messaggio": f"Spedizione {ex['barcode']} già esistente",
                    "shipment_id": ex["id"], "barcode": ex["barcode"]}
    if not p.get("righe"):
        raise BusinessRuleError("Spedizione senza righe", code="DATO_MANCANTE")
    bc = next_code(conn, "SHIPMENT", "UPS")
    sh = conn.execute(
        """INSERT INTO wms.shipments(barcode, external_madiwor_ref, sales_order_id, cliente_ref, cliente_nome)
           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
        (bc, ext, p.get("sales_order_id"), p.get("cliente_ref"), p.get("cliente_nome") or "?")).fetchone()
    for r in p["righe"]:
        fp = conn.execute("SELECT id FROM wms.finished_products WHERE external_sku_id=%s AND versione=%s",
                          (str(r["articolo"]), str(r.get("versione") or "1"))).fetchone()
        if not fp:
            raise BusinessRuleError(f"Articolo {r['articolo']} versione {r.get('versione') or '1'} sconosciuto",
                                    code="ARTICOLO_SCONOSCIUTO")
        job_id = None
        if r.get("commessa"):
            j = conn.execute("SELECT id FROM wms.production_jobs WHERE external_madiwor_id=%s", (str(r["commessa"]),)).fetchone()
            job_id = j["id"] if j else None
        conn.execute("""INSERT INTO wms.shipment_lines(shipment_id, finished_product_id, production_job_id, quantita_richiesta)
                        VALUES (%s,%s,%s,%s)""", (sh["id"], fp["id"], job_id, int(r["quantita"])))
    tx.audit("SPEDIZIONE_CREATA", "SHIPMENT", sh["id"], dopo=p)
    return {"messaggio": f"Spedizione {bc} creata", "shipment_id": sh["id"], "barcode": bc,
            "stampa": [{"tipo": "spedizione", "id": sh["id"]}]}


@command("PRELEVA_COLLO", roles=SPED | PROD)
def cmd_preleva_collo(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    sh = conn.execute("SELECT * FROM wms.shipments WHERE id=%s FOR UPDATE",
                      (as_uuid(p.get("shipment_id"), "spedizione"),)).fetchone()
    if not sh:
        raise NotFound("Spedizione non trovata", code="SPEDIZIONE_NON_TROVATA")
    if sh["stato"] not in ("APERTA", "PRONTA"):
        raise BusinessRuleError(f"Spedizione {sh['barcode']} {sh['stato'].lower()}", code="SPEDIZIONE_CHIUSA")
    pkg = _get_pkg(conn, p.get("package_id"))
    if pkg["stato"] == "SPEDITO":
        raise BusinessRuleError(f"Collo {pkg['barcode']} già spedito", code="COLLO_GIA_SPEDITO")
    if pkg["stato"] == "PRELEVATO":
        line = conn.execute("SELECT shipment_id FROM wms.shipment_lines WHERE id=%s", (pkg["shipment_line_id"],)).fetchone()
        if line and line["shipment_id"] == sh["id"]:
            return {"esito": "INVARIATO", "messaggio": f"Collo {pkg['barcode']} già in questa spedizione"}
        raise BusinessRuleError(f"Collo {pkg['barcode']} già prelevato per un'altra spedizione", code="COLLO_IMPEGNATO")
    if pkg["stato"] != "DISPONIBILE":
        raise BusinessRuleError(f"Collo {pkg['barcode']} in stato {pkg['stato']}", code="COLLO_NON_DISPONIBILE")
    if pkg["stato_qualita"] != "APPROVATO":
        raise BusinessRuleError("Lotto non approvato", code="LOTTO_NON_APPROVATO")
    lines = conn.execute("SELECT * FROM wms.shipment_lines WHERE shipment_id=%s AND finished_product_id=%s FOR UPDATE",
                         (sh["id"], pkg["finished_product_id"])).fetchall()
    lines = [l for l in lines if l["production_job_id"] in (None, pkg["production_job_id"])]
    if not lines:
        raise BusinessRuleError(f"Collo {pkg['barcode']}: articolo/versione non presente in questa spedizione",
                                code="COLLO_NON_COMPATIBILE")
    line = next((l for l in lines if l["quantita_richiesta"] - l["quantita_preparata"] >= pkg["quantita"]), None)
    if not line:
        rest = sum(l["quantita_richiesta"] - l["quantita_preparata"] for l in lines)
        raise BusinessRuleError(f"Collo da {pkg['quantita']} pz: ne mancano solo {rest}", code="QUANTITA_ECCEDENTE")
    dest = tx.actor.device_location_id if tx.actor.postazione == "SPEDIZIONE" else p.get("ubicazione_id")
    conn.execute("UPDATE wms.shipment_lines SET quantita_preparata=quantita_preparata+%s WHERE id=%s",
                 (pkg["quantita"], line["id"]))
    conn.execute("""UPDATE wms.finished_goods_packages SET stato='PRELEVATO', shipment_line_id=%s,
                    ubicazione_id=coalesce(%s, ubicazione_id), version=version+1 WHERE id=%s""",
                 (line["id"], dest, pkg["id"]))
    tx.move("PICKING", "PACKAGE", pkg["id"], 0, "pz", origine=pkg["ubicazione_id"], destinazione=dest,
            reference=sh["id"], commessa=pkg["production_job_id"])
    tot = conn.execute("SELECT bool_and(quantita_preparata >= quantita_richiesta) AS ok, "
                       "sum(quantita_richiesta-quantita_preparata) AS mancano FROM wms.shipment_lines WHERE shipment_id=%s",
                       (sh["id"],)).fetchone()
    if tot["ok"]:
        conn.execute("UPDATE wms.shipments SET stato='PRONTA' WHERE id=%s", (sh["id"],))
    return {"messaggio": f"Collo {pkg['barcode']} ({pkg['quantita']} pz) nella spedizione {sh['barcode']}"
                         + ("" if tot["ok"] else f" — mancano {tot['mancano']} pz"),
            "spedizione_completa": bool(tot["ok"]), "mancano": tot["mancano"]}


@command("ANNULLA_PICKING", roles=SPED | PROD)
def cmd_annulla_picking(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    pkg = _get_pkg(conn, p.get("package_id"))
    if pkg["stato"] != "PRELEVATO":
        raise BusinessRuleError("Collo non prelevato", code="STATO_NON_VALIDO")
    line = conn.execute("SELECT * FROM wms.shipment_lines WHERE id=%s FOR UPDATE", (pkg["shipment_line_id"],)).fetchone()
    sh = conn.execute("SELECT * FROM wms.shipments WHERE id=%s FOR UPDATE", (line["shipment_id"],)).fetchone()
    if sh["stato"] == "USCITA":
        raise BusinessRuleError("Spedizione già uscita", code="SPEDIZIONE_CHIUSA")
    conn.execute("UPDATE wms.shipment_lines SET quantita_preparata=quantita_preparata-%s WHERE id=%s",
                 (pkg["quantita"], line["id"]))
    conn.execute("UPDATE wms.finished_goods_packages SET stato='DISPONIBILE', shipment_line_id=NULL, version=version+1 "
                 "WHERE id=%s", (pkg["id"],))
    conn.execute("UPDATE wms.shipments SET stato='APERTA' WHERE id=%s", (sh["id"],))
    tx.move("ANNULLO_PICKING", "PACKAGE", pkg["id"], 0, "pz", reference=sh["id"])
    return {"messaggio": f"Collo {pkg['barcode']} tolto dalla spedizione {sh['barcode']}"}


@command("CONFERMA_USCITA", roles=SPED)
def cmd_conferma_uscita(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    sh = conn.execute("SELECT * FROM wms.shipments WHERE id=%s FOR UPDATE",
                      (as_uuid(p.get("shipment_id"), "spedizione"),)).fetchone()
    if not sh:
        raise NotFound("Spedizione non trovata", code="SPEDIZIONE_NON_TROVATA")
    if sh["stato"] == "USCITA":
        raise BusinessRuleError(f"Spedizione {sh['barcode']} già uscita", code="SPEDIZIONE_GIA_USCITA")
    if sh["stato"] == "ANNULLATA":
        raise BusinessRuleError("Spedizione annullata", code="SPEDIZIONE_CHIUSA")
    if sh["stato"] != "PRONTA" and not p.get("parziale"):
        raise BusinessRuleError("Spedizione incompleta: conferma come parziale se è voluto", code="SPEDIZIONE_INCOMPLETA")
    pkgs = conn.execute(
        """SELECT p.* FROM wms.finished_goods_packages p JOIN wms.shipment_lines l ON l.id=p.shipment_line_id
           WHERE l.shipment_id=%s AND p.stato='PRELEVATO' ORDER BY p.barcode FOR UPDATE OF p""", (sh["id"],)).fetchall()
    if not pkgs:
        raise BusinessRuleError("Nessun collo prelevato", code="SPEDIZIONE_VUOTA")
    for k in pkgs:
        tx.move("USCITA", "PACKAGE", k["id"], -k["quantita"], "pz", origine=k["ubicazione_id"], reference=sh["id"],
                causale=p.get("vettore") or "Consegna al vettore")
        conn.execute("UPDATE wms.finished_goods_packages SET stato='SPEDITO', ubicazione_id=NULL, version=version+1 "
                     "WHERE id=%s", (k["id"],))
    conn.execute("UPDATE wms.shipments SET stato='USCITA', uscita_at=now() WHERE id=%s", (sh["id"],))
    return {"messaggio": f"Spedizione {sh['barcode']} uscita: {len(pkgs)} colli, {sum(k['quantita'] for k in pkgs)} pz",
            "colli": [k["barcode"] for k in pkgs]}


@command("RESO", roles=set())
def cmd_reso(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    pkg = _get_pkg(conn, p.get("package_id"))
    if pkg["stato"] != "SPEDITO":
        raise BusinessRuleError("Solo un collo spedito può rientrare come reso", code="STATO_NON_VALIDO")
    if not p.get("causale"):
        raise BusinessRuleError("Serve una causale di reso", code="CAUSALE_MANCANTE")
    loc = _locate_default(tx, p, tipo_fallback="QUARANTENA")
    tx.move("RESO", "PACKAGE", pkg["id"], pkg["quantita"], "pz", destinazione=loc["id"], causale=p["causale"])
    conn.execute("UPDATE wms.finished_goods_packages SET stato='RESO', ubicazione_id=%s, version=version+1 WHERE id=%s",
                 (loc["id"], pkg["id"]))
    return {"messaggio": f"Collo {pkg['barcode']} rientrato in {loc['codice']} (da valutare)"}


@command("SPOSTA_COLLO", roles=ALL_OPS)
def cmd_sposta_collo(tx: Tx, p: dict) -> dict:
    pkg = _get_pkg(tx.conn, p.get("package_id"))
    dest = get_location(tx.conn, p.get("destinazione_id"))
    if pkg["stato"] not in ("DISPONIBILE", "RESO", "BLOCCATO"):
        raise BusinessRuleError(f"Collo in stato {pkg['stato']}: non spostabile", code="STATO_NON_VALIDO")
    if pkg["ubicazione_id"] == dest["id"]:
        return {"esito": "INVARIATO", "messaggio": f"{pkg['barcode']} è già in {dest['codice']}"}
    tx.move("SPOSTAMENTO", "PACKAGE", pkg["id"], 0, "pz", origine=pkg["ubicazione_id"], destinazione=dest["id"])
    tx.conn.execute("UPDATE wms.finished_goods_packages SET ubicazione_id=%s, version=version+1 WHERE id=%s",
                    (dest["id"], pkg["id"]))
    return {"messaggio": f"{pkg['barcode']} → {dest['codice']}"}


# ---------------------------------------------------------------------------
# Annullo dell'ultima operazione (evento compensativo, mai cancellazione)
# ---------------------------------------------------------------------------
UNDOABLE = {"SPOSTA_BOBINA", "PRENOTA", "ASSEGNA_BOBINA", "PRELEVA_COLLO", "RICEVI_BOBINA", "SPOSTA_COLLO"}


def _reverse_reservation_movement(tx: Tx, mv: dict):
    conn = tx.conn
    res = conn.execute("SELECT * FROM wms.material_reservations WHERE id=%s FOR UPDATE", (mv["reference_id"],)).fetchone()
    roll = get_roll(conn, mv["entity_id"])
    delta = -D(mv["quantita"])
    if res["status"] == "ATTIVA":
        new_res = D(res["quantity"]) + delta
    else:
        # una prenotazione chiusa da questo comando torna attiva per la quantità rilasciata
        new_res = delta
    if new_res < 0:
        raise BusinessRuleError("Prenotazione già modificata: annullo impossibile", code="NON_ANNULLABILE")
    if new_res == 0:
        conn.execute("UPDATE wms.material_reservations SET status='RILASCIATA', closed_at=now() WHERE id=%s", (res["id"],))
    else:
        conn.execute("UPDATE wms.material_reservations SET quantity=%s, status='ATTIVA', closed_at=NULL WHERE id=%s",
                     (new_res, res["id"]))
    _roll_update(conn, roll["id"], metri_riservati=D(roll["metri_riservati"]) + delta)
    conn.execute("UPDATE wms.production_job_materials SET metri_prenotati=metri_prenotati+%s WHERE id=%s",
                 (delta, res["job_material_id"]))
    tx.move("STORNO", "ROLL", roll["id"], delta, "m_ris", reference=res["id"], reversal_of=mv["id"],
            commessa=mv["commessa_id"], causale="Annullo " + mv["tipo_movimento"])


@command("ANNULLA_COMANDO", roles=None)
def cmd_annulla(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    target_id = as_uuid(p.get("event_id"), "operazione")
    cmd = conn.execute("SELECT * FROM wms.commands WHERE event_id=%s", (target_id,)).fetchone()
    if not cmd:
        raise NotFound("Operazione non trovata", code="OPERAZIONE_NON_TROVATA")
    if cmd["command_type"] not in UNDOABLE:
        raise BusinessRuleError(f"{cmd['command_type']} non si annulla: usa una rettifica autorizzata", code="NON_ANNULLABILE")
    minutes = int(setting(conn, "finestra_annullo_minuti", 10))
    own = cmd["operatore_id"] is not None and cmd["operatore_id"] == tx.actor.user_id
    age = dt.datetime.now(dt.timezone.utc) - cmd["created_at"]
    if tx.actor.role_level < LEVEL_RESPONSABILE and not (own and age <= dt.timedelta(minutes=minutes)):
        raise Forbidden("Puoi annullare solo una tua operazione recente: chiama il responsabile", code="RICHIEDE_AUTORIZZAZIONE")
    mvs = conn.execute("SELECT * FROM wms.inventory_movements WHERE command_event_id=%s ORDER BY id DESC", (target_id,)).fetchall()
    if not mvs:
        raise BusinessRuleError("Operazione senza movimenti", code="NON_ANNULLABILE")
    if conn.execute("SELECT 1 FROM wms.inventory_movements WHERE reversal_of = ANY(%s)", ([m["id"] for m in mvs],)).fetchone():
        raise BusinessRuleError("Operazione già annullata", code="GIA_ANNULLATA")
    max_id = max(m["id"] for m in mvs)
    entities = {(m["entity_type"], m["entity_id"]) for m in mvs}
    for et, eid in entities:
        later = conn.execute("SELECT 1 FROM wms.inventory_movements WHERE entity_type=%s AND entity_id=%s AND id>%s "
                             "AND command_event_id<>%s LIMIT 1", (et, eid, max_id, target_id)).fetchone()
        if later:
            raise BusinessRuleError("Dopo questa operazione ce ne sono state altre sullo stesso oggetto: "
                                    "serve una rettifica", code="NON_ANNULLABILE")
    for (et, eid) in sorted(entities, key=lambda x: str(x[1])):
        if et == "ROLL":
            get_roll(conn, eid)
    ct = cmd["command_type"]
    for mv in mvs:
        t = mv["tipo_movimento"]
        if mv["unita_misura"] == "m_ris":
            _reverse_reservation_movement(tx, mv)
        elif t in ("SPOSTAMENTO",) and mv["entity_type"] == "ROLL":
            tx.move("STORNO", "ROLL", mv["entity_id"], 0, "m", origine=mv["destinazione_id"], destinazione=mv["origine_id"],
                    reversal_of=mv["id"], causale="Annullo spostamento")
            _roll_update(conn, mv["entity_id"], ubicazione_id=mv["origine_id"])
        elif t == "SPOSTAMENTO" and mv["entity_type"] == "PACKAGE":
            tx.move("STORNO", "PACKAGE", mv["entity_id"], 0, "pz", origine=mv["destinazione_id"],
                    destinazione=mv["origine_id"], reversal_of=mv["id"], causale="Annullo spostamento")
            conn.execute("UPDATE wms.finished_goods_packages SET ubicazione_id=%s, version=version+1 WHERE id=%s",
                         (mv["origine_id"], mv["entity_id"]))
        elif t == "ASSEGNAZIONE":
            a = conn.execute("SELECT * FROM wms.roll_assignments WHERE id=%s FOR UPDATE", (mv["reference_id"],)).fetchone()
            if a["stato"] != "IN_CORSO":
                raise BusinessRuleError("Montaggio già chiuso: annullo impossibile", code="NON_ANNULLABILE")
            conn.execute("UPDATE wms.roll_assignments SET stato='ANNULLATA', fine_at=now() WHERE id=%s", (a["id"],))
            tx.move("STORNO", "ROLL", mv["entity_id"], 0, "m", origine=mv["destinazione_id"], destinazione=mv["origine_id"],
                    reversal_of=mv["id"], commessa=mv["commessa_id"], causale="Annullo montaggio")
            _roll_update(conn, mv["entity_id"], stato="DISPONIBILE", assigned_job_id=None, ubicazione_id=mv["origine_id"])
        elif t == "PICKING":
            pkg = _get_pkg(conn, mv["entity_id"])
            line = conn.execute("SELECT * FROM wms.shipment_lines WHERE id=%s FOR UPDATE", (pkg["shipment_line_id"],)).fetchone()
            conn.execute("UPDATE wms.shipment_lines SET quantita_preparata=quantita_preparata-%s WHERE id=%s",
                         (pkg["quantita"], line["id"]))
            conn.execute("UPDATE wms.finished_goods_packages SET stato='DISPONIBILE', shipment_line_id=NULL, "
                         "ubicazione_id=%s, version=version+1 WHERE id=%s", (mv["origine_id"], pkg["id"]))
            conn.execute("UPDATE wms.shipments SET stato='APERTA' WHERE id=%s AND stato='PRONTA'", (line["shipment_id"],))
            tx.move("STORNO", "PACKAGE", pkg["id"], 0, "pz", origine=mv["destinazione_id"], destinazione=mv["origine_id"],
                    reversal_of=mv["id"], causale="Annullo prelievo")
        elif t == "RICEVIMENTO":
            roll = get_roll(conn, mv["entity_id"])
            if D(roll["metri_riservati"]) > 0 or roll["stato"] != "DISPONIBILE":
                raise BusinessRuleError("Bobina già usata: annullo impossibile", code="NON_ANNULLABILE")
            tx.move("STORNO", "ROLL", roll["id"], -D(mv["quantita"]), "m", origine=roll["ubicazione_id"],
                    reversal_of=mv["id"], causale="Annullo ricevimento")
            _roll_update(conn, roll["id"], metri_residui=0, stato="ANNULLATA", ubicazione_id=None)
        else:
            raise BusinessRuleError(f"Movimento {t} non annullabile", code="NON_ANNULLABILE")
    if ct == "ASSEGNA_BOBINA":
        job_id = mvs[0]["commessa_id"]
        open_a = conn.execute("SELECT count(*) AS n FROM wms.roll_assignments WHERE job_id=%s AND stato<>'ANNULLATA'",
                              (job_id,)).fetchone()["n"]
        if open_a == 0:
            conn.execute("UPDATE wms.production_jobs SET stato='APERTA' WHERE id=%s AND stato='IN_PRODUZIONE'", (job_id,))
    tx.audit("ANNULLO", "COMMAND", target_id, prima={"comando": ct}, motivo=p.get("causale") or "Annullo ultima operazione")
    return {"messaggio": f"Annullata: {ct.replace('_', ' ').lower()}", "annullato": str(target_id)}


# ---------------------------------------------------------------------------
# Anagrafica codici (non tocca giacenze, solo audit)
# ---------------------------------------------------------------------------
@command("ASSOCIA_CODICE", roles=set())
def cmd_associa_codice(tx: Tx, p: dict) -> dict:
    """Associa un codice letto (fornitore, GTIN, Madiwor) a un materiale. Solo responsabile.
    `identifica_unita` va messo a true SOLO se quel codice è diverso per ogni singola bobina."""
    conn = tx.conn
    code = str(p.get("code") or "").strip()
    ns = p.get("namespace") or "FORNITORE"
    if not code:
        raise BusinessRuleError("Codice mancante", code="DATO_MANCANTE")
    if ns not in ("FORNITORE", "GTIN", "MADIWOR_MATERIALE", "MADIWOR_ARTICOLO"):
        raise BusinessRuleError("Namespace non valido", code="DATO_NON_VALIDO")
    mat = conn.execute("SELECT id, descrizione FROM wms.materials WHERE id=%s",
                       (as_uuid(p.get("material_id"), "materiale"),)).fetchone()
    if not mat:
        raise NotFound("Materiale non trovato", code="MATERIALE_NON_TROVATO")
    r = conn.execute(
        """INSERT INTO wms.barcode_aliases(code, namespace, entity_type, entity_id, identifica_unita, note, created_by)
           VALUES (%s,%s,'MATERIAL',%s,%s,%s,%s) ON CONFLICT (code, namespace, entity_type, entity_id) DO NOTHING
           RETURNING id""", (code, ns, mat["id"], bool(p.get("identifica_unita")), p.get("note"), tx.actor.user_id)).fetchone()
    tx.audit("ASSOCIA_CODICE", "MATERIAL", mat["id"], dopo={"code": code, "namespace": ns})
    return {"messaggio": f"Codice {code} associato a {mat['descrizione']}", "nuovo": r is not None}
