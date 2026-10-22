"""Scan Context Engine.

Una sola schermata "SCANSIONA UN CODICE". L'azione dipende da: codice letto, postazione, utente,
contesto della postazione (commessa aperta, oggetto in attesa di ubicazione, spedizione aperta),
stato dell'oggetto letto.

Garanzie:
- ogni scansione ha un client_scan_id (UUID generato sul dispositivo): la stessa scansione rispedita
  (retry, coda offline) restituisce la risposta già registrata e non esegue nulla due volte;
- stessa lettura dallo stesso dispositivo entro la finestra configurata, quando la precedente aveva
  eseguito un'operazione, è trattata come doppia scansione accidentale e non esegue nulla;
- i codici ambigui non eseguono nulla: si chiede di scegliere;
- le scansioni di una postazione sono serializzate (lock sulla riga di contesto);
- nessuna dipendenza dall'AI: tutto è deterministico.
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from psycopg.types.json import Jsonb

from . import engine
from .barcodes import Candidate, printable, recognize
from .engine import D, Actor, _jsonable, remaining_need
from .errors import WmsError

PREFERENZE = {
    "MACCHINA": ["JOB", "ROLL", "LOCATION"],
    "RICEVIMENTO": ["MATERIAL", "ROLL", "LOCATION"],
    "MAGAZZINO": ["ROLL", "PACKAGE", "LOCATION"],
    "SPEDIZIONE": ["SHIPMENT", "PACKAGE"],
    "UFFICIO": ["JOB", "FINISHED_PRODUCT"],
}


def _resp(esito: str, titolo: str, messaggio: str = "", **kw) -> dict:
    suono = {"OK": "ok", "INFO": "ok", "ERRORE": "errore", "DOPPIA": "attenzione", "AVVISO": "attenzione",
             "CHIEDI": "attenzione", "SCEGLI": "attenzione", "LOGIN": "ok", "SCONOSCIUTO": "errore"}[esito]
    return {"esito": esito, "suono": suono, "titolo": titolo, "messaggio": messaggio, **kw}


def handle_scan(conn, actor: Actor, code: str, client_scan_id, *, client_ts: dt.datetime | None = None,
                offline: bool = False, scelta: dict | None = None) -> dict:
    client_scan_id = engine.as_uuid(client_scan_id, "client_scan_id")
    with conn.transaction():
        conn.execute("INSERT INTO wms.device_context(device_id) VALUES (%s) ON CONFLICT DO NOTHING", (actor.device_id,))
        ctxrow = conn.execute("SELECT stato FROM wms.device_context WHERE device_id=%s FOR UPDATE", (actor.device_id,)).fetchone()
        prev = conn.execute("SELECT dettagli FROM wms.scan_events WHERE client_scan_id=%s", (client_scan_id,)).fetchone()
        if prev:
            r = dict(prev["dettagli"]["risposta"])
            r["ripetuta"] = True
            return r
        ctx = dict(ctxrow["stato"] or {})
        rec = recognize(conn, code)
        when = client_ts or dt.datetime.now(dt.timezone.utc)

        resp = _double_scan(conn, actor, printable(rec.normalized), when) if not scelta else None
        if resp is None:
            try:
                resp = _dispatch(conn, actor, ctx, rec, client_scan_id, scelta)
            except WmsError as e:
                resp = _resp("ERRORE", e.message, codice=e.code, dettagli=_jsonable(e.details))
        resp["contesto"] = _ctx_summary(conn, ctx)
        resp = _jsonable(resp)
        conn.execute("UPDATE wms.device_context SET stato=%s, updated_at=now() WHERE device_id=%s",
                     (Jsonb(_jsonable(ctx)), actor.device_id))
        conn.execute(
            """INSERT INTO wms.scan_events(client_scan_id, client_ts, device_id, user_id, raw_code, tipo_risolto, entita_id,
                 azione_proposta, esito, offline, dettagli) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (client_scan_id, when, actor.device_id, actor.user_id, printable(rec.normalized),
             rec.unico.tipo if rec.unico else rec.stato, rec.unico.id if rec.unico else None,
             (resp.get("comando") or {}).get("tipo"), resp["esito"], offline, Jsonb({"risposta": resp})))
        return resp


