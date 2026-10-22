"""Errori di dominio. Il messaggio è in italiano ed è quello mostrato all'operatore."""


class WmsError(Exception):
    code = "ERRORE"
    http_status = 400

    def __init__(self, message: str, code: str | None = None, **details):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details

    def to_dict(self) -> dict:
        return {"esito": "ERRORE", "codice": self.code, "messaggio": self.message, "dettagli": self.details}


class BusinessRuleError(WmsError):
    """Operazione rifiutata da una regola di magazzino (nessuna scrittura avvenuta)."""
    code = "REGOLA"
    http_status = 409


class NotFound(WmsError):
    code = "NON_TROVATO"
    http_status = 404


class Forbidden(WmsError):
    code = "NON_AUTORIZZATO"
    http_status = 403


class IdempotencyConflict(WmsError):
    """Stesso event_id riusato con un contenuto diverso: è un errore del client, non un retry."""
    code = "EVENT_ID_RIUSATO"
    http_status = 409


class IntegrationAuthError(WmsError):
    code = "CREDENZIALI_INTEGRAZIONE"
    http_status = 502


class AIUnavailable(WmsError):
    code = "AI_NON_DISPONIBILE"
    http_status = 503
