"""Bottoms up Winery (Ponzone, Piemonte) — prima vendemmia, ~700 etichette frontali su bordolese 750 ml, applicazione a mano.
Brief: look premium e tradizionale, carta goffrata avorio/crema, stampa bordeaux con dettagli verdi, foil oro (nome o cornice), rilievo, finitura opaca.
Il logo del cliente non è ancora arrivato: al suo posto un sigillo-monogramma da sostituire. Testi del vino = segnaposto da confermare.
Formato proposto 90 × 120 mm invece di 150 × 200 (troppo alto e largo per la bordolese)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from grafico import Label, contenitore, render, place, segno_e, forma, f2
import ornamenti as O

BORD, VERDE, NERO = "#6B1F2E", "#3F5A3C", "#2A1A1C"
SER, SERI, CAPS, SANS, SCRIPT = "cormorant-garamond:600:normal", "cormorant-garamond:500:italic", "cinzel:600:normal", "archivo:400:normal", "pinyon-script:400:normal"
TXT = dict(vino="Vino Rosso", zona="Ponzone · Piemonte", annata="2026", alc="13,5% vol", vol="75 cl")   # segnaposto da confermare

def sigillo(L, cx, cy, r, livello="foil", colore=BORD):
    """Segnaposto del logo: cerchio doppio con monogramma BU, da sostituire con il logo vero."""
    d = f"M{f2(cx-r)} {f2(cy)}a{f2(r)} {f2(r)} 0 1 0 {f2(2*r)} 0a{f2(r)} {f2(r)} 0 1 0 {f2(-2*r)} 0Z" + f"M{f2(cx-r*.93)} {f2(cy)}a{f2(r*.93)} {f2(r*.93)} 0 1 0 {f2(1.86*r)} 0a{f2(r*.93)} {f2(r*.93)} 0 1 0 {f2(-1.86*r)} 0Z"
    d += f"M{f2(cx-r*.86)} {f2(cy)}a{f2(r*.86)} {f2(r*.86)} 0 1 0 {f2(1.72*r)} 0a{f2(r*.86)} {f2(r*.86)} 0 1 0 {f2(-1.72*r)} 0Z" + f"M{f2(cx-r*.83)} {f2(cy)}a{f2(r*.83)} {f2(r*.83)} 0 1 0 {f2(1.66*r)} 0a{f2(r*.83)} {f2(r*.83)} 0 1 0 {f2(-1.66*r)} 0Z"
    L.add(livello, f'<path d="{d}" fill-rule="evenodd"' + (f' fill="{colore}"' if livello == "stampa" else "") + "/>")
    L.testo(livello, SER, "BU", r * 1.0, cx, cy + r * .34, anchor="middle", track=.02, colore=colore)

def tradizione():
    """A — Tradizione: quello che chiedono, fatto bene. Cornice doppia in foil, nome in foil + rilievo, bordeaux e verde."""
    L = Label(90, 120, shape="round", raggio=4, materiale="carta_avorio_goffrata", foil="oro", nome="Bottoms up – A Tradizione")
    L.add("foil", O.cornice(L, 3.2, .45, doppia=(1.1, .2)))
    sigillo(L, 45, 25, 9.5, "foil")
    L.add("rilievo", f'<path d="M{45-9.5} 25a9.5 9.5 0 1 0 19 0a9.5 9.5 0 1 0 -19 0Z"/>')
    L.testi([("foil", CAPS, "BOTTOMS UP", 9.2, 45, 49, dict(anchor="middle", track=.08, maxW=68)),
             ("rilievo", CAPS, "BOTTOMS UP", 9.2, 45, 49, dict(anchor="middle", track=.08, maxW=68)),
             ("stampa", CAPS, "WINERY", 3.2, 45, 55.5, dict(anchor="middle", track=.5, colore=VERDE))])
    L.add("stampa", f'<g fill="{VERDE}">{O.filetto(45, 61, 14)}</g>')
    L.testi([("stampa", SERI, TXT["vino"], 13, 45, 76, dict(anchor="middle", maxW=66, colore=BORD)),
             ("stampa", SER, TXT["annata"], 7, 45, 89, dict(anchor="middle", track=.08, colore=BORD)),
             ("stampa", SERI, TXT["zona"], 4, 45, 97, dict(anchor="middle", colore=VERDE)),
             ("stampa", CAPS, TXT["alc"].upper(), 3.1, 12, 109.5, dict(track=.06, colore=BORD)),
             ("stampa", CAPS, TXT["vol"].upper(), 3.1, 78, 109.5, dict(anchor="end", track=.06, colore=BORD))])
    return L

def colline():
    """B — Le colline di Ponzone: le prime viti della cantina disegnate come un'incisione; il nome in corsivo d'oro, fustella ad arco."""
    L = Label(90, 120, shape="arch", materiale="carta_crema_liscia", foil="oro", nome="Bottoms up – B Colline")
    L.add("stampa", f'<g stroke="{VERDE}">{O.colline(10, 50, 70, 30, strati=4, seed=5)}</g>')
    L.add("foil", f'<path d="M45 47a5 5 0 1 0 .01 0Z"/>')                       # il sole sopra le colline, in foil
    L.add("foil", O.cornice(L, 3, .3))
    L.testi([("foil", SCRIPT, "Bottoms Up", 16, 45, 40, dict(anchor="middle", maxW=66)),
             ("rilievo", SCRIPT, "Bottoms Up", 16, 45, 40, dict(anchor="middle", maxW=66)),
             ("stampa", CAPS, "WINERY · PONZONE", 2.9, 45, 25, dict(anchor="middle", track=.4, colore=BORD)),
             ("stampa", SERI, TXT["vino"], 11, 45, 94, dict(anchor="middle", maxW=64, colore=BORD)),
             ("stampa", CAPS, "PRIMA VENDEMMIA · " + TXT["annata"], 3.2, 45, 101.5, dict(anchor="middle", track=.18, colore=VERDE)),
             ("stampa", CAPS, f'{TXT["alc"].upper()}   ·   {TXT["vol"].upper()}', 3, 45, 111, dict(anchor="middle", track=.08, colore=BORD))])
    return L

def brindisi():
    """C — Brindisi: il nome è un brindisi. Grande sigillo in foil e rilievo come un timbro di ceralacca, tutto il resto è tipografia."""
    L = Label(85, 115, shape="rect", raggio=1.5, materiale="carta_bianca_goffrata", foil="oro", nome="Bottoms up – C Brindisi")
    L.add("stampa", f'<path d="M-2 92H87V117H-2Z" fill="{BORD}"/>')             # fascia bordeaux al piede, va in abbondanza
    sigillo(L, 42.5, 34, 15, "foil")
    L.add("rilievo", f'<path d="M27.5 34a15 15 0 1 0 30 0a15 15 0 1 0 -30 0Z"/>')
    L.testi([("stampa", CAPS, "BOTTOMS UP", 6.4, 42.5, 63, dict(anchor="middle", track=.22, maxW=72, colore=NERO)),
             ("stampa", SERI, "a toast from Ponzone", 4.6, 42.5, 70, dict(anchor="middle", colore=VERDE)),
             ("stampa", SER, TXT["vino"].upper(), 4.4, 42.5, 81, dict(anchor="middle", track=.2, colore=BORD)),
             ("foil", SER, TXT["annata"], 7, 42.5, 103, dict(anchor="middle", track=.12)),
             ("stampa", SANS, TXT["alc"], 2.6, 7, 110, dict(colore="#F3E9E1")),
             ("stampa", SANS, TXT["vol"], 2.6, 78, 110, dict(anchor="end", colore="#F3E9E1"))])
    return L

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "out", "bottoms_up"); os.makedirs(out, exist_ok=True)
    files = []
    for key, fn in (("A", tradizione), ("B", colline), ("C", brindisi)):
        L = fn()
        open(f"{out}/{key}-piatta.svg", "w").write(L.piatta(quote=True))
        open(f"{out}/{key}-bottiglia.svg", "w").write(contenitore("bordolese", L, k=key))
        open(f"{out}/{key}-stampa.svg", "w").write(L.file_stampa(extra=["Bottiglia: bordolese 75 cl, applicazione a mano", "Quantità: 700"]))
        for lv, s in L.separazioni().items():
            open(f"{out}/{key}-sep-{lv}.svg", "w").write(s)
        files += [f"{out}/{key}-bottiglia.svg", f"{out}/{key}-piatta.svg"]
    render(files, f"{out}/controllo.png", altezza=620)
    print("ok", out)
