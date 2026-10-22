"""Flusso operatore a tre scansioni: arrivo → prima di stampare → fine. Il sistema decide posto, commessa
ed etichette; il consumo definitivo arriva dallo storico della macchina."""
import datetime as dt
import uuid
from decimal import Decimal

from conftest import receive, run
from wms import machine, madiwor, scan, seed

XEIKON_HEADER = ('#,JobName,Collection,Job Folder,Input Type,Input Size (kb),Pages,Sigs,Layout Width (mm),Width Waste (mm),'
                 'EndTime,Time (s),Total Time (s),Width (mm),Height (mm),Colors,PageMode,NOC,Sheets,Trials,Run Length (m),'
                 'Output Size (kb),Sim CMYK/Sheet (mg),Sim Spot/Sheet (mg),C (g),M (g),Y (g),K (g),CMYK (g),Spot (g),'
                 'CMYK+Spot (g),CMYK/Sheet (mg),Spot/Sheet (mg),Units,Speed (cm/s),Medium,State,Comment,User,Color Clicks,'
                 'B/W Clicks,Total Clicks,Total Medium Ref (A3)')
# due righe reali dall'export del 02/09/2026 + la riga Total
REAL_ROWS = [
    '1,112958 montata.pdf,Xeikon CX3S On Z4-07MBR,Z4-07MBR_000743,pdf,830,1,1,330,0,2026-09-02_09:52:46,812,1399,330,84,'
    'CMYK,Simplex,1550,1550,0,122.319,1801,197,0,176.3,167.2,121.5,200.1,665.1,0,665.1,429,0,CMYK,16.7,'
    '"Label:_Ritrama,_STARLIGHT_WS_BARRIER_AP1300,_137µm,_330mm",Completed,NULL,expert,412,0,412,1865240.2',
    '2,112958 montata.pdf,Xeikon CX3S On Z4-07MBR,Z4-07MBR_000743,pdf,830,1,1,330,-8,2026-09-02_09:32:25,522,1399,322,84,'
    'CMYK,Simplex,1550,947,0,77.206,1801,197,0,88.3,148.4,90.7,145.5,472.9,0,472.9,499,0,CMYK,16.7,'
    '"Label:_Ritrama,_STARLIGHT_WS_BARRIER_AP1300,_137µm,_330mm",Held,Job held by engine or other job,expert,268,0,268,1864962.2',
    '257,Total,,,,1029443,277,1774,,,,70584,670119,,,,,285249,100175,21,8034.175,486914,,,768,1055.4,955,3416.1,6193.8,0,'
    '6193.8,,,,,,,,,36557,2032,38589,5.70E+08',
]


def scan_(conn, actor, code, ts=None):
    return scan.handle_scan(conn, actor, code, uuid.uuid4(), client_ts=ts)


def later(sec):
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=sec)


def roll(conn, rid):
    return conn.execute("SELECT r.*, l.codice FROM wms.material_rolls r LEFT JOIN wms.warehouse_locations l "
                        "ON l.id=r.ubicazione_id WHERE r.id=%s", (rid,)).fetchone()


def feed_machine(conn, actors, assignment_ids, metri_each, coverage_after=True):
    """Crea righe di storico dentro gli intervalli dei montaggi indicati (come farebbe l'export Xeikon)."""
    righe = []
    for aid, m in zip(assignment_ids, metri_each):
        a = conn.execute("SELECT inizio_at, fine_at FROM wms.roll_assignments WHERE id=%s", (aid,)).fetchone()
        mid = a["inizio_at"] + (a["fine_at"] - a["inizio_at"]) / 2
        righe.append({"job_name": "lavoro montata.pdf", "medium": "EPIQUE 170mm", "stato": "Completed",
                      "fine_at": mid.isoformat(), "durata_s": 60, "metri": str(m)})
    if coverage_after:
        last = conn.execute("SELECT max(fine_at) f FROM wms.roll_assignments").fetchone()["f"]
        righe.append({"job_name": "Universal", "medium": "", "stato": "Completed",
                      "fine_at": (last + dt.timedelta(seconds=1)).isoformat(), "durata_s": 1, "metri": "0"})
    return run(conn, actors["resp"], "IMPORTA_STORICO_MACCHINA", {"macchina": "CX3S", "righe": righe, "file": "test.csv"})


