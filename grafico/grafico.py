"""UltraPixel — strumenti del grafico AI.

Un'etichetta è disegnata in millimetri, origine in alto a sinistra del formato finito, su livelli separati:
  stampa   CMYK (anche immagini)          bianco   inchiostro bianco (film trasparenti, carte colorate)
  foil     foil a caldo                     rilievo  embossing / rilievo a secco
  vernice  vernice selettiva serigrafica   (la fustella e l'abbondanza le aggiunge l'etichetta)
Da qui escono: anteprima piatta, anteprima sul contenitore, separazioni per livello, file di stampa SVG a livelli.

    from grafico import Label, render
    L = Label(90, 120, shape="round", materiale="carta_avorio_goffrata")
    L.testo("stampa", "bodoni-moda:500:normal", "TENUTA", 9, 45, 30, anchor="middle", colore="#1b1b1b")
    L.add("foil", '<path d="…"/>', ); L.foil_colore = "oro"
    open("piatta.svg", "w").write(L.piatta())
    open("bottiglia.svg", "w").write(contenitore("bordolese", L))
    render(["piatta.svg"], "controllo.png")
"""
import html, json, math, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
esc = html.escape
f2 = lambda v: f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)

# ---------------------------------------------------------------- testi in tracciati
def testi(reqs):
    """reqs: lista di dict {font, text, size, x, y, anchor, track, maxW} -> lista di {d, w, size}. Una sola chiamata a node."""
    out = subprocess.run(["node", os.path.join(HERE, "text.js")], input=json.dumps(reqs), capture_output=True, text=True, cwd=HERE)
    if out.returncode:
        raise RuntimeError(out.stderr.strip()[-500:])
    return json.loads(out.stdout)

# ---------------------------------------------------------------- materiali, foil
MATERIALI = {   # aspetto in anteprima. tipo carta/film; tex = grana (frequenza, opacità)
    "carta_avorio_goffrata": {"bg": "#F2EADA", "tex": (3.0, .34), "tipo": "carta", "nome": "Carta avorio goffrata (feltro)"},
    "carta_bianca_goffrata": {"bg": "#F6F4EE", "tex": (3.2, .3), "tipo": "carta", "nome": "Carta bianca goffrata"},
    "carta_crema_liscia": {"bg": "#F3ECDC", "tex": (5, .12), "tipo": "carta", "nome": "Carta crema liscia"},
    "carta_bianca_naturale": {"bg": "#F8F7F2", "tex": (4.5, .16), "tipo": "carta", "nome": "Carta bianca naturale non patinata"},
    "carta_bianca_patinata": {"bg": "#FDFDFC", "tex": None, "tipo": "carta", "nome": "Carta bianca patinata"},
    "carta_cotone": {"bg": "#EFEBE1", "tex": (2.4, .38), "tipo": "carta", "nome": "Carta cotone spessa (per rilievo profondo)"},
    "carta_kraft": {"bg": "#C9A97E", "tex": (2.6, .4), "tipo": "carta", "nome": "Carta kraft"},
    "carta_nera": {"bg": "#1E1D1C", "tex": (3, .22), "tipo": "carta", "nome": "Carta nera in pasta"},
    "film_bianco": {"bg": "#FBFBFB", "tex": None, "tipo": "film", "nome": "Film PP bianco"},
    "film_trasparente": {"bg": None, "tex": None, "tipo": "film", "nome": "Film PP trasparente"},
    "film_argento": {"bg": "#C9CDD0", "tex": None, "tipo": "film", "metal": True, "nome": "Film PP argento metallizzato"},
}
FOIL = {"oro": ["#7d5d1a", "#c9a54a", "#fff1b8", "#b8902f", "#6f5216"], "argento": ["#6d7377", "#c4c9cc", "#ffffff", "#a3a9ad", "#5c6266"],
        "rame": ["#6b3a1f", "#b8683d", "#ffd2b0", "#a2552d", "#5a2f18"], "oro_rosa": ["#8a5a4a", "#d9a08c", "#ffe1d6", "#c08572", "#7a4b3d"],
        "nero_lucido": ["#000", "#2b2b2b", "#6a6a6a", "#1a1a1a", "#000"], "blu": ["#14315c", "#3e6db3", "#a9c6f0", "#2d548f", "#102748"]}
FOIL_FLAT = {"oro": "#C9A54A", "argento": "#B9BEC2", "rame": "#B8683D", "oro_rosa": "#D29C88", "nero_lucido": "#111", "blu": "#3E6DB3"}

