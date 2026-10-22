-- Operatore predefinito per postazione: con un solo operatore non serve il badge.
-- Se più avanti ci saranno più persone, basta lasciare il campo vuoto e tornare al login con badge.
BEGIN;
ALTER TABLE wms.devices ADD COLUMN utente_predefinito uuid REFERENCES wms.users(id);
COMMIT;
