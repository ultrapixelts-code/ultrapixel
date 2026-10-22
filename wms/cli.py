"""Comandi di servizio.

  python -m wms.cli migra                      applica le migrazioni (additive, schema wms)
  python -m wms.cli verifica                   registro ↔ giacenze; exit 1 se incoerenti (per cron/allarme)
  python -m wms.cli postazione NOME TIPO [UBIC] crea una postazione e stampa il suo token (una volta sola)
  python -m wms.cli utente USERNAME "NOME" RUOLO BADGE PIN
  python -m wms.cli ubicazione CODICE TIPO [MACCHINA]
"""
from __future__ import annotations

import sys

from . import auth, db, ledger


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    conn = db.connect()
    cmd, args = argv[0], argv[1:]
    if cmd == "migra":
        print("Applicate:", db.apply_migrations(conn) or "nessuna (già aggiornato)")
    elif cmd == "verifica":
        problems = ledger.verify(conn)
        for p in problems:
            print("INCOERENZA:", p)
        print("OK: registro e giacenze coincidono" if not problems else f"{len(problems)} incoerenze")
        return 1 if problems else 0
    elif cmd == "postazione":
        nome, tipo = args[0], args[1]
        loc = None
        if len(args) > 2:
            loc = conn.execute("SELECT id FROM wms.warehouse_locations WHERE codice=%s", (args[2],)).fetchone()["id"]
        with conn.transaction():
            _, tok = auth.create_device(conn, nome, tipo, loc)
        print("Token postazione (si mostra una volta sola, va incollato sul dispositivo):", tok)
    elif cmd == "utente":
        username, nome, ruolo, badge, pin = args
        with conn.transaction():
            conn.execute("INSERT INTO wms.users(username, display_name, role_code, badge_code, pin_hash) VALUES (%s,%s,%s,%s,%s)",
                         (username, nome, ruolo, badge, auth.hash_pin(pin)))
        print("Utente creato. Badge:", badge)
    elif cmd == "ubicazione":
        codice, tipo = args[0], args[1]
        with conn.transaction():
            conn.execute("INSERT INTO wms.warehouse_locations(codice, barcode, tipo, machine_code) VALUES (%s,%s,%s,%s)",
                         (codice, "UPL" + "".join(c for c in codice.upper() if c.isalnum()), tipo, args[2] if len(args) > 2 else None))
        print("Ubicazione creata")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