# ---------------------------------------------------------------- forme di fustella
def rr(x, y, w, h, r):
    r = max(0, min(r, w / 2, h / 2)); F = f2
    if not r:
        return f"M{F(x)} {F(y)}H{F(x+w)}V{F(y+h)}H{F(x)}Z"
    return (f"M{F(x+r)} {F(y)}H{F(x+w-r)}A{F(r)} {F(r)} 0 0 1 {F(x+w)} {F(y+r)}V{F(y+h-r)}A{F(r)} {F(r)} 0 0 1 {F(x+w-r)} {F(y+h)}"
            f"H{F(x+r)}A{F(r)} {F(r)} 0 0 1 {F(x)} {F(y+h-r)}V{F(y+r)}A{F(r)} {F(r)} 0 0 1 {F(x+r)} {F(y)}Z")

def forma(shape, w, h, i=0, r=None):
    """Contorno della fustella (i=0) o una linea rientrata di i mm. shape: rect, round, oval, circle, arch, shield, notch."""
    F = f2
    if shape in ("oval", "circle"):
        rx, ry = w / 2 - i, h / 2 - i
        return f"M{F(w/2-rx)} {F(h/2)}A{F(rx)} {F(ry)} 0 1 0 {F(w/2+rx)} {F(h/2)}A{F(rx)} {F(ry)} 0 1 0 {F(w/2-rx)} {F(h/2)}Z"
    if shape == "arch":
        R = min(w * .22, h * .2)
        return f"M{F(i)} {F(h-i)}V{F(R)}A{F(w/2-i)} {F(max(.5, R-i*.6))} 0 0 1 {F(w-i)} {F(R)}V{F(h-i)}Z"
    if shape == "shield":   # dritta sopra, punta arrotondata sotto
        R = min(w * .3, h * .25)
        return f"M{F(i)} {F(i)}H{F(w-i)}V{F(h-R)}Q{F(w-i)} {F(h-i)} {F(w/2)} {F(h-i)}Q{F(i)} {F(h-i)} {F(i)} {F(h-R)}Z"
    if shape == "notch":    # angoli smussati verso l'interno
        c = min(w, h) * .07 - i * .3
        return (f"M{F(i+c)} {F(i)}H{F(w-i-c)}A{F(c)} {F(c)} 0 0 0 {F(w-i)} {F(i+c)}V{F(h-i-c)}A{F(c)} {F(c)} 0 0 0 {F(w-i-c)} {F(h-i)}"
                f"H{F(i+c)}A{F(c)} {F(c)} 0 0 0 {F(i)} {F(h-i-c)}V{F(i+c)}A{F(c)} {F(c)} 0 0 0 {F(i+c)} {F(i)}Z")
    rad = r if r is not None else (6 if shape == "round" else 1.2)
    return rr(i, i, w - 2 * i, h - 2 * i, rad - i)

# ---------------------------------------------------------------- etichetta
LIVELLI = ("stampa", "bianco", "foil", "rilievo", "vernice")
SPOT = {"bianco": "#FFFFFF", "foil": "#E3A21A", "rilievo": "#6F5BE8", "vernice": "#22B8D6"}

