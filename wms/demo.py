"""Istanza di PROVA: dati dimostrativi e postazioni con token noti. Si attiva SOLO con WMS_DEMO=1
e solo su un database vuoto: non va mai usata sul database di produzione."""
from __future__ import annotations

import uuid

from . import engine, madiwor, seed

POSTAZIONI = {
    "Postazione ricevimento": "demo-ricevimento",
    "Postazione magazzino": "demo-magazzino",
    "Postazione Xeikon": "demo-xeikon",
    "Postazione Xeikon (2)": "demo-xeikon-2",
    "Postazione spedizione": "demo-spedizione",
}


def single_operator(conn):
    """Un solo operatore al momento: tutte le postazioni lavorano a suo nome, senza badge."""
    u = conn.execute("SELECT id FROM wms.users WHERE username='operatore'").fetchone()
    if not u:
        u = conn.execute("""INSERT INTO wms.users(username, display_name, role_code)
                            VALUES ('operatore','Operatore','RESPONSABILE_MAGAZZINO') RETURNING id""").fetchone()
    conn.execute("UPDATE wms.devices SET utente_predefinito=%s WHERE utente_predefinito IS NULL", (u["id"],))


def bootstrap(conn) -> bool:
    if conn.execute("SELECT count(*) n FROM wms.users").fetchone()["n"] > 0:
        single_operator(conn)
        return False
    ids = seed.seed_master(conn, fixed_tokens=POSTAZIONI)

    def actor(username, device):
        u = conn.execute("SELECT u.id, u.role_code, r.livello FROM wms.users u JOIN wms.roles r ON r.code=u.role_code "
                         "WHERE username=%s", (username,)).fetchone()
        d = conn.execute("SELECT * FROM wms.devices WHERE id=%s", (ids["devices"][device],)).fetchone()
        return engine.Actor(u["id"], u["role_code"], u["livello"], d["id"], d["postazione"], d["location_id"], "UI")

    ric = actor("op.produzione", "Postazione ricevimento")
    resp = actor("resp.magazzino", "Postazione magazzino")
    epique = str(ids["mat"]["EPIQUE-FSC-S2047N"])
    for metri in (40, 75, 300):
        engine.execute(conn, ric, uuid.uuid4(), "RICEVI_BOBINA", {"material_id": epique, "larghezza_mm": 170, "metri": metri})
    engine.execute(conn, ric, uuid.uuid4(), "RICEVI_BOBINA",
                   {"material_id": str(ids["mat"]["MATT-WINE-FSC"]), "larghezza_mm": 170, "metri": 200})
    engine.execute(conn, ric, uuid.uuid4(), "RICEVI_BOBINA", {"material_id": epique, "larghezza_mm": 330, "metri": 500})
    engine.execute(conn, resp, uuid.uuid4(), "ASSOCIA_CODICE", {"code": "AA335", "material_id": epique})
    engine.execute(conn, resp, uuid.uuid4(), "ASSOCIA_CODICE",
                   {"code": "08012345678907", "namespace": "GTIN", "material_id": epique})
    madiwor.import_job(conn, seed.load_job_fixture(), "FIXTURE")
    single_operator(conn)
    return True


