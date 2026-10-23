"""API HTTP del modulo magazzino + schermata scanner (PWA).

Avvio locale:  WMS_DATABASE_URL=... flask --app wms.app run
Produzione:    gunicorn "wms.app:create_app()"   (stesso schema del servizio Flask già su Render)

Autenticazione: ogni postazione ha un token dispositivo (header X-Device-Token, salvato una volta
sul dispositivo); l'operatore entra scansionando il badge e riceve un token di sessione
(Authorization: Bearer ...). Nessun token passa mai negli URL.
"""
from __future__ import annotations

import datetime as dt
import os
import pathlib
import threading
conn_lock = threading.Lock()

from flask import Flask, Response, g, jsonify, request, send_from_directory

from . import auth, db, engine, labels, machine, madiwor, scan
from .errors import WmsError
from .engine import _jsonable

STATIC = pathlib.Path(__file__).resolve().parent / "static"
_local = threading.local()


def _conn():
    c = getattr(_local, "conn", None)
    if c is None or c.closed:
        _local.conn = c = db.connect(os.environ.get("WMS_DATABASE_URL"))
    return c


def _ts(v):
    if not v:
        return None
    try:
        t = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def create_app(dsn: str | None = None) -> Flask:
    if dsn:
        os.environ["WMS_DATABASE_URL"] = dsn
    app = Flask(__name__, static_folder=None)
    app.config["JSON_AS_ASCII"] = False

    @app.errorhandler(WmsError)
    def _wms_error(e: WmsError):
        return jsonify(e.to_dict()), e.http_status

    def device():
        g.device = auth.device_from_token(_conn(), request.headers.get("X-Device-Token"))
        return g.device

    def actor(offline=False, client_ts=None, fonte="SCANNER"):
        d = device()
        h = request.headers.get("Authorization", "")
        tok = h[7:] if h.startswith("Bearer ") else None
        return auth.actor_from_session(_conn(), d, tok, offline=offline, client_ts=client_ts, fonte=fonte)

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "scanner.html")

    @app.get("/static/<path:p>")
    def static_files(p):
        resp = send_from_directory(STATIC, p)
        if p == "sw.js":
            resp.headers["Service-Worker-Allowed"] = "/"
        return resp

    @app.get("/demo")
    def demo_page():
        if os.environ.get("WMS_DEMO") != "1":
            return Response("Non disponibile", status=404)
        from . import demo
        return Response(demo.page(_conn()), mimetype="text/html")

    @app.get("/cartellino-quarti")
    def cartellino_quarti():
        """Cartellino da plastificare e tenere in macchina: a fine lavoro si legge quanto è rimasto."""
        from .labels import code128_svg
        voci = [("UPQ0", "Finita"), ("UPQ1", "1/4"), ("UPQ2", "2/4"), ("UPQ3", "3/4")]
        celle = "".join(f'<div class=v><b>{t}</b>{code128_svg(c, 14)}<small>{c}</small></div>' for c, t in voci)
        html = ("<!doctype html><html lang=it><meta charset=utf-8><title>Cartellino fine lavoro</title><style>"
                "@page{size:A5 landscape;margin:8mm}body{font-family:Arial,sans-serif;margin:0}"
                "h1{font-size:16pt;margin:0 0 4mm}.g{display:grid;grid-template-columns:1fr 1fr;gap:6mm}"
                ".v{border:1px solid #000;border-radius:3mm;padding:4mm 6mm;text-align:center}"
                ".v b{display:block;font-size:28pt;margin-bottom:2mm}.v small{font:10pt monospace}</style>"
                f"<h1>Fine lavoro: quanto è rimasto sulla bobina?</h1><div class=g>{celle}</div></html>")
        return Response(html, mimetype="text/html")

    @app.get("/api/salute")
    def salute():
        _conn().execute("SELECT 1")
        return {"ok": True}

    @app.post("/api/login")
    def login():
        d = device()
        b = request.get_json(force=True) or {}
        tok = auth.login(_conn(), d, badge=b.get("badge"), username=b.get("username"), pin=b.get("pin"))
        a = auth.actor_from_session(_conn(), d, tok)
        u = _conn().execute("SELECT display_name FROM wms.users WHERE id=%s", (a.user_id,)).fetchone()
        return {"sessione": tok, "operatore": u["display_name"], "ruolo": a.role_code, "postazione": d["postazione"],
                "dispositivo": d["nome"]}

    @app.post("/api/logout")
    def logout():
        d = device()
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            _conn().execute("DELETE FROM wms.sessions WHERE token_hash=%s AND device_id=%s", (auth.sha(h[7:]), d["id"]))
        return {"ok": True}

    @app.get("/api/stato")
    def stato():
        a = actor()
        u = _conn().execute("SELECT display_name FROM wms.users WHERE id=%s", (a.user_id,)).fetchone()
        out = {"operatore": u["display_name"], "ruolo": a.role_code, "postazione": a.postazione,
               "dispositivo": g.device["nome"], "senza_badge": bool(g.device.get("utente_predefinito"))}
        if os.environ.get("WMS_DEMO") == "1":
            from .demo import POSTAZIONI
            out["demo_postazioni"] = [{"nome": n.replace("Postazione ", ""), "token": t} for n, t in POSTAZIONI.items()
                                      if "(2)" not in n]
        if a.postazione == "MACCHINA" and a.device_location_id:
            mc = _conn().execute("SELECT machine_code FROM wms.warehouse_locations WHERE id=%s", (a.device_location_id,)).fetchone()
            out["prossimo"] = machine.next_job(_conn(), mc["machine_code"] if mc else None)
        return jsonify(_jsonable(out))

    @app.post("/api/scan")
    def do_scan():
        b = request.get_json(force=True) or {}
        ts = _ts(b.get("client_ts"))
        a = actor(offline=bool(b.get("offline")), client_ts=ts)
        r = scan.handle_scan(_conn(), a, b.get("code", ""), b.get("client_scan_id"), client_ts=ts,
                             offline=bool(b.get("offline")), scelta=b.get("scelta"))
        return jsonify(r)

    @app.post("/api/command")
    def do_command():
        b = request.get_json(force=True) or {}
        ts = _ts(b.get("client_ts"))
        a = actor(offline=bool(b.get("offline")), client_ts=ts, fonte="UI")
        tipo = b.get("tipo")
        if tipo == "IMPORTA_COMMESSA":
            raise WmsError("Le commesse si importano solo dall'adattatore Madiwor", code="NON_CONSENTITO")
        r = engine.execute(_conn(), a, b.get("event_id"), tipo, b.get("payload") or {})
        r["contesto"] = scan.after_command(_conn(), a, tipo, r)
        if r["contesto"].get("in_attesa_ubicazione"):
            r["prossimo_passo"] = "Scansiona l'ubicazione"
        return jsonify(_jsonable(r))

    @app.post("/api/etichette")
    def etichette():
        actor()
        b = request.get_json(force=True) or {}
        prof = _conn().execute("SELECT * FROM wms.printer_profiles ORDER BY nome LIMIT 1").fetchone()
        items = labels.items_for(_conn(), b.get("tipo"), b.get("ids") or [])
        html = labels.label_html(items, float(prof["larghezza_mm"]), float(prof["altezza_mm"]), float(prof["gap_mm"]))
        return Response(html, mimetype="text/html")

    @app.get("/api/giacenze")
    def giacenze():
        actor()
        rows = _conn().execute("SELECT * FROM wms.v_giacenze_materiali WHERE bobine > 0 ORDER BY descrizione").fetchall()
        return jsonify(_jsonable(rows))

    @app.get("/api/commessa/<ext>")
    def commessa(ext):
        actor()
        j = _conn().execute("SELECT id FROM wms.production_jobs WHERE external_madiwor_id=%s", (ext,)).fetchone()
        if not j:
            raise WmsError("Commessa non trovata", code="NON_TROVATO")
        return jsonify(_jsonable(scan.job_summary(_conn(), j["id"])))

    @app.get("/api/anomalie")
    def anomalie():
        actor()
        return jsonify(_jsonable(inventory_checks(_conn())))

    @app.post("/api/macchine/<codice>/storico")
    def storico_macchina(codice):
        """Carica l'export 'print history' della macchina (CSV) e verifica i consumi stimati."""
        a = actor(fonte="UI")
        text = request.get_data(as_text=True)
        righe = machine.parse_xeikon_csv(text)
        import hashlib, uuid as _u
        ev = _u.uuid5(_u.NAMESPACE_URL, f"storico:{codice}:{hashlib.sha256(text.encode()).hexdigest()}")
        r = engine.execute(_conn(), a, ev, "IMPORTA_STORICO_MACCHINA",
                           {"macchina": codice, "righe": righe, "file": request.args.get("file")})
        return jsonify(_jsonable(r))

    @app.post("/api/demo/simula-storico")
    def simula_storico():
        """SOLO istanza di prova: crea uno storico Xeikon finto (stima −3%) per mostrare la verifica dei consumi."""
        if os.environ.get("WMS_DEMO") != "1":
            return Response("Non disponibile", status=404)
        a = actor(fonte="UI")
        import uuid as _u
        rows = _conn().execute("""SELECT id, inizio_at, fine_at, metri_utilizzati FROM wms.roll_assignments
                                  WHERE stato='DA_VERIFICARE' AND macchina='CX3S' ORDER BY inizio_at""").fetchall()
        if not rows:
            return jsonify({"messaggio": "Nessun consumo stimato da verificare"})
        righe = [{"job_name": "SIMULAZIONE", "medium": "simulato", "stato": "Completed",
                  "fine_at": (x["inizio_at"] + (x["fine_at"] - x["inizio_at"]) / 2).isoformat(), "durata_s": 60,
                  "metri": str((engine.D(x["metri_utilizzati"]) * engine.D("0.97")).quantize(engine.D("0.01")))} for x in rows]
        righe.append({"job_name": "SIMULAZIONE", "medium": "", "stato": "Completed", "durata_s": 0, "metri": "0",
                      "fine_at": (max(x["fine_at"] for x in rows) + __import__("datetime").timedelta(seconds=1)).isoformat()})
        return jsonify(_jsonable(engine.execute(_conn(), a, _u.uuid4(), "IMPORTA_STORICO_MACCHINA",
                                                {"macchina": "CX3S", "righe": righe, "file": "simulazione"})))

    @app.post("/api/demo/ricomincia")
    def demo_ricomincia():
        """SOLO istanza di prova: cancella tutto lo schema wms e ricarica i dati demo da zero."""
        if os.environ.get("WMS_DEMO") != "1":
            return Response("Non disponibile", status=404)
        actor(fonte="UI")
        from . import demo
        c = _conn()
        with conn_lock:
            c.execute("DROP SCHEMA IF EXISTS wms CASCADE")
            c.execute("DROP TABLE IF EXISTS public.wms_schema_migrations")
            db.apply_migrations(c)
            demo.bootstrap(c)
        return jsonify({"messaggio": "Dati di prova ricaricati da zero"})

    @app.get("/api/metriche")
    def metriche():
        """Scansioni e interazioni manuali per tipo di operazione (sez. 5: 'misurare')."""
        actor()
        rows = _conn().execute("""
            SELECT c.command_type AS operazione,
                   count(*) FILTER (WHERE m.fonte='SCANNER') AS da_scansione,
                   count(*) FILTER (WHERE m.fonte='UI')      AS da_modulo_manuale,
                   count(*) AS totale
            FROM wms.commands c
            LEFT JOIN LATERAL (SELECT fonte FROM wms.inventory_movements x WHERE x.command_event_id=c.event_id
                               ORDER BY id LIMIT 1) m ON true
            WHERE c.created_at > now() - interval '30 days'
            GROUP BY 1 ORDER BY 4 DESC""").fetchall()
        scans = _conn().execute("""SELECT esito, count(*) AS n FROM wms.scan_events
                                   WHERE ts > now() - interval '30 days' GROUP BY 1 ORDER BY 2 DESC""").fetchall()
        return jsonify(_jsonable({"operazioni": rows, "scansioni_per_esito": scans}))

    @app.post("/api/madiwor/commessa")
    def importa():
        a = actor()
        if a.role_level < engine.LEVEL_RESPONSABILE:
            raise WmsError("Solo il responsabile importa commesse a mano", code="NON_AUTORIZZATO")
        b = request.get_json(force=True) or {}
        job = madiwor.MadiworJob(
            external_id=str(b["external_id"]), cliente_nome=b["cliente_nome"], sales_order_id=b.get("sales_order_id"),
            cliente_ref=b.get("cliente_ref"), articolo=b.get("articolo"), descrizione=b.get("descrizione"),
            quantita=b.get("quantita"), data_consegna=madiwor._parse_date(b.get("data_consegna")),
            stato=b.get("stato", "ATTIVA"), fasi=b.get("fasi") or [], specifiche=b.get("specifiche") or {},
            materiali=[madiwor.MaterialeRichiesto(m["descrizione"], engine.D(m["larghezza_mm"]) if m.get("larghezza_mm") else None,
                                                  engine.D(m["metri"])) for m in b.get("materiali") or []])
        return jsonify(_jsonable(madiwor.import_job(_conn(), job, b.get("fonte", "EXPORT_STRUTTURATO"))))

    return app


