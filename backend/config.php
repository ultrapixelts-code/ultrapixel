<?php
// UltraPixel site backend — ready to use on Keliweb, nothing to fill in.
// Requests are saved in data/leads.sqlite (created by itself) and emailed to notify_to with the file attached.
return [
  'db_dsn'      => '',                     // empty = SQLite in backend/data/. For MySQL: 'mysql:host=localhost;dbname=…;charset=utf8mb4' plus db_user / db_pass
  'db_user'     => null,
  'db_pass'     => null,
  // Sites allowed to send requests (no trailing slash).
  'origins'     => ['https://ultrapixel.it', 'https://www.ultrapixel.it', 'https://ultrapixel.fr', 'https://www.ultrapixel.fr'],
  'notify_to'   => 'info@ultrapixel.it',
  'mail_from'   => 'info@ultrapixel.it',
  // Admin pages (backend/admin/) stay closed until a password hash is set here:
  //   php -r "echo password_hash('your password', PASSWORD_DEFAULT);"
  'admin_user'  => 'admin',
  'admin_hash'  => '',
];
