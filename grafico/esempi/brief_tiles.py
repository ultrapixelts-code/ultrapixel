"""Miniature dei contenitori per il brief guidato (pagina /prova): etichetta neutra, solo la forma."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grafico import Label, contenitore
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server", "static", "brief")
SIZE = {"bordolese": (90, 110, "round"), "borgognotta": (95, 105, "round"), "champagnotta": (100, 90, "oval"), "longneck": (75, 85, "rect"),
        "steinie": (80, 70, "rect"), "flacone": (80, 70, "round"), "cilindro": (70, 90, "rect"), "vaso": (110, 60, "rect"), "lattina": (200, 100, "rect")}
for t, (w, h, s) in SIZE.items():
    L = Label(w, h, shape=s, materiale="carta_avorio_goffrata")
    L.add("stampa", f'<rect x="{w*.2:.1f}" y="{h*.38:.1f}" width="{w*.6:.1f}" height="{h*.08:.1f}" fill="#101214" opacity=".75"/>'
                    f'<rect x="{w*.32:.1f}" y="{h*.54:.1f}" width="{w*.36:.1f}" height="{h*.035:.1f}" fill="#101214" opacity=".35"/>')
    svg = contenitore(t, L, k="b" + t[:3])
    open(os.path.join(OUT, f"c-{t}.svg"), "w").write(svg)
    print(t, len(svg))