def _double_scan(conn, actor: Actor, normalized: str, when: dt.datetime) -> dict | None:
    win = int(engine.setting(conn, f"finestra_doppia_scansione_s_{actor.postazione}",
                             engine.setting(conn, "finestra_doppia_scansione_s", 3)))
    last = conn.execute(
        """SELECT raw_code, client_ts, azione_proposta, esito FROM wms.scan_events
           WHERE device_id=%s ORDER BY id DESC LIMIT 1""", (actor.device_id,)).fetchone()
    if (last and last["raw_code"] == normalized and last["azione_proposta"] and last["esito"] in ("OK", "AVVISO")
            and abs((when - last["client_ts"]).total_seconds()) <= win):
        return _resp("DOPPIA", "Doppia lettura ignorata", f"{normalized} era appena stato registrato")
    return None


def _cmd(conn, actor, scan_id, tipo, payload, n=0) -> dict:
    """Esegue un comando con event_id derivato dalla scansione: un retry della scansione = stesso comando."""
    r = engine.execute(conn, actor, uuid.uuid5(scan_id, f"cmd{n}"), tipo, payload)
    return r


def _ok_from(r: dict, titolo: str | None = None, **kw) -> dict:
    esito = "AVVISO" if r.get("avvisi") or r.get("esito") == "AVVISO" else "OK"
    return _resp(esito, titolo or r.get("messaggio", "Fatto"), " · ".join(r.get("avvisi", [])),
                 comando={"event_id": r["event_id"], "tipo": r["comando"]}, risultato=r,
                 stampa=r.get("stampa"), **kw)


def _dispatch(conn, actor: Actor, ctx: dict, rec, scan_id, scelta) -> dict:
    if scelta:
        cand = Candidate(scelta["tipo"], engine.as_uuid(scelta["id"]), scelta.get("etichetta", ""), "SCELTA")
    elif rec.stato == "NON_VALIDO":
        return _resp("ERRORE", rec.motivo or "Codice non valido", printable(rec.raw)[:60])
    elif rec.stato == "SCONOSCIUTO":
        if actor.postazione == "RICEVIMENTO":
            return _resp("SCONOSCIUTO", "Codice sconosciuto",
                         "Il responsabile deve associarlo a un materiale (una volta sola).",
                         codice_letto=rec.normalized, gs1=rec.gs1)
        return _resp("SCONOSCIUTO", "Codice sconosciuto", rec.motivo or rec.normalized)
    elif rec.stato == "AMBIGUO":
        pref = PREFERENZE.get(actor.postazione or "", [])
        ordered = sorted(rec.candidati, key=lambda c: pref.index(c.tipo) if c.tipo in pref else 99)
        return _resp("SCEGLI", "Codice valido per più oggetti", "Scegli quale intendi",
                     scelte=[{"tipo": c.tipo, "id": c.id, "etichetta": c.etichetta} for c in ordered],
                     codice_letto=rec.normalized)
    else:
        cand = rec.unico
    t = cand.tipo
    if t == "USER":
        return _resp("LOGIN", f"Badge di {cand.etichetta}", "Cambio operatore", badge=rec.normalized)
    if t == "JOB":
        return _on_job(conn, actor, ctx, cand.id)
    if t == "ROLL":
        return _on_roll(conn, actor, ctx, cand.id, scan_id)
    if t == "LOCATION":
        return _on_location(conn, actor, ctx, cand.id, scan_id)
    if t == "PACKAGE":
        return _on_package(conn, actor, ctx, cand.id, scan_id)
    if t == "SHIPMENT":
        return _on_shipment(conn, actor, ctx, cand.id)
    if t == "MATERIAL":
        return _on_material(conn, actor, ctx, cand, rec, scan_id)
    if t == "FINISHED_PRODUCT":
        n = conn.execute("""SELECT count(*) AS colli, coalesce(sum(p.quantita),0) AS pz FROM wms.finished_goods_packages p
                            JOIN wms.production_lots l ON l.id=p.lotto_id WHERE l.finished_product_id=%s
                            AND p.stato='DISPONIBILE'""", (cand.id,)).fetchone()
        return _resp("INFO", cand.etichetta, f"A magazzino: {n['colli']} colli, {n['pz']} pz")
    return _resp("ERRORE", "Tipo di codice non gestito qui", t)


