"""Da una proposta descritta in JSON (scritta dal modello) a etichetta, anteprime e file di stampa.
Il modello non esegue codice: descrive gli elementi e qui vengono disegnati con grafico.py. Tutto è validato e limitato.

Proposta:
{ "nome": "Erbario", "concetto": "...",
  "formato": {"w": 70, "h": 80, "forma": "round", "raggio": 3},
  "materiale": "carta_avorio_goffrata", "foil": "oro",
  "contenitore": {"tipo": "flacone", "colore": "ambra", "tappo": "disco", "d": 62, "h": 150},
  "elementi": [ ... vedi ELEMENTI ... ] }
"""
import math, re
from grafico import Label, contenitore, place, segno_e, forma, rr, f2, immagine, MATERIALI, FOIL
import ornamenti as O, botanica

FONT_OK = {"bodoni-moda", "playfair-display", "dm-serif-display", "cormorant-garamond", "eb-garamond", "fraunces", "cinzel", "archivo", "inter", "manrope", "zilla-slab", "pinyon-script"}
LIVELLI = {"stampa", "foil", "rilievo", "bianco", "vernice"}
FORME = {"rect", "round", "oval", "circle", "arch", "shield", "notch"}
CONT = {"bordolese", "borgognotta", "champagnotta", "flacone", "cilindro", "vaso", "lattina"}
COL = re.compile(r"^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$")
PATH = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9 ,.\-eE]{1,20000}$")

def num(v, lo, hi, default):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v)) if math.isfinite(v) else default

def col(v, default="#1B1F1D"):
    return v if isinstance(v, str) and COL.match(v) else default

def font(v):
    fam, *rest = (str(v or "archivo:400:normal") + "::").split(":")[:3]
    if fam not in FONT_OK:
        fam = "archivo"
    w = rest[0] if rest[0].isdigit() else "400"; st = "italic" if rest[1] == "italic" else "normal"
    return f"{fam}:{w}:{st}"

def strati(el):
    lv = el.get("livello", "stampa"); lv = lv if lv in LIVELLI else "stampa"
    out = [lv]
    if el.get("rilievo") and lv != "rilievo":
        out.append("rilievo")
    return out

def _put(L, livelli, svg_fill, colore):
    for lv in livelli:
        L.add(lv, svg_fill.replace("FILL", f' fill="{colore}"' if lv == "stampa" else ""))

