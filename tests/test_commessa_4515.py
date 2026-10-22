"""Caso reale della specifica (sez. 15): commessa 4515, con lo scanner come lo userebbe l'operatore."""
import uuid
from decimal import Decimal

from conftest import receive, run
from wms import madiwor, scan, seed


def scan_(conn, actor, code, **kw):
    return scan.handle_scan(conn, actor, code, uuid.uuid4(), **kw)


def test_commessa_4515_end_to_end(conn, ids, actors):
    prod, sped = actors["prod"], actors["sped"]
    # bobine a magazzino: una corta che non basta, una che basta, una del materiale sbagliato, una troppo larga
    corta = receive(conn, actors, ids, 40)[0]
    giusta = receive(conn, actors, ids, 75)[0]
    lunga = receive(conn, actors, ids, 300)[0]
    sbagliata = receive(conn, actors, ids, 200, mat="MATT-WINE-FSC")[0]
    larga = receive(conn, actors, ids, 500, larghezza=330)[0]

    # 1. import senza duplicare (anche ripetuto)
    job = seed.load_job_fixture()
    r1 = madiwor.import_job(conn, job, "FIXTURE")
    r2 = madiwor.import_job(conn, job, "FIXTURE")
    assert r1["esito"] == "CREATO" and r2["esito"] == "INVARIATO"
    assert conn.execute("SELECT count(*) n FROM wms.production_jobs WHERE external_madiwor_id='4515'").fetchone()["n"] == 1

    # 2-3. materiale identificato per testo esatto Madiwor, fabbisogno = metratura della commessa (54 m, 170 mm)
    jm = conn.execute("SELECT * FROM wms.production_job_materials WHERE job_id=%s", (r1["job_id"],)).fetchone()
    assert jm["material_id"] == ids["mat"]["EPIQUE-FSC-S2047N"]
    assert jm["metri_teorici"] == Decimal("54.00") and jm["larghezza_richiesta_mm"] == Decimal("170.00")

    # 4-5. bobine compatibili + prenotazione: scelta la bobina da 75 m (copre con l'avanzo minore), non la più vecchia
    pren = r1["prenotazione"]["prenotazioni"]
    assert [p["bobina"] for p in pren] == [giusta["barcode"]]
    alt = r1["prenotazione"]["mancanze"]
    assert alt == []
    assert jm["metri_prenotati"] == Decimal("54.00")

    # 6. scansione commessa 4515 in macchina
    s = scan_(conn, prod, "4515")
    assert s["esito"] == "INFO" and s["commessa"]["commessa"] == "4515"
    assert s["commessa"]["materiali"][0]["bobine"][0]["barcode"] == giusta["barcode"]

    # bobina sbagliata e bobina troppo larga vengono bloccate, nessun movimento
    bad = scan_(conn, prod, sbagliata["barcode"])
    assert bad["esito"] == "ERRORE" and "Materiale sbagliato" in bad["titolo"]
    wide = scan_(conn, prod, larga["barcode"])
    assert wide["esito"] == "ERRORE" and "Larghezza" in wide["titolo"]

    # 7-9. scansione della bobina selezionata: verifica + assegnazione
    ok = scan_(conn, prod, giusta["barcode"])
    assert ok["esito"] == "OK", ok
    roll = conn.execute("SELECT * FROM wms.material_rolls WHERE id=%s", (giusta["id"],)).fetchone()
    assert roll["stato"] == "IN_PRODUZIONE" and roll["metri_residui"] == Decimal("75.00")   # prenotare/montare ≠ consumare

    # 10. fine bobina senza misura → solo stima, nessun consumo fisico
    est = run(conn, prod, "CHIUDI_BOBINA", {"roll_id": str(giusta["id"])})
    assert est["verificato"] is False and Decimal(str(est["stima_consumo"])) == Decimal("54.00")
    roll = conn.execute("SELECT * FROM wms.material_rolls WHERE id=%s", (giusta["id"],)).fetchone()
    assert roll["stato"] == "DA_VERIFICARE" and roll["metri_residui"] == Decimal("75.00")
    assert roll["metri_stimati"] == Decimal("21.00")
    # 11. misura reale → consumo definitivo e residuo
    ver = run(conn, actors["mag"], "VERIFICA_METRATURA", {"roll_id": str(giusta["id"]), "metri_misurati": 18,
                                                         "metri_scarto": 5})
    assert Decimal(str(ver["utilizzati"])) == Decimal("52.00") and Decimal(str(ver["scarto"])) == Decimal("5.00")
    jm = conn.execute("SELECT * FROM wms.production_job_materials WHERE id=%s", (jm["id"],)).fetchone()
    assert jm["metri_consumati"] == Decimal("52.00") and jm["metri_consumo_stimato"] == 0 and jm["metri_prenotati"] == 0

    # 12. fasi successive in ordine; produzione registrabile solo a lavorazioni chiuse
    jid = str(r1["job_id"])
    err = None
    try:
        run(conn, prod, "REGISTRA_PRODUZIONE", {"job_id": jid, "quantita": 650})
    except Exception as e:  # noqa: BLE001
        err = e
    assert err is not None and "LAVORAZIONI_APERTE" in str(getattr(err, "code", ""))
    for fase in ("STAMPA", "VERNICIATURA", "RILIEVO", "FUSTELLATURA"):
        run(conn, prod, "COMPLETA_FASE", {"job_id": jid, "fase": fase})

    # 13. 650 conformi solo dopo produzione + controllo
    lot = run(conn, prod, "REGISTRA_PRODUZIONE", {"job_id": jid, "quantita": 662})
    try:
        run(conn, prod, "CONFEZIONA", {"lot_id": lot["lot_id"], "quantita": 325})
        raise AssertionError("confezionare prima del controllo deve essere vietato")
    except Exception as e:  # noqa: BLE001
        assert getattr(e, "code", "") == "LOTTO_NON_APPROVATO"
    run(conn, prod, "CONTROLLO_QUALITA", {"lot_id": lot["lot_id"], "conformi": 650, "scarti": 12})
    l = conn.execute("SELECT * FROM wms.production_lots WHERE id=%s", (lot["lot_id"],)).fetchone()
    assert (l["quantita_conforme"], l["quantita_scartata"], l["stato_qualita"]) == (650, 12, "APPROVATO")

    # 14. colli identificabili (non si presume la quantità standard per rotolo)
    c1 = run(conn, prod, "CONFEZIONA", {"lot_id": lot["lot_id"], "quantita": 325})
    c2 = run(conn, prod, "CONFEZIONA", {"lot_id": lot["lot_id"], "quantita": 325})
    assert c1["collo"] != c2["collo"]
    fasi = {f["fase"]: f["stato"] for f in conn.execute("SELECT fase, stato FROM wms.job_phases WHERE job_id=%s", (jid,))}
    assert fasi["CONTROLLO"] == "COMPLETATA" and fasi["IMBALLAGGIO"] == "COMPLETATA"

    # 15. spedizione corretta via scanner: una scansione per collo
    sh = run(conn, actors["resp"], "CREA_SPEDIZIONE", {"external_madiwor_ref": "DDT-1426-1", "sales_order_id": "1426",
                                                        "cliente_nome": "Azienda Agricola Cacovich di Cacovich Dimitri",
                                                        "righe": [{"articolo": "117951", "quantita": 650, "commessa": "4515"}]})
    assert scan_(conn, sped, sh["barcode"])["esito"] == "INFO"
    p1 = scan_(conn, sped, c1["collo"])
    assert p1["esito"] == "OK" and "mancano 325 pz" in p1["titolo"]
    p2 = scan_(conn, sped, c2["collo"])
    assert p2["esito"] == "OK" and p2["risultato"]["spedizione_completa"] is True
    out = run(conn, sped, "CONFERMA_USCITA", {"shipment_id": str(sh["shipment_id"]), "vettore": "GLS"})
    assert "650 pz" in out["messaggio"]

    # 16. retry di tutto: nessuna duplicazione
    again = madiwor.import_job(conn, job, "FIXTURE")
    assert again["esito"] == "INVARIATO"
    sh2 = run(conn, actors["resp"], "CREA_SPEDIZIONE", {"external_madiwor_ref": "DDT-1426-1", "cliente_nome": "x",
                                                         "righe": [{"articolo": "117951", "quantita": 650}]})
    assert sh2["esito"] == "INVARIATO"
    assert conn.execute("SELECT count(*) n FROM wms.shipments").fetchone()["n"] == 1
    # bobine non toccate restano intatte
    for b, m in ((corta, "40.00"), (lunga, "300.00")):
        assert conn.execute("SELECT metri_residui FROM wms.material_rolls WHERE id=%s", (b["id"],)).fetchone()["metri_residui"] == Decimal(m)