# --- commessa ---------------------------------------------------------------
def job_summary(conn, job_id) -> dict:
    job = engine.get_job(conn, job_id, lock=False)
    righe = []
    for jm in conn.execute("""SELECT jm.*, m.descrizione FROM wms.production_job_materials jm
                              LEFT JOIN wms.materials m ON m.id=jm.material_id WHERE jm.job_id=%s AND jm.attiva""",
                           (job["id"],)).fetchall():
        pren = conn.execute(
            """SELECT b.barcode, x.quantity, l.codice AS ubicazione, b.stato FROM wms.material_reservations x
               JOIN wms.material_rolls b ON b.id=x.roll_id LEFT JOIN wms.warehouse_locations l ON l.id=b.ubicazione_id
               WHERE x.job_material_id=%s AND x.status='ATTIVA' ORDER BY x.quantity DESC""", (jm["id"],)).fetchall()
        righe.append({"materiale": jm["descrizione"] or jm["material_label_source"], "risolto": jm["material_id"] is not None,
                      "larghezza_mm": jm["larghezza_richiesta_mm"], "teorico": jm["metri_teorici"],
                      "prenotato": jm["metri_prenotati"], "consumato": jm["metri_consumati"],
                      "stimato": jm["metri_consumo_stimato"], "scarto": jm["metri_scarto"],
                      "da_coprire": max(Decimal("0"), remaining_need(jm) - D(jm["metri_prenotati"])),
                      "bobine": pren})
    fasi = conn.execute("SELECT fase, stato, macchina FROM wms.job_phases WHERE job_id=%s ORDER BY seq", (job["id"],)).fetchall()
    return {"id": job["id"], "commessa": job["external_madiwor_id"], "ordine": job["sales_order_id"],
            "cliente": job["cliente_nome"], "articolo": job["articolo_codice"], "descrizione": job["descrizione"],
            "quantita": job["quantita_ordinata"], "consegna": job["data_consegna"], "stato": job["stato"],
            "materiali": righe, "fasi": fasi}


def _on_job(conn, actor, ctx, job_id) -> dict:
    s = job_summary(conn, job_id)
    if s["stato"] == "ANNULLATA":
        ctx.pop("job_id", None)
        return _resp("ERRORE", f"Commessa {s['commessa']} ANNULLATA", "Non va prodotta", commessa=s)
    ctx["job_id"] = str(job_id)
    ctx.pop("pending", None)
    mancanze = [r for r in s["materiali"] if r["da_coprire"] > 0 or not r["risolto"]]
    bob = [b for r in s["materiali"] for b in r["bobine"]]
    if actor.postazione == "MACCHINA":
        titolo = f"Commessa {s['commessa']} — {s['cliente']}"
        msg = ("Prendi " + ", ".join(f"{b['barcode']} ({b['ubicazione'] or '-'})" for b in bob) + " e scansionala"
               if bob else "Nessuna bobina prenotata: scansiona una bobina compatibile")
    else:
        titolo, msg = f"Commessa {s['commessa']}", s["cliente"]
    if mancanze:
        return _resp("AVVISO", titolo, msg + " · MATERIALE MANCANTE", commessa=s)
    return _resp("INFO", titolo, msg, commessa=s)


# --- bobina -----------------------------------------------------------------
def roll_summary(conn, roll_id) -> dict:
    r = conn.execute("""SELECT r.*, m.descrizione, l.codice AS ubicazione, j.external_madiwor_id AS commessa
                        FROM wms.material_rolls r JOIN wms.materials m ON m.id=r.material_id
                        LEFT JOIN wms.warehouse_locations l ON l.id=r.ubicazione_id
                        LEFT JOIN wms.production_jobs j ON j.id=r.assigned_job_id WHERE r.id=%s""", (roll_id,)).fetchone()
    return {"id": r["id"], "barcode": r["barcode"], "materiale": r["descrizione"], "larghezza_mm": r["larghezza_mm"],
            "stato": r["stato"], "metri_fisici": r["metri_residui"], "metri_riservati": r["metri_riservati"],
            "metri_disponibili": engine.roll_available(r), "metri_stimati": r["metri_stimati"],
            "origine_metratura": r["origine_dato_metratura"], "ubicazione": r["ubicazione"], "commessa": r["commessa"],
            "ubicazione_confermata": r["ubicazione_confermata"]}


def _place_text(c: dict | None) -> tuple[str, str]:
    if not c:
        return "Nessun posto libero", "Chiedi al responsabile dove appoggiarla"
    return f"Metti in {c['codice']}", " · ".join(c["istruzioni"]) or c["motivo"]


