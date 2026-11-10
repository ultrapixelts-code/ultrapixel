"""Illustrazione botanica procedurale (tratto da incisione): esempio di come si disegna una pianta in vettoriale senza modelli di immagini.
Sprig = rametto di rosmarino (foglie aghiformi, fiori bilabiati). Livelli separati: linee, colore dei fiori, calici, masse piene per il rilievo.
Unità: box di circa 100 x 120; si inserisce in etichetta con grafico.place(..., vb=VB).
Per un'altra pianta: riusare leaf()/stem()/flower() cambiando forma delle foglie, fillotassi e fiore, oppure disegnare a mano i tracciati."""
VB = (6, 2, 92, 118)
import math, random

def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return tuple(u**3*a + 3*u*u*t*b + 3*u*t*t*c + t**3*d for a, b, c, d in zip(p0, p1, p2, p3))

def tang(p0, p1, p2, p3, t):
    u = 1 - t
    v = tuple(3*u*u*(b-a) + 6*u*t*(c-b) + 3*t*t*(d-c) for a, b, c, d in zip(p0, p1, p2, p3))
    l = math.hypot(*v) or 1
    return (v[0]/l, v[1]/l)

def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0]*c - v[1]*s, v[0]*s + v[1]*c)

f = lambda v: f"{v:.2f}"
def poly(pts, close=True):
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + ("Z" if close else "")
def smooth(pts, close=True):
    """Catmull-Rom through points -> cubic path."""
    n = len(pts); P = pts + pts[:3] if close else [pts[0]] + pts + [pts[-1]]
    out = f"M{f(pts[0][0])} {f(pts[0][1])}"
    rng = range(n) if close else range(n - 1)
    for i in rng:
        p0, p1, p2, p3 = (P[i], P[i+1], P[i+2], P[i+3]) if not close else (pts[(i-1) % n], pts[i], pts[(i+1) % n], pts[(i+2) % n])
        c1 = (p1[0] + (p2[0]-p0[0])/6, p1[1] + (p2[1]-p0[1])/6); c2 = (p2[0] - (p3[0]-p1[0])/6, p2[1] - (p3[1]-p1[1])/6)
        out += f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}"
    return out + ("Z" if close else "")

