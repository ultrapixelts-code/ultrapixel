"""Scelta deterministica delle bobine per un fabbisogno.

Non è FIFO puro. Criteri, in ordine:
 1. solo materiale identico o equivalenza tecnica APPROVATA (mai somiglianza del nome);
 2. solo larghezza compatibile (entro tolleranza): le bobine più larghe sono proposte a parte
    come "richiede taglio", mai scelte in automatico;
 3. se una sola bobina copre il fabbisogno: quella che lascia meno avanzo (usa prima le
    rimanenze corte, riduce sfridi e bobine aperte);
 4. a parità: materiale identico prima dell'equivalente, bobina già misurata prima di una
    con metratura solo dichiarata, ricevimento più vecchio, codice (per avere sempre lo
    stesso risultato);
 5. se nessuna bobina basta da sola: combinazione col minor numero di bobine;
 6. più commesse in concorrenza: `plan_open_jobs` assegna per data di consegna (le urgenti
    prima) in simulazione, senza scrivere nulla, per prevedere le carenze.
Ogni scelta riporta il motivo, così l'operatore (o l'assistente AI) può spiegarla.
"""
from __future__ import annotations

from decimal import Decimal

from .engine import D, material_compatibility, setting


def _candidates(conn, jm: dict, job: dict):
    rows = conn.execute(
        """SELECT r.*, l.codice AS ubicazione, l.zona,
                  (r.metri_residui - r.metri_riservati) AS disponibili
           FROM wms.material_rolls r LEFT JOIN wms.warehouse_locations l ON l.id=r.ubicazione_id
           WHERE r.stato='DISPONIBILE' AND (r.metri_residui - r.metri_riservati) > 0
             AND (r.material_id=%s OR r.material_id IN (
                   SELECT compatible_material_id FROM wms.material_equivalences
                   WHERE material_id=%s AND active))
           ORDER BY r.barcode""", (jm["material_id"], jm["material_id"])).fetchall()
    tol = D(setting(conn, "tolleranza_larghezza_mm", 0))
    req_w = D(jm["larghezza_richiesta_mm"]) if jm["larghezza_richiesta_mm"] is not None else None
    ok, wider = [], []
    for r in rows:
        comp = material_compatibility(conn, jm["material_id"], r["material_id"], job.get("cliente_ref"))
        if comp is None:
            continue
        r = {**r, "comp": comp, "disponibili": D(r["disponibili"])}
        if req_w is None or abs(D(r["larghezza_mm"]) - req_w) <= tol:
            ok.append(r)
        elif D(r["larghezza_mm"]) > req_w:
            wider.append(r)
    return ok, wider


def _key_single(r, need):
    return (r["disponibili"] - need,                      # avanzo minimo
            0 if r["comp"] == "IDENTICO" else 1,
            0 if r["origine_dato_metratura"] == "MISURA" else 1,
            r["data_ricezione"], r["barcode"])


def choose_rolls(conn, jm: dict, job: dict, need: Decimal) -> dict:
    need = D(need)
    ok, wider = _candidates(conn, jm, job)
    con_taglio = [{"roll_id": r["id"], "bobina": r["barcode"], "larghezza_mm": D(r["larghezza_mm"]),
                   "disponibili": r["disponibili"], "ubicazione": r["ubicazione"]}
                  for r in sorted(wider, key=lambda r: (D(r["larghezza_mm"]), -r["disponibili"], r["barcode"]))[:3]]
    if need <= 0:
        return {"scelte": [], "mancano": Decimal("0"), "con_taglio": []}
    covering = [r for r in ok if r["disponibili"] >= need]
    if covering:
        best = min(covering, key=lambda r: _key_single(r, need))
        motivo = (f"copre da sola i {need} m lasciando l'avanzo più piccolo ({best['disponibili'] - need} m)"
                  + ("" if best["comp"] == "IDENTICO" else f"; materiale equivalente approvato ({best['comp']})"))
        return {"scelte": [{"roll_id": best["id"], "bobina": best["barcode"], "metri": need,
                            "ubicazione": best["ubicazione"], "motivo": motivo}],
                "mancano": Decimal("0"), "con_taglio": con_taglio}
    # nessuna basta: meno bobine possibili (le più lunghe), poi stessa logica di parità
    scelte, rest = [], need
    pool = sorted(ok, key=lambda r: (-r["disponibili"], 0 if r["comp"] == "IDENTICO" else 1, r["data_ricezione"], r["barcode"]))
    for r in pool:
        if rest <= 0:
            break
        q = min(rest, r["disponibili"])
        scelte.append({"roll_id": r["id"], "bobina": r["barcode"], "metri": q, "ubicazione": r["ubicazione"],
                       "motivo": "nessuna bobina basta da sola: combinazione col minor numero di bobine"})
        rest -= q
    return {"scelte": scelte, "mancano": max(Decimal("0"), rest), "con_taglio": con_taglio}


def plan_open_jobs(conn) -> list[dict]:
    """Simulazione di sola lettura: copre i fabbisogni non ancora prenotati delle commesse aperte,
    in ordine di consegna, e segnala dove il materiale non basta. Non scrive nulla."""
    jobs = conn.execute(
        """SELECT * FROM wms.production_jobs WHERE stato IN ('APERTA','IN_PRODUZIONE')
           ORDER BY data_consegna NULLS LAST, external_madiwor_id""").fetchall()
    used: dict = {}
    out = []
    for job in jobs:
        for jm in conn.execute("SELECT * FROM wms.production_job_materials WHERE job_id=%s AND attiva", (job["id"],)).fetchall():
            from .engine import to_reserve
            need = to_reserve(jm)
            if need <= 0:
                continue
            if jm["material_id"] is None:
                out.append({"commessa": job["external_madiwor_id"], "consegna": job["data_consegna"],
                            "materiale": jm["material_label_source"], "mancano": need, "motivo": "materiale non risolto"})
                continue
            ok, _ = _candidates(conn, jm, job)
            rest = need
            for r in sorted(ok, key=lambda r: _key_single(r, need)):
                free = r["disponibili"] - used.get(r["id"], Decimal("0"))
                if free <= 0 or rest <= 0:
                    continue
                q = min(free, rest)
                used[r["id"]] = used.get(r["id"], Decimal("0")) + q
                rest -= q
            if rest > 0:
                out.append({"commessa": job["external_madiwor_id"], "consegna": job["data_consegna"],
                            "materiale": jm["material_label_source"], "mancano": rest,
                            "motivo": "giacenza disponibile insufficiente rispetto alle commesse più urgenti"})
    return out