class Label:
    def __init__(self, w, h, shape="round", raggio=None, abbondanza=2, materiale="carta_bianca_naturale", foil="oro", nome="etichetta"):
        self.w, self.h, self.shape, self.raggio, self.b = w, h, shape, raggio, abbondanza
        self.materiale, self.foil_colore, self.nome = materiale, foil, nome
        self.L = {k: [] for k in LIVELLI}
        self.defs = []       # defs condivisi dai livelli (maschere, gradienti del disegno)
        self.note = []       # righe per la specifica tecnica

    # contenuto
    def add(self, livello, svg):
        self.L[livello].append(svg); return self
    def defs_add(self, svg):
        self.defs.append(svg); return self
    def testo(self, livello, font, text, size, x, y, anchor="start", track=0, maxW=None, colore="#1B1F1D"):
        r = testi([dict(font=font, text=text, size=size, x=x, y=y, anchor=anchor, track=track, maxW=maxW)])[0]
        self.add(livello, f'<path d="{r["d"]}"' + (f' fill="{colore}"' if livello == "stampa" else "") + "/>")
        return r
    def testi(self, items):
        """items: lista di (livello, font, text, size, x, y, {anchor, track, maxW, colore}) in una sola chiamata."""
        res = testi([dict(font=f, text=t, size=s, x=x, y=y, **{k: v for k, v in o.items() if k != "colore"}) for _, f, t, s, x, y, o in items])
        for (lv, *_rest, o), r in zip(items, res):
            self.add(lv, f'<path d="{r["d"]}"' + (f' fill="{o.get("colore", "#1B1F1D")}"' if lv == "stampa" else "") + "/>")
        return res
    def fustella(self, i=0):
        return forma(self.shape, self.w, self.h, i, self.raggio)

    # rendering
    def _defs(self, k, live):
        m = MATERIALI[self.materiale]; fo = FOIL.get(self.foil_colore, FOIL["oro"]); W, H = self.w, self.h
        g = (f'<linearGradient id="{k}foil" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{f2(W)}" y2="{f2(H*.6)}">' +
             "".join(f'<stop offset="{i/(len(fo)-1):.2f}" stop-color="{c}"/>' for i, c in enumerate(fo)) + "</linearGradient>")
        emb = (f'<filter id="{k}emb" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur in="SourceAlpha" stdDeviation=".16" result="b"/>'
               '<feOffset in="b" dx="-.2" dy="-.2" result="h0"/><feComposite in="h0" in2="SourceAlpha" operator="out" result="h1"/><feFlood flood-color="#fff" flood-opacity=".95"/><feComposite in2="h1" operator="in" result="hi"/>'
               '<feOffset in="b" dx=".24" dy=".24" result="s0"/><feComposite in="s0" in2="SourceAlpha" operator="out" result="s1"/><feFlood flood-color="#3c3222" flood-opacity=".5"/><feComposite in2="s1" operator="in" result="sh"/>'
               '<feMerge><feMergeNode in="sh"/><feMergeNode in="hi"/></feMerge></filter>')
        tex = ""
        if m["tex"]:
            fq, op = m["tex"]; dark = m["bg"] and int(m["bg"][1:3], 16) < 90
            tex = (f'<filter id="{k}tex" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="{fq}" numOctaves="3" seed="4"/>'
                   + ('<feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 -1.4 .9"/>' if dark else '<feColorMatrix values="0 0 0 0 .4 0 0 0 0 .35 0 0 0 0 .27 0 0 0 -1.5 1.02"/>') + "</filter>")
        varn = f'<filter id="{k}var"><feFlood flood-color="#fff" flood-opacity=".35"/><feComposite in2="SourceAlpha" operator="in"/></filter>'
        return g + emb + tex + varn + f'<clipPath id="{k}die"><path d="{self.fustella()}"/></clipPath>' + "".join(self.defs).replace("@", k)

    def disegno(self, k="L", vivo=True, abbondanza=False):
        """Gruppo SVG in mm con l'aspetto finito (carta, stampa, foil, rilievo, vernice)."""
        m = MATERIALI[self.materiale]; W, H, B = self.w, self.h, self.b; J = lambda lv: "".join(self.L[lv]).replace("@", k)
        o = f'<defs>{self._defs(k, vivo)}</defs><g{"" if abbondanza else f" clip-path=\"url(#{k}die)\""}>'
        full = f'x="{-B}" y="{-B}" width="{W+2*B}" height="{H+2*B}"'
        if m["bg"]:
            o += f'<rect {full} fill="{m["bg"]}"/>'
            if m.get("metal"):
                o += f'<rect {full} fill="url(#{k}foil)" opacity=".25"/>'
            if m["tex"]:
                o += f'<rect {full} filter="url(#{k}tex)" opacity="{m["tex"][1]}"/>'
        if self.L["bianco"]:
            o += f'<g fill="#FFFFFF">{J("bianco")}</g>'
        o += J("stampa")
        if self.L["foil"]:
            o += f'<g fill="url(#{k}foil)">{J("foil")}</g>'
        if self.L["vernice"]:
            o += f'<g filter="url(#{k}var)">{J("vernice")}</g>'
        if self.L["rilievo"]:
            o += f'<g fill="#000" filter="url(#{k}emb)">{J("rilievo")}</g>'
        o += "</g>"
        if abbondanza:
            o += (f'<path d="M{-B} {-B}h{W+2*B}v{H+2*B}h{-(W+2*B)}Z{self.fustella()}" fill="#F4F4F0" fill-opacity=".7" fill-rule="evenodd"/>'
                  f'<path d="{self.fustella()}" fill="none" stroke="#00A651" stroke-width=".3"/>')
        return o

    def piatta(self, k="P", quote=False, ombra=True):
        W, H = self.w, self.h; pad = 8 if quote else 5
        o = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {W+2*pad} {H+2*pad}">'
        if ombra:
            o += f'<defs><filter id="{k}sh" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="1"/></filter></defs><path d="{self.fustella()}" transform="translate(.4 1)" fill="#000" opacity=".1" filter="url(#{k}sh)"/>'
        o += self.disegno(k, abbondanza=quote)
        if quote:
            o += (f'<g font-family="Arial" font-size="2.4" fill="#686D71"><path d="M0 {H+4}H{W}M0 {H+3}v2M{W} {H+3}v2M{W+4} 0V{H}M{W+3} 0h2M{W+3} {H}h2" stroke="#686D71" stroke-width=".2"/>'
                  f'<text x="{W/2}" y="{H+7.2}" text-anchor="middle">{f2(W)} mm</text><text transform="translate({W+7} {H/2}) rotate(90)" text-anchor="middle">{f2(H)} mm</text></g>')
        return o + "</svg>"

    def separazioni(self):
        """{livello: svg} solo per i livelli usati, più la fustella con l'abbondanza."""
        W, H, B = self.w, self.h, self.b; out = {}
        base = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-B-1} {-B-1} {W+2*B+2} {H+2*B+2}"><defs>{"".join(self.defs).replace("@", "S")}<clipPath id="Sdie"><path d="{self.fustella()}"/></clipPath></defs>'
        frame = f'<path d="{self.fustella()}" fill="#fff" stroke="#A7ADB0" stroke-width=".25"/>'
        for lv in LIVELLI:
            if not self.L[lv]:
                continue
            body = "".join(self.L[lv]).replace("@", "S")
            body = body if lv == "stampa" else f'<g fill="{ {"bianco": "#7A8086", "foil": "#B8902F", "rilievo": "#6F5BE8", "vernice": "#22B8D6"}[lv] }">{body}</g>'
            out[lv] = base + frame + body + "</svg>"
        out["fustella"] = base + f'<rect x="{-B}" y="{-B}" width="{W+2*B}" height="{H+2*B}" fill="none" stroke="#A7ADB0" stroke-width=".25" stroke-dasharray="1 1"/><path d="{self.fustella()}" fill="none" stroke="#00A651" stroke-width=".4"/></svg>'
        return out

    def spec(self, extra=()):
        m = MATERIALI[self.materiale]; usati = [lv for lv in LIVELLI if self.L[lv]]
        fin = []
        if self.L["foil"]: fin.append(f"foil {self.foil_colore.replace('_', ' ')}")
        if self.L["rilievo"]: fin.append("rilievo")
        if self.L["vernice"]: fin.append("vernice selettiva serigrafica")
        if self.L["bianco"]: fin.append("bianco")
        return [f"Formato: {f2(self.w)} × {f2(self.h)} mm (fustella {self.shape})", "Distanza: 3 mm", f"Materiale: {m['nome']}",
                "File: 1", "Stampa: CMYK" + (" + bianco" if self.L["bianco"] else ""), "Finitura: " + (", ".join(fin) or "nessuna"),
                f"Abbondanza: {f2(self.b)} mm", "Livelli: " + ", ".join(usati + ["fustella"])] + list(extra) + self.note

    def file_stampa(self, extra=()):
        """SVG in mm a livelli, pronto per Illustrator: testi già in tracciati, fondo carta non stampato."""
        W, H, B = self.w, self.h, self.b; lab = {"stampa": "Stampa CMYK", "bianco": "Bianco – colore speciale", "foil": f"Foil {self.foil_colore} – colore speciale",
                                                 "rilievo": "Rilievo – colore speciale", "vernice": "Vernice selettiva – colore speciale"}
        o = (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
             f'width="{f2(W+2*B)}mm" height="{f2(H+2*B)}mm" viewBox="{-B} {-B} {f2(W+2*B)} {f2(H+2*B)}">\n<title>{esc(self.nome)} – {f2(W)} × {f2(H)} mm</title>\n'
             f'<desc>{esc(chr(10).join(self.spec(extra)))}</desc>\n<defs>{"".join(self.defs).replace("@", "X")}</defs>\n')
        for lv in LIVELLI:
            if self.L[lv]:
                fill = "" if lv == "stampa" else f' fill="{SPOT[lv] if lv != "bianco" else "#E6E6E6"}"'
                o += f'<g id="{lv}" inkscape:groupmode="layer" inkscape:label="{lab[lv]}"{fill}>{"".join(self.L[lv]).replace("@", "X")}</g>\n'
        o += (f'<g id="fustella" inkscape:groupmode="layer" inkscape:label="Fustella" fill="none" stroke="#00A651" stroke-width=".1"><path d="{self.fustella()}"/></g>\n'
              f'<g id="abbondanza" inkscape:groupmode="layer" inkscape:label="Abbondanza {f2(B)} mm (riferimento)" fill="none" stroke="#A7ADB0" stroke-width=".1" stroke-dasharray="1 1"><rect x="{-B}" y="{-B}" width="{f2(W+2*B)}" height="{f2(H+2*B)}"/></g>\n</svg>\n')
        return per_illustrator(o)

