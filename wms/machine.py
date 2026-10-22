"""Dati macchina: storico di stampa (Xeikon CX3S "print history") → consumo reale delle bobine.

Principio: la macchina monta una bobina alla volta. Tutta la carta passata in macchina tra la scansione
"inizio" e la scansione "fine" di una bobina è consumo di quella bobina (lavori, prove, calibrazioni,
lavori interrotti: la carta è passata comunque). Il consumo stimato diventa definitivo solo quando lo
storico copre tutto l'intervallo.

Limiti noti (da verificare in reparto):
- "Run Length (m)" è la carta stampata: non include l'eventuale carta di aggancio/scarto all'inizio
  del rotolo. Se serve, si aggiunge una tolleranza per bobina in configurazione.
- Si assume che un export contenga TUTTI i lavori fino alla sua riga più recente.
- Come far arrivare l'export in automatico dalla Xeikon (cartella condivisa, X-800) è da definire.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
from decimal import Decimal
from zoneinfo import ZoneInfo

from psycopg.types.json import Jsonb

from . import engine
from .engine import D, BusinessRuleError, Tx, get_roll, _release, _roll_update

TZ = ZoneInfo("Europe/Rome")


def parse_xeikon_csv(text: str) -> list[dict]:
    """Legge l'export "print history" della Xeikon. Colonne usate: JobName, EndTime, Time (s), Run Length (m),
    Medium, State. La riga 'Total' viene ignorata."""
    rows = []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        end = (r.get("EndTime") or "").strip()
        if not end or r.get("#", "").strip().lower() == "total":
            continue
        try:
            fine = dt.datetime.strptime(end, "%Y-%m-%d_%H:%M:%S").replace(tzinfo=TZ)
            metri = Decimal((r.get("Run Length (m)") or "0").strip() or "0")
        except (ValueError, ArithmeticError) as exc:
            raise BusinessRuleError(f"Riga storico non leggibile: {end}", code="STORICO_NON_VALIDO") from exc
        rows.append({"job_name": (r.get("JobName") or "").strip(), "medium": (r.get("Medium") or "").strip(),
                     "stato": (r.get("State") or "").strip(), "fine_at": fine.isoformat(),
                     "durata_s": int(float(r.get("Time (s)") or 0)), "metri": str(metri)})
    if not rows:
        raise BusinessRuleError("Storico vuoto o formato non riconosciuto", code="STORICO_NON_VALIDO")
    return rows


def meters_in_window(conn, macchina: str, start, end) -> Decimal | None:
    """Metri passati in macchina tra start (escluso) ed end (incluso). None se lo storico non copre ancora end."""
    cov = conn.execute("SELECT coperto_fino FROM wms.machine_data_coverage WHERE macchina=%s", (macchina,)).fetchone()
    if not cov or end is None or cov["coperto_fino"] < end:
        return None
    r = conn.execute("""SELECT coalesce(sum(metri),0) AS s FROM wms.machine_runs
                        WHERE macchina=%s AND fine_at > %s AND fine_at <= %s""", (macchina, start, end)).fetchone()
    return D(r["s"])


def reconcile_roll(tx: Tx, roll_id) -> dict:
    """Trasforma in consumo definitivo le chiusure stimate di una bobina, in ordine, finché lo storico macchina le copre."""
    conn = tx.conn
    roll = get_roll(conn, roll_id)
    pending = conn.execute("""SELECT * FROM wms.roll_assignments WHERE roll_id=%s AND stato='DA_VERIFICARE'
                              AND consumo_tipo='STIMATO' ORDER BY inizio_at FOR UPDATE""", (roll["id"],)).fetchall()
    done, tot = 0, Decimal("0")
    for a in pending:
        if not a["macchina"]:
            break
        consumo = meters_in_window(conn, a["macchina"], a["inizio_at"], a["fine_at"])
        if consumo is None:
            break
        roll = get_roll(conn, roll["id"])
        start = D(roll["metri_residui"])
        if consumo > start:
            tx.warnings.append(f"{roll['barcode']}: la macchina riporta {consumo:g} m ma la bobina ne aveva {start:g}: "
                               "serve un controllo")
            tx.audit("ANOMALIA_CONSUMO", "ROLL", roll["id"], dopo={"consumo_macchina": consumo, "metri_verificati": start})
            break
        stima = D(a["metri_utilizzati"] or 0)
        conn.execute("""UPDATE wms.production_job_materials SET metri_consumo_stimato=greatest(metri_consumo_stimato-%s,0),
                        metri_consumati=metri_consumati+%s WHERE id=%s""", (stima, consumo, a["job_material_id"]))
        for res in conn.execute("SELECT * FROM wms.material_reservations WHERE job_material_id=%s AND roll_id=%s "
                                "AND status='ATTIVA' FOR UPDATE", (a["job_material_id"], roll["id"])).fetchall():
            _release(tx, res, causale="Consumo verificato da macchina", final_status="CONSUMATA")
        roll = get_roll(conn, roll["id"])
        nuovo = start - consumo
        over = D(roll["metri_riservati"]) - nuovo
        if over > 0:
            for res in conn.execute("SELECT * FROM wms.material_reservations WHERE roll_id=%s AND status='ATTIVA' "
                                    "ORDER BY created_at DESC FOR UPDATE", (roll["id"],)).fetchall():
                if over <= 0:
                    break
                over -= _release(tx, res, over, causale="Residuo reale inferiore alle prenotazioni")
        if consumo > 0:
            tx.move("CONSUMO", "ROLL", roll["id"], -consumo, "m", commessa=a["job_id"], reference=a["id"],
                    metadata={"tipo_dato": "MACCHINA", "macchina": a["macchina"], "stima_precedente": stima})
        _roll_update(conn, roll["id"], metri_residui=nuovo, origine_dato_metratura="CALCOLATO",
                     ultima_verifica=dt.datetime.now(dt.timezone.utc))
        conn.execute("""UPDATE wms.roll_assignments SET stato='CHIUSA', consumo_tipo='MACCHINA', metri_inizio=%s,
                        inizio_verificato=true, metri_utilizzati=%s, metri_scarto=0, metri_fine=%s WHERE id=%s""",
                     (start, consumo, nuovo, a["id"]))
        done += 1
        tot += consumo
    if done:
        roll = get_roll(conn, roll["id"])
        rest = conn.execute("""SELECT coalesce(sum(metri_utilizzati),0) AS s, count(*) AS n FROM wms.roll_assignments
                               WHERE roll_id=%s AND stato='DA_VERIFICARE'""", (roll["id"],)).fetchone()
        open_a = conn.execute("SELECT id FROM wms.roll_assignments WHERE roll_id=%s AND stato='IN_CORSO'",
                              (roll["id"],)).fetchone()
        verified = D(roll["metri_residui"])
        if rest["n"] == 0 and open_a:
            conn.execute("UPDATE wms.roll_assignments SET metri_inizio=%s, inizio_verificato=true WHERE id=%s",
                         (verified, open_a["id"]))
            _roll_update(conn, roll["id"], metri_stimati=None)
        elif rest["n"] == 0 and roll["stato"] == "DA_VERIFICARE":
            _roll_update(conn, roll["id"], metri_stimati=None, stato="ESAURITA" if verified == 0 else "DISPONIBILE",
                         ubicazione_id=None if verified == 0 else roll["ubicazione_id"])
        elif rest["n"] > 0:
            _roll_update(conn, roll["id"], metri_stimati=max(Decimal("0"), verified - D(rest["s"])))
    return {"verificati": done, "consumo": tot}


@engine.command("IMPORTA_STORICO_MACCHINA", roles=set())
def cmd_importa_storico(tx: Tx, p: dict) -> dict:
    conn = tx.conn
    macchina = p.get("macchina")
    righe = p.get("righe") or []
    if not macchina or not righe:
        raise BusinessRuleError("Macchina o righe mancanti", code="DATO_MANCANTE")
    nuove = 0
    for r in righe:
        x = conn.execute("""INSERT INTO wms.machine_runs(macchina, job_name, medium, stato, fine_at, durata_s, metri, file_origine)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id""",
                         (macchina, r.get("job_name"), r.get("medium"), r.get("stato"), r["fine_at"], r.get("durata_s"),
                          D(r["metri"]), p.get("file"))).fetchone()
        nuove += 1 if x else 0
    fino = max(dt.datetime.fromisoformat(r["fine_at"]) for r in righe)
    conn.execute("""INSERT INTO wms.machine_data_coverage(macchina, coperto_fino) VALUES (%s,%s)
                    ON CONFLICT (macchina) DO UPDATE SET coperto_fino=greatest(wms.machine_data_coverage.coperto_fino, EXCLUDED.coperto_fino)""",
                 (macchina, fino))
    rolls = conn.execute("""SELECT DISTINCT roll_id FROM wms.roll_assignments WHERE macchina=%s AND stato='DA_VERIFICARE'
                            ORDER BY roll_id""", (macchina,)).fetchall()
    verificate, consumo = 0, Decimal("0")
    for r in rolls:
        v = reconcile_roll(tx, r["roll_id"])
        verificate += v["verificati"]
        consumo += v["consumo"]
    tx.audit("IMPORTA_STORICO", "MACHINE", macchina, dopo={"righe": len(righe), "nuove": nuove, "fino": fino})
    return {"messaggio": f"Storico {macchina}: {nuove} righe nuove, {verificate} consumi confermati ({consumo:g} m)",
            "righe_nuove": nuove, "consumi_verificati": verificate, "coperto_fino": fino}


def next_job(conn, machine_code: str | None) -> dict | None:
    """Prossimo lavoro per una macchina: commessa aperta più urgente con stampa da fare su quella macchina."""
    j = conn.execute(
        """SELECT j.id, j.external_madiwor_id, j.cliente_nome, j.data_consegna FROM wms.production_jobs j
           WHERE j.stato='APERTA' AND EXISTS (SELECT 1 FROM wms.job_phases f WHERE f.job_id=j.id AND f.fase='STAMPA'
                 AND f.stato<>'COMPLETATA' AND (f.macchina IS NULL OR f.macchina=%s))
           ORDER BY j.data_consegna NULLS LAST, j.external_madiwor_id LIMIT 1""", (machine_code,)).fetchone()
    if not j:
        return None
    b = conn.execute("""SELECT b.barcode, l.codice AS ubicazione FROM wms.material_reservations r
                        JOIN wms.material_rolls b ON b.id=r.roll_id LEFT JOIN wms.warehouse_locations l ON l.id=b.ubicazione_id
                        WHERE r.job_id=%s AND r.status='ATTIVA' ORDER BY r.quantity DESC LIMIT 1""", (j["id"],)).fetchone()
    return {"commessa": j["external_madiwor_id"], "cliente": j["cliente_nome"], "consegna": j["data_consegna"],
            "bobina": b["barcode"] if b else None, "ubicazione": b["ubicazione"] if b else None}