class Sprig:
    def __init__(self, seed=3):
        self.r = random.Random(seed)
        self.ink, self.hair, self.color, self.color2, self.tint, self.emb, self.calyx = [], [], [], [], [], [], []

    def leaf(self, P, d, L, W, side, bend=.18, tint=True):
        r = self.r; n = (-d[1]*side, d[0]*side)   # normal pointing back toward the stem tip side
        cl = []
        for i in range(19):
            s = i / 18
            cl.append((P[0] + d[0]*L*s + n[0]*bend*L*s*s, P[1] + d[1]*L*s + n[1]*bend*L*s*s))
        def norm(i):
            a = cl[max(0, i-1)]; b = cl[min(18, i+1)]; v = (b[0]-a[0], b[1]-a[1]); l = math.hypot(*v) or 1
            return (-v[1]/l, v[0]/l)
        left, right = [], []
        for i, c in enumerate(cl):
            s = i / 18; w = W * (math.sin(math.pi * min(s*1.08, 1)) ** .55) * (1 - .35*s) / 2
            nn = norm(i); left.append((c[0] + nn[0]*w, c[1] + nn[1]*w)); right.append((c[0] - nn[0]*w, c[1] - nn[1]*w))
        outline = left + right[::-1]
        dpath = smooth(outline)
        self.ink.append((dpath, .24))
        mid = cl[2:15]; self.hair.append((smooth(mid, False), .13))
        # revolute margin: a second line close to one edge, gives the leaf its curl
        rv = [(c[0]*.62 + l[0]*.38, c[1]*.62 + l[1]*.38) for c, l in zip(cl[3:16], (left if side > 0 else right)[3:16])]
        self.hair.append((smooth(rv, False), .11))
        if tint: self.tint.append(dpath)
        self.emb.append(dpath)
        return cl[-1]

    def stem(self, ctrl, w0, w1, hatch=True):
        pts, l, rr = [], [], []
        for i in range(41):
            t = i / 40; p = bez(*ctrl, t); tg = tang(*ctrl, t); nn = (-tg[1], tg[0]); w = (w0 + (w1 - w0) * t) / 2
            pts.append(p); l.append((p[0] + nn[0]*w, p[1] + nn[1]*w)); rr.append((p[0] - nn[0]*w, p[1] - nn[1]*w))
        self.ink.append((smooth(l, False), .3)); self.ink.append((smooth(rr, False), .3))
        self.emb.append(smooth(l + rr[::-1]))
        if hatch:   # short engraving strokes on the shadow side of the woody part
            for i in range(2, 22, 1):
                t = i / 40; p = bez(*ctrl, t); tg = tang(*ctrl, t); nn = (-tg[1], tg[0]); w = (w0 + (w1 - w0) * t) / 2
                a = (p[0] - nn[0]*w*.95, p[1] - nn[1]*w*.95); b = (p[0] - nn[0]*w*.15 + tg[0]*.9, p[1] - nn[1]*w*.15 + tg[1]*.9)
                self.hair.append((poly([a, b], False), .11))

    def flower(self, P, ang, F=7.5, tilt=0):
        r = self.r
        def T(x, y):
            x, y = x*F/7.5, y*F/7.5*(1 - abs(tilt)*.3)
            c, s = math.cos(ang), math.sin(ang); return (P[0] + x*c - y*s, P[1] + x*s + y*c)
        def ell(cx, cy, rx, ry, a, n=24):
            pts = []
            for i in range(n):
                t = 2*math.pi*i/n; x = rx*math.cos(t); y = ry*math.sin(t); x, y = x*math.cos(a) - y*math.sin(a), x*math.sin(a) + y*math.cos(a)
                pts.append(T(cx + x, cy + y))
            return smooth(pts)
        # calyx (two-lipped, sage) and tube
        cal = smooth([T(0, -.5), T(1.2, -1.0), T(2.6, -1.1), T(2.9, 0), T(2.6, 1.0), T(1.2, .9), T(0, .5)])
        self.calyx.append(cal); self.ink.append((cal, .2)); self.hair.append((poly([T(.6, 0), T(2.4, .1)], False), .1))
        upper = ell(4.7, -1.0, 2.6, 1.0, -.38); lower = ell(5.1, 1.2, 1.9, 1.25, .45); s1 = ell(3.7, 2.15, 1.05, .75, .9); s2 = ell(3.5, -.1, 1.0, .7, 0)
        for p_ in (s2, s1, lower, upper):
            self.color.append(p_)
        self.color2.append(ell(5.2, 1.5, .85, .6, .4))   # darker throat spot on the lower lip
        for p_, w in ((upper, .16), (lower, .16), (s1, .13)):
            self.ink.append((p_, w))
        self.hair.append((smooth([T(5.6, 1.0), T(6.2, 1.4), T(6.5, 2.1)], False), .1))
        # two long arching stamens and the style
        for k, (ex, ey) in enumerate(((8.6, -3.6), (8.1, -2.4), (8.9, -2.9))):
            self.hair.append((smooth([T(4.2, -.6), T(6.5, -2.2 - k*.2), T(ex, ey)], False), .12))
            self.ink.append((ell(ex, ey, .28, .2, 0, 10), .14))

    def build(self, kind="full"):
        r = self.r
        branches = {
            "full": [(((22, 116), (30, 86), (40, 52), (60, 8)), 2.6, .45, .95),
                     (((31, 86), (46, 70), (66, 56), (92, 36)), 1.6, .4, .95),
                     (((36, 62), (31, 46), (22, 32), (8, 20)), 1.3, .35, .9)],
            "single": [(((20, 116), (34, 84), (46, 48), (70, 6)), 1.9, .4, .9)],
        }[kind]
        for bi, (ctrl, w0, w1, fl) in enumerate(branches):
            self.stem(ctrl, w0, w1, hatch=(bi == 0))
            n = 34 if bi == 0 else 24; start = .1 if bi == 0 else .06
            for i in range(n):
                t = start + (.97 - start) * i / (n - 1); P = bez(*ctrl, t); tg = tang(*ctrl, t)
                for side in ((1, -1) if i % 2 == 0 else (-1, 1)):   # opposite pairs
                    if r.random() < .12: continue
                    a = math.radians(34 - 22 * t + r.uniform(-8, 8))
                    L = (12.5 - 8 * t) * r.uniform(.8, 1.1) * (.88 if bi else 1); W = L * .13
                    if r.random() < .2: L *= .6
                    d = rot(tg, -a * side)
                    self.leaf(P, d, L, W, -side)
                if .4 < t < .88 and i % 4 == 1 and r.random() < fl * .75:
                    for k in range(r.choice((1, 1, 2))):
                        side = 1 if (i + k) % 2 else -1
                        d = rot(tg, -math.radians(r.uniform(35, 70)) * side)
                        fa = math.atan2(d[1], d[0]); fp = (P[0] + d[0]*(1 + k*1.6), P[1] + d[1]*(1 + k*1.6))
                        self.flower(fp, fa, F=r.uniform(6.4, 8.0), tilt=r.uniform(-.4, .4))
            # crowded apical bud: tiny leaves at the tip
            tp = bez(*ctrl, 1); tg = tang(*ctrl, 1)
            for k in range(5):
                self.leaf(tp, rot(tg, (k - 2) * .28), 3.2 - abs(k - 2) * .5, .7, 1 if k % 2 else -1, bend=.1)
        return self


def livelli(kind="full", seed=7, fiore="#9FAEEB", gola="#6C7BD0", inchiostro="#24302A", calice="#B9C3AE", sfalsa=True):
    """Restituisce dict: tratto (linee), colore (fiori + calici, leggermente sfalsato come un acquerello), colore_piatto, masse (per il rilievo)."""
    s = Sprig(seed).build(kind)
    lines = "".join(f'<path d="{d}" stroke-width="{w}"/>' for d, w in s.ink + s.hair)
    off = ' transform="translate(.45 .35)"' if sfalsa else ""
    return {"tratto": f'<g fill="none" stroke="{inchiostro}" stroke-linecap="round" stroke-linejoin="round">{lines}</g>',
            "colore": f'<g{off}><g fill="{fiore}">' + "".join(f'<path d="{d}"/>' for d in s.color) + f'</g><g fill="{gola}" opacity=".75">' + "".join(f'<path d="{d}"/>' for d in s.color2) + f'</g></g><g fill="{calice}">' + "".join(f'<path d="{d}"/>' for d in s.calyx) + '</g>',
            "colore_piatto": f'<g fill="{fiore}">' + "".join(f'<path d="{d}"/>' for d in s.color + s.color2) + '</g>',
            "masse": "".join(f'<path d="{d}"/>' for d in s.emb)}