# ---------------------------------------------------------------- compatibilità con Illustrator
import re as _re
def per_illustrator(svg):
    """Illustrator legge le immagini incorporate solo con xlink:href (SVG 1.1) e non gestisce bene gli <svg> annidati:
    le immagini prendono xlink:href e i riquadri annidati 'a tutta etichetta' diventano immagine + tracciato di ritaglio."""
    n = [0]
    def piatto(m):
        x, y, w, h, vw, vh, par, href = m.group(1, 2, 3, 4, 5, 6, 7, 8)
        x, y, w, h, vw, vh = map(float, (x, y, w, h, vw, vh)); r = vw / vh
        if par.endswith("slice"):
            iw, ih = (w, w / r) if w / h > r else (h * r, h)
        else:
            iw, ih = (w, w / r) if w / h < r else (h * r, h)
        ix, iy = x + (w - iw) / 2, y + (h - ih) / 2; n[0] += 1; cid = f"clipimg{n[0]}"
        return (f'<clipPath id="{cid}"><rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}"/></clipPath>'
                f'<g clip-path="url(#{cid})"><image xlink:href="{href}" x="{ix:.3f}" y="{iy:.3f}" width="{iw:.3f}" height="{ih:.3f}" preserveAspectRatio="none"/></g>')
    svg = _re.sub(r'<svg x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)" viewBox="0 0 ([\d.]+) ([\d.]+)" preserveAspectRatio="(xMidYMid (?:slice|meet))">'
                  r'<image href="([^"]+)" width="[\d.]+" height="[\d.]+"/></svg>', piatto, svg)
    svg = svg.replace('<image href="', '<image xlink:href="')
    if 'xmlns:xlink' not in svg:
        svg = svg.replace('<svg xmlns="http://www.w3.org/2000/svg"', '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"', 1)
    return svg