def _auto_job(conn, actor, roll) -> dict | None:
    """Commessa per questa bobina su questa macchina: prima quella che l'ha prenotata, poi la consegna più urgente."""
    mc = conn.execute("SELECT machine_code FROM wms.warehouse_locations WHERE id=%s", (actor.device_location_id,)).fetchone()
    mc = mc["machine_code"] if mc else None
    rows = conn.execute(
        """SELECT j.*, jm.id AS jm_id, jm.material_id, jm.larghezza_richiesta_mm, jm.metri_teorici, jm.metri_consumati,
                  jm.metri_consumo_stimato,
                  EXISTS (SELECT 1 FROM wms.material_reservations r WHERE r.job_material_id=jm.id AND r.roll_id=%s
                          AND r.status='ATTIVA') AS prenotata
           FROM wms.production_jobs j JOIN wms.production_job_materials jm ON jm.job_id=j.id AND jm.attiva
           WHERE j.stato IN ('APERTA','IN_PRODUZIONE')
             AND NOT EXISTS (SELECT 1 FROM wms.job_phases f WHERE f.job_id=j.id AND f.fase='STAMPA'
                             AND (f.stato='COMPLETATA' OR (f.macchina IS NOT NULL AND f.macchina IS DISTINCT FROM %s)))""",
        (roll["id"], mc)).fetchall()
    ok = []
    for r in rows:
        if r["material_id"] is None or remaining_need(r) <= 0:
            continue
        if engine.material_compatibility(conn, r["material_id"], roll["material_id"], r["cliente_ref"]) is None:
            continue
        if not engine.width_ok(conn, roll["larghezza_mm"], r["larghezza_richiesta_mm"]):
            continue
        ok.append(r)
    if not ok:
        return None
    ok.sort(key=lambda r: (0 if r["prenotata"] else 1, r["data_consegna"] or dt.date.max, r["external_madiwor_id"]))
    best = ok[0]
    return {"id": best["id"], "commessa": best["external_madiwor_id"], "altre": len({r["id"] for r in ok}) - 1}


def _on_roll(conn, actor, ctx, roll_id, scan_id) -> dict:
    from .machine import next_job
    s = roll_summary(conn, roll_id)
    if actor.postazione == "MACCHINA":
        roll = conn.execute("SELECT * FROM wms.material_rolls WHERE id=%s", (roll_id,)).fetchone()
        if s["stato"] == "IN_PRODUZIONE":
            # fine lavoro: chiusura senza chiedere nulla (consumo dalla macchina o stimato), poi posto e etichetta
            r = _cmd(conn, actor, scan_id, "CHIUDI_BOBINA", {"roll_id": str(roll_id)})
            after = roll_summary(conn, roll_id)
            if after["stato"] == "ESAURITA" or (after["metri_stimati"] is not None and after["metri_stimati"] <= 0):
                titolo, istr, stampa = "Bobina finita", "Butta l'anima vuota", None
            else:
                c = _cmd(conn, actor, scan_id, "COLLOCA_BOBINA", {"roll_id": str(roll_id)}, 1).get("collocazione")
                titolo, istr = _place_text(c)
                stampa = [{"tipo": "bobina", "id": str(roll_id)}]
            nj = next_job(conn, (conn.execute("SELECT machine_code FROM wms.warehouse_locations WHERE id=%s",
                                              (actor.device_location_id,)).fetchone() or {}).get("machine_code"))
            dati = ("consumo dalla macchina " + f"{D(r['consumo_macchina']):g} m") if r.get("verificato") else \
                   (f"consumo stimato {D(r['stima_consumo']):g} m, lo conferma la macchina" if r.get("stima_consumo") is not None else r["messaggio"])
            ctx.pop("job_id", None)
            return _resp("OK", titolo, f"{istr} — {dati}", comando={"event_id": r["event_id"], "tipo": r["comando"]},
                         bobina=roll_summary(conn, roll_id), stampa=stampa, prossimo=nj)
        job_id = ctx.get("job_id")
        auto = None
        if not job_id:
            auto = _auto_job(conn, actor, roll)
            if not auto:
                return _resp("ERRORE", "Nessuna commessa usa questa bobina",
                             f"{s['materiale']} {D(s['larghezza_mm']):g} mm: nessun lavoro aperto per questa macchina", bobina=s)
            job_id = str(auto["id"])
        r = _cmd(conn, actor, scan_id, "ASSEGNA_BOBINA", {"job_id": job_id, "roll_id": str(roll_id)})
        ctx["job_id"] = job_id
        summary = job_summary(conn, job_id)
        extra = f" · altre {auto['altre']} commesse possono usarla" if auto and auto["altre"] else ""
        return _resp("AVVISO" if r.get("avvisi") else "OK", f"Commessa {summary['commessa']}",
                     f"Monta {s['barcode']} — a fine lavoro rileggila" + extra + ("" if not r.get("avvisi") else " · " + " · ".join(r["avvisi"])),
                     comando={"event_id": r["event_id"], "tipo": r["comando"]}, commessa=summary)
    if ctx.get("target"):
        r = _cmd(conn, actor, scan_id, "SPOSTA_BOBINA", {"roll_id": str(roll_id), "destinazione_id": ctx["target"]["id"]})
        return _ok_from(r, bobina=roll_summary(conn, roll_id))
    ctx["pending"] = {"tipo": "ROLL", "id": str(roll_id), "barcode": s["barcode"]}
    return _resp("INFO", f"{s['barcode']} — {s['materiale']}",
                 f"{s['metri_fisici']} m ({s['metri_disponibili']} liberi) in {s['ubicazione'] or '-'} · "
                 "scansiona l'ubicazione per spostarla", bobina=s)


