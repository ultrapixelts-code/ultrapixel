<?php
// Portale clienti UltraPixel — utenti e impostazioni.
// Le password non sono scritte qui: solo la loro impronta (password_hash). Per cambiarne una:
//   php -r "echo password_hash('nuova password', PASSWORD_DEFAULT);"
// e sostituisci il valore 'hash' dell'utente.
if (!defined('UPX_PORTAL')) { http_response_code(404); exit; }
return [
  'users' => [
    // clienti: vedono solo le etichette con il loro codice cliente e mandano ordini
    'debroas'  => ['hash' => '$2y$10$f5WGmNr4vCcqw84eZXw7ceLPSPd1Acw6rIW.fnTzOoO4/amo2Y0bq', 'role' => 'client', 'name' => 'Groupe Debroas', 'customer' => '887',
                   'address' => "Groupe Debroas\n1C chemin des Beaumes\n07260 Joyeuse\nFrance"],
    // UltraPixel: caricano le schede tecniche, vedono tutti gli ordini
    'thierry'  => ['hash' => '$2y$10$OhcBvh9/VPmtsLQysSDmEOtRY6UyzXP63ics6U27cdSPcZbz5s0A6', 'role' => 'staff', 'name' => 'Thierry Vial'],
    'gabriele' => ['hash' => '$2y$10$njNgm3jU1/CR9ZiBIO2AmOQBnv1eRbepFg3VFu3jfE0GadCWf.HWm', 'role' => 'staff', 'name' => 'Gabriele Russian'],
  ],
  'customers'    => ['887' => 'Groupe Debroas'],
  'default_customer' => '887',             // codice usato se la scheda PDF non riporta il cliente
  'order_email'  => 'info@ultrapixel.it, thierry.vial@ultrapixel.fr',   // chi riceve gli ordini (modificabile dal portale)
  'mail_from'    => 'info@ultrapixel.it',
];
