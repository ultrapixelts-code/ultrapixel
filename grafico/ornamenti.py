"""Ornamenti vettoriali per etichette (mm). Ogni funzione restituisce un frammento SVG senza fill: il colore lo dà il livello o il chiamante."""
import math
from grafico import forma, rr, f2

def cornice(L, rientro=2.5, spessore=.3, doppia=None):
    """Linea che segue la fustella, rientrata. doppia=(distanza, spessore2) aggiunge una seconda linea interna."""
    d = forma(L.shape, L.w, L.h, rientro, L.raggio) + forma(L.shape, L.w, L.h, rientro + spessore, L.raggio)
    if doppia:
        g, s2 = doppia; d += forma(L.shape, L.w, L.h, rientro + spessore + g, L.raggio) + forma(L.shape, L.w, L.h, rientro + spessore + g + s2, L.raggio)
    return f'<path d="{d}" fill-rule="evenodd"/>'

def filetto(cx, y, mezza, spessore=.28, rombo=1.1, gap=2.2):
    """Filetto orizzontale con rombo centrale."""
    p = rr(cx - mezza - gap, y - spessore / 2, mezza, spessore, 0) + rr(cx + gap, y - spessore / 2, mezza, spessore, 0)
    if rombo:
        p += f"M{f2(cx)} {f2(y-rombo)}L{f2(cx+rombo)} {f2(y)}L{f2(cx)} {f2(y+rombo)}L{f2(cx-rombo)} {f2(y)}Z"
    return f'<path d="{p}"/>'

def linea(x1, y1, x2, y2, spessore=.25):
    a = math.atan2(y2 - y1, x2 - x1); nx, ny = -math.sin(a) * spessore / 2, math.cos(a) * spessore / 2
    return f'<path d="M{f2(x1+nx)} {f2(y1+ny)}L{f2(x2+nx)} {f2(y2+ny)}L{f2(x2-nx)} {f2(y2-ny)}L{f2(x1-nx)} {f2(y1-ny)}Z"/>'

def puntini(L, rientro=3, passo=1.6, r=.22):
    """Bordo a puntini lungo un rettangolo rientrato (fustelle rect/round)."""
    w, h = L.w - 2 * rientro, L.h - 2 * rientro; out = []
    for x in [rientro + i * passo for i in range(int(w / passo) + 1)]:
        out += [(x, rientro), (x, L.h - rientro)]
    for y in [rientro + i * passo for i in range(1, int(h / passo))]:
        out += [(rientro, y), (L.w - rientro, y)]
    return '<path d="' + "".join(f"M{f2(x-r)} {f2(y)}a{r} {r} 0 1 0 {2*r} 0a{r} {r} 0 1 0 {-2*r} 0Z" for x, y in out) + '"/>'

def onda(x, y, larghezza, ampiezza=.8, periodi=4, spessore=.25):
    """Linea ondulata (acqua) come forma piena."""
    pts = [(x + larghezza * i / 80, y + ampiezza * math.sin(2 * math.pi * periodi * i / 80)) for i in range(81)]
    top = " L".join(f"{f2(a)} {f2(b - spessore/2)}" for a, b in pts); bot = " L".join(f"{f2(a)} {f2(b + spessore/2)}" for a, b in pts[::-1])
    return f'<path d="M{top} L{bot}Z"/>'

def colline(x, y, w, h, strati=4, seed=3, filari=True, spessore=.22):
    """Paesaggio di colline a tratto (linee con stroke, per il livello stampa): strati di crinali e filari di vite sulle colline davanti."""
    import random
    r = random.Random(seed); out = []
    for k in range(strati):
        base = y + h * (.25 + .75 * k / max(1, strati - 1)) ; amp = h * (.22 - .03 * k); ph = r.uniform(0, 6.28); fr = r.uniform(.8, 1.6)
        pts = [(x + w * i / 60, base - amp * (.5 + .5 * math.sin(ph + fr * 6.28 * i / 60)) * (1 - .3 * math.sin(3.14 * i / 60))) for i in range(61)]
        out.append(f'<path d="M' + " L".join(f"{f2(a)} {f2(b)}" for a, b in pts) + f'" fill="none" stroke-width="{f2(spessore*(1+.3*k))}"/>')
        if filari and k >= strati - 2:
            for j in range(4, 57, 3):
                a, b = pts[j]; dx = (j - 30) / 30 * w * .02
                out.append(f'<path d="M{f2(a)} {f2(b+.6)}L{f2(a+dx)} {f2(min(y+h, b + h*.16))}" fill="none" stroke-width="{f2(spessore*.6)}"/>')
    return "".join(out)
