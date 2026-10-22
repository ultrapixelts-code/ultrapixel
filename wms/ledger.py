"""Verifica che le proiezioni (bobine, colli, lotti, prenotazioni) coincidano con il registro movimenti.

Se questa verifica fallisce, il sistema NON è affidabile: è il controllo di consistenza usato nei test
dopo ogni scenario e disponibile come controllo periodico in produzione."""
from __future__ import annotations

from decimal import Decimal


def verify(conn) -> list[str]:
    problems: list[str] = []
    rows = conn.execute(
        """SELECT r.barcode, r.metri_residui, r.metri_riservati, r.stato,
                  coalesce(sum(m.quantita) FILTER (WHERE m.unita_misura='m'),0)     AS led_fisico,
                  coalesce(sum(m.quantita) FILTER (WHERE m.unita_misura='m_ris'),0) AS led_ris
           FROM wms.material_rolls r LEFT JOIN wms.inventory_movements m
             ON m.entity_type='ROLL' AND m.entity_id=r.id
           GROUP BY r.id""").fetchall()
    for r in rows:
        if Decimal(r["led_fisico"]) != Decimal(r["metri_residui"]):
            problems.append(f"{r['barcode']}: residui {r['metri_residui']} ≠ registro {r['led_fisico']}")
        if Decimal(r["led_ris"]) != Decimal(r["metri_riservati"]):
            problems.append(f"{r['barcode']}: riservati {r['metri_riservati']} ≠ registro {r['led_ris']}")
        if r["metri_residui"] < 0 or r["metri_riservati"] < 0:
            problems.append(f"{r['barcode']}: valori negativi")
        if r["stato"] in ("ESAURITA", "TAGLIATA", "ANNULLATA") and r["metri_residui"] != 0:
            problems.append(f"{r['barcode']}: stato {r['stato']} con {r['metri_residui']} m")
    # prenotazioni: tabella ↔ proiezione bobina ↔ proiezione fabbisogno
    for r in conn.execute(
        """SELECT b.barcode, b.metri_riservati, coalesce(sum(x.quantity) FILTER (WHERE x.status='ATTIVA'),0) AS att
           FROM wms.material_rolls b LEFT JOIN wms.material_reservations x ON x.roll_id=b.id
           GROUP BY b.id HAVING b.metri_riservati <> coalesce(sum(x.quantity) FILTER (WHERE x.status='ATTIVA'),0)""").fetchall():
        problems.append(f"{r['barcode']}: riservati {r['metri_riservati']} ≠ prenotazioni attive {r['att']}")
    for r in conn.execute(
        """SELECT jm.id, jm.metri_prenotati, coalesce(sum(x.quantity) FILTER (WHERE x.status='ATTIVA'),0) AS att
           FROM wms.production_job_materials jm LEFT JOIN wms.material_reservations x ON x.job_material_id=jm.id
           GROUP BY jm.id HAVING jm.metri_prenotati <> coalesce(sum(x.quantity) FILTER (WHERE x.status='ATTIVA'),0)""").fetchall():
        problems.append(f"fabbisogno {r['id']}: prenotati {r['metri_prenotati']} ≠ prenotazioni attive {r['att']}")
    # consumi della commessa = movimenti CONSUMO/SCARTO
    for r in conn.execute(
        """SELECT jm.id, jm.metri_consumati, jm.metri_scarto,
                  coalesce(-sum(m.quantita) FILTER (WHERE m.tipo_movimento='CONSUMO'),0) AS cons,
                  coalesce(-sum(m.quantita) FILTER (WHERE m.tipo_movimento='SCARTO'),0) AS scar
           FROM wms.production_job_materials jm
           LEFT JOIN wms.roll_assignments a ON a.job_material_id=jm.id
           LEFT JOIN wms.inventory_movements m ON m.reference_id=a.id AND m.tipo_movimento IN ('CONSUMO','SCARTO')
           GROUP BY jm.id""").fetchall():
        if Decimal(r["cons"]) != Decimal(r["metri_consumati"]) or Decimal(r["scar"]) != Decimal(r["metri_scarto"]):
            problems.append(f"fabbisogno {r['id']}: consumi {r['metri_consumati']}/{r['metri_scarto']} ≠ "
                            f"registro {r['cons']}/{r['scar']}")
    # colli: giacenza da registro = quantità se in magazzino, 0 se spedito
    for r in conn.execute(
        """SELECT p.barcode, p.quantita, p.stato, coalesce(sum(m.quantita),0) AS led
           FROM wms.finished_goods_packages p LEFT JOIN wms.inventory_movements m
             ON m.entity_type='PACKAGE' AND m.entity_id=p.id AND m.unita_misura='pz'
           GROUP BY p.id""").fetchall():
        atteso = 0 if r["stato"] == "SPEDITO" else r["quantita"]
        if Decimal(r["led"]) != Decimal(atteso):
            problems.append(f"collo {r['barcode']}: registro {r['led']} ≠ atteso {atteso} ({r['stato']})")
    # lotti: confezionato ≤ conforme ≤ prodotto (vincoli DB) e prodotto = registro
    for r in conn.execute(
        """SELECT l.codice, l.quantita_prodotta, l.quantita_confezionata,
                  coalesce(sum(m.quantita) FILTER (WHERE m.unita_misura='pz_prod'),0) AS prod,
                  (SELECT coalesce(sum(p.quantita),0) FROM wms.finished_goods_packages p WHERE p.lotto_id=l.id) AS pk
           FROM wms.production_lots l LEFT JOIN wms.inventory_movements m ON m.entity_type='LOT' AND m.entity_id=l.id
           GROUP BY l.id""").fetchall():
        if Decimal(r["prod"]) != Decimal(r["quantita_prodotta"]):
            problems.append(f"lotto {r['codice']}: prodotto {r['quantita_prodotta']} ≠ registro {r['prod']}")
        if Decimal(r["pk"]) != Decimal(r["quantita_confezionata"]):
            problems.append(f"lotto {r['codice']}: confezionato {r['quantita_confezionata']} ≠ colli {r['pk']}")
    # spedizioni: preparato = somma colli prelevati/spediti
    for r in conn.execute(
        """SELECT l.id, l.quantita_preparata,
                  (SELECT coalesce(sum(p.quantita),0) FROM wms.finished_goods_packages p
                   WHERE p.shipment_line_id=l.id AND p.stato IN ('PRELEVATO','SPEDITO','RESO')) AS pk
           FROM wms.shipment_lines l""").fetchall():
        if Decimal(r["pk"]) != Decimal(r["quantita_preparata"]):
            problems.append(f"riga spedizione {r['id']}: preparato {r['quantita_preparata']} ≠ colli {r['pk']}")
    return problems