# ---------------------------------------------------------------- impaginazione
def place(svg, bx, by, bw, bh, vb, align="center"):
    """Inserisce un disegno con viewBox vb=(x, y, w, h) nel riquadro (bx, by, bw, bh) mm, in proporzione."""
    s = min(bw / vb[2], bh / vb[3]); ox = bx + (bw - vb[2] * s) * {"start": 0, "center": .5, "end": 1}[align] - vb[0] * s; oy = by + (bh - vb[3] * s) / 2 - vb[1] * s
    return f'<g transform="translate({ox:.3f} {oy:.3f}) scale({s:.5f})">{svg}</g>'

def immagine(href, x, y, w, h, colore=None, maschera_id="@img"):
    """Immagine (logo, foto). colore=None: a colori. colore="#hex": il logo diventa un solo colore (scuro = inchiostro).
    Restituisce (defs, contenuto); per foil/rilievo usare colore e mettere il contenuto nel livello giusto (il fill lo dà il livello)."""
    img = f'<image href="{href}" x="{f2(x)}" y="{f2(y)}" width="{f2(w)}" height="{f2(h)}" preserveAspectRatio="xMidYMid meet"'
    if colore is None:
        return "", img + "/>"
    d = (f'<filter id="{maschera_id}f" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="-.3 -1 -.1 0 1.4 -.3 -1 -.1 0 1.4 -.3 -1 -.1 0 1.4 0 0 0 1 0"/></filter>'
         f'<mask id="{maschera_id}" maskUnits="userSpaceOnUse" x="{f2(x)}" y="{f2(y)}" width="{f2(w)}" height="{f2(h)}">{img} filter="url(#{maschera_id}f)"/></mask>')
    return d, f'<rect x="{f2(x)}" y="{f2(y)}" width="{f2(w)}" height="{f2(h)}" mask="url(#{maschera_id})"' + (f' fill="{colore}"' if colore != "livello" else "") + "/>"