def _ask_measure(s) -> dict:
    return _resp("CHIEDI", f"{s['barcode']}: metratura da verificare",
                 f"Stima {s['metri_stimati']} m. Misura e inserisci i metri reali.", bobina=s,
                 chiedi={"azione": "VERIFICA_METRATURA", "dati": {"roll_id": s["id"]},
                         "campi": [{"nome": "metri_misurati", "etichetta": "Metri misurati", "tipo": "numero",
                                    "obbligatorio": True}]})


# --- ubicazione ---------------------------------------------------------------
def _on_location(conn, actor, ctx, loc_id, scan_id) -> dict:
    loc = engine.get_location(conn, loc_id)
    pend = ctx.pop("pending", None)
    if pend:
        tipo = "SPOSTA_BOBINA" if pend["tipo"] == "ROLL" else "SPOSTA_COLLO"
        key = "roll_id" if pend["tipo"] == "ROLL" else "package_id"
        r = _cmd(conn, actor, scan_id, tipo, {key: pend["id"], "destinazione_id": str(loc["id"])})
        return _ok_from(r)
    if ctx.get("target", {}).get("id") == str(loc["id"]):
        ctx.pop("target")
        return _resp("INFO", f"Fine stoccaggio in {loc['codice']}")
    ctx["target"] = {"id": str(loc["id"]), "codice": loc["codice"]}
    n = conn.execute("""SELECT (SELECT count(*) FROM wms.material_rolls WHERE ubicazione_id=%s AND stato NOT IN
                          ('ESAURITA','TAGLIATA','ANNULLATA')) AS bobine,
                               (SELECT count(*) FROM wms.finished_goods_packages WHERE ubicazione_id=%s
                                AND stato IN ('DISPONIBILE','RESO','BLOCCATO')) AS colli""", (loc["id"], loc["id"])).fetchone()
    return _resp("INFO", f"Ubicazione {loc['codice']}",
                 f"{n['bobine']} bobine, {n['colli']} colli · ora ogni bobina/collo letto viene messo qui "
                 "(rileggi l'ubicazione per finire)")


