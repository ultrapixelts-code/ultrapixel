-- Fine lavoro: l'operatore indica a occhio quanto è rimasto sulla bobina (finita, 1/4, 2/4, 3/4).
-- È una stima: il dato definitivo resta lo storico della macchina; la differenza viene controllata.
ALTER TABLE wms.roll_assignments
  ADD COLUMN quarti_dichiarati smallint CHECK (quarti_dichiarati BETWEEN 0 AND 4);

INSERT INTO wms.settings(key, value, note) VALUES
  ('tolleranza_quarti', '0.125',
   'Differenza ammessa tra i quarti indicati dall''operatore e il dato macchina, come frazione della bobina intera.')
ON CONFLICT (key) DO NOTHING;
