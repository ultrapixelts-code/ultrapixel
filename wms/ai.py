"""AI Warehouse Assistant — interfaccia astratta.

Confini (imposti dal codice, non solo dalla documentazione):
- gli strumenti a disposizione dell'AI girano in transazioni READ ONLY: un tentativo di scrittura
  fallisce nel database;
- l'unica scrittura possibile è `record_recommendation`, che inserisce una PROPOSTA in
  wms.ai_recommendations con motivazione, dati usati e affidabilità; nessuna proposta modifica giacenze:
  per diventare un movimento deve essere eseguita da una persona con un comando normale;
- il modulo non importa e non riceve il motore transazionale (`engine.execute`);
- se il provider non risponde, lo scanner e tutti i movimenti continuano a funzionare.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Protocol

from psycopg.types.json import Jsonb

from .errors import AIUnavailable, BusinessRuleError


class AIProvider(Protocol):
    name: str

    def complete(self, system: str, prompt: str, tools: dict) -> dict: ...


class UnavailableProvider:
    """Provider usato quando non è configurata alcuna chiave o il servizio è giù."""
    name = "nessuno"

    def complete(self, system, prompt, tools):
        raise AIUnavailable("Assistente AI non disponibile: le operazioni di magazzino funzionano normalmente")


class ReadOnlyTools:
    """Strumenti di sola lettura esposti all'AI."""

    def __init__(self, conn):
        self.conn = conn

    def _ro(self, sql, args=()):
        with self.conn.transaction():
            self.conn.execute("SET TRANSACTION READ ONLY")
            return self.conn.execute(sql, args).fetchall()

    def giacenze(self, testo: str | None = None) -> list[dict]:
        return self._ro("""SELECT codice_interno, descrizione, larghezza_mm, bobine, metri_fisici, metri_riservati,
                                  metri_disponibili, metri_stimati_da_verificare FROM wms.v_giacenze_materiali
                           WHERE %s::text IS NULL OR descrizione ILIKE '%%'||%s||'%%' ORDER BY descrizione""", (testo, testo))

    def bobine_ferme(self, giorni: int = 90) -> list[dict]:
        return self._ro("""SELECT r.barcode, m.descrizione, r.metri_residui, r.data_ricezione,
                                  (SELECT max(ts) FROM wms.inventory_movements x WHERE x.entity_id=r.id) AS ultimo_movimento
                           FROM wms.material_rolls r JOIN wms.materials m ON m.id=r.material_id
                           WHERE r.stato='DISPONIBILE' AND (SELECT max(ts) FROM wms.inventory_movements x
                                 WHERE x.entity_id=r.id) < now() - make_interval(days => %s)""", (giorni,))

    def carenze(self) -> list[dict]:
        from .optimizer import plan_open_jobs
        with self.conn.transaction():
            self.conn.execute("SET TRANSACTION READ ONLY")
            return plan_open_jobs(self.conn)

    def sql_libero(self, sql: str) -> list[dict]:
        """Esiste solo per dimostrare (nei test) che anche una query arbitraria non può scrivere."""
        return self._ro(sql)


def record_recommendation(conn, provider: str, tipo: str, suggerimento: dict, motivazione: str, dati_usati: dict,
                          affidabilita: float, oggetto_ref: str | None = None):
    if not motivazione or not dati_usati:
        raise BusinessRuleError("Una proposta AI deve indicare motivazione e dati usati", code="AI_PROPOSTA_INCOMPLETA")
    if not 0 <= affidabilita <= 1:
        raise BusinessRuleError("Affidabilità fuori scala", code="AI_PROPOSTA_INCOMPLETA")
    with conn.transaction():
        r = conn.execute(
            """INSERT INTO wms.ai_recommendations(provider, tipo, oggetto_ref, suggerimento, motivazione, dati_usati, affidabilita)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (provider, tipo, oggetto_ref, Jsonb(json.loads(json.dumps(suggerimento, default=str))), motivazione,
             Jsonb(json.loads(json.dumps(dati_usati, default=str))), Decimal(str(affidabilita)))).fetchone()
        conn.execute("""INSERT INTO wms.audit_logs(actor_type, actor_id, azione, entita, entita_id, dopo)
                        VALUES ('AI',%s,'PROPOSTA','AI_RECOMMENDATION',%s,%s)""",
                     (provider, str(r["id"]), Jsonb({"tipo": tipo})))
    return r["id"]


class WarehouseAssistant:
    def __init__(self, conn, provider: AIProvider | None = None):
        self.conn = conn
        self.provider = provider or UnavailableProvider()
        self.tools = ReadOnlyTools(conn)

    def ask(self, domanda: str) -> dict:
        tools = {"giacenze": self.tools.giacenze, "bobine_ferme": self.tools.bobine_ferme, "carenze": self.tools.carenze}
        return self.provider.complete(
            "Sei l'assistente di magazzino UltraPixel. Usa solo i dati degli strumenti. Non inventare quantità. "
            "Indica sempre dati usati e affidabilità. Non puoi eseguire movimenti.", domanda, tools)