# --- collo / spedizione -------------------------------------------------------
def _on_package(conn, actor, ctx, pkg_id, scan_id) -> dict:
    p = conn.execute("""SELECT p.*, l.codice AS lotto, fp.external_sku_id, loc.codice AS ubicazione
                        FROM wms.finished_goods_packages p JOIN wms.production_lots l ON l.id=p.lotto_id
                        JOIN wms.finished_products fp ON fp.id=l.finished_product_id
                        LEFT JOIN wms.warehouse_locations loc ON loc.id=p.ubicazione_id WHERE p.id=%s""", (pkg_id,)).fetchone()
    info = {"barcode": p["barcode"], "articolo": p["external_sku_id"], "quantita": p["quantita"], "lotto": p["lotto"],
            "stato": p["stato"], "ubicazione": p["ubicazione"]}
    if actor.postazione == "SPEDIZIONE":
        if not ctx.get("shipment_id"):
            return _resp("INFO", f"Collo {p['barcode']}", "Scansiona prima la spedizione", collo=info)
        r = _cmd(conn, actor, scan_id, "PRELEVA_COLLO", {"shipment_id": ctx["shipment_id"], "package_id": str(pkg_id)})
        if r.get("esito") == "INVARIATO":
            return _resp("INFO", r["messaggio"], collo=info)
        return _ok_from(r, collo=info)
    if ctx.get("target"):
        r = _cmd(conn, actor, scan_id, "SPOSTA_COLLO", {"package_id": str(pkg_id), "destinazione_id": ctx["target"]["id"]})
        return _ok_from(r, collo=info)
    ctx["pending"] = {"tipo": "PACKAGE", "id": str(pkg_id), "barcode": p["barcode"]}
    return _resp("INFO", f"Collo {p['barcode']} — art. {p['external_sku_id']}",
                 f"{p['quantita']} pz, lotto {p['lotto']}, {p['stato']} · scansiona l'ubicazione per spostarlo", collo=info)


def shipment_summary(conn, sh_id) -> dict:
    sh = conn.execute("SELECT * FROM wms.shipments WHERE id=%s", (sh_id,)).fetchone()
    righe = conn.execute(
        """SELECT l.id, fp.external_sku_id AS articolo, fp.versione, l.quantita_richiesta, l.quantita_preparata,
                  (SELECT json_agg(json_build_object('barcode', p.barcode, 'pz', p.quantita, 'ubicazione', loc.codice)
                                   ORDER BY p.data_creazione)
                   FROM wms.finished_goods_packages p JOIN wms.production_lots lt ON lt.id=p.lotto_id
                   LEFT JOIN wms.warehouse_locations loc ON loc.id=p.ubicazione_id
                   WHERE lt.finished_product_id=l.finished_product_id AND p.stato='DISPONIBILE'
                     AND lt.stato_qualita='APPROVATO'
                     AND (l.production_job_id IS NULL OR lt.production_job_id=l.production_job_id)) AS colli_suggeriti
           FROM wms.shipment_lines l JOIN wms.finished_products fp ON fp.id=l.finished_product_id
           WHERE l.shipment_id=%s ORDER BY fp.external_sku_id""", (sh_id,)).fetchall()
    return {"id": sh["id"], "barcode": sh["barcode"], "cliente": sh["cliente_nome"], "stato": sh["stato"], "righe": righe}


def _on_shipment(conn, actor, ctx, sh_id) -> dict:
    s = shipment_summary(conn, sh_id)
    if s["stato"] in ("USCITA", "ANNULLATA"):
        return _resp("ERRORE", f"Spedizione {s['barcode']} {s['stato'].lower()}", spedizione=s)
    ctx["shipment_id"] = str(sh_id)
    return _resp("INFO", f"Spedizione {s['barcode']} — {s['cliente']}", "Scansiona i colli", spedizione=s)