def test_parser_storico_xeikon_reale():
    rows = machine.parse_xeikon_csv("\n".join([XEIKON_HEADER] + REAL_ROWS))
    assert len(rows) == 2                                    # la riga Total è ignorata
    assert rows[0]["metri"] == "122.319" and rows[0]["stato"] == "Completed"
    assert rows[1]["stato"] == "Held" and rows[0]["fine_at"].startswith("2026-09-02T09:52:46+02:00")


def test_tre_scansioni_con_dati_macchina(conn, ids, actors):
    conn.execute("UPDATE wms.materials SET larghezza_mm=170, metri_nominali=300 WHERE codice_interno='EPIQUE-FSC-S2047N'")
    run(conn, actors["resp"], "ASSOCIA_CODICE", {"code": "AA335", "material_id": str(ids["mat"]["EPIQUE-FSC-S2047N"])})
    madiwor.import_job(conn, seed.load_job_fixture(), "FIXTURE")
    # 1. arrivo: una lettura
    s1 = scan_(conn, actors["ric"], "AA335")
    assert s1["esito"] == "OK" and s1["stampa"], s1
    rid = s1["bobina"]["id"]
    # 2. prima di stampare: una lettura in macchina, la commessa la trova il sistema
    s2 = scan_(conn, actors["prod"], s1["bobina"]["barcode"])
    assert s2["esito"] == "OK" and s2["titolo"] == "Commessa 4515", s2
    # 3. fine: una lettura, nessuna domanda
    s3 = scan_(conn, actors["prod"], s1["bobina"]["barcode"], ts=later(30))
    assert s3["esito"] == "OK" and s3["titolo"].startswith("Metti in") and "stimato" in s3["messaggio"]
    assert s3["stampa"] == [{"tipo": "bobina", "id": rid}]
    r = roll(conn, rid)
    assert r["stato"] == "DA_VERIFICARE" and r["metri_residui"] == Decimal("300.00")   # la stima non tocca il fisico
    # arriva lo storico Xeikon: 61,5 m passati in macchina in quell'intervallo
    aid = conn.execute("SELECT id FROM wms.roll_assignments WHERE roll_id=%s", (rid,)).fetchone()["id"]
    imp = feed_machine(conn, actors, [aid], ["61.5"])
    assert imp["consumi_verificati"] == 1
    r = roll(conn, rid)
    assert (r["stato"], r["metri_residui"], r["metri_stimati"]) == ("DISPONIBILE", Decimal("238.50"), None)
    jm = conn.execute("SELECT * FROM wms.production_job_materials").fetchone()
    assert (jm["metri_consumati"], jm["metri_consumo_stimato"]) == (Decimal("61.50"), 0)
    # reimportare lo stesso storico non cambia nulla
    again = feed_machine(conn, actors, [aid], ["61.5"])
    assert again["righe_nuove"] == 0 and roll(conn, rid)["metri_residui"] == Decimal("238.50")


def test_riuso_bobina_prima_dei_dati_macchina(conn, ids, actors):
    """La bobina si può rimontare prima che arrivi lo storico: le chiusure stimate si verificano poi in ordine."""
    b = receive(conn, actors, ids, 200)[0]
    madiwor.import_job(conn, seed.load_job_fixture(), "FIXTURE")
    j2 = seed.load_job_fixture(); j2.external_id = "4520"; j2.materiali[0].metri = Decimal("40")
    madiwor.import_job(conn, j2, "FIXTURE")
    for k in range(2):
        a = scan_(conn, actors["prod"], b["barcode"], ts=later(100 * k))
        assert a["esito"] in ("OK", "AVVISO"), a
        e = scan_(conn, actors["prod"], b["barcode"], ts=later(100 * k + 30))
        assert e["esito"] == "OK", e
    r = roll(conn, b["id"])
    assert r["stato"] == "DA_VERIFICARE" and r["metri_stimati"] == Decimal("106.00")      # 200 − 54 − 40 stimati
    aids = [x["id"] for x in conn.execute("SELECT id FROM wms.roll_assignments ORDER BY inizio_at")]
    feed_machine(conn, actors, aids, ["58", "45.25"])
    r = roll(conn, b["id"])
    assert (r["stato"], r["metri_residui"]) == ("DISPONIBILE", Decimal("96.75"))
    cons = conn.execute("SELECT -sum(quantita) s FROM wms.inventory_movements WHERE tipo_movimento='CONSUMO'").fetchone()["s"]
    assert cons == Decimal("103.25")


