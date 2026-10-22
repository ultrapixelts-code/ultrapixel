"""Autenticazione: token dispositivo + sessione operatore. Permessi verificati sempre lato server."""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os
import secrets

from .engine import Actor
from .errors import Forbidden

SESSION_HOURS = 12


def sha(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_pin(pin: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 200_000)
    return salt.hex() + "$" + dk.hex()


def check_pin(pin: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, dk = stored.split("$", 1)
    return hmac.compare_digest(hash_pin(pin, bytes.fromhex(salt)).split("$", 1)[1], dk)


def create_device(conn, nome: str, postazione: str, location_id=None) -> tuple[dict, str]:
    token = secrets.token_urlsafe(32)
    d = conn.execute("""INSERT INTO wms.devices(nome, postazione, location_id, token_hash) VALUES (%s,%s,%s,%s)
                        RETURNING *""", (nome, postazione, location_id, sha(token))).fetchone()
    return d, token


def device_from_token(conn, token: str | None) -> dict:
    if not token:
        raise Forbidden("Dispositivo non registrato", code="DISPOSITIVO_SCONOSCIUTO")
    d = conn.execute("SELECT * FROM wms.devices WHERE token_hash=%s AND active", (sha(token),)).fetchone()
    if not d:
        raise Forbidden("Dispositivo non registrato", code="DISPOSITIVO_SCONOSCIUTO")
    return d


def login(conn, device: dict, *, badge: str | None = None, username: str | None = None, pin: str | None = None) -> str:
    if badge:
        u = conn.execute("SELECT * FROM wms.users WHERE badge_code=%s AND active", (badge,)).fetchone()
    else:
        u = conn.execute("SELECT * FROM wms.users WHERE username=%s AND active", (username,)).fetchone()
        if u and not check_pin(pin or "", u["pin_hash"]):
            u = None
    if not u:
        raise Forbidden("Credenziali non valide", code="LOGIN_FALLITO")
    token = secrets.token_urlsafe(32)
    with conn.transaction():
        conn.execute("""INSERT INTO wms.sessions(token_hash, user_id, device_id, expires_at) VALUES (%s,%s,%s,%s)""",
                     (sha(token), u["id"], device["id"], dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=SESSION_HOURS)))
        conn.execute("""INSERT INTO wms.audit_logs(actor_type, actor_id, azione, entita, entita_id)
                        VALUES ('UTENTE',%s,'LOGIN','DEVICE',%s)""", (str(u["id"]), str(device["id"])))
    return token


def actor_from_session(conn, device: dict, session_token: str | None, *, fonte="SCANNER", offline=False,
                       client_ts=None) -> Actor:
    if not session_token:
        raise Forbidden("Accesso richiesto: scansiona il tuo badge", code="LOGIN_RICHIESTO")
    s = conn.execute(
        """SELECT u.id, u.role_code, r.livello FROM wms.sessions s JOIN wms.users u ON u.id=s.user_id
           JOIN wms.roles r ON r.code=u.role_code
           WHERE s.token_hash=%s AND s.device_id=%s AND s.expires_at > now() AND u.active""",
        (sha(session_token), device["id"])).fetchone()
    if not s:
        raise Forbidden("Sessione scaduta: scansiona il tuo badge", code="LOGIN_RICHIESTO")
    return Actor(user_id=s["id"], role_code=s["role_code"], role_level=s["livello"], device_id=device["id"],
                 postazione=device["postazione"], device_location_id=device["location_id"], fonte=fonte,
                 offline=offline, client_ts=client_ts)
