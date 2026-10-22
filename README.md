# UltraPixel OS — Smart Warehouse 2.0 (modulo WMS)

Magazzino a registro per etichette autoadesive in bobina: bobine singole con metratura, prenotazioni per commessa,
assegnazione in macchina, consumi misurati o stimati, taglio con genealogia, lotti e controllo qualità, colli,
picking e uscita, resi. Interfaccia: una sola schermata **SCANSIONA UN CODICE** per pistola USB in modalità tastiera.

Stato: **Fase 1 implementata e testata in locale** (più il nucleo di Fase 2–3 necessario al caso 4515).
Non ancora installato sul database di produzione e non ancora in uso.

## Architettura trovata (Fase 0, 22/10/2026)

| Pezzo esistente | Dove | Ruolo per il WMS |
|---|---|---|
| PostgreSQL 18.6 `ultrapixel-os` (Render, Oregon, piano 256 MB / 1 GB, 80 MB usati) | schema `public` | **Riusato.** Il WMS vive nello schema separato `wms`, nessuna tabella `public` toccata |
| Docket Etichette (artifact claude.ai, DB dell'artifact) | preventivi, pipeline, prestampa, produzione | Resta com'è. La sua scheda "Magazzino" (giacenza digitata a mano per materiale) va **sostituita in lettura** dal WMS al go-live, per non avere due registri |
| Repo `ultrapixelts-code/ultrapixel` | sito + servizio Flask del preventivatore pubblico | Stesso stack (Python/Flask/gunicorn su Render) riusato per l'API WMS |
| Madiwor | ordini, commesse, schede lavoro PDF | **Nessuna API** (verificato da Gabriele con Madiwor). Integrazione via export strutturato o PDF, vedi sotto |
| Etichette Anima (artifact) | etichette 35×30 mm, gap 3 mm | Stesso formato riusato come profilo di stampa iniziale |

## Struttura

```
migrations/001_wms_core.sql   schema wms: anagrafiche, bobine, commesse, prenotazioni, lotti, colli, spedizioni,
                              registro comandi (idempotenza) e movimenti (append-only, trigger anti UPDATE/DELETE)
wms/engine.py                 Warehouse Transaction Engine: unico punto di scrittura delle giacenze
wms/scan.py                   Scan Context Engine: codice + postazione + contesto → azione
wms/barcodes.py               riconoscimento: prefissi interni, lookup DB, GS1-128, QR solo da domini ammessi
wms/optimizer.py              scelta deterministica bobine (non FIFO) + simulazione carenze per data consegna
wms/madiwor.py                adapter Madiwor: export strutturato / PDF con confidenza e quarantena, import idempotente
wms/ledger.py                 verifica registro ↔ giacenze (usata dopo ogni test e come controllo periodico)
wms/ai.py                     assistente AI: solo strumenti in sola lettura + proposte motivate, mai movimenti
wms/labels.py                 etichette HTML con Code 128 (verificato con decoder zxing)
wms/app.py                    API Flask + anomalie inventario + metriche scansioni
wms/static/                   schermata scanner (PWA, coda offline, suoni, F8 annulla, F9 ristampa)
fixtures/commessa_4515.json   caso reale della specifica, solo per test
tests/                        37 test su PostgreSQL reale
```

## Regole che il codice garantisce

- **Un solo proprietario per dato.** Madiwor: clienti, ordini, commesse, specifiche. WMS: bobine, metrature, ubicazioni, movimenti, prenotazioni, lotti, colli, uscite.
- **Nessuna modifica silenziosa.** Ogni variazione di giacenza è un movimento nel registro append-only; le tabelle bobine/colli sono proiezioni verificabili (`python -m wms.cli verifica`).
- **Idempotenza.** Ogni scansione e ogni comando portano un ID generato sul dispositivo: retry, doppio Invio o coda offline non eseguono mai due volte.
- **Concorrenza.** Righe bloccate in transazione; vincoli DB (una sola assegnazione aperta per bobina, riservato ≤ fisico, nessun negativo).
- **Prenotazione ≠ consumo; stima ≠ consumo.** Una chiusura senza misura lascia la bobina `DA_VERIFICARE` con consumo stimato separato; diventa consumo solo con la misura.
- **Correzioni solo compensative.** F8 annulla l'ultima operazione con uno storno (stesso operatore entro 10 minuti, oppure responsabile). Rettifiche con causale e soglia di autorizzazione.
- **Nessuna sostituzione per somiglianza di nome.** Solo materiale identico o equivalenza validata da una persona.
- **Codici numerici mai indovinati dalla lunghezza.** Si cercano nel DB; se valgono per più oggetti si chiede di scegliere.

## Avvio locale

```bash
pip install -r requirements.txt
export WMS_DATABASE_URL="postgresql://..."      # database di sviluppo, NON quello di produzione
python -m wms.cli migra
python -m wms.cli ubicazione A-01-01 SCAFFALE
python -m wms.cli utente op.xeikon "Operatore Xeikon" OPERATORE_PRODUZIONE UPBX01 1234
python -m wms.cli postazione "Xeikon" MACCHINA XEIKON      # stampa il token da incollare sul PC della macchina
flask --app "wms.app:create_app()" run
```

Test (richiedono un PostgreSQL vuoto dedicato): `WMS_TEST_DATABASE_URL=... pytest tests`.

## Integrazione Madiwor — cosa è verificato e cosa no

| Canale (ordine della specifica) | Stato |
|---|---|
| API ufficiali | **Non esistono** (confermato da Madiwor a Gabriele) |
| Webhook | Nessuno noto |
| Export strutturato | Adapter pronto (`StructuredExportSource`), **mappa colonne vuota**: va compilata su un export reale |
| Scheda lavoro PDF | Adapter pronto con ancore verificate (#numero, CUSTOMER, SPECIFICATIONS); materiale / larghezza / metratura **da calibrare** su un PDF reale; senza quei campi → quarantena |
| Barcode/QR del kiosk | Formato **non noto**: i QR di `ultrapixel.madiwor.net` sono rifiutati finché il percorso non viene configurato in `wms.settings` |

## Piano di migrazione (non distruttivo)

1. **Prova** su un database Render separato (o copia), con dati reali di 2-3 materiali e una postazione.
2. **Installazione**: `python -m wms.cli migra` sul database `ultrapixel-os` (crea solo lo schema `wms`; si toglie con `DROP SCHEMA wms CASCADE` senza effetti sul resto).
3. **Servizio**: web service Render nella **stessa regione del database (Oregon)**: ogni scansione fa ~10 query, in Frankfurt ognuna attraverserebbe l'oceano.
4. **Anagrafica**: caricare in `wms.materials` solo i materiali a listino (i 63 attivi del Docket), non le 580 voci di `public.materials` che contengono descrizioni estratte dai PDF.
5. **Inventario iniziale**: ricevimento di ogni bobina esistente con etichetta UPR (origine metratura `MISURA` o `FORNITORE`).
6. **Go-live**: da quel giorno la scheda "Magazzino" del Docket smette di essere modificabile a mano.
7. **Controllo notturno**: `python -m wms.cli verifica` come cron job; exit 1 = allarme.