def inventory_checks(conn) -> dict:
    """Inventario intelligente: dove conviene contare/verificare. Solo lettura."""
    q = conn.execute
    return {
        "bobine_ferme_90_giorni": q("""SELECT r.barcode, m.descrizione, r.metri_residui, l.codice AS ubicazione,
                (SELECT max(ts) FROM wms.inventory_movements x WHERE x.entity_id=r.id) AS ultimo_movimento
            FROM wms.material_rolls r JOIN wms.materials m ON m.id=r.material_id
            LEFT JOIN wms.warehouse_locations l ON l.id=r.ubicazione_id
            WHERE r.stato='DISPONIBILE' AND (SELECT max(ts) FROM wms.inventory_movements x WHERE x.entity_id=r.id)
                  < now() - interval '90 days' ORDER BY ultimo_movimento""").fetchall(),
        "metrature_stimate_da_verificare": q("""SELECT r.barcode, r.metri_stimati, r.metri_residui, l.codice AS ubicazione
            FROM wms.material_rolls r LEFT JOIN wms.warehouse_locations l ON l.id=r.ubicazione_id
            WHERE r.stato='DA_VERIFICARE'""").fetchall(),
        "metrature_mai_misurate": q("""SELECT r.barcode, r.metri_residui, r.origine_dato_metratura FROM wms.material_rolls r
            WHERE r.stato='DISPONIBILE' AND r.ultima_verifica IS NULL AND r.metri_residui < r.metri_iniziali""").fetchall(),
        "ubicazioni_incoerenti": q("""SELECT r.barcode, l.codice AS ubicazione, r.stato FROM wms.material_rolls r
            JOIN wms.warehouse_locations l ON l.id=r.ubicazione_id
            WHERE (l.tipo='MACCHINA' AND r.stato='DISPONIBILE'
                   AND r.ultima_verifica < now() - interval '1 day')
               OR (r.stato IN ('ESAURITA','TAGLIATA','ANNULLATA'))""").fetchall(),
        "consumo_diverso_dal_teorico": q("""SELECT j.external_madiwor_id AS commessa, jm.material_label_source AS materiale,
                jm.metri_teorici, jm.metri_consumati + jm.metri_scarto AS reale,
                round(100*(jm.metri_consumati + jm.metri_scarto - jm.metri_teorici)/nullif(jm.metri_teorici,0),1) AS scostamento_pct
            FROM wms.production_job_materials jm JOIN wms.production_jobs j ON j.id=jm.job_id
            WHERE jm.attiva AND jm.metri_consumati > 0
              AND abs(jm.metri_consumati + jm.metri_scarto - jm.metri_teorici) > 0.15*jm.metri_teorici""").fetchall(),
        "colli_mai_usciti_commessa_spedita": q("""SELECT p.barcode, j.external_madiwor_id AS commessa, p.quantita
            FROM wms.finished_goods_packages p JOIN wms.production_lots l ON l.id=p.lotto_id
            JOIN wms.production_jobs j ON j.id=l.production_job_id
            WHERE p.stato='DISPONIBILE' AND EXISTS (SELECT 1 FROM wms.shipment_lines sl JOIN wms.shipments s ON s.id=sl.shipment_id
                  WHERE sl.production_job_id=j.id AND s.stato='USCITA')""").fetchall(),
        "sotto_soglia": q("""SELECT codice_interno, descrizione, metri_disponibili, soglia_riordino FROM (
                SELECT m.codice_interno, m.descrizione, m.soglia_riordino,
                       sum(v.metri_disponibili) AS metri_disponibili
                FROM wms.materials m JOIN wms.v_giacenze_materiali v ON v.material_id=m.id
                WHERE m.soglia_riordino IS NOT NULL GROUP BY m.id) x
            WHERE metri_disponibili < soglia_riordino""").fetchall(),
    }