def test_storico_incoerente_non_viene_applicato(conn, ids, actors):
    b = receive(conn, actors, ids, 50)[0]
    madiwor.import_job(conn, seed.load_job_fixture(), "FIXTURE")
    scan_(conn, actors["prod"], b["barcode"])
    scan_(conn, actors["prod"], b["barcode"], ts=later(30))
    aid = conn.execute("SELECT id FROM wms.roll_assignments").fetchone()["id"]
    imp = feed_machine(conn, actors, [aid], ["80"])          # più carta di quanta ne avesse la bobina
    assert imp["consumi_verificati"] == 0 and any("controllo" in w for w in imp["avvisi"])
    assert roll(conn, b["id"])["stato"] == "DA_VERIFICARE"


def test_commessa_scelta_dal_sistema(conn, ids, actors):
    b1, b2 = receive(conn, actors, ids, 100, n=2)
    j_late = seed.load_job_fixture(); j_late.external_id = "5001"; j_late.data_consegna = dt.date(2026, 12, 1)
    madiwor.import_job(conn, j_late, "FIXTURE")              # prenota b1 (prima bobina adatta)
    j_urgent = seed.load_job_fixture(); j_urgent.external_id = "5002"; j_urgent.data_consegna = dt.date(2026, 10, 25)
    madiwor.import_job(conn, j_urgent, "FIXTURE", auto_reserve=False)
    other = seed.load_job_fixture(); other.external_id = "5003"; other.data_consegna = dt.date(2026, 10, 1)
    other.fasi = [{"fase": "STAMPA", "macchina": "ALTRA"}]
    madiwor.import_job(conn, other, "FIXTURE", auto_reserve=False)
    reserved = conn.execute("SELECT b.barcode FROM wms.material_reservations r JOIN wms.material_rolls b ON b.id=r.roll_id "
                            "WHERE r.status='ATTIVA'").fetchone()["barcode"]
    free = b2["barcode"] if reserved == b1["barcode"] else b1["barcode"]
    # la bobina prenotata va alla sua commessa anche se non è la più urgente
    assert scan_(conn, actors["prod"], reserved)["titolo"] == "Commessa 5001"
    # una bobina libera va alla consegna più urgente che usa questa macchina (5003 è su un'altra macchina)
    assert scan_(conn, actors["prod2"], free)["titolo"] == "Commessa 5002"
    c = receive(conn, actors, ids, 100, mat="MATT-WINE-FSC")[0]
    assert scan_(conn, actors["prod"], c["barcode"], ts=later(10))["esito"] == "ERRORE"


def test_posto_scelto_guardando_il_magazzino(conn, ids, actors):
    from wms.slotting import choose_location
    # spezzone → area rimanenze
    corto = receive(conn, actors, ids, 60)[0]
    assert choose_location(conn, corto["id"])["codice"] == "B-02-01"
    # bobina pesante → scorta, ripiano basso; stesso materiale raggruppato
    p1 = receive(conn, actors, ids, 800)[0]
    c1 = choose_location(conn, p1["id"])
    assert c1["codice"] == "A-01-01" and "ripiano basso" in c1["motivo"]
    run(conn, actors["ric"], "COLLOCA_BOBINA", {"roll_id": str(p1["id"])})
    leggera = receive(conn, actors, ids, 300)[0]
    assert "stesso materiale" in choose_location(conn, leggera["id"])["motivo"]
    # posto pieno → si passa al successivo
    conn.execute("UPDATE wms.warehouse_locations SET capacita_bobine=1 WHERE codice='A-01-01'")
    assert choose_location(conn, leggera["id"])["codice"] == "A-01-02"
    # prenotata per una consegna a breve → pronto macchina vicino alla Xeikon
    j = seed.load_job_fixture(); j.data_consegna = dt.date.today() + dt.timedelta(days=1)
    madiwor.import_job(conn, j, "FIXTURE")
    pren = conn.execute("SELECT roll_id FROM wms.material_reservations WHERE status='ATTIVA'").fetchone()["roll_id"]
    c = choose_location(conn, pren)
    assert c["codice"] == "P-XEIKON" and "4515" in c["motivo"]


def test_prossimo_lavoro_per_la_macchina(conn, ids, actors):
    receive(conn, actors, ids, 100)
    madiwor.import_job(conn, seed.load_job_fixture(), "FIXTURE")
    nj = machine.next_job(conn, "CX3S")
    assert nj["commessa"] == "4515" and nj["bobina"] == "UPR000001"
    assert machine.next_job(conn, "ALTRA") is None          # la 4515 si stampa sulla CX3S
