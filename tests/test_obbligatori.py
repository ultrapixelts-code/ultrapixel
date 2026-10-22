"""Test obbligatori della specifica (sezione 16). Dopo ogni test la fixture `conn` verifica che
registro movimenti e giacenze coincidano (nessuno stock negativo, nessuna quantità duplicata)."""
import datetime as dt
import threading
import uuid
from decimal import Decimal

import pytest

from conftest import DSN, ev, make_actor, receive, run
from wms import ai, barcodes, db as wdb, engine, madiwor, scan, seed
from wms.errors import AIUnavailable, BusinessRuleError, Forbidden, IdempotencyConflict, IntegrationAuthError


def scan_(conn, actor, code, sid=None, **kw):
    return scan.handle_scan(conn, actor, code, sid or uuid.uuid4(), **kw)


def roll(conn, rid):
    return conn.execute("SELECT * FROM wms.material_rolls WHERE id=%s", (rid,)).fetchone()


def job4515(conn, auto_reserve=True, **changes):
    j = seed.load_job_fixture()
    for k, v in changes.items():
        setattr(j, k, v)
    return madiwor.import_job(conn, j, "FIXTURE", auto_reserve=auto_reserve)


def expect(code, fn, *a, **kw):
    with pytest.raises((BusinessRuleError, Forbidden)) as e:
        fn(*a, **kw)
    assert e.value.code == code, e.value.message
    return e.value


