import os
import pathlib
import sys
import uuid

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wms import db as wdb  # noqa: E402
from wms import engine, ledger, madiwor, seed  # noqa: E402,F401
from wms.engine import Actor  # noqa: E402

DSN = os.environ.get("WMS_TEST_DATABASE_URL", "host=/tmp port=5433 user=postgres dbname=wms_test")


def _reset(conn):
    conn.execute("DROP SCHEMA IF EXISTS wms CASCADE")
    conn.execute("DROP TABLE IF EXISTS public.wms_schema_migrations")
    wdb.apply_migrations(conn)


@pytest.fixture
def conn():
    c = wdb.connect(DSN)
    _reset(c)
    yield c
    problems = ledger.verify(c)
    c.close()
    assert not problems, "Registro e giacenze non coincidono:\n" + "\n".join(problems)


@pytest.fixture
def ids(conn):
    return seed.seed_master(conn)


def make_actor(conn, ids, username="op.produzione", device="Postazione Xeikon", fonte="SCANNER") -> Actor:
    u = conn.execute("SELECT u.id, u.role_code, r.livello FROM wms.users u JOIN wms.roles r ON r.code=u.role_code "
                     "WHERE username=%s", (username,)).fetchone()
    d = conn.execute("SELECT * FROM wms.devices WHERE id=%s", (ids["devices"][device],)).fetchone()
    return Actor(user_id=u["id"], role_code=u["role_code"], role_level=u["livello"], device_id=d["id"],
                 postazione=d["postazione"], device_location_id=d["location_id"], fonte=fonte)


@pytest.fixture
def actors(conn, ids):
    return {
        "prod": make_actor(conn, ids),
        "prod2": make_actor(conn, ids, "op.produzione2", "Postazione Xeikon (2)"),
        "ric": make_actor(conn, ids, "op.produzione", "Postazione ricevimento"),
        "mag": make_actor(conn, ids, "op.produzione", "Postazione magazzino"),
        "sped": make_actor(conn, ids, "op.spedizione", "Postazione spedizione"),
        "resp": make_actor(conn, ids, "resp.magazzino", "Postazione magazzino"),
    }


def ev():
    return uuid.uuid4()


def run(conn, actor, cmd, payload, event_id=None):
    return engine.execute(conn, actor, event_id or ev(), cmd, payload)


def receive(conn, actors, ids, metri, larghezza=170, mat="EPIQUE-FSC-S2047N", n=1, **kw):
    r = run(conn, actors["ric"], "RICEVI_BOBINA",
            {"material_id": str(ids["mat"][mat]), "larghezza_mm": larghezza, "metri": metri, "numero_bobine": n, **kw})
    return r["bobine"]