# --- materiale (codice fornitore / GTIN) ----------------------------------------
def _on_material(conn, actor, ctx, cand: Candidate, rec, scan_id) -> dict:
    mat = conn.execute("SELECT * FROM wms.materials WHERE id=%s", (cand.id,)).fetchone()
    if actor.postazione != "RICEVIMENTO":
        g = conn.execute("""SELECT coalesce(sum(metri_fisici),0) AS f, coalesce(sum(metri_disponibili),0) AS d
                            FROM wms.v_giacenze_materiali WHERE material_id=%s""", (mat["id"],)).fetchone()
        return _resp("INFO", mat["descrizione"], f"{g['f']} m fisici, {g['d']} m disponibili")
    dati = {"material_id": mat["id"], "codice_letto": rec.normalized, "colloca": True}
    campi = []
    metri = rec.gs1.get("311") if rec.gs1 else None
    if metri is None and cand.extra.get("identifica_unita") and cand.extra.get("metri_dichiarati"):
        metri = cand.extra["metri_dichiarati"]
    if metri is None and mat["metri_nominali"] is not None:
        metri = mat["metri_nominali"]          # metratura nominale dichiarata dal fornitore per questo materiale
        dati["metratura_nominale"] = True
    if metri is not None:
        dati["metri"] = D(metri)
        dati["origine_metratura"] = "FORNITORE"
    else:
        campi.append({"nome": "metri", "etichetta": "Metri della bobina", "tipo": "numero", "obbligatorio": True})
    if mat["larghezza_mm"] is not None:
        dati["larghezza_mm"] = mat["larghezza_mm"]
    else:
        campi.append({"nome": "larghezza_mm", "etichetta": "Larghezza (mm)", "tipo": "numero", "obbligatorio": True})
    if rec.gs1 and rec.gs1.get("10"):
        dati["lotto_fornitore"] = rec.gs1["10"]
    if not campi:
        # tutto noto: si registra subito, si sceglie il posto e si stampa l'etichetta
        r = _cmd(conn, actor, scan_id, "RICEVI_BOBINA", dati)
        b = r["bobine"][0]
        titolo, istr = _place_text(b.get("collocazione"))
        nota = " · metratura nominale del fornitore" if dati.get("metratura_nominale") else ""
        return _resp("OK", titolo, istr + nota, comando={"event_id": r["event_id"], "tipo": r["comando"]},
                     bobina=roll_summary(conn, b["id"]), stampa=r.get("stampa"),
                     collocazione=b.get("collocazione"))
    return _resp("CHIEDI", f"Ricevimento: {mat['descrizione']}",
                 "Inserisci solo i dati mancanti" if any(c.get("obbligatorio") for c in campi) else "Conferma con Invio",
                 chiedi={"azione": "RICEVI_BOBINA", "dati": dati, "campi": campi})


def _ctx_summary(conn, ctx) -> dict:
    out = {}
    if ctx.get("job_id"):
        j = conn.execute("SELECT external_madiwor_id FROM wms.production_jobs WHERE id=%s", (ctx["job_id"],)).fetchone()
        out["commessa"] = j["external_madiwor_id"] if j else None
    if ctx.get("pending"):
        out["in_attesa_ubicazione"] = ctx["pending"]["barcode"]
    if ctx.get("target"):
        out["stoccaggio_in"] = ctx["target"]["codice"]
    if ctx.get("shipment_id"):
        s = conn.execute("SELECT barcode FROM wms.shipments WHERE id=%s", (ctx["shipment_id"],)).fetchone()
        out["spedizione"] = s["barcode"] if s else None
    return out


def after_command(conn, actor: Actor, tipo: str, result: dict) -> dict:
    """Dopo un comando confermato da modulo, aggiorna il contesto della postazione così che il passo
    fisico successivo richieda una sola scansione (es. bobina appena ricevuta → scansiona lo scaffale)."""
    pend = None
    if tipo == "RICEVI_BOBINA" and len(result.get("bobine") or []) == 1 and not result["bobine"][0].get("collocazione"):
        b = result["bobine"][0]
        pend = {"tipo": "ROLL", "id": str(b["id"]), "barcode": b["barcode"]}
    elif tipo in ("CHIUDI_BOBINA", "VERIFICA_METRATURA") and (result.get("residui") or 0) > 0:
        r = conn.execute("SELECT id, barcode FROM wms.material_rolls WHERE id=%s",
                         (conn.execute("SELECT entity_id FROM wms.inventory_movements WHERE command_event_id=%s "
                                       "AND entity_type='ROLL' LIMIT 1", (result["event_id"],)).fetchone()["entity_id"],)).fetchone()
        pend = {"tipo": "ROLL", "id": str(r["id"]), "barcode": r["barcode"]}
    elif tipo == "CONFEZIONA":
        pend = {"tipo": "PACKAGE", "id": str(result["package_id"]), "barcode": result["collo"]}
    with conn.transaction():
        conn.execute("INSERT INTO wms.device_context(device_id) VALUES (%s) ON CONFLICT DO NOTHING", (actor.device_id,))
        row = conn.execute("SELECT stato FROM wms.device_context WHERE device_id=%s FOR UPDATE", (actor.device_id,)).fetchone()
        ctx = dict(row["stato"] or {})
        if pend and not result.get("duplicato"):
            ctx["pending"] = pend
        conn.execute("UPDATE wms.device_context SET stato=%s, updated_at=now() WHERE device_id=%s",
                     (Jsonb(_jsonable(ctx)), actor.device_id))
    out = _ctx_summary(conn, ctx)
    return out
