"""Dove mettere una bobina: scelta deterministica, con il motivo scritto.

Guarda tutto il magazzino ogni volta:
 1. posto pieno (capienza raggiunta) o bloccato → escluso;
 2. bobina prenotata per una commessa in consegna a breve → area PRONTO_MACCHINA vicina alla
    macchina della commessa;
 3. spezzone sotto la soglia rimanenze → area RIMANENZE;
 4. altrimenti area SCORTA;
 5. a parità: stesso materiale già nel posto (si trova più in fretta), bobina pesante su ripiano basso,
    posto meno pieno, codice (risultato sempre uguale a parità di dati).
Le istruzioni "come" vengono dalla configurazione del posto e del materiale: nessuna regola inventata.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from .engine import D, setting


def _occupancy(conn) -> dict:
    rows = conn.execute("""SELECT ubicazione_id, count(*) AS n FROM wms.material_rolls
                           WHERE ubicazione_id IS NOT NULL AND stato NOT IN ('ESAURITA','TAGLIATA','ANNULLATA','IN_PRODUZIONE')
                           GROUP BY 1""").fetchall()
    return {r["ubicazione_id"]: r["n"] for r in rows}


def target_area(conn, roll: dict) -> tuple[str, str | None, str]:
    """(area, macchina_vicina, motivo)"""
    giorni = int(setting(conn, "giorni_pronto_macchina", 2))
    res = conn.execute(
        """SELECT j.external_madiwor_id, j.data_consegna, (SELECT macchina FROM wms.job_phases f WHERE f.job_id=j.id
                  AND f.fase='STAMPA' LIMIT 1) AS macchina
           FROM wms.material_reservations r JOIN wms.production_jobs j ON j.id=r.job_id
           WHERE r.roll_id=%s AND r.status='ATTIVA' AND j.stato IN ('APERTA','IN_PRODUZIONE')
           ORDER BY j.data_consegna NULLS LAST LIMIT 1""", (roll["id"],)).fetchone()
    if res and res["data_consegna"] and res["data_consegna"] <= dt.date.today() + dt.timedelta(days=giorni):
        return "PRONTO_MACCHINA", res["macchina"], f"serve alla commessa {res['external_madiwor_id']} in consegna il {res['data_consegna']:%d/%m}"
    metri = D(roll["metri_stimati"] if roll.get("metri_stimati") is not None else roll["metri_residui"])
    if metri < D(setting(conn, "soglia_rimanenza_metri", 100)):
        return "RIMANENZE", None, f"spezzone da {metri:g} m"
    return "SCORTA", None, "bobina a scorta"


def choose_location(conn, roll_id) -> dict | None:
    roll = conn.execute("""SELECT r.*, m.descrizione, m.istruzioni_stoccaggio FROM wms.material_rolls r
                           JOIN wms.materials m ON m.id=r.material_id WHERE r.id=%s""", (roll_id,)).fetchone()
    area, macchina, motivo_area = target_area(conn, roll)
    occ = _occupancy(conn)
    locs = conn.execute("""SELECT * FROM wms.warehouse_locations WHERE stato='ATTIVA' AND tipo='SCAFFALE'
                           AND id IS DISTINCT FROM %s ORDER BY codice""", (roll["ubicazione_id"],)).fetchall()
    same = {r["ubicazione_id"]: r["n"] for r in conn.execute(
        """SELECT ubicazione_id, count(*) AS n FROM wms.material_rolls WHERE material_id=%s AND id<>%s
           AND stato IN ('DISPONIBILE','DA_VERIFICARE') AND ubicazione_id IS NOT NULL GROUP BY 1""",
        (roll["material_id"], roll["id"])).fetchall()}
    heavy = D(roll["metri_residui"]) >= D(setting(conn, "soglia_bobina_pesante_metri", 500))

    def free(l):
        return l["capacita_bobine"] is None or occ.get(l["id"], 0) < l["capacita_bobine"]

    def fits_area(l, a):
        la = l["area"] or "SCORTA"
        if la != a:
            return False
        return a != "PRONTO_MACCHINA" or not macchina or not l["macchina_vicina"] or l["macchina_vicina"] == macchina

    pool = [l for l in locs if free(l) and fits_area(l, area)]
    fallback = None
    if not pool and area != "SCORTA":
        fallback = f"area {area.lower().replace('_', ' ')} piena"
        pool = [l for l in locs if free(l) and fits_area(l, "SCORTA")]
    if not pool:
        pool = [l for l in locs if free(l)]
        fallback = fallback or "nessun posto libero nell'area giusta"
    if not pool:
        return None

    def key(l):
        lvl = l["livello"] or 1
        return (-same.get(l["id"], 0),
                (lvl if heavy else 0),
                occ.get(l["id"], 0),
                l["codice"])
    best = min(pool, key=key)
    motivi = [motivo_area]
    if same.get(best["id"]):
        motivi.append(f"già {same[best['id']]} bobine dello stesso materiale")
    if heavy and (best["livello"] or 1) == 1:
        motivi.append("bobina pesante: ripiano basso")
    if fallback:
        motivi.append(fallback)
    cap = best["capacita_bobine"]
    istr = [f"ripiano {best['livello']}" + (" (basso)" if best["livello"] == 1 else "") if best["livello"] else None,
            best["istruzioni"], roll["istruzioni_stoccaggio"]]
    return {"id": best["id"], "codice": best["codice"], "area": best["area"] or "SCORTA",
            "istruzioni": [i for i in istr if i], "motivo": "; ".join(motivi),
            "occupazione": f"{occ.get(best['id'], 0) + 1}/{cap}" if cap else None}
