-- UltraPixel OS — Smart Warehouse 2.0 — migrazione 001
-- Additiva e non distruttiva: crea solo lo schema "wms". Non modifica nessuna tabella di "public".
-- I collegamenti verso public.materials / public.customers / public.dies sono riferimenti testuali
-- (os_*_id) senza foreign key, così la migrazione si applica anche se quelle tabelle cambiano.

BEGIN;

CREATE SCHEMA IF NOT EXISTS wms;
-- gen_random_uuid() è nativa da PostgreSQL 13: nessuna estensione richiesta (Render: PostgreSQL 18)

-- ---------------------------------------------------------------------------
-- Funzione comune: tabelle append-only (nessun UPDATE / DELETE consentito)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION wms.forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Tabella % è append-only: % non consentito', TG_TABLE_NAME, TG_OP
    USING ERRCODE = 'insufficient_privilege';
END $$;

-- ---------------------------------------------------------------------------
-- Utenti, ruoli, postazioni
-- ---------------------------------------------------------------------------
CREATE TABLE wms.roles (
  code        text PRIMARY KEY,
  descrizione text NOT NULL,
  livello     int  NOT NULL            -- usato per soglie di autorizzazione
);
INSERT INTO wms.roles(code, descrizione, livello) VALUES
  ('OPERATORE_PRODUZIONE', 'Operatore produzione', 10),
  ('OPERATORE_SPEDIZIONE', 'Operatore spedizione', 10),
  ('RESPONSABILE_MAGAZZINO','Responsabile magazzino', 30),
  ('SUPERVISORE',          'Supervisore', 40),
  ('AMMINISTRATORE',       'Amministratore', 50);

