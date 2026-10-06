# UltraPixel — backend moduli e statistiche (PHP + MySQL, per Keliweb)

Riceve le richieste dai moduli del sito, le salva, avvisa via email e offre un pannello riservato.

## Installazione
1. Nel pannello hosting crea un database MySQL e un utente.
2. Carica la cartella `backend/` nella radice del sito (risultato: `https://ultrapixel.it/backend/`).
3. Copia `config.sample.php` in `config.php` e compila: dati database, `origins` (domini del sito), `notify_to`, `mail_from` (una casella che esiste sul dominio), `admin_user`.
4. Genera l'hash della password admin: `php -r "echo password_hash('LA-TUA-PASSWORD', PASSWORD_DEFAULT);"` e incollalo in `admin_hash`.
5. Le tabelle si creano da sole alla prima richiesta.
6. Nel sito, in `content/en.json` → `site`: `formEndpoint` = `https://ultrapixel.it/backend/api/lead.php`, `analyticsEndpoint` = `https://ultrapixel.it/backend/api/event.php`; poi `python3 build.py`.

## Indirizzi
- `api/lead.php` (POST JSON) — richieste dai moduli
- `api/event.php` (POST JSON) — eventi statistici senza cookie
- `admin/` — elenco richieste, stato e note; `admin/stats.php`; `admin/export.php?f=csv|xlsx`

## Verifiche dopo l'installazione
- `https://ultrapixel.it/backend/config.php` e `lib.php` devono rispondere 403 (protezione `.htaccess`, richiede Apache/LiteSpeed).
- Invia un modulo di prova da ogni lingua e controlla che arrivi l'email e che compaia in `admin/`.
- Se `admin/` rifiuta sempre la password, l'hosting non passa l'intestazione Authorization: vedi `.htaccess`.

Provato in locale con PHP e SQLite. Non ancora provati: MySQL, `.htaccess` su Apache, invio email reale.