def segno_e(x, y, s, colore):
    """Il segno ℮ (quantità stimata), altezza maiuscole s, x a sinistra, y linea di base. Restituisce (svg, larghezza)."""
    r = s * .33; cx, cy = x + r, y - s * .34; sw = s * .07
    return (f'<path d="M{cx-r*.78:.2f} {cy:.2f}H{cx+r*.78:.2f}" stroke="{colore}" stroke-width="{sw:.2f}" fill="none"/>'
            f'<path d="M{cx+r*.78:.2f} {cy:.2f}A{r*.8:.2f} {r:.2f} 0 1 0 {cx+r*.55:.2f} {cy+r*.75:.2f}" stroke="{colore}" stroke-width="{sw:.2f}" fill="none" stroke-linecap="round"/>', 2 * r)

# ---------------------------------------------------------------- contenitori (anteprima)
VETRO = {"verde": ["#07110b", "#1d3524", "#14261a", "#050a07"], "ambra": ["#1c0802", "#5a2208", "#7b3510", "#140501"], "nero": ["#050505", "#2a2a2a", "#141414", "#000"],
         "trasparente": ["#c9d3d0", "#f4f8f7", "#dfe7e5", "#b7c2bf"], "bianco": ["#d9d9d6", "#ffffff", "#f1f1ee", "#cfcfcb"], "blu": ["#06142a", "#1b3d6e", "#122c52", "#040c1a"]}
TAPPI = {"capsula": None, "disco": "#0b0b0b", "pompa": "#0b0b0b", "coperchio": "#1a1a1a", "sughero": "#b58a57"}