def costruisci(p, logo=None):
    """p: dict proposta. logo: (data_url, rapporto w/h) o None. Restituisce (Label, avvisi, contenitore_kwargs)."""
    fm = p.get("formato") or {}; W = num(fm.get("w"), 20, 300, 90); H = num(fm.get("h"), 20, 300, 120)
    shape = fm.get("forma") if fm.get("forma") in FORME else "round"
    mat = p.get("materiale") if p.get("materiale") in MATERIALI else "carta_bianca_naturale"
    fo = p.get("foil") if p.get("foil") in FOIL else "oro"
    L = Label(W, H, shape=shape, raggio=num(fm.get("raggio"), 0, 20, 3) if "raggio" in fm else None, materiale=mat, foil=fo, nome=str(p.get("nome", "proposta"))[:60])
    avvisi, scatole, testi = [], [], []
    for i, el in enumerate((p.get("elementi") or [])[:80]):
        t = el.get("tipo"); c = col(el.get("colore")); lv = strati(el)
        try:
            if t == "testo":
                s = str(el.get("testo", ""))[:120]
                if not s.strip():
                    continue
                al = el.get("allinea") if el.get("allinea") in ("start", "middle", "end") else "start"
                size = num(el.get("corpo"), .8, 80, 4); x = num(el.get("x"), -5, W + 5, W / 2); y = num(el.get("y"), -5, H + 5, H / 2)
                mw = num(el.get("max_larghezza"), 1, 400, W - 6)
                testi.append((i, lv, font(el.get("font")), s, size, x, y, dict(anchor=al, track=num(el.get("spaziatura"), -.1, 1, 0), maxW=mw, colore=c)))
            elif t == "cornice":
                d = O.cornice(L, num(el.get("rientro"), 0, 30, 3), num(el.get("spessore"), .1, 5, .3),
                              doppia=(num(el["doppia"][0], .2, 10, 1), num(el["doppia"][1], .1, 5, .2)) if isinstance(el.get("doppia"), list) and len(el["doppia"]) == 2 else None)
                _put(L, lv, d.replace("<path ", "<path FILL "), c)
            elif t == "filetto":
                d = O.filetto(num(el.get("cx"), 0, W, W / 2), num(el.get("y"), 0, H, H / 2), num(el.get("mezza"), 1, 150, 12), num(el.get("spessore"), .1, 3, .28),
                              num(el.get("rombo"), 0, 5, 1.1) if el.get("rombo", True) else 0)
                _put(L, lv, d.replace("<path ", "<path FILL "), c)
            elif t == "rettangolo":
                x, y, w, h = (num(el.get(k), -5, 320, 0) for k in ("x", "y", "w", "h"))
                _put(L, lv, f'<path FILL d="{rr(x, y, w, h, num(el.get("r"), 0, 50, 0))}"/>', c)
            elif t == "cerchio":
                cx, cy, r = num(el.get("cx"), -5, W + 5, W / 2), num(el.get("cy"), -5, H + 5, H / 2), num(el.get("r"), .2, 150, 5)
                d = f"M{f2(cx-r)} {f2(cy)}a{f2(r)} {f2(r)} 0 1 0 {f2(2*r)} 0a{f2(r)} {f2(r)} 0 1 0 {f2(-2*r)} 0Z"
                if el.get("spessore"):
                    r2_ = max(.1, r - num(el.get("spessore"), .1, r, .3)); d += f"M{f2(cx-r2_)} {f2(cy)}a{f2(r2_)} {f2(r2_)} 0 1 0 {f2(2*r2_)} 0a{f2(r2_)} {f2(r2_)} 0 1 0 {f2(-2*r2_)} 0Z"
                _put(L, lv, f'<path FILL d="{d}" fill-rule="evenodd"/>', c)
            elif t == "monogramma":
                cx, cy, r = num(el.get("cx"), 0, W, W / 2), num(el.get("cy"), 0, H, H / 3), num(el.get("r"), 2, 60, 8)
                d = "".join(f"M{f2(cx-q)} {f2(cy)}a{f2(q)} {f2(q)} 0 1 0 {f2(2*q)} 0a{f2(q)} {f2(q)} 0 1 0 {f2(-2*q)} 0Z" for q in (r, r * .93, r * .86, r * .83))
                _put(L, lv, f'<path FILL d="{d}" fill-rule="evenodd"/>', c)
                testi.append((i, lv, font(el.get("font") or "cormorant-garamond:600:normal"), str(el.get("lettere", "AB"))[:4], r, cx, cy + r * .34, dict(anchor="middle", track=.02, maxW=r * 1.5, colore=c)))
            elif t == "illustrazione":
                bx, by, bw, bh = [num(v, -5, 320, d) for v, d in zip((el.get("box") or [0, 0, W, H])[:4], (0, 0, W, H))]
                kind = el.get("soggetto", "rametto")
                if kind in ("rametto", "rosmarino", "lavanda", "olivo", "timo", "alloro"):
                    pianta = kind if kind != "rametto" else el.get("pianta", "rosmarino")
                    B = botanica.livelli("single" if el.get("singolo") else "full", seed=int(num(el.get("seme"), 1, 999, 7)), fiore=col(el.get("colore_fiori"), "#9FAEEB"),
                                         gola=col(el.get("colore_fiori_scuro"), "#6C7BD0"), inchiostro=c, pianta=pianta, frutto=col(el.get("colore_frutti"), "#3F4A2A"))
                    if lv[0] == "stampa":
                        L.add("stampa", place(("" if el.get("senza_colore") else B["colore"]) + B["tratto"], bx, by, bw, bh, botanica.VB))
                    else:   # foil/rilievo/bianco: masse piene (i tratti fini non reggono la lavorazione)
                        L.add(lv[0], place(B["masse"], bx, by, bw, bh, botanica.VB))
                        if el.get("fiori_stampati", True) and lv[0] == "rilievo":
                            L.add("stampa", place(B["colore_piatto"], bx, by, bw, bh, botanica.VB))
                    if "rilievo" in lv[1:]:
                        L.add("rilievo", place(B["masse"], bx, by, bw, bh, botanica.VB))
                elif kind == "colline":
                    L.add("stampa", f'<g stroke="{c}">{O.colline(bx, by, bw, bh, strati=int(num(el.get("strati"), 2, 6, 4)), seed=int(num(el.get("seme"), 1, 999, 5)))}</g>')
                elif kind == "onde":
                    n = int(num(el.get("righe"), 1, 8, 3))
                    g = "".join(O.onda(bx, by + bh * k / max(1, n), bw, num(el.get("ampiezza"), .1, 10, .8), num(el.get("periodi"), .5, 20, 4), num(el.get("spessore"), .1, 2, .25)) for k in range(n))
                    _put(L, lv, g.replace("<path ", "<path FILL "), c)
                else:
                    avvisi.append(f"elemento {i}: soggetto '{kind}' non disponibile (usa rametto, colline, onde o un disegno 'vettoriale')")
            elif t == "vettoriale":   # disegno libero del modello: solo tracciati, ripuliti
                vb = el.get("viewBox") or [0, 0, 100, 100]
                vb = [num(v, -10000, 10000, d) for v, d in zip(vb[:4], (0, 0, 100, 100))]
                if vb[2] <= 0 or vb[3] <= 0:
                    raise ValueError("viewBox")
                parts = []
                for sh in (el.get("tracciati") or [])[:200]:
                    d = str(sh.get("d", ""))
                    if not PATH.match(d):
                        continue
                    sw = sh.get("tratto")
                    if sw:
                        parts.append(f'<path d="{d}" fill="none" stroke="{col(sh.get("colore"), c)}" stroke-width="{f2(num(sw, .05, 50, 1))}" stroke-linecap="round" stroke-linejoin="round"/>')
                    else:
                        parts.append(f'<path d="{d}"' + (f' fill="{col(sh.get("colore"), c)}"' if lv[0] == "stampa" else "") + (' fill-rule="evenodd"' if sh.get("evenodd") else "") + "/>")
                bx, by, bw, bh = [num(v, -5, 320, d) for v, d in zip((el.get("box") or [0, 0, W, H])[:4], (0, 0, W, H))]
                g = place("".join(parts), bx, by, bw, bh, vb)
                for l_ in lv:
                    L.add(l_, g if l_ == "stampa" else re.sub(r' fill="#[0-9a-fA-F]+"', "", g))
                scatole.append((i, "disegno", bx, by, bx + bw, by + bh))
            elif t == "logo":
                if not logo:
                    avvisi.append(f"elemento {i}: il cliente non ha caricato un logo (usa un monogramma o il nome in testo)")
                    continue
                url, ratio = logo; bx, by, bw, bh = [num(v, -5, 320, d) for v, d in zip((el.get("box") or [W * .3, 5, W * .4, H * .2])[:4], (W * .3, 5, W * .4, H * .2))]
                lw, lh = (bw, bw / ratio) if bw / ratio <= bh else (bh * ratio, bh); x, y = bx + (bw - lw) / 2, by + (bh - lh) / 2
                mono = el.get("modo") == "monocromo" or lv[0] != "stampa"
                dd, body = immagine(url, x, y, lw, lh, colore=(c if lv[0] == "stampa" else "livello") if mono else None, maschera_id=f"@lg{i}")
                if dd:
                    L.defs_add(dd)
                for l_ in lv:
                    if l_ == "stampa":
                        L.add("stampa", body)
                    else:
                        L.add(l_, immagine(url, x, y, lw, lh, colore="livello", maschera_id=f"@lg{i}")[1])
                scatole.append((i, "logo", x, y, x + lw, y + lh))
            elif t == "quantita":   # "250 ml ℮" con il segno corretto
                x = num(el.get("x"), 0, W, W - 6); y = num(el.get("y"), 0, H, H - 5); size = num(el.get("corpo"), .8, 20, 2.4)
                testi.append((i, lv, font(el.get("font")), str(el.get("testo", "250 ml"))[:20], size, x, y, dict(anchor="end", track=num(el.get("spaziatura"), 0, 1, .04), maxW=W, colore=c, _e=True)))
            else:
                avvisi.append(f"elemento {i}: tipo '{t}' sconosciuto")
        except Exception as ex:   # un elemento sbagliato non blocca la proposta
            avvisi.append(f"elemento {i} ({t}): non disegnato ({type(ex).__name__})")
    # testi in un'unica chiamata
    if testi:
        items = []
        for i, lv, fnt, s, size, x, y, o in testi:
            eo = o.pop("_e", False)
            if eo:
                o["anchor"] = "end"; x = x - size * .9
            items.append((i, lv, fnt, s, size, x, y, o, eo))
        res = L.testi([(lv[0], fnt, s, size, x, y, o) for i, lv, fnt, s, size, x, y, o, eo in items])
        for (i, lv, fnt, s, size, x, y, o, eo), r in zip(items, res):
            for extra in lv[1:]:
                L.add(extra, f'<path d="{r["d"]}"/>')
            x0 = x - r["w"] / 2 if o["anchor"] == "middle" else x - r["w"] if o["anchor"] == "end" else x
            scatole.append((i, f"testo '{s[:24]}'", x0, y - r["size"] * .72, x0 + r["w"], y + r["size"] * .2))
            if r["size"] < size * .98:
                avvisi.append(f"elemento {i}: testo '{s[:30]}' ridotto da {size:.1f} a {r['size']:.1f} mm per stare in {o['maxW']:.0f} mm")
            if r["size"] * .72 < 1.0:
                avvisi.append(f"elemento {i}: testo '{s[:30]}' alto meno di 1 mm: illeggibile o non stampabile")
            if eo:
                svg, _ = segno_e(x + r["size"] * .25, y, r["size"], o["colore"])
                L.add(lv[0], svg if lv[0] == "stampa" else re.sub(r'stroke="[^"]+"', 'stroke="#000"', svg))
    # controlli di impaginazione
    m = 2
    for i, what, x0, y0, x1, y1 in scatole:
        if x0 < m - .01 or y0 < m - .01 or x1 > W - m + .01 or y1 > H - m + .01:
            avvisi.append(f"elemento {i}: {what} esce dal margine di sicurezza di 2 mm ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) su {W:.0f}×{H:.0f}")
        if shape in ("oval", "circle"):
            for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                if ((px - W / 2) / (W / 2 - m)) ** 2 + ((py - H / 2) / (H / 2 - m)) ** 2 > 1.0:
                    avvisi.append(f"elemento {i}: {what} esce dall'ovale"); break
    for a in range(len(scatole)):
        for b in range(a + 1, len(scatole)):
            i, wa, ax0, ay0, ax1, ay1 = scatole[a]; j, wb, bx0, by0, bx1, by1 = scatole[b]
            ov = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
            if "disegno" in (wa, wb) and not (wa.startswith("testo") or wb.startswith("testo")):
                continue
            if ov[0] > .3 and ov[1] > .3:
                avvisi.append(f"elementi {i} e {j}: {wa} e {wb} si sovrappongono")
    ck = p.get("contenitore") or {}
    kw = dict(tipo=ck.get("tipo") if ck.get("tipo") in CONT else "bordolese", colore=ck.get("colore") if ck.get("colore") in ("verde", "ambra", "nero", "trasparente", "bianco", "blu") else None,
              tappo=ck.get("tappo") if ck.get("tappo") in ("disco", "pompa", "coperchio", "sughero", "capsula") else None,
              d=num(ck.get("d"), 20, 200, 0) or None, h=num(ck.get("h"), 30, 400, 0) or None, liquido=col(ck.get("liquido"), None) if ck.get("liquido") else None)
    if kw["d"] and W > math.pi * kw["d"] * .55:
        avvisi.append(f"formato: {W:.0f} mm di larghezza coprono più di metà del contenitore (Ø {kw['d']:.0f} mm)")
    return L, avvisi[:30], kw

def anteprime(p, logo=None, k="P"):
    """{'contenitore': svg, 'piatta': svg, 'stampa': svg file, 'spec': [...], 'avvisi': [...]}"""
    L, avvisi, kw = costruisci(p, logo)
    tipo = kw.pop("tipo")
    if tipo in ("bordolese", "borgognotta", "champagnotta") and kw.get("tappo") in ("disco", "pompa", "coperchio"):
        kw["tappo"] = None
    if tipo in ("bordolese", "borgognotta", "champagnotta") and kw.get("tappo") in ("sughero", "capsula"):
        kw["tappo"] = None
    return {"contenitore": contenitore(tipo, L, k=k, **kw), "piatta": L.piatta(k=k + "f", quote=True), "stampa": L.file_stampa(),
            "spec": L.spec(), "avvisi": avvisi, "separazioni": L.separazioni()}