def page(conn) -> str:
    from .labels import code128_svg
    rolls = conn.execute("""SELECT r.barcode, m.descrizione, r.larghezza_mm, r.metri_residui, r.stato
                            FROM wms.material_rolls r JOIN wms.materials m ON m.id=r.material_id ORDER BY r.barcode""").fetchall()
    locs = conn.execute("SELECT barcode, codice FROM wms.warehouse_locations ORDER BY codice").fetchall()
    pk = conn.execute("SELECT barcode, quantita, stato FROM wms.finished_goods_packages ORDER BY barcode").fetchall()
    sh = conn.execute("SELECT barcode, cliente_nome, stato FROM wms.shipments ORDER BY barcode").fetchall()

    def card(code, title, sub=""):
        return (f'<div class=c><div class=t>{title}</div><div class=s>{sub}</div>{code128_svg(code, 10)}'
                f'<button onclick="copy(this)" data-c="{code}">{code}</button></div>')
    sec = lambda t, cards: f"<h2>{t}</h2><div class=g>{''.join(cards)}</div>"  # noqa: E731
    post = "".join(f'<a class=p href="#" onclick="go(\'{tok}\')">{n}</a>' for n, tok in POSTAZIONI.items())
    return f"""<!doctype html><html lang=it><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Prova scanner</title><style>
body{{font:16px system-ui;margin:0;background:#f3f5f9;color:#16213b}} main{{max-width:1100px;margin:auto;padding:20px}}
h1{{margin:0 0 4px}} h2{{margin:28px 0 8px;font-size:18px}} .note{{background:#fff4e0;padding:10px 14px;border-radius:10px}}
.p{{display:inline-block;margin:6px 8px 0 0;padding:12px 16px;background:#2f6feb;color:#fff;border-radius:10px;text-decoration:none;font-weight:700}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}}
.c{{background:#fff;border-radius:10px;padding:10px;border:1px solid #e7eaf2}} .t{{font-weight:700;font-size:14px}} .s{{font-size:12px;color:#5b6b85;min-height:1.2em}}
button{{margin-top:6px;width:100%;font:700 14px monospace;padding:6px;border:1px solid #d3dae8;border-radius:8px;background:#e8f0fe;cursor:pointer}}
ol li{{margin:4px 0}}
</style></head><body><main>
<h1>Istanza di prova — Smart Warehouse</h1>
<p class=note>Dati finti su un database di prova separato (scade il 21/11/2026). Niente qui tocca il magazzino reale.
Se hai una pistola, leggi i codici dallo schermo; altrimenti clicca un codice per copiarlo, incollalo nel campo e premi Invio.</p>
<h2>1. Scegli la postazione</h2>{post}
<h2>Percorso consigliato (postazione Xeikon)</h2><ol>
<li>Commessa <b>4515</b> → mostra fabbisogno e bobina prenotata</li>
<li><b>UPR000004</b> (materiale sbagliato) → bloccata · <b>UPR000005</b> (330 mm) → bloccata</li>
<li><b>UPR000002</b> → montata · dopo qualche secondo rileggila → chiede i metri residui</li>
<li>Postazione magazzino: <b>UPLA0101</b> poi più bobine → stoccaggio a raffica · F8 annulla l'ultima</li>
<li>Postazione ricevimento: <b>AA335</b> → chiede solo i metri · etichetta GS1 sotto → metri e lotto già letti, scrivi solo la larghezza (170) e Invio, poi scansiona un'ubicazione</li></ol>
{sec("Commesse e codici fornitore", [card("4515", "Commessa 4515", "Cacovich · 650 pz"), card("AA335", "Codice fornitore EPIQUE", "identifica solo l'articolo"),
    card("01" + "08012345678907" + "3111005000" + "10LOTDEMO", "Etichetta GS1 fornitore", "EPIQUE · 500 m · lotto LOTDEMO")])}
{sec("Bobine", [card(r["barcode"], r["descrizione"], f"{r['larghezza_mm']:g} mm · {r['metri_residui']:g} m · {r['stato'].lower()}") for r in rolls])}
{sec("Ubicazioni", [card(l["barcode"], l["codice"]) for l in locs])}
{sec("Colli e spedizioni", [card(p["barcode"], "Collo", f"{p['quantita']} pz · {p['stato'].lower()}") for p in pk]
    + [card(s["barcode"], "Spedizione", s["cliente_nome"]) for s in sh]) if (pk or sh) else ""}
</main><script>
function go(t){{localStorage.setItem('wms.device',JSON.stringify(t));localStorage.removeItem('wms.session');location.href='/';}}
function copy(b){{navigator.clipboard&&navigator.clipboard.writeText(b.dataset.c);b.textContent='copiato ✓';setTimeout(()=>b.textContent=b.dataset.c,1200);}}
</script></body></html>"""
