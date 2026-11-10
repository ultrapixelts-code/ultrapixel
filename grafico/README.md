# Grafico AI UltraPixel

Strumenti con cui Claude fa il lavoro del grafico su qualunque etichetta (vino, cosmetici, alimentare, integratori, chimico):
dal brief del cliente alle direzioni sul contenitore, fino al file di stampa a livelli. La procedura è nella skill
`grafico-etichette` del progetto UltraPixel OS; qui ci sono gli strumenti.

## Installazione (una volta per sessione)
```
cd grafico && npm install --silent && pip install playwright --break-system-packages -q
```

## File
- `grafico.py` — etichetta a livelli (`Label`: stampa, bianco, foil, rilievo, vernice), fustelle (rect, round, oval, circle, arch, shield, notch),
  materiali (carte e film), foil, testi in tracciati (`Label.testo` / `Label.testi`), immagini e loghi monocromatici (`immagine`), segno ℮,
  anteprima piatta con quote, anteprima sul contenitore (`contenitore`: bordolese, borgognotta, champagnotta, flacone, cilindro, vaso, lattina),
  separazioni per livello, file di stampa SVG a livelli con specifica, `render` per il controllo visivo.
- `text.js` — testi in tracciati con opentype.js. Caratteri disponibili (`famiglia:peso:stile`):
  bodoni-moda, playfair-display, dm-serif-display, cormorant-garamond, eb-garamond, fraunces (serif);
  cinzel (maiuscole classiche); archivo, inter, manrope (sans); zilla-slab (slab); pinyon-script (corsivo calligrafico).
- `botanica.py` — illustrazione botanica procedurale (rosmarino) come esempio di disegno vettoriale di una pianta.
- `ornamenti.py` — cornici che seguono la fustella, filetti, puntini, onde, colline con filari.
- `settori.md` — diciture obbligatorie per settore e cosa UltraPixel può stampare davvero.
- `esempi/bottoms_up.py` — caso completo vino (3 direzioni); `esempi/tavola/` — esempio dei file della tavola per il cliente.

## Uscite
In `grafico/out/<cliente>/`: `X-piatta.svg`, `X-<contenitore>.svg`, `X-sep-<livello>.svg`, `X-stampa.svg` (file per Illustrator, testi in tracciati,
livelli separati, fondo carta non stampato, specifica nel campo descrizione). `out/` non va nel repository.