# 1 -------------------------------------------------------------------------------
def test_doppia_scansione_accidentale(conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    job = job4515(conn)
    scan_(conn, actors["prod"], "4515")
    first = scan_(conn, actors["prod"], b["barcode"])
    second = scan_(conn, actors["prod"], b["barcode"])          # rimbalzo della pistola
    assert first["esito"] == "OK" and second["esito"] == "DOPPIA"
    assert conn.execute("SELECT count(*) n FROM wms.roll_assignments").fetchone()["n"] == 1
    # stesso scan_id rispedito (retry di rete) → stessa risposta, nessuna esecuzione
    sid = uuid.uuid4()
    a = scan_(conn, actors["mag"], "UPLA0101", sid=sid)
    b2 = scan_(conn, actors["mag"], "UPLA0101", sid=sid)
    assert b2.get("ripetuta") is True and a["titolo"] == b2["titolo"]


def test_scansione_ripetuta_intenzionale_dopo_finestra(conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    job4515(conn)
    t0 = dt.datetime.now(dt.timezone.utc)
    scan_(conn, actors["prod"], "4515", client_ts=t0)
    assert scan_(conn, actors["prod"], b["barcode"], client_ts=t0 + dt.timedelta(seconds=1))["esito"] == "OK"
    # dopo la finestra, rileggere la bobina montata = fine lavoro: si chiude senza domande e si indica il posto
    r = scan_(conn, actors["prod"], b["barcode"], client_ts=t0 + dt.timedelta(seconds=30))
    assert r["esito"] == "OK" and r["comando"]["tipo"] == "CHIUDI_BOBINA" and r["titolo"].startswith("Metti in")


# 2 -------------------------------------------------------------------------------
def test_due_operatori_stessa_bobina(conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    j1 = job4515(conn, auto_reserve=False)["job_id"]
    j2 = madiwor.import_job(conn, madiwor.MadiworJob("4516", "Altro cliente", materiali=[
        madiwor.MaterialeRichiesto("EPIQUE FSC S2047N - BG45WH IMP FSC", Decimal("170"), Decimal("30"))],
        fasi=[{"fase": "STAMPA"}]), "FIXTURE", auto_reserve=False)["job_id"]
    barrier = threading.Barrier(2)
    results = {}

    def worker(name, job_id, device, user):
        c = wdb.connect(DSN)
        actor = make_actor(c, ids, user, device)
        barrier.wait()
        try:
            results[name] = engine.execute(c, actor, ev(), "ASSEGNA_BOBINA", {"job_id": str(job_id), "roll_id": str(b["id"])})
        except BusinessRuleError as e:
            results[name] = e
        finally:
            c.close()

    t1 = threading.Thread(target=worker, args=("a", j1, "Postazione Xeikon", "op.produzione"))
    t2 = threading.Thread(target=worker, args=("b", j2, "Postazione Xeikon (2)", "op.produzione2"))
    t1.start(); t2.start(); t1.join(); t2.join()
    ok = [r for r in results.values() if isinstance(r, dict)]
    ko = [r for r in results.values() if isinstance(r, BusinessRuleError)]
    assert len(ok) == 1 and len(ko) == 1
    assert ko[0].code in ("BOBINA_GIA_IN_USO", "RISERVATA_ALTRA_COMMESSA", "VINCOLO_DB")
    assert conn.execute("SELECT count(*) n FROM wms.roll_assignments WHERE stato='IN_CORSO'").fetchone()["n"] == 1


# 3 -------------------------------------------------------------------------------
def test_scansione_senza_rete(conn, ids, actors):
    """Coda offline: le scansioni arrivano in blocco, ripetute (retry) e con ora del dispositivo."""
    b = receive(conn, actors, ids, 100)[0]
    job4515(conn)
    t0 = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)
    queue = [(uuid.uuid4(), "4515", t0), (uuid.uuid4(), b["barcode"], t0 + dt.timedelta(seconds=5))]
    first = [scan_(conn, actors["prod"], c, sid=s, client_ts=t, offline=True) for s, c, t in queue]
    replay = [scan_(conn, actors["prod"], c, sid=s, client_ts=t, offline=True) for s, c, t in queue]
    assert [r["esito"] for r in first] == ["INFO", "OK"]
    assert all(r.get("ripetuta") for r in replay)
    assert conn.execute("SELECT count(*) n FROM wms.roll_assignments").fetchone()["n"] == 1
    assert conn.execute("SELECT bool_and(offline) o FROM wms.scan_events").fetchone()["o"] is True
    # una scansione offline diventata impossibile nel frattempo viene rifiutata, non forzata
    c2 = receive(conn, actors, ids, 10)[0]
    run(conn, actors["resp"], "RETTIFICA", {"roll_id": str(c2["id"]), "metri_nuovi": 0, "causale": "bobina finita"})
    late = scan_(conn, actors["prod2"], "4515", client_ts=t0)
    late = scan_(conn, actors["prod2"], c2["barcode"], client_ts=t0 + dt.timedelta(seconds=9), offline=True)
    assert late["esito"] == "ERRORE" and "esaurita" in late["titolo"].lower()


# 4 -------------------------------------------------------------------------------
def test_qr_malformato_e_dominio_non_ammesso(conn, ids, actors):
    for code in ["https://evil.example.com/job/4515", "http://", "https://ultrapixel.madiwor.net/x?y=4515",
                 "UPR12", "UPRABCDEF", "\x00\x01", ""]:
        r = scan_(conn, actors["prod"], code)
        assert r["esito"] in ("ERRORE", "SCONOSCIUTO"), (code, r)
    # nessun dominio Madiwor viene seguito: anche un QR del dominio giusto ma con percorso non configurato è rifiutato
    rec = barcodes.recognize(conn, "https://ultrapixel.madiwor.net/F/AxqusvPz")
    assert rec.stato == "NON_VALIDO" and "non ancora configurato" in rec.motivo
    # quando il formato reale sarà noto basta configurarlo
    conn.execute("""UPDATE wms.settings SET value='["^/kiosk/job/(?P<commessa>\\\\d+)$"]' WHERE key='qr_percorsi_commessa'""")
    job4515(conn, auto_reserve=False)
    assert barcodes.recognize(conn, "https://ultrapixel.madiwor.net/kiosk/job/4515").unico.tipo == "JOB"


def test_codici_numerici_non_riconosciuti_per_lunghezza(conn, ids, actors):
    job4515(conn, auto_reserve=False)
    # un codice fornitore numerico lungo come una commessa resta "sconosciuto", non diventa una commessa
    assert barcodes.recognize(conn, "4516").stato == "SCONOSCIUTO"
    # stesso codice usato da due entità → ambiguo, si chiede di scegliere
    run(conn, actors["resp"], "ASSOCIA_CODICE", {"code": "4515", "namespace": "FORNITORE",
                                                 "material_id": str(ids["mat"]["MATT-WINE-FSC"])})
    r = scan_(conn, actors["prod"], "4515")
    assert r["esito"] == "SCEGLI" and r["scelte"][0]["tipo"] == "JOB"     # in macchina la commessa è proposta per prima
    assert conn.execute("SELECT count(*) n FROM wms.inventory_movements").fetchone()["n"] == 0   # nessuna azione eseguita


# 5 -------------------------------------------------------------------------------
def test_materiale_incompatibile_e_equivalenza_approvata(conn, ids, actors):
    sb = receive(conn, actors, ids, 200, mat="SKIN-BLANC-PLUS-FSC")[0]
    jid = job4515(conn)["job_id"]
    expect("MATERIALE_NON_COMPATIBILE", run, conn, actors["prod"], "ASSEGNA_BOBINA", {"job_id": str(jid), "roll_id": str(sb["id"])})
    # nomi simili non bastano: serve un'equivalenza validata da una persona
    conn.execute("""INSERT INTO wms.material_equivalences(material_id, compatible_material_id, compatibility_type, validated_by)
                    VALUES (%s,%s,'SOSTITUTO_APPROVATO',%s)""",
                 (ids["mat"]["EPIQUE-FSC-S2047N"], ids["mat"]["SKIN-BLANC-PLUS-FSC"], ids["users"]["resp.magazzino"]))
    r = run(conn, actors["prod"], "ASSEGNA_BOBINA", {"job_id": str(jid), "roll_id": str(sb["id"])})
    assert r["compatibilita"] == "SOSTITUTO_APPROVATO" and "equivalente approvato" in r["messaggio"]


def test_larghezza_non_compatibile_e_alternativa_con_taglio(conn, ids, actors):
    larga = receive(conn, actors, ids, 500, larghezza=330)[0]
    r = job4515(conn)
    assert r["prenotazione"]["prenotazioni"] == []
    manc = r["prenotazione"]["mancanze"][0]
    assert Decimal(str(manc["mancano_metri"])) == Decimal("54")
    assert manc["alternative_con_taglio"][0]["bobina"] == larga["barcode"]     # proposta, non scelta
    expect("LARGHEZZA_NON_COMPATIBILE", run, conn, actors["prod"], "ASSEGNA_BOBINA",
           {"job_id": str(r["job_id"]), "roll_id": str(larga["id"])})


# 6 -------------------------------------------------------------------------------
def test_bobina_con_metratura_insufficiente(conn, ids, actors):
    corta = receive(conn, actors, ids, 30)[0]
    jid = job4515(conn, auto_reserve=False)["job_id"]
    jm = conn.execute("SELECT id FROM wms.production_job_materials WHERE job_id=%s", (jid,)).fetchone()["id"]
    expect("BOBINA_INSUFFICIENTE", run, conn, actors["prod"], "PRENOTA", {"job_material_id": str(jm), "roll_id": str(corta["id"]), "metri": 54})
    # montarla è possibile ma con avviso: servirà un'altra bobina
    r = run(conn, actors["prod"], "ASSEGNA_BOBINA", {"job_id": str(jid), "roll_id": str(corta["id"])})
    assert any("mancano 24.00 m" in a for a in r["avvisi"])
    run(conn, actors["prod"], "CHIUDI_BOBINA", {"roll_id": str(corta["id"]), "metri_residui": 0})
    assert roll(conn, corta["id"])["stato"] == "ESAURITA"


def test_bobina_gia_esaurita(conn, ids, actors):
    b = receive(conn, actors, ids, 54)[0]
    jid = job4515(conn)["job_id"]
    run(conn, actors["prod"], "ASSEGNA_BOBINA", {"job_id": str(jid), "roll_id": str(b["id"])})
    run(conn, actors["prod"], "CHIUDI_BOBINA", {"roll_id": str(b["id"]), "metri_residui": 0})
    expect("BOBINA_ESAURITA", run, conn, actors["prod"], "ASSEGNA_BOBINA", {"job_id": str(jid), "roll_id": str(b["id"])})
    expect("STATO_NON_VALIDO", run, conn, actors["mag"], "SPOSTA_BOBINA", {"roll_id": str(b["id"]), "destinazione_id": str(ids["loc"]["A-01-01"])})


# 7 -------------------------------------------------------------------------------
def test_commessa_annullata(conn, ids, actors):
    b1, b2 = receive(conn, actors, ids, 40, n=2)
    r = job4515(conn)
    assert Decimal(str(sum(Decimal(str(p["metri"])) for p in r["prenotazione"]["prenotazioni"]))) == Decimal("54")
    run(conn, actors["prod"], "ASSEGNA_BOBINA", {"job_id": str(r["job_id"]), "roll_id": str(b1["id"])})
    run(conn, actors["prod"], "CHIUDI_BOBINA", {"roll_id": str(b1["id"]), "metri_residui": 0})   # 40 m consumati davvero
    canc = job4515(conn, stato="ANNULLATA")
    assert canc["esito"] == "ANNULLATO"
    assert conn.execute("SELECT count(*) n FROM wms.material_reservations WHERE status='ATTIVA'").fetchone()["n"] == 0
    assert roll(conn, b2["id"])["metri_riservati"] == 0
    # lo storico fisico resta: il consumo di 40 m non viene annullato
    assert conn.execute("SELECT -sum(quantita) s FROM wms.inventory_movements WHERE tipo_movimento='CONSUMO'").fetchone()["s"] == Decimal("40.00")
    assert scan_(conn, actors["prod"], "4515")["esito"] == "ERRORE"
    expect("COMMESSA_ANNULLATA", run, conn, actors["prod"], "ASSEGNA_BOBINA", {"job_id": str(r["job_id"]), "roll_id": str(b2["id"])})


# 8 -------------------------------------------------------------------------------
def test_modifica_quantita_ordinata(conn, ids, actors):
    receive(conn, actors, ids, 200)
    r = job4515(conn)
    jm = lambda: conn.execute("SELECT * FROM wms.production_job_materials WHERE job_id=%s AND attiva", (r["job_id"],)).fetchone()  # noqa: E731
    assert jm()["metri_prenotati"] == Decimal("54")
    j = seed.load_job_fixture(); j.quantita = 400; j.materiali[0].metri = Decimal("34")
    up = madiwor.import_job(conn, j, "FIXTURE")
    assert up["esito"] == "AGGIORNATO" and Decimal(str(up["rilasciati_metri"])) == Decimal("20")
    assert jm()["metri_teorici"] == Decimal("34") and jm()["metri_prenotati"] == Decimal("34")
    j.quantita = 1000; j.materiali[0].metri = Decimal("83")
    up = madiwor.import_job(conn, j, "FIXTURE")
    assert jm()["metri_prenotati"] == Decimal("83")                     # ricalcolo solo di ciò che non è consumato
    assert conn.execute("SELECT source_version v FROM wms.production_jobs").fetchone()["v"] == 3


# 9 -------------------------------------------------------------------------------
def test_cambio_specifiche_materiale(conn, ids, actors):
    receive(conn, actors, ids, 200)
    receive(conn, actors, ids, 200, mat="MATT-WINE-FSC")
    r = job4515(conn)
    j = seed.load_job_fixture()
    j.materiali = [madiwor.MaterialeRichiesto("MATT WINE FSC S2047N - BG45WH", Decimal("170"), Decimal("54"))]
    up = madiwor.import_job(conn, j, "FIXTURE")
    assert Decimal(str(up["rilasciati_metri"])) == Decimal("54")
    rows = conn.execute("SELECT material_label_source, attiva, metri_prenotati FROM wms.production_job_materials "
                        "WHERE job_id=%s ORDER BY attiva", (r["job_id"],)).fetchall()
    assert [(x["attiva"], x["metri_prenotati"]) for x in rows] == [(False, 0), (True, Decimal("54"))]
    # materiale sconosciuto: nessuna sostituzione "per somiglianza", errore di integrazione visibile
    j.materiali = [madiwor.MaterialeRichiesto("EPIQUE FSC S2047N BG45WH", Decimal("170"), Decimal("54"))]
    up = madiwor.import_job(conn, j, "FIXTURE")
    assert up["materiali_non_risolti"] == ["EPIQUE FSC S2047N BG45WH"]
    assert conn.execute("SELECT count(*) n FROM wms.integration_errors WHERE errore LIKE 'Materiale non associato%'").fetchone()["n"] == 1


# 10 ------------------------------------------------------------------------------
def test_ordine_ripetuto_stesso_articolo(conn, ids, actors):
    receive(conn, actors, ids, 75, n=2)
    a = job4515(conn)
    j = seed.load_job_fixture(); j.external_id = "4600"; j.sales_order_id = "1500"
    b = madiwor.import_job(conn, j, "FIXTURE")
    assert a["job_id"] != b["job_id"]
    assert conn.execute("SELECT count(*) n FROM wms.finished_products").fetchone()["n"] == 0  # creato solo a produzione
    used = {p["bobina"] for p in a["prenotazione"]["prenotazioni"]} | {p["bobina"] for p in b["prenotazione"]["prenotazioni"]}
    assert len(used) == 2       # due commesse, due bobine distinte: niente doppia prenotazione degli stessi metri


def _to_control(conn, actors, jid, q=650):
    for f in ("STAMPA", "VERNICIATURA", "RILIEVO", "FUSTELLATURA"):
        run(conn, actors["prod"], "COMPLETA_FASE", {"job_id": str(jid), "fase": f})
    return run(conn, actors["prod"], "REGISTRA_PRODUZIONE", {"job_id": str(jid), "quantita": q})


# 11-13 ---------------------------------------------------------------------------
def test_rilavorazione_scarto_e_produzione_parziale(conn, ids, actors):
    jid = job4515(conn, auto_reserve=False)["job_id"]
    expect("FASE_PRECEDENTE_APERTA", run, conn, actors["prod"], "COMPLETA_FASE", {"job_id": str(jid), "fase": "RILIEVO"})
    lot1 = _to_control(conn, actors, jid, 400)                         # produzione parziale: primo lotto
    run(conn, actors["prod"], "CONTROLLO_QUALITA", {"lot_id": lot1["lot_id"], "conformi": 0, "scarti": 400})   # scarto totale
    expect("LOTTO_NON_APPROVATO", run, conn, actors["prod"], "CONFEZIONA", {"lot_id": lot1["lot_id"], "quantita": 1})
    run(conn, actors["prod"], "RILAVORA_FASE", {"job_id": str(jid), "fase": "RILIEVO", "causale": "rilievo fuori registro"})
    expect("LAVORAZIONI_APERTE", run, conn, actors["prod"], "REGISTRA_PRODUZIONE", {"job_id": str(jid), "quantita": 10})
    run(conn, actors["prod"], "COMPLETA_FASE", {"job_id": str(jid), "fase": "RILIEVO"})
    run(conn, actors["prod"], "COMPLETA_FASE", {"job_id": str(jid), "fase": "FUSTELLATURA"})
    lot2 = run(conn, actors["prod"], "REGISTRA_PRODUZIONE", {"job_id": str(jid), "quantita": 700})
    expect("QUANTITA_INCOERENTE", run, conn, actors["prod"], "CONTROLLO_QUALITA", {"lot_id": lot2["lot_id"], "conformi": 700, "scarti": 5})
    run(conn, actors["prod"], "CONTROLLO_QUALITA", {"lot_id": lot2["lot_id"], "conformi": 650, "scarti": 50})
    lots = conn.execute("SELECT codice, stato_qualita, quantita_conforme FROM wms.production_lots ORDER BY codice").fetchall()
    assert [(l["codice"], l["stato_qualita"], l["quantita_conforme"]) for l in lots] == [
        ("L4515-1", "RESPINTO", 0), ("L4515-2", "APPROVATO", 650)]


# 14 ------------------------------------------------------------------------------
def test_confezione_parziale(conn, ids, actors):
    jid = job4515(conn, auto_reserve=False)["job_id"]
    lot = _to_control(conn, actors, jid, 650)
    run(conn, actors["prod"], "CONTROLLO_QUALITA", {"lot_id": lot["lot_id"], "conformi": 650, "scarti": 0})
    run(conn, actors["prod"], "CONFEZIONA", {"lot_id": lot["lot_id"], "quantita": 500})
    fase = conn.execute("SELECT stato FROM wms.job_phases WHERE fase='IMBALLAGGIO'").fetchone()["stato"]
    assert fase == "DA_FARE"
    expect("QUANTITA_NON_VALIDA", run, conn, actors["prod"], "CONFEZIONA", {"lot_id": lot["lot_id"], "quantita": 151})
    run(conn, actors["prod"], "CONFEZIONA", {"lot_id": lot["lot_id"], "quantita": 150})
    assert conn.execute("SELECT stato FROM wms.job_phases WHERE fase='IMBALLAGGIO'").fetchone()["stato"] == "COMPLETATA"


def _packed(conn, actors, ids, qty=(325, 325)):
    jid = job4515(conn, auto_reserve=False)["job_id"]
    lot = _to_control(conn, actors, jid, sum(qty))
    run(conn, actors["prod"], "CONTROLLO_QUALITA", {"lot_id": lot["lot_id"], "conformi": sum(qty), "scarti": 0})
    pk = [run(conn, actors["prod"], "CONFEZIONA", {"lot_id": lot["lot_id"], "quantita": q}) for q in qty]
    sh = run(conn, actors["resp"], "CREA_SPEDIZIONE", {"external_madiwor_ref": "D1", "cliente_nome": "Cacovich",
                                                        "righe": [{"articolo": "117951", "quantita": sum(qty)}]})
    return jid, pk, sh


# 15 ------------------------------------------------------------------------------
def test_collo_spedito_due_volte(conn, ids, actors):
    jid, pk, sh = _packed(conn, actors, ids)
    for p in pk:
        run(conn, actors["sped"], "PRELEVA_COLLO", {"shipment_id": str(sh["shipment_id"]), "package_id": str(p["package_id"])})
    run(conn, actors["sped"], "CONFERMA_USCITA", {"shipment_id": str(sh["shipment_id"])})
    expect("SPEDIZIONE_GIA_USCITA", run, conn, actors["sped"], "CONFERMA_USCITA", {"shipment_id": str(sh["shipment_id"])})
    sh2 = run(conn, actors["resp"], "CREA_SPEDIZIONE", {"external_madiwor_ref": "D2", "cliente_nome": "Cacovich",
                                                         "righe": [{"articolo": "117951", "quantita": 325}]})
    expect("COLLO_GIA_SPEDITO", run, conn, actors["sped"], "PRELEVA_COLLO",
           {"shipment_id": str(sh2["shipment_id"]), "package_id": str(pk[0]["package_id"])})
    assert conn.execute("SELECT sum(quantita) s FROM wms.inventory_movements WHERE tipo_movimento='USCITA'").fetchone()["s"] == -650


def test_picking_collo_sbagliato_o_eccedente(conn, ids, actors):
    jid, pk, sh = _packed(conn, actors, ids, qty=(400, 250))
    sh_small = run(conn, actors["resp"], "CREA_SPEDIZIONE", {"external_madiwor_ref": "D9", "cliente_nome": "x",
                                                              "righe": [{"articolo": "117951", "quantita": 300}]})
    expect("QUANTITA_ECCEDENTE", run, conn, actors["sped"], "PRELEVA_COLLO",
           {"shipment_id": str(sh_small["shipment_id"]), "package_id": str(pk[0]["package_id"])})
    j = seed.load_job_fixture(); j.external_id = "4700"; j.articolo = "999999"
    madiwor.import_job(conn, j, "FIXTURE", auto_reserve=False)
    other_lot = _to_control(conn, actors, conn.execute("SELECT id FROM wms.production_jobs WHERE external_madiwor_id='4700'").fetchone()["id"], 10)
    run(conn, actors["prod"], "CONTROLLO_QUALITA", {"lot_id": other_lot["lot_id"], "conformi": 10, "scarti": 0})
    wrong = run(conn, actors["prod"], "CONFEZIONA", {"lot_id": other_lot["lot_id"], "quantita": 10})
    expect("COLLO_NON_COMPATIBILE", run, conn, actors["sped"], "PRELEVA_COLLO",
           {"shipment_id": str(sh["shipment_id"]), "package_id": str(wrong["package_id"])})


# 16 ------------------------------------------------------------------------------
def test_reso(conn, ids, actors):
    jid, pk, sh = _packed(conn, actors, ids)
    for p in pk:
        run(conn, actors["sped"], "PRELEVA_COLLO", {"shipment_id": str(sh["shipment_id"]), "package_id": str(p["package_id"])})
    run(conn, actors["sped"], "CONFERMA_USCITA", {"shipment_id": str(sh["shipment_id"])})
    expect("RUOLO_NON_AUTORIZZATO", run, conn, actors["sped"], "RESO", {"package_id": str(pk[0]["package_id"]), "causale": "x"})
    run(conn, actors["resp"], "RESO", {"package_id": str(pk[0]["package_id"]), "causale": "etichette rovinate"})
    p = conn.execute("SELECT p.stato, l.codice FROM wms.finished_goods_packages p JOIN wms.warehouse_locations l "
                     "ON l.id=p.ubicazione_id WHERE p.id=%s", (pk[0]["package_id"],)).fetchone()
    assert (p["stato"], p["codice"]) == ("RESO", "QUARANTENA")


# 17 ------------------------------------------------------------------------------
def test_bobina_tagliata_in_figlie(conn, ids, actors):
    madre = receive(conn, actors, ids, 500, larghezza=340)[0]
    expect("TAGLIO_NON_VALIDO", run, conn, actors["prod"], "TAGLIA_BOBINA",
           {"roll_id": str(madre["id"]), "figlie": [{"larghezza_mm": 170, "metri": 500}, {"larghezza_mm": 171, "metri": 500}]})
    r = run(conn, actors["prod"], "TAGLIA_BOBINA",
            {"roll_id": str(madre["id"]), "figlie": [{"larghezza_mm": 170, "metri": 495}, {"larghezza_mm": 165, "metri": 495}]})
    figlie = conn.execute("SELECT * FROM wms.material_rolls WHERE parent_roll_id=%s ORDER BY barcode", (madre["id"],)).fetchall()
    assert len(figlie) == 2 and all(f["lotto_fornitore"] == roll(conn, madre["id"])["lotto_fornitore"] for f in figlie)
    assert roll(conn, madre["id"])["stato"] == "TAGLIATA"
    assert Decimal(str(r["sfrido_mm_x_m"])) == Decimal(340 * 500 - 170 * 495 - 165 * 495)
    # la figlia da 170 mm ora serve la commessa 4515
    j = job4515(conn)
    assert j["prenotazione"]["prenotazioni"][0]["bobina"] == figlie[0]["barcode"]


# 18 ------------------------------------------------------------------------------
def test_importazione_ripetuta_e_retry_comando(conn, ids, actors):
    j = seed.load_job_fixture()
    results = [madiwor.import_job(conn, j, "FIXTURE") for _ in range(3)]
    assert [r["esito"] for r in results] == ["CREATO", "INVARIATO", "INVARIATO"]
    # ritorno a un contenuto già visto: viene applicato davvero (non scambiato per duplicato)
    j2 = seed.load_job_fixture(); j2.quantita = 700; j2.materiali[0].metri = Decimal("58")
    madiwor.import_job(conn, j2, "FIXTURE")
    back = madiwor.import_job(conn, j, "FIXTURE")
    assert back["esito"] == "AGGIORNATO"
    assert conn.execute("SELECT metri_teorici FROM wms.production_job_materials").fetchone()["metri_teorici"] == Decimal("54")
    # stesso event_id: risultato registrato, nessun secondo ricevimento
    e = ev()
    payload = {"material_id": str(ids["mat"]["EPIQUE-FSC-S2047N"]), "larghezza_mm": 170, "metri": 100}
    a = engine.execute(conn, actors["ric"], e, "RICEVI_BOBINA", payload)
    b = engine.execute(conn, actors["ric"], e, "RICEVI_BOBINA", payload)
    assert b["duplicato"] is True and a["bobine"] == b["bobine"]
    assert conn.execute("SELECT count(*) n FROM wms.material_rolls").fetchone()["n"] == 1
    with pytest.raises(IdempotencyConflict):
        engine.execute(conn, actors["ric"], e, "RICEVI_BOBINA", {**payload, "metri": 200})


# 19 ------------------------------------------------------------------------------
def test_ai_non_disponibile(conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    job4515(conn)
    assistant = ai.WarehouseAssistant(conn)            # nessun provider configurato
    with pytest.raises(AIUnavailable):
        assistant.ask("quante bobine di epique ho?")
    scan_(conn, actors["prod"], "4515")
    assert scan_(conn, actors["prod"], b["barcode"])["esito"] == "OK"   # lo scanner funziona lo stesso


def test_ai_non_puo_scrivere(conn, ids, actors):
    receive(conn, actors, ids, 100)
    tools = ai.ReadOnlyTools(conn)
    assert tools.giacenze("EPIQUE")[0]["metri_fisici"] == Decimal("100.00")
    import psycopg
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        tools.sql_libero("UPDATE wms.material_rolls SET metri_residui=999 RETURNING id")
    with pytest.raises(BusinessRuleError):
        ai.record_recommendation(conn, "test", "RIORDINO", {"x": 1}, "", {}, 0.5)
    rid = ai.record_recommendation(conn, "test", "RIORDINO", {"materiale": "EPIQUE", "metri": 500},
                                   "consumo medio superiore alla giacenza", {"giacenza": 100}, 0.6)
    assert rid and conn.execute("SELECT metri_residui FROM wms.material_rolls").fetchone()["metri_residui"] == Decimal("100.00")


# 20 ------------------------------------------------------------------------------
def test_credenziali_madiwor_non_valide(conn, ids, actors):
    def fetcher():
        raise IntegrationAuthError("401 dal server di esportazione")
    src = madiwor.StructuredExportSource(rows=[], column_map={"external_id": "a", "cliente_nome": "b", "materiale": "c",
                                                               "metri": "d"}, fetcher=fetcher)
    rep = madiwor.sync_once(conn, src)
    assert rep == {"esito": "ERRORE_CREDENZIALI", "importate": 0}
    assert conn.execute("SELECT count(*) n FROM wms.production_jobs").fetchone()["n"] == 0
    assert conn.execute("SELECT count(*) n FROM wms.integration_errors").fetchone()["n"] == 1
    # una mappa colonne incompleta non indovina i nomi: si ferma
    with pytest.raises(BusinessRuleError):
        madiwor.StructuredExportSource(rows=[], column_map={"external_id": "a"}).fetch()


def test_pdf_ambiguo_va_in_quarantena(conn, ids, actors):
    testo = "Production #4515\nCUSTOMER\nAzienda Agricola Cacovich\nSPECIFICATIONS\n117951 Nariousna 80 mm 150 mm 650\n"
    ex = madiwor.PdfJobSheetSource(testo, "scheda_4515.pdf").extract()
    assert ex.da_quarantena and "materiale" in ex.mancanti and "metri" in ex.mancanti
    madiwor.quarantine(conn, "PDF", "scheda_4515.pdf", "campi mancanti: " + ", ".join(ex.mancanti), {"conf": ex.confidenza})
    testo2 = testo.replace("Production #4515", "Production #4515 rif #4516")
    ex2 = madiwor.PdfJobSheetSource(testo2, "x.pdf", {"materiale": r"Material:\s*(.+)", "metri": r"Meters:\s*([\d.,]+)"}).extract()
    assert ex2.da_quarantena and "external_id (incerto)" in ex2.mancanti


# --- extra: correzione dell'ultima operazione, rettifiche, permessi ----------------
def test_annullo_ultima_operazione_compensativo(conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    jid = job4515(conn)["job_id"]
    a = run(conn, actors["prod"], "ASSEGNA_BOBINA", {"job_id": str(jid), "roll_id": str(b["id"])})
    u = run(conn, actors["prod"], "ANNULLA_COMANDO", {"event_id": a["event_id"]})
    r = roll(conn, b["id"])
    assert r["stato"] == "DISPONIBILE" and r["ubicazione_id"] == ids["loc"]["RICEVIMENTO"] and r["metri_riservati"] == 54
    assert "annullata" in u["messaggio"].lower()
    expect("GIA_ANNULLATA", run, conn, actors["prod"], "ANNULLA_COMANDO", {"event_id": a["event_id"]})
    # nessuna cancellazione: il registro conserva movimento e storno
    tipi = [m["tipo_movimento"] for m in conn.execute("SELECT tipo_movimento FROM wms.inventory_movements ORDER BY id")]
    assert "ASSEGNAZIONE" in tipi and "STORNO" in tipi
    with pytest.raises(Exception):
        conn.execute("DELETE FROM wms.inventory_movements")
    # un altro operatore non può annullare un'operazione non sua
    m = run(conn, actors["mag"], "SPOSTA_BOBINA", {"roll_id": str(b["id"]), "destinazione_id": str(ids["loc"]["A-01-01"])})
    expect("RICHIEDE_AUTORIZZAZIONE", run, conn, actors["prod2"], "ANNULLA_COMANDO", {"event_id": m["event_id"]})
    run(conn, actors["resp"], "ANNULLA_COMANDO", {"event_id": m["event_id"]})
    assert roll(conn, b["id"])["ubicazione_id"] == ids["loc"]["RICEVIMENTO"]


def test_rettifica_soglia_e_negativi(conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    expect("CAUSALE_MANCANTE", run, conn, actors["mag"], "RETTIFICA", {"roll_id": str(b["id"]), "metri_nuovi": 90, "causale": ""})
    run(conn, actors["mag"], "RETTIFICA", {"roll_id": str(b["id"]), "metri_nuovi": 90, "causale": "misura"})
    expect("RICHIEDE_AUTORIZZAZIONE", run, conn, actors["mag"], "RETTIFICA", {"roll_id": str(b["id"]), "metri_nuovi": 10, "causale": "x"})
    expect("GIACENZA_NEGATIVA", run, conn, actors["resp"], "RETTIFICA", {"roll_id": str(b["id"]), "metri_nuovi": -1, "causale": "x"})
    run(conn, actors["resp"], "RETTIFICA", {"roll_id": str(b["id"]), "metri_nuovi": 10, "causale": "conteggio inventario"})
    assert roll(conn, b["id"])["metri_residui"] == Decimal("10.00")


def test_ruoli_lato_server(conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    jid = job4515(conn)["job_id"]
    expect("RUOLO_NON_AUTORIZZATO", run, conn, actors["sped"], "ASSEGNA_BOBINA", {"job_id": str(jid), "roll_id": str(b["id"])})
    expect("RUOLO_NON_AUTORIZZATO", run, conn, actors["prod"], "BLOCCA_BOBINA", {"roll_id": str(b["id"]), "causale": "x"})


def test_ricevimento_una_scansione(conn, ids, actors):
    """Arrivo: una lettura e basta. Il sistema registra, sceglie il posto, stampa l'etichetta."""
    gtin = "08012345678907"   # cifra di controllo calcolata (verificata su EAN reale 4006381333931)
    assert barcodes._gtin_ok(gtin)
    run(conn, actors["resp"], "ASSOCIA_CODICE", {"code": gtin, "namespace": "GTIN", "material_id": str(ids["mat"]["EPIQUE-FSC-S2047N"])})
    conn.execute("UPDATE wms.materials SET larghezza_mm=170 WHERE id=%s", (ids["mat"]["EPIQUE-FSC-S2047N"],))
    code = "01" + gtin + "3111006000" + "10LOT77"          # AI 311, 1 decimale, 006000 → 600,0 m; lotto LOT77
    s = scan_(conn, actors["ric"], code)
    assert s["esito"] == "OK" and s["titolo"] == "Metti in A-01-01", s      # 600 m = pesante → ripiano 1
    assert s["stampa"] and s["bobina"]["metri_fisici"] == 600.0
    r = roll(conn, s["bobina"]["id"])
    assert r["lotto_fornitore"] == "LOT77" and r["ubicazione_confermata"] is False
    # un codice che identifica solo l'articolo, senza metratura nominale configurata: si chiede solo quella
    run(conn, actors["resp"], "ASSOCIA_CODICE", {"code": "AA335", "material_id": str(ids["mat"]["EPIQUE-FSC-S2047N"])})
    s2 = scan_(conn, actors["ric"], "AA335")
    assert s2["esito"] == "CHIEDI" and [c["nome"] for c in s2["chiedi"]["campi"]] == ["metri"]
    # con la metratura nominale del fornitore in anagrafica basta la lettura
    conn.execute("UPDATE wms.materials SET metri_nominali=500 WHERE id=%s", (ids["mat"]["EPIQUE-FSC-S2047N"],))
    s3 = scan_(conn, actors["ric"], "AA335", client_ts=dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=5))
    assert s3["esito"] == "OK" and "nominale" in s3["messaggio"]


def test_stoccaggio_a_raffica(conn, ids, actors):
    bs = receive(conn, actors, ids, 100, n=3)
    assert scan_(conn, actors["mag"], "UPLB0201")["esito"] == "INFO"
    for b in bs:
        assert scan_(conn, actors["mag"], b["barcode"])["esito"] == "OK"
    scan_(conn, actors["mag"], "UPLB0201")       # rilettura: fine stoccaggio
    assert {roll(conn, b["id"])["ubicazione_id"] for b in bs} == {ids["loc"]["B-02-01"]}