CREATE TABLE wms.users (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username     text NOT NULL UNIQUE,
  display_name text NOT NULL,
  role_code    text NOT NULL REFERENCES wms.roles(code),
  badge_code   text UNIQUE,              -- codice badge scansionabile (opzionale)
  pin_hash     text,                     -- pbkdf2, mai in chiaro
  active       boolean NOT NULL DEFAULT true,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE wms.devices (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome          text NOT NULL UNIQUE,
  postazione    text NOT NULL CHECK (postazione IN ('RICEVIMENTO','MAGAZZINO','MACCHINA','SPEDIZIONE','UFFICIO')),
  location_id   uuid,                    -- ubicazione fisica della postazione (es. la macchina)
  token_hash    text NOT NULL UNIQUE,    -- sha256 del token del dispositivo
  active        boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- Contesto di scansione della postazione (commessa aperta, bobina in attesa di ubicazione, spedizione aperta...)
CREATE TABLE wms.device_context (
  device_id   uuid PRIMARY KEY,
  stato       jsonb NOT NULL DEFAULT '{}',
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE wms.sessions (
  token_hash  text PRIMARY KEY,
  user_id     uuid NOT NULL REFERENCES wms.users(id),
  device_id   uuid NOT NULL REFERENCES wms.devices(id),
  created_at  timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL
);

-- ---------------------------------------------------------------------------
-- Anagrafiche
-- ---------------------------------------------------------------------------
CREATE TABLE wms.suppliers (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome            text NOT NULL,
  os_supplier_id  text UNIQUE,           -- public.suppliers.supplier_id
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE wms.materials (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codice_interno    text NOT NULL UNIQUE,
  os_material_id    text UNIQUE,         -- public.materials.material_id (storico)
  codice_fornitore  text,
  fornitore_id      uuid REFERENCES wms.suppliers(id),
  descrizione       text NOT NULL,
  descrizione_madiwor text,              -- testo esatto con cui Madiwor indica il materiale
  categoria         text NOT NULL DEFAULT 'MATERIA_PRIMA'
                    CHECK (categoria IN ('MATERIA_PRIMA','AUSILIARIO','LAMINA','VERNICE','INCHIOSTRO','ALTRO')),
  larghezza_mm      numeric(8,2),        -- larghezza standard, se esiste
  supporto          text,
  adesivo           text,
  liner             text,
  finitura          text,
  certificazioni    text[] NOT NULL DEFAULT '{}',
  unita_misura      text NOT NULL DEFAULT 'm' CHECK (unita_misura IN ('m','m2','pz','kg')),
  costo_per_um      numeric(12,4),
  soglia_riordino   numeric(12,2),
  stato             text NOT NULL DEFAULT 'ATTIVO' CHECK (stato IN ('ATTIVO','SOSPESO','DISMESSO')),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX materials_descr_madiwor_uq ON wms.materials (lower(descrizione_madiwor))
  WHERE descrizione_madiwor IS NOT NULL;

-- Equivalenze tecniche: solo esplicite e validate da una persona. Mai dedotte dal nome.
CREATE TABLE wms.material_equivalences (
  material_id            uuid NOT NULL REFERENCES wms.materials(id),
  compatible_material_id uuid NOT NULL REFERENCES wms.materials(id),
  compatibility_type     text NOT NULL CHECK (compatibility_type IN ('IDENTICO','SOSTITUTO_APPROVATO')),
  validated_by           uuid NOT NULL REFERENCES wms.users(id),
  validated_at           timestamptz NOT NULL DEFAULT now(),
  constraints            jsonb NOT NULL DEFAULT '{}',   -- es. {"solo_clienti":[...], "no_macchine":[...]}
  active                 boolean NOT NULL DEFAULT true,
  PRIMARY KEY (material_id, compatible_material_id),
  CHECK (material_id <> compatible_material_id)
);

CREATE TABLE wms.warehouse_locations (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codice        text NOT NULL UNIQUE,
  barcode       text NOT NULL UNIQUE,
  zona          text,
  scaffale      text,
  posizione     text,
  tipo          text NOT NULL CHECK (tipo IN ('SCAFFALE','RICEVIMENTO','MACCHINA','SPEDIZIONE','QUARANTENA','ESTERNO')),
  machine_code  text,                    -- per tipo MACCHINA (es. XEIKON / CX3S)
  stato         text NOT NULL DEFAULT 'ATTIVA' CHECK (stato IN ('ATTIVA','BLOCCATA','DISMESSA')),
  created_at    timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE wms.devices ADD CONSTRAINT devices_location_fk FOREIGN KEY (location_id) REFERENCES wms.warehouse_locations(id);

-- Codici esterni noti (barcode fornitore, codici Madiwor) → entità interna
CREATE TABLE wms.barcode_aliases (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code         text NOT NULL,
  namespace    text NOT NULL,             -- es. FORNITORE, MADIWOR_ARTICOLO, MADIWOR_MATERIALE
  entity_type  text NOT NULL CHECK (entity_type IN ('MATERIAL','FINISHED_PRODUCT','LOCATION','SUPPLIER')),
  entity_id    uuid NOT NULL,
  identifica_unita boolean NOT NULL DEFAULT false, -- true solo se il codice identifica una singola bobina
  metri_dichiarati numeric(12,2),          -- metratura ricavabile in modo verificato dal codice, se esiste
  note         text,
  created_by   uuid REFERENCES wms.users(id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (code, namespace, entity_type, entity_id)
);
CREATE INDEX barcode_aliases_code_idx ON wms.barcode_aliases (code);

-- ---------------------------------------------------------------------------
-- Commesse (dati di proprietà Madiwor, copiati e versionati)
-- ---------------------------------------------------------------------------
CREATE TABLE wms.production_jobs (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_madiwor_id  text NOT NULL UNIQUE,        -- numero produzione Madiwor (es. 4515)
  sales_order_id       text,
  cliente_ref          text,                        -- public.customers.customer_id se risolto
  cliente_nome         text NOT NULL,
  articolo_codice      text,
  descrizione          text,
  quantita_ordinata    integer CHECK (quantita_ordinata IS NULL OR quantita_ordinata >= 0),
  data_consegna        date,
  stato                text NOT NULL DEFAULT 'APERTA'
                       CHECK (stato IN ('APERTA','IN_PRODUZIONE','COMPLETATA','ANNULLATA','SOSPESA')),
  specifiche           jsonb NOT NULL DEFAULT '{}',
  fabbisogno_teorico   jsonb NOT NULL DEFAULT '{}',
  source_kind          text NOT NULL,               -- EXPORT_STRUTTURATO / PDF / FIXTURE
  source_hash          text NOT NULL,               -- sha256 del payload normalizzato
  source_version       integer NOT NULL DEFAULT 1,
  last_synced_at       timestamptz NOT NULL DEFAULT now(),
  created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE wms.production_job_materials (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id                 uuid NOT NULL REFERENCES wms.production_jobs(id),
  material_id            uuid REFERENCES wms.materials(id),    -- NULL = materiale non risolto
  material_label_source  text NOT NULL,                         -- testo come arriva da Madiwor
  larghezza_richiesta_mm numeric(8,2),
  metri_teorici          numeric(12,2) NOT NULL CHECK (metri_teorici >= 0),
  metri_prenotati        numeric(12,2) NOT NULL DEFAULT 0 CHECK (metri_prenotati >= 0),
  metri_consumati        numeric(12,2) NOT NULL DEFAULT 0 CHECK (metri_consumati >= 0),   -- solo misurati
  metri_consumo_stimato  numeric(12,2) NOT NULL DEFAULT 0 CHECK (metri_consumo_stimato >= 0),
  metri_scarto           numeric(12,2) NOT NULL DEFAULT 0 CHECK (metri_scarto >= 0),
  attiva                 boolean NOT NULL DEFAULT true,         -- false se la specifica è cambiata
  UNIQUE (job_id, material_label_source, larghezza_richiesta_mm)
);

-- Fasi di lavorazione (WIP). Ogni commessa può avere più fasi e più macchine.
CREATE TABLE wms.job_phases (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id        uuid NOT NULL REFERENCES wms.production_jobs(id),
  seq           int  NOT NULL,
  fase          text NOT NULL CHECK (fase IN ('STAMPA','STAMPA_A_CALDO','VERNICIATURA','RILIEVO','SECONDA_STAMPA',
                                              'FUSTELLATURA','RIFINITURA','RIBOBINATURA','CONTROLLO','IMBALLAGGIO')),
  macchina      text,
  stato         text NOT NULL DEFAULT 'DA_FARE' CHECK (stato IN ('DA_FARE','IN_CORSO','COMPLETATA','RILAVORAZIONE')),
  quantita_out  integer,
  completata_at timestamptz,
  completata_da uuid REFERENCES wms.users(id),
  UNIQUE (job_id, seq)
);

-- ---------------------------------------------------------------------------
-- Bobine (una riga per bobina fisica) — proiezione del registro movimenti
-- ---------------------------------------------------------------------------
CREATE TABLE wms.material_rolls (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  barcode                 text NOT NULL UNIQUE,
  material_id             uuid NOT NULL REFERENCES wms.materials(id),
  lotto_fornitore         text,
  parent_roll_id          uuid REFERENCES wms.material_rolls(id),
  larghezza_mm            numeric(8,2) NOT NULL CHECK (larghezza_mm > 0),
  metri_iniziali          numeric(12,2) NOT NULL CHECK (metri_iniziali >= 0),
  metri_residui           numeric(12,2) NOT NULL CHECK (metri_residui >= 0),   -- dato fisico verificato
  metri_riservati         numeric(12,2) NOT NULL DEFAULT 0 CHECK (metri_riservati >= 0),
  metri_stimati           numeric(12,2) CHECK (metri_stimati IS NULL OR metri_stimati >= 0), -- stima NON verificata
  ubicazione_id           uuid REFERENCES wms.warehouse_locations(id),
  stato                   text NOT NULL CHECK (stato IN ('DISPONIBILE','IN_PRODUZIONE','DA_VERIFICARE','ESAURITA','TAGLIATA','QUARANTENA','ANNULLATA')),
  assigned_job_id         uuid REFERENCES wms.production_jobs(id),
  data_ricezione          timestamptz NOT NULL DEFAULT now(),
  costo_per_m             numeric(12,4),
  origine_dato_metratura  text NOT NULL CHECK (origine_dato_metratura IN ('FORNITORE','MISURA','STIMA','CALCOLATO')),
  ultima_verifica         timestamptz,
  version                 integer NOT NULL DEFAULT 1,
  CONSTRAINT riservati_entro_residui CHECK (metri_riservati <= metri_residui)
);
CREATE INDEX material_rolls_material_idx ON wms.material_rolls (material_id, stato);

CREATE TABLE wms.material_reservations (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id         uuid NOT NULL REFERENCES wms.production_jobs(id),
  job_material_id uuid NOT NULL REFERENCES wms.production_job_materials(id),
  roll_id        uuid NOT NULL REFERENCES wms.material_rolls(id),
  quantity       numeric(12,2) NOT NULL CHECK (quantity > 0),
  status         text NOT NULL DEFAULT 'ATTIVA' CHECK (status IN ('ATTIVA','CONSUMATA','RILASCIATA')),
  created_at     timestamptz NOT NULL DEFAULT now(),
  closed_at      timestamptz
);
CREATE UNIQUE INDEX reservations_one_active_per_roll_job
  ON wms.material_reservations (job_material_id, roll_id) WHERE status = 'ATTIVA';

-- Montaggio di una bobina su una macchina per una commessa
CREATE TABLE wms.roll_assignments (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id          uuid NOT NULL REFERENCES wms.production_jobs(id),
  job_material_id uuid NOT NULL REFERENCES wms.production_job_materials(id),
  roll_id         uuid NOT NULL REFERENCES wms.material_rolls(id),
  location_id     uuid NOT NULL REFERENCES wms.warehouse_locations(id),
  metri_inizio    numeric(12,2) NOT NULL,
  inizio_at       timestamptz NOT NULL DEFAULT now(),
  stato           text NOT NULL DEFAULT 'IN_CORSO' CHECK (stato IN ('IN_CORSO','CHIUSA','DA_VERIFICARE','ANNULLATA')),
  metri_fine      numeric(12,2),
  consumo_tipo    text CHECK (consumo_tipo IN ('MISURATO','MACCHINA','STIMATO')),
  metri_utilizzati numeric(12,2),
  metri_scarto    numeric(12,2),
  fine_at         timestamptz
);
CREATE UNIQUE INDEX one_open_assignment_per_roll ON wms.roll_assignments (roll_id) WHERE stato = 'IN_CORSO';

-- ---------------------------------------------------------------------------
-- Prodotti finiti, lotti, colli
-- ---------------------------------------------------------------------------
CREATE TABLE wms.finished_products (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_sku_id  text NOT NULL,        -- ID prodotto Madiwor (es. 117951)
  versione         text NOT NULL DEFAULT '1',
  cliente_ref      text,
  codice_articolo  text NOT NULL,
  descrizione      text,
  specifiche       jsonb NOT NULL DEFAULT '{}',
  UNIQUE (external_sku_id, versione)
);

CREATE TABLE wms.production_lots (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codice              text NOT NULL UNIQUE,
  production_job_id   uuid NOT NULL REFERENCES wms.production_jobs(id),
  finished_product_id uuid NOT NULL REFERENCES wms.finished_products(id),
  quantita_prodotta   integer NOT NULL DEFAULT 0 CHECK (quantita_prodotta >= 0),
  quantita_conforme   integer NOT NULL DEFAULT 0 CHECK (quantita_conforme >= 0),
  quantita_scartata   integer NOT NULL DEFAULT 0 CHECK (quantita_scartata >= 0),
  quantita_confezionata integer NOT NULL DEFAULT 0 CHECK (quantita_confezionata >= 0),
  stato_qualita       text NOT NULL DEFAULT 'IN_ATTESA'
                      CHECK (stato_qualita IN ('IN_ATTESA','APPROVATO','RESPINTO','RILAVORAZIONE')),
  created_at          timestamptz NOT NULL DEFAULT now(),
  CHECK (quantita_conforme + quantita_scartata <= quantita_prodotta),
  CHECK (quantita_confezionata <= quantita_conforme)
);

CREATE TABLE wms.shipments (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  barcode              text NOT NULL UNIQUE,
  external_madiwor_ref text UNIQUE,         -- riferimento consegna Madiwor, se esiste
  sales_order_id       text,
  cliente_ref          text,
  cliente_nome         text NOT NULL,
  stato                text NOT NULL DEFAULT 'APERTA' CHECK (stato IN ('APERTA','PRONTA','USCITA','ANNULLATA')),
  uscita_at            timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE wms.shipment_lines (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  shipment_id          uuid NOT NULL REFERENCES wms.shipments(id),
  finished_product_id  uuid NOT NULL REFERENCES wms.finished_products(id),
  production_job_id    uuid REFERENCES wms.production_jobs(id),   -- vincolo di riserva opzionale
  quantita_richiesta   integer NOT NULL CHECK (quantita_richiesta > 0),
  quantita_preparata   integer NOT NULL DEFAULT 0 CHECK (quantita_preparata >= 0),
  UNIQUE (shipment_id, finished_product_id, production_job_id)
);

CREATE TABLE wms.finished_goods_packages (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  barcode          text NOT NULL UNIQUE,
  lotto_id         uuid NOT NULL REFERENCES wms.production_lots(id),
  quantita         integer NOT NULL CHECK (quantita > 0),
  unita_misura     text NOT NULL DEFAULT 'pz',
  ubicazione_id    uuid REFERENCES wms.warehouse_locations(id),
  stato            text NOT NULL DEFAULT 'DISPONIBILE'
                   CHECK (stato IN ('DISPONIBILE','PRELEVATO','SPEDITO','RESO','BLOCCATO')),
  shipment_line_id uuid REFERENCES wms.shipment_lines(id),
  version          integer NOT NULL DEFAULT 1,
  data_creazione   timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Registro: comandi (idempotenza) e movimenti (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE wms.commands (
  event_id      uuid PRIMARY KEY,                -- generato dal client: retry = stesso event_id
  command_type  text NOT NULL,
  payload_hash  text NOT NULL,
  payload       jsonb NOT NULL,
  result        jsonb NOT NULL,
  operatore_id  uuid REFERENCES wms.users(id),
  device_id     uuid REFERENCES wms.devices(id),
  client_ts     timestamptz,
  offline       boolean NOT NULL DEFAULT false,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER commands_append_only BEFORE UPDATE OR DELETE ON wms.commands
  FOR EACH ROW EXECUTE FUNCTION wms.forbid_mutation();

CREATE TABLE wms.inventory_movements (
  id              bigserial PRIMARY KEY,
  event_id        uuid NOT NULL UNIQUE,         -- derivato dal comando: uuid5(command_event_id, n)
  command_event_id uuid NOT NULL REFERENCES wms.commands(event_id) DEFERRABLE INITIALLY DEFERRED,
  ts              timestamptz NOT NULL DEFAULT now(),
  tipo_movimento  text NOT NULL CHECK (tipo_movimento IN (
                    'RICEVIMENTO','SPOSTAMENTO','PRENOTAZIONE','RILASCIO_PRENOTAZIONE',
                    'ASSEGNAZIONE','CONSUMO','SCARTO','RIENTRO','VERIFICA_METRATURA',
                    'TAGLIO_USCITA','TAGLIO_INGRESSO','RETTIFICA','STORNO',
                    'PRODUZIONE','CONTROLLO_QUALITA','CONFEZIONAMENTO','PICKING','ANNULLO_PICKING',
                    'USCITA','RESO','BLOCCO','SBLOCCO')),
  entity_type     text NOT NULL CHECK (entity_type IN ('ROLL','PACKAGE','LOT','RESERVATION')),
  entity_id       uuid NOT NULL,
  quantita        numeric(12,2) NOT NULL DEFAULT 0,   -- con segno: + entra, − esce
  unita_misura    text NOT NULL,
  origine_id      uuid REFERENCES wms.warehouse_locations(id),
  destinazione_id uuid REFERENCES wms.warehouse_locations(id),
  commessa_id     uuid REFERENCES wms.production_jobs(id),
  operatore_id    uuid REFERENCES wms.users(id),
  device_id       uuid REFERENCES wms.devices(id),
  fonte           text NOT NULL CHECK (fonte IN ('SCANNER','UI','MADIWOR','MACCHINA','SISTEMA')),
  causale         text,
  reference_id    uuid,
  reversal_of     bigint REFERENCES wms.inventory_movements(id),
  metadata        jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX movements_entity_idx ON wms.inventory_movements (entity_type, entity_id, id);
CREATE INDEX movements_job_idx ON wms.inventory_movements (commessa_id);
CREATE UNIQUE INDEX movements_single_reversal ON wms.inventory_movements (reversal_of) WHERE reversal_of IS NOT NULL;
CREATE TRIGGER movements_append_only BEFORE UPDATE OR DELETE ON wms.inventory_movements
  FOR EACH ROW EXECUTE FUNCTION wms.forbid_mutation();

-- ---------------------------------------------------------------------------
-- Scansioni, sincronizzazione, errori, audit, AI, inventari, stampa
-- ---------------------------------------------------------------------------
CREATE TABLE wms.scan_events (
  id             bigserial PRIMARY KEY,
  ts             timestamptz NOT NULL DEFAULT now(),
  client_scan_id uuid UNIQUE,
  client_ts      timestamptz,
  device_id      uuid REFERENCES wms.devices(id),
  user_id        uuid REFERENCES wms.users(id),
  raw_code       text NOT NULL,
  tipo_risolto   text,
  entita_id      uuid,
  azione_proposta text,
  esito          text NOT NULL,
  offline        boolean NOT NULL DEFAULT false,
  dettagli       jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX scan_events_device_ts ON wms.scan_events (device_id, ts DESC);
CREATE TRIGGER scan_events_append_only BEFORE UPDATE OR DELETE ON wms.scan_events
  FOR EACH ROW EXECUTE FUNCTION wms.forbid_mutation();

CREATE TABLE wms.sync_events (
  id            bigserial PRIMARY KEY,
  ts            timestamptz NOT NULL DEFAULT now(),
  source        text NOT NULL,
  external_id   text NOT NULL,
  entity        text NOT NULL,
  esito         text NOT NULL CHECK (esito IN ('CREATO','AGGIORNATO','INVARIATO','ANNULLATO','QUARANTENA','ERRORE')),
  payload_hash  text,
  dettagli      jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE wms.integration_errors (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ts             timestamptz NOT NULL DEFAULT now(),
  source         text NOT NULL,
  document_ref   text,
  errore         text NOT NULL,
  confidence     numeric(4,3),
  payload        jsonb NOT NULL DEFAULT '{}',
  in_quarantena  boolean NOT NULL DEFAULT true,
  risolto_at     timestamptz,
  risolto_da     uuid REFERENCES wms.users(id)
);

CREATE TABLE wms.audit_logs (
  id          bigserial PRIMARY KEY,
  ts          timestamptz NOT NULL DEFAULT now(),
  actor_type  text NOT NULL CHECK (actor_type IN ('UTENTE','SISTEMA','AI','INTEGRAZIONE')),
  actor_id    text,
  azione      text NOT NULL,
  entita      text,
  entita_id   text,
  prima       jsonb,
  dopo        jsonb,
  motivo      text
);
CREATE TRIGGER audit_logs_append_only BEFORE UPDATE OR DELETE ON wms.audit_logs
  FOR EACH ROW EXECUTE FUNCTION wms.forbid_mutation();

CREATE TABLE wms.ai_recommendations (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ts            timestamptz NOT NULL DEFAULT now(),
  provider      text NOT NULL,
  tipo          text NOT NULL,
  oggetto_ref   text,
  suggerimento  jsonb NOT NULL,
  motivazione   text NOT NULL,
  dati_usati    jsonb NOT NULL,
  affidabilita  numeric(4,3) NOT NULL CHECK (affidabilita BETWEEN 0 AND 1),
  stato         text NOT NULL DEFAULT 'PROPOSTO' CHECK (stato IN ('PROPOSTO','ACCETTATO','RIFIUTATO','SCADUTO')),
  deciso_da     uuid REFERENCES wms.users(id),
  deciso_at     timestamptz
);

CREATE TABLE wms.inventory_counts (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ts             timestamptz NOT NULL DEFAULT now(),
  entity_type    text NOT NULL CHECK (entity_type IN ('ROLL','PACKAGE','LOCATION')),
  entity_id      uuid NOT NULL,
  motivo         text NOT NULL,
  atteso         numeric(12,2),
  contato        numeric(12,2),
  stato          text NOT NULL DEFAULT 'DA_CONTARE' CHECK (stato IN ('DA_CONTARE','CONTATO','RETTIFICATO','CHIUSO')),
  contato_da     uuid REFERENCES wms.users(id)
);

CREATE TABLE wms.printer_profiles (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome        text NOT NULL UNIQUE,
  formato     text NOT NULL CHECK (formato IN ('HTML_PDF','ZPL')),
  larghezza_mm numeric(6,2) NOT NULL,
  altezza_mm   numeric(6,2) NOT NULL,
  gap_mm       numeric(6,2) NOT NULL DEFAULT 3,
  dpi          int NOT NULL DEFAULT 203,
  opzioni      jsonb NOT NULL DEFAULT '{}'
);
-- Profilo di partenza: stessa etichetta 35×30 mm con 3 mm di distanza già usata da "Etichette Anima".
INSERT INTO wms.printer_profiles(nome, formato, larghezza_mm, altezza_mm, gap_mm)
  VALUES ('Etichetta 35x30 (come Etichette Anima)', 'HTML_PDF', 35, 30, 3);

-- Contatori per barcode interni leggibili (UPR-000123, UPC-000045, ...)
CREATE TABLE wms.counters (
  name   text PRIMARY KEY,
  value  bigint NOT NULL DEFAULT 0
);
INSERT INTO wms.counters(name) VALUES ('ROLL'),('PACKAGE'),('LOT'),('SHIPMENT');

-- Configurazione (regole barcode, domini ammessi nei QR, parametri)
CREATE TABLE wms.settings (
  key        text PRIMARY KEY,
  value      jsonb NOT NULL,
  note       text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO wms.settings(key, value, note) VALUES
  ('qr_domini_ammessi', '["ultrapixel.madiwor.net"]',
   'Dominio Madiwor visto nei link preventivo. Percorsi dei QR commessa DA VERIFICARE su una scheda reale.'),
  ('qr_percorsi_commessa', '[]',
   'Regex dei percorsi QR che identificano una commessa. Vuoto finché non si vede un QR reale: i QR restano "non riconosciuti".'),
  ('finestra_doppia_scansione_s', '3',
   'Stessa lettura dallo stesso dispositivo entro N secondi = doppia scansione accidentale.'),
  ('tolleranza_larghezza_mm', '0',
   'Differenza ammessa tra larghezza bobina e larghezza richiesta senza taglio.'),
  ('soglia_rettifica_metri', '50',
   'Rettifiche oltre questa soglia (in valore assoluto) richiedono ruolo RESPONSABILE_MAGAZZINO o superiore.'),
  ('finestra_annullo_minuti', '10',
   'Entro quanti minuti l''operatore può annullare da solo la propria ultima operazione.');

-- ---------------------------------------------------------------------------
-- Vista giacenze: separa fisico, riservato, disponibile, stimato e in arrivo
-- ---------------------------------------------------------------------------
CREATE VIEW wms.v_giacenze_materiali AS
SELECT m.id AS material_id, m.codice_interno, m.descrizione,
       r.larghezza_mm,
       count(r.id) FILTER (WHERE r.stato NOT IN ('ESAURITA','TAGLIATA'))                    AS bobine,
       coalesce(sum(r.metri_residui)   FILTER (WHERE r.stato NOT IN ('ESAURITA','TAGLIATA')),0) AS metri_fisici,
       coalesce(sum(r.metri_riservati) FILTER (WHERE r.stato NOT IN ('ESAURITA','TAGLIATA')),0) AS metri_riservati,
       coalesce(sum(r.metri_residui - r.metri_riservati)
                FILTER (WHERE r.stato = 'DISPONIBILE'),0)                                  AS metri_disponibili,
       coalesce(sum(r.metri_stimati)   FILTER (WHERE r.stato = 'DA_VERIFICARE'),0)          AS metri_stimati_da_verificare,
       NULL::numeric AS metri_in_arrivo,   -- ordini d'acquisto non ancora gestiti: dato assente, non zero
       m.soglia_riordino
FROM wms.materials m
LEFT JOIN wms.material_rolls r ON r.material_id = m.id
GROUP BY m.id, r.larghezza_mm;

COMMIT;
