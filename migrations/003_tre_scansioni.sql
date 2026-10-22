-- Flusso a tre scansioni: il sistema decide posizione e istruzioni, il consumo arriva dalla macchina.
BEGIN;

-- Ubicazioni: capienza, ripiano e area servono a scegliere il posto senza chiederlo all'operatore
ALTER TABLE wms.warehouse_locations
  ADD COLUMN capacita_bobine int CHECK (capacita_bobine IS NULL OR capacita_bobine > 0),
  ADD COLUMN livello int,                                  -- 1 = ripiano più basso
  ADD COLUMN area text CHECK (area IN ('SCORTA','PRONTO_MACCHINA','RIMANENZE')),
  ADD COLUMN macchina_vicina text,                         -- per area PRONTO_MACCHINA (es. CX3S)
  ADD COLUMN istruzioni text;                              -- come appoggiare la bobina in questo posto

-- Materiali: metratura nominale dichiarata dal fornitore e istruzioni di stoccaggio
ALTER TABLE wms.materials
  ADD COLUMN metri_nominali numeric(12,2) CHECK (metri_nominali IS NULL OR metri_nominali > 0),
  ADD COLUMN istruzioni_stoccaggio text;

-- Una posizione decisa dal sistema è "assegnata"; diventa "confermata" quando qualcuno la legge lì
ALTER TABLE wms.material_rolls ADD COLUMN ubicazione_confermata boolean NOT NULL DEFAULT true;

-- Montaggio partito da una metratura stimata (bobina riusata prima che arrivassero i dati macchina)
ALTER TABLE wms.roll_assignments
  ADD COLUMN inizio_verificato boolean NOT NULL DEFAULT true,
  ADD COLUMN macchina text;

-- Storico di stampa della macchina (es. export "print history" della Xeikon CX3S)
CREATE TABLE wms.machine_runs (
  id            bigserial PRIMARY KEY,
  macchina      text NOT NULL,
  job_name      text,
  medium        text,
  stato         text,
  fine_at       timestamptz NOT NULL,
  durata_s      int,
  metri         numeric(12,3) NOT NULL CHECK (metri >= 0),
  file_origine  text,
  importato_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (macchina, fine_at, job_name, metri)
);
CREATE INDEX machine_runs_win ON wms.machine_runs (macchina, fine_at);

CREATE TABLE wms.machine_data_coverage (
  macchina    text PRIMARY KEY,
  coperto_fino timestamptz NOT NULL       -- fino a quando abbiamo lo storico completo
);

INSERT INTO wms.settings(key, value, note) VALUES
  ('finestra_doppia_scansione_s_RICEVIMENTO', '1',
   'In ricevimento si leggono bobine uguali una dopo l''altra: finestra più corta (solo rimbalzo della pistola).'),
  ('soglia_rimanenza_metri', '100', 'Sotto questa metratura una bobina va nell''area rimanenze.'),
  ('soglia_bobina_pesante_metri', '500', 'Da questa metratura in su la bobina va su un ripiano basso.'),
  ('giorni_pronto_macchina', '2', 'Bobine prenotate per commesse in consegna entro N giorni → area pronto macchina.')
ON CONFLICT (key) DO NOTHING;

COMMIT;