def contenitore(tipo, L, colore=None, tappo=None, d=None, h=None, centro=None, liquido=None, k="C", sfondo=None):
    """Anteprima SVG del contenitore con l'etichetta applicata.
    tipo: bordolese, borgognotta, champagnotta, flacone (boston round), cilindro (flacone dritto), vaso, lattina.
    d, h: diametro e altezza in mm (default tipici); centro: altezza del centro etichetta dalla base (mm)."""
    D = {"bordolese": (75, 300), "borgognotta": (82, 295), "champagnotta": (90, 300), "longneck": (60, 232), "steinie": (64, 172), "flacone": (62, 150), "cilindro": (55, 180), "vaso": (85, 95), "lattina": (66, 115)}[tipo]
    d = d or D[0]; h = h or D[1]; R = d / 2; cx = R + 26; base = h + 14; W = L.w; H = L.h
    vetro = VETRO[colore or {"bordolese": "verde", "borgognotta": "verde", "champagnotta": "verde", "longneck": "ambra", "steinie": "ambra", "flacone": "ambra", "cilindro": "bianco", "vaso": "trasparente", "lattina": "argento"}.get(tipo, "verde")] if (colore or tipo != "lattina") else ["#8d9498", "#eef0f1", "#a7adb0", "#5f666a"]
    top = base - h
    if tipo in ("bordolese", "borgognotta", "champagnotta"):
        nr = 15 if tipo == "champagnotta" else 14.5; sh = base - (200 if tipo == "bordolese" else 145); neck = base - (232 if tipo == "bordolese" else 222)
        c1, c2 = (sh - 24, neck + 16) if tipo == "bordolese" else (sh - 42, neck + 30)
        body = (f"M{cx-R+6} {base}Q{cx-R} {base} {cx-R} {base-6}L{cx-R} {sh}C{cx-R} {c1} {cx-nr} {c2} {cx-nr} {neck}L{cx-nr} {top+12}L{cx-nr-1.6} {top+9}L{cx-nr-1.6} {top}"
                f"L{cx+nr+1.6} {top}L{cx+nr+1.6} {top+9}L{cx+nr} {top+12}L{cx+nr} {neck}C{cx+nr} {c2} {cx+R} {c1} {cx+R} {sh}L{cx+R} {base-6}Q{cx+R} {base} {cx+R-6} {base}Z")
        capc = tappo or "#3a1d22"
        cap = (f'<path d="M{cx-nr-1.9} {top-.5}H{cx+nr+1.9}V{top+10}L{cx+nr+.4} {top+13}V{neck-4}H{cx-nr-.4}V{top+13}L{cx-nr-1.9} {top+10}Z" fill="{capc}"/>'
               f'<path d="M{cx-nr-1.9} {top-.5}H{cx+nr+1.9}V{top+10}L{cx+nr+.4} {top+13}V{neck-4}H{cx-nr-.4}V{top+13}L{cx-nr-1.9} {top+10}Z" fill="url(#{k}cap)"/>')
        body_rng = ({"bordolese": 18, "borgognotta": 15, "champagnotta": 15}[tipo], base - sh)
    elif tipo in ("longneck", "steinie"):   # bottiglie da birra con tappo a corona
        nr = 13.2; lng = tipo == "longneck"
        sh = base - (h * (.5 if lng else .6)); neck = base - (h * (.68 if lng else .8)); c1, c2 = sh - (12 if lng else 10), neck + (10 if lng else 8)
        body = (f"M{cx-R+5} {base}Q{cx-R} {base} {cx-R} {base-6}L{cx-R} {sh}C{cx-R} {c1} {cx-nr} {c2} {cx-nr} {neck}L{cx-nr+1.2} {top+9}L{cx-nr-1} {top+5}L{cx-nr-1} {top+2}"
                f"L{cx+nr+1} {top+2}L{cx+nr+1} {top+5}L{cx+nr-1.2} {top+9}L{cx+nr} {neck}C{cx+nr} {c2} {cx+R} {c1} {cx+R} {sh}L{cx+R} {base-6}Q{cx+R} {base} {cx+R-5} {base}Z")
        cc = tappo if (tappo or "").startswith("#") else "#B8902F"
        cap = (f'<path d="M{cx-nr-1.6} {top+1}H{cx+nr+1.6}V{top+6}H{cx-nr-1.6}Z" fill="{cc}"/><path d="M{cx-nr-1.6} {top+1}H{cx+nr+1.6}V{top+6}H{cx-nr-1.6}Z" fill="url(#{k}cap)"/>'
               + "".join(f'<path d="M{cx-nr-1+i*1.6:.1f} {top+4}v2.4" stroke="#000" stroke-opacity=".35" stroke-width=".4"/>' for i in range(int((2*nr+2)/1.6))))
        body_rng = (8, base - sh - 4)
    elif tipo in ("flacone", "cilindro"):
        nr = d * (.2 if tipo == "flacone" else .16); sh = top + (h * .34 if tipo == "flacone" else h * .2); neck = top + h * .2 if tipo == "flacone" else top + h * .14
        capH = h * .17
        body = (f"M{cx-R+5} {base}Q{cx-R} {base} {cx-R} {base-6}V{sh+8}C{cx-R} {sh-6} {cx-R*.62} {sh-14 if tipo=='flacone' else sh-4} {cx-nr-2} {neck+4}V{neck}H{cx+nr+2}V{neck+4}"
                f"C{cx+R*.62} {sh-14 if tipo=='flacone' else sh-4} {cx+R} {sh-6} {cx+R} {sh+8}V{base-6}Q{cx+R} {base} {cx+R-5} {base}Z")
        cc = TAPPI.get(tappo or "disco") or "#0b0b0b"
        cw = nr * 2.5
        cap = (f'<rect x="{cx-cw/2}" y="{neck-capH}" width="{cw}" height="{capH+1}" rx="1.6" fill="{cc}"/><rect x="{cx-cw/2}" y="{neck-capH}" width="{cw}" height="{capH+1}" rx="1.6" fill="url(#{k}cap)"/>'
               + ("".join(f'<path d="M{cx-cw/2+1+i*1.2:.1f} {neck-capH*.45:.1f}v{capH*.4:.1f}" stroke="#2a2a2a" stroke-width=".3"/>' for i in range(int((cw-2)/1.2))) if (tappo or "disco") == "disco" else "")
               + (f'<rect x="{cx-3}" y="{neck-capH-16}" width="6" height="16" fill="{cc}"/><rect x="{cx-3}" y="{neck-capH-19}" width="22" height="5" rx="2" fill="{cc}"/>' if tappo == "pompa" else ""))
        body_rng = (8, base - sh - 6)
    elif tipo == "vaso":
        lid = h * .16
        body = f"M{cx-R+4} {base}Q{cx-R} {base} {cx-R} {base-5}V{top+lid+6}Q{cx-R} {top+lid} {cx-R+5} {top+lid}H{cx+R-5}Q{cx+R} {top+lid} {cx+R} {top+lid+6}V{base-5}Q{cx+R} {base} {cx+R-4} {base}Z"
        cc = TAPPI.get(tappo or "coperchio") or "#1a1a1a"
        cap = f'<rect x="{cx-R-1}" y="{top}" width="{d+2}" height="{lid+1}" rx="2" fill="{cc}"/><rect x="{cx-R-1}" y="{top}" width="{d+2}" height="{lid+1}" rx="2" fill="url(#{k}cap)"/>'
        body_rng = (6, h - lid - 6)
    else:   # lattina
        body = f"M{cx-R+4} {base}Q{cx-R} {base} {cx-R} {base-6}V{top+10}L{cx-R+5} {top+2}H{cx+R-5}L{cx+R} {top+10}V{base-6}Q{cx+R} {base} {cx+R-4} {base}Z"
        cap = ""; body_rng = (10, h - 14)
    lo, hi = body_rng; cy = base - (centro if centro else (lo + hi) / 2)
    ang = min(W / (2 * R), 1.45); dw = 2 * R * math.sin(ang); lx = cx - dw / 2; ly = cy - H / 2
    clear = (colore or "") in ("trasparente",) or (tipo == "vaso" and not colore)
    fill_in = f'<path d="{body}" fill="{liquido}" opacity=".85" transform="translate({cx} {base}) scale(.94 .97) translate({-cx} {-base})"/>' if (clear and liquido) else ""
    shade = (f'<linearGradient id="{k}ls" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".45"/><stop offset=".16" stop-color="#000" stop-opacity=".08"/>'
             '<stop offset=".38" stop-color="#fff" stop-opacity=".16"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset=".86" stop-color="#000" stop-opacity=".18"/><stop offset="1" stop-color="#000" stop-opacity=".5"/></linearGradient>')
    VW = 2 * cx; VH = base + 8
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW:.1f} {VH:.1f}">' + (f'<rect width="{VW:.1f}" height="{VH:.1f}" fill="{sfondo}"/>' if sfondo else "") + '<defs>'
            f'<linearGradient id="{k}g" x1="0" x2="1">' + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in zip(("0", ".22", ".5", "1"), vetro)) + '</linearGradient>'
            f'<linearGradient id="{k}cap" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".45"/><stop offset=".35" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#000" stop-opacity=".5"/></linearGradient>{shade}'
            f'<radialGradient id="{k}fl" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#101214" stop-opacity=".25"/><stop offset="1" stop-color="#101214" stop-opacity="0"/></radialGradient></defs>'
            f'<ellipse cx="{cx}" cy="{base+1.5}" rx="{R+16}" ry="4.5" fill="url(#{k}fl)"/>'
            f'<path d="{body}" fill="url(#{k}g)"' + (' opacity=".55"' if clear else "") + f'/>{fill_in}{cap}'
            f'<rect x="{cx-R*.66:.1f}" y="{top + (h*.25):.1f}" width="{R*.09:.1f}" height="{h*.55:.1f}" rx="1.5" fill="#fff" opacity=".14"/>'
            f'<svg x="{lx:.2f}" y="{ly:.2f}" width="{dw:.2f}" height="{H}" viewBox="0 0 {W} {H}" preserveAspectRatio="none" overflow="visible">{L.disegno(k + "L")}'
            f'<path d="{L.fustella()}" fill="url(#{k}ls)"/></svg>'
            f'<rect x="{cx+R*.5:.1f}" y="{top + (h*.3):.1f}" width="{R*.05:.1f}" height="{h*.45:.1f}" rx="1" fill="#fff" opacity=".1"/></svg>')

# ---------------------------------------------------------------- controllo visivo
def render(svgs, png, altezza=700, sfondo="#E9E7E1"):
    """Affianca uno o più SVG in un PNG per guardarli (Read del PNG). Usa Chrome via Playwright."""
    from playwright.sync_api import sync_playwright
    page = f"<body style='margin:0;background:{sfondo};display:flex;gap:16px;padding:16px;align-items:flex-end'>" + "".join(
        f"<img src='file://{os.path.abspath(s)}' style='height:{altezza}px'>" for s in svgs) + "</body>"
    tmp = os.path.abspath(png) + ".html"; open(tmp, "w").write(page)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None)
        pg = b.new_page(viewport={"width": 1800, "height": altezza + 40}); pg.goto("file://" + tmp); pg.wait_for_timeout(500)
        w = pg.evaluate("document.body.scrollWidth"); pg.set_viewport_size({"width": min(max(w, 400), 3000), "height": altezza + 40}); pg.screenshot(path=png); b.close()
    os.remove(tmp); return png
