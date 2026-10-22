"""Etichette interne (bobina, collo, ubicazione, spedizione) in HTML stampabile con barcode Code 128.

Formato di partenza: 35×30 mm con 3 mm di distanza, lo stesso già usato da "Etichette Anima" sulla
stampante di etichette esistente. Il modello di stampante non è noto: si stampa dal browser
(nessun driver ZPL ipotizzato). Il profilo è in wms.printer_profiles.
"""
from __future__ import annotations

import html
from decimal import Decimal

# Code 128: larghezze barra/spazio per i valori 0..106 (106 = stop)
_P = ("212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 "
      "113222 123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 "
      "212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 "
      "113123 113321 133121 313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 "
      "314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 "
      "241211 221114 413111 241112 134111 111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 "
      "214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412 211214 "
      "211232 2331112").split()
START_B = 104


def code128_widths(text: str) -> list[int]:
    """Codifica in Code Set B (ASCII 32-126). Ritorna la sequenza barra/spazio/barra... in moduli."""
    if not text or any(not 32 <= ord(c) <= 126 for c in text):
        raise ValueError("Code 128-B: solo caratteri ASCII stampabili")
    values = [START_B] + [ord(c) - 32 for c in text]
    check = (values[0] + sum(i * v for i, v in enumerate(values[1:], start=1))) % 103
    values += [check, 106]
    return [int(w) for v in values for w in _P[v]]


def code128_svg(text: str, height_mm: float = 9, quiet: int = 10) -> str:
    widths = code128_widths(text)
    total = sum(widths) + 2 * quiet
    x, rects = quiet, []
    for i, w in enumerate(widths):
        if i % 2 == 0:
            rects.append(f'<rect x="{x}" y="0" width="{w}" height="100"/>')
        x += w
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} 100" preserveAspectRatio="none" '
            f'style="width:100%;height:{height_mm}mm;display:block" shape-rendering="crispEdges">'
            f'<rect width="{total}" height="100" fill="#fff"/><g fill="#000">{"".join(rects)}</g></svg>')


def _fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, (Decimal, float)):
        return f"{Decimal(str(v)).normalize():f}".replace(".", ",")
    return html.escape(str(v))


def label_html(items: list[dict], w_mm=35, h_mm=30, gap_mm=3) -> str:
    """items: [{"barcode":..., "titolo":..., "righe":[...]}] → pagina HTML, una etichetta per pagina."""
    pages = []
    for it in items:
        righe = "".join(f"<div class=r>{r}</div>" for r in it.get("righe", []))
        pages.append(f"""<section class=lab><div class=t>{html.escape(it['titolo'])}</div>{righe}
          <div class=bc>{code128_svg(it['barcode'])}</div><div class=c>{html.escape(it['barcode'])}</div></section>""")
    return f"""<!doctype html><html lang=it><head><meta charset=utf-8><title>Etichette</title><style>
@page {{ size: {w_mm:g}mm {h_mm:g}mm; margin: 0 }}
*{{box-sizing:border-box}} body{{margin:0;font-family:Arial,Helvetica,sans-serif;color:#000;background:#fff}}
.lab{{width:{w_mm:g}mm;height:{h_mm:g}mm;padding:1.2mm 1.5mm;display:flex;flex-direction:column;gap:.3mm;
      page-break-after:always;break-after:page;overflow:hidden}}
.t{{font-weight:700;font-size:7.5pt;line-height:1.05;max-height:2.2em;overflow:hidden}}
.r{{font-size:6.2pt;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bc{{margin-top:auto}} .c{{font:700 8pt monospace;text-align:center;letter-spacing:.06em}}
@media screen{{body{{background:#ddd;padding:8px}} .lab{{background:#fff;margin:0 auto {gap_mm:g}mm;box-shadow:0 1px 3px #0003}}}}
</style></head><body>{''.join(pages)}<script>window.onload=()=>{{if(location.hash==='#stampa')window.print()}}</script>
</body></html>"""


def items_for(conn, tipo: str, ids: list) -> list[dict]:
    out = []
    for i in ids:
        if tipo == "bobina":
            r = conn.execute("""SELECT r.*, m.descrizione FROM wms.material_rolls r JOIN wms.materials m ON m.id=r.material_id
                                WHERE r.id=%s""", (i,)).fetchone()
            out.append({"barcode": r["barcode"], "titolo": r["descrizione"],
                        "righe": [f"{_fmt(r['larghezza_mm'])} mm × {_fmt(r['metri_residui'])} m",
                                  f"Lotto {_fmt(r['lotto_fornitore'])}", f"Ric. {r['data_ricezione']:%d/%m/%Y}"]})
        elif tipo == "collo":
            r = conn.execute("""SELECT p.*, l.codice AS lotto, fp.external_sku_id, fp.descrizione, j.cliente_nome
                                FROM wms.finished_goods_packages p JOIN wms.production_lots l ON l.id=p.lotto_id
                                JOIN wms.finished_products fp ON fp.id=l.finished_product_id
                                JOIN wms.production_jobs j ON j.id=l.production_job_id WHERE p.id=%s""", (i,)).fetchone()
            out.append({"barcode": r["barcode"], "titolo": f"Art. {r['external_sku_id']} — {r['descrizione'] or ''}",
                        "righe": [f"{r['quantita']} pz · lotto {html.escape(r['lotto'])}", html.escape(r["cliente_nome"])]})
        elif tipo == "ubicazione":
            r = conn.execute("SELECT * FROM wms.warehouse_locations WHERE id=%s", (i,)).fetchone()
            out.append({"barcode": r["barcode"], "titolo": f"Ubicazione {r['codice']}", "righe": [r["tipo"].title()]})
        elif tipo == "spedizione":
            r = conn.execute("SELECT * FROM wms.shipments WHERE id=%s", (i,)).fetchone()
            out.append({"barcode": r["barcode"], "titolo": f"Spedizione {r['cliente_nome']}",
                        "righe": [f"Ordine {_fmt(r['sales_order_id'])}"]})
        elif tipo == "badge":
            r = conn.execute("SELECT * FROM wms.users WHERE id=%s", (i,)).fetchone()
            out.append({"barcode": r["badge_code"], "titolo": r["display_name"], "righe": [r["role_code"].replace("_", " ").title()]})
    return out
