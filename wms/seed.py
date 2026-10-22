"""Dati di partenza minimi (anagrafiche, ubicazioni, utenti, postazioni).

I materiali qui inseriti sono SOLO quelli necessari ai test e alla demo, presi dall'anagrafica reale
(public.materials su Render): MAT_000382 è il materiale della commessa 4515. La larghezza NON è un
attributo del materiale in anagrafica: sta sulla singola bobina.
"""
from __future__ import annotations

import json
import pathlib

from . import auth
from .madiwor import MadiworJob, MaterialeRichiesto, _parse_date
from .engine import D

ROOT = pathlib.Path(__file__).resolve().parent.parent


def seed_master(conn) -> dict:
    ids: dict = {"loc": {}, "users": {}, "devices": {}, "tokens": {}, "mat": {}}
    with conn.transaction():
        sup = conn.execute("INSERT INTO wms.suppliers(nome, os_supplier_id) VALUES ('Fornitore SUP_000033','SUP_000033') "
                           "RETURNING id").fetchone()["id"]
        for code, os_id, descr, madiwor, fcode in [
            ("EPIQUE-FSC-S2047N", "MAT_000382", "EPIQUE FSC S2047N -BG45WH IMP FSC",
             "EPIQUE FSC S2047N - BG45WH IMP FSC", "AA335"),
            ("MATT-WINE-FSC", "MAT_000421", "MATT WINE FSC S2047N - BG45WH", "MATT WINE FSC S2047N - BG45WH", "AG628"),
            ("SKIN-BLANC-PLUS-FSC", "MAT_000425", "SKIN BLANC PLUS FSC S2047N-BG45WH FSC", None, "AJ031"),
        ]:
            ids["mat"][code] = conn.execute(
                """INSERT INTO wms.materials(codice_interno, os_material_id, codice_fornitore, fornitore_id, descrizione,
                     descrizione_madiwor, supporto, adesivo, certificazioni, unita_misura)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'m') RETURNING id""",
                (code, os_id, fcode, sup, descr, madiwor, descr.split(" S20")[0], "S2047N", ["FSC"] if "FSC" in descr else [])
            ).fetchone()["id"]
        for codice, tipo, machine in [("RICEVIMENTO", "RICEVIMENTO", None), ("A-01-01", "SCAFFALE", None),
                                      ("A-01-02", "SCAFFALE", None), ("B-02-01", "SCAFFALE", None),
                                      ("XEIKON", "MACCHINA", "CX3S"), ("CARTES", "MACCHINA", "HS"),
                                      ("SPEDIZIONE", "SPEDIZIONE", None), ("QUARANTENA", "QUARANTENA", None)]:
            ids["loc"][codice] = conn.execute(
                """INSERT INTO wms.warehouse_locations(codice, barcode, tipo, machine_code, zona)
                   VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                (codice, "UPL" + codice.replace("-", ""), tipo, machine, codice.split("-")[0])).fetchone()["id"]
        for username, nome, role, badge, pin in [
            ("op.produzione", "Operatore produzione", "OPERATORE_PRODUZIONE", "UPBPROD01", "1111"),
            ("op.produzione2", "Operatore produzione 2", "OPERATORE_PRODUZIONE", "UPBPROD02", "2222"),
            ("op.spedizione", "Operatore spedizione", "OPERATORE_SPEDIZIONE", "UPBSPED01", "3333"),
            ("resp.magazzino", "Responsabile magazzino", "RESPONSABILE_MAGAZZINO", "UPBRESP01", "4444"),
        ]:
            ids["users"][username] = conn.execute(
                """INSERT INTO wms.users(username, display_name, role_code, badge_code, pin_hash)
                   VALUES (%s,%s,%s,%s,%s) RETURNING id""", (username, nome, role, badge, auth.hash_pin(pin))).fetchone()["id"]
        for nome, post, loc in [("Postazione ricevimento", "RICEVIMENTO", "RICEVIMENTO"),
                                ("Postazione magazzino", "MAGAZZINO", None),
                                ("Postazione Xeikon", "MACCHINA", "XEIKON"),
                                ("Postazione Xeikon (2)", "MACCHINA", "XEIKON"),
                                ("Postazione spedizione", "SPEDIZIONE", "SPEDIZIONE")]:
            d, tok = auth.create_device(conn, nome, post, ids["loc"][loc] if loc else None)
            ids["devices"][nome] = d["id"]
            ids["tokens"][nome] = tok
    return ids


def load_job_fixture(name: str = "commessa_4515.json") -> MadiworJob:
    d = json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))
    return MadiworJob(
        external_id=d["external_id"], sales_order_id=d.get("sales_order_id"), cliente_nome=d["cliente_nome"],
        cliente_ref=d.get("cliente_ref"), articolo=d.get("articolo"), descrizione=d.get("descrizione"),
        quantita=d.get("quantita"), data_consegna=_parse_date(d.get("data_consegna")), stato=d.get("stato", "ATTIVA"),
        materiali=[MaterialeRichiesto(m["descrizione"], D(m["larghezza_mm"]) if m.get("larghezza_mm") else None, D(m["metri"]))
                   for m in d.get("materiali", [])],
        fasi=d.get("fasi", []), specifiche=d.get("specifiche", {}))
