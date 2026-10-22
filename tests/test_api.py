"""API HTTP: autenticazione lato server, scansione, comandi, etichette, retry di rete."""
import uuid

import pytest

from conftest import DSN, receive
from wms import madiwor, seed
from wms.app import create_app


@pytest.fixture
def client(conn, ids):
    app = create_app(DSN)
    app.testing = True
    return app.test_client()


def H(ids, device, session=None):
    h = {"X-Device-Token": ids["tokens"][device]}
    if session:
        h["Authorization"] = "Bearer " + session
    return h


def login(client, ids, device, badge):
    r = client.post("/api/login", json={"badge": badge}, headers=H(ids, device))
    assert r.status_code == 200, r.json
    return r.json["sessione"]


def test_dispositivo_e_sessione_obbligatori(client, ids):
    assert client.post("/api/scan", json={"code": "x", "client_scan_id": str(uuid.uuid4())}).status_code == 403
    r = client.post("/api/scan", json={"code": "x", "client_scan_id": str(uuid.uuid4())}, headers=H(ids, "Postazione Xeikon"))
    assert r.status_code == 403 and r.json["codice"] == "LOGIN_RICHIESTO"
    assert client.post("/api/login", json={"badge": "NONESISTE"}, headers=H(ids, "Postazione Xeikon")).status_code == 403
    # la sessione vale solo sul dispositivo dove è stata aperta
    s = login(client, ids, "Postazione Xeikon", "UPBPROD01")
    r = client.get("/api/stato", headers=H(ids, "Postazione spedizione", s))
    assert r.status_code == 403


def test_flusso_http_inizio_produzione(client, conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    madiwor.import_job(conn, seed.load_job_fixture(), "FIXTURE")
    s = login(client, ids, "Postazione Xeikon", "UPBPROD01")
    h = H(ids, "Postazione Xeikon", s)
    r1 = client.post("/api/scan", json={"code": "4515", "client_scan_id": str(uuid.uuid4())}, headers=h).json
    sid = str(uuid.uuid4())
    r2 = client.post("/api/scan", json={"code": b["barcode"], "client_scan_id": sid}, headers=h).json
    r2b = client.post("/api/scan", json={"code": b["barcode"], "client_scan_id": sid, "offline": True}, headers=h).json
    assert r1["esito"] == "INFO" and r2["esito"] == "OK" and r2b["ripetuta"] is True
    # annullo da tastiera (F8) = comando compensativo dello stesso operatore
    u = client.post("/api/command", json={"event_id": str(uuid.uuid4()), "tipo": "ANNULLA_COMANDO",
                                          "payload": {"event_id": r2["comando"]["event_id"]}}, headers=h)
    assert u.status_code == 200, u.json
    # le commesse non si creano dalla schermata scanner
    x = client.post("/api/command", json={"event_id": str(uuid.uuid4()), "tipo": "IMPORTA_COMMESSA", "payload": {}}, headers=h)
    assert x.status_code == 400


def test_etichette_e_metriche(client, conn, ids, actors):
    b = receive(conn, actors, ids, 100)[0]
    s = login(client, ids, "Postazione ricevimento", "UPBPROD01")
    r = client.post("/api/etichette", json={"tipo": "bobina", "ids": [str(b["id"])]}, headers=H(ids, "Postazione ricevimento", s))
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and b["barcode"] in html and "<svg" in html and "35mm 30mm" in html
    m = client.get("/api/metriche", headers=H(ids, "Postazione ricevimento", s)).json
    assert m["operazioni"][0]["operazione"] == "RICEVI_BOBINA"


def test_anomalie_inventario(client, conn, ids, actors):
    receive(conn, actors, ids, 100)
    s = login(client, ids, "Postazione magazzino", "UPBRESP01")
    a = client.get("/api/anomalie", headers=H(ids, "Postazione magazzino", s)).json
    assert set(a) >= {"bobine_ferme_90_giorni", "metrature_stimate_da_verificare", "ubicazioni_incoerenti",
                      "consumo_diverso_dal_teorico", "colli_mai_usciti_commessa_spedita"}


def test_code128_leggibile_da_un_decoder(conn):
    zx = pytest.importorskip("zxingcpp")
    Image = pytest.importorskip("PIL.Image")
    from wms.labels import code128_widths
    for t in ("UPR000123", "UPC000045", "UPLA0101", "UPBPROD01"):
        w = code128_widths(t); mod, q = 3, 12
        img = Image.new("L", ((sum(w) + 2 * q) * mod, 60), 255)
        x = q * mod
        for i, wd in enumerate(w):
            if i % 2 == 0:
                for xx in range(x, x + wd * mod):
                    for y in range(60):
                        img.putpixel((xx, y), 0)
            x += wd * mod
        assert [r.text for r in zx.read_barcodes(img)] == [t]


def test_ricevimento_due_scansioni_via_http(client, conn, ids, actors):
    """Obiettivo sez. 17: materiale noto = max 2 scansioni (+ conferma). Etichetta GS1 con GTIN, metri e lotto."""
    from conftest import run
    gtin = "08012345678907"
    run(conn, actors["resp"], "ASSOCIA_CODICE", {"code": gtin, "namespace": "GTIN", "material_id": str(ids["mat"]["EPIQUE-FSC-S2047N"])})
    conn.execute("UPDATE wms.materials SET larghezza_mm=170")
    s = login(client, ids, "Postazione ricevimento", "UPBPROD01")
    h = H(ids, "Postazione ricevimento", s)
    sc = client.post("/api/scan", json={"code": "01" + gtin + "3111005000" + "10L9", "client_scan_id": str(uuid.uuid4())}, headers=h).json
    assert sc["esito"] == "CHIEDI"                                                     # scansione 1
    cmd = client.post("/api/command", json={"event_id": str(uuid.uuid4()), "tipo": sc["chiedi"]["azione"],
                                            "payload": sc["chiedi"]["dati"]}, headers=h).json   # Invio
    assert cmd["contesto"]["in_attesa_ubicazione"] == cmd["bobine"][0]["barcode"] and cmd["stampa"]
    mv = client.post("/api/scan", json={"code": "UPLA0102", "client_scan_id": str(uuid.uuid4())}, headers=h).json   # scansione 2
    assert mv["esito"] == "OK"
    r = conn.execute("SELECT r.metri_residui, r.lotto_fornitore, l.codice FROM wms.material_rolls r "
                     "JOIN wms.warehouse_locations l ON l.id=r.ubicazione_id").fetchone()
    assert (r["metri_residui"], r["lotto_fornitore"], r["codice"]) == (500, "L9", "A-01-02")
    n = conn.execute("SELECT count(*) n FROM wms.scan_events WHERE device_id=%s", (ids["devices"]["Postazione ricevimento"],)).fetchone()["n"]
    assert n == 2
