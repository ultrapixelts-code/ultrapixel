<?php
// Copy this file to config.php and fill it in. config.php must never be public: .htaccess blocks it.
return [
  'db_dsn'      => 'mysql:host=localhost;dbname=zbduzvpf_ultrapixel;charset=utf8mb4',
  'db_user'     => 'zbduzvpf_ultrapixel',
  'db_pass'     => 'DATABASE_PASSWORD',
  // Site origins allowed to send requests (no trailing slash).
  'origins'     => ['https://ultrapixel.it', 'https://www.ultrapixel.it', 'https://ultrapixel-homepage.onrender.com'],
  'notify_to'   => 'info@ultrapixel.it',
  'mail_from'   => 'sito@ultrapixel.it',          // a mailbox of the same domain
  'admin_user'  => 'admin',
  // Generate with:  php -r "echo password_hash('your password', PASSWORD_DEFAULT);"
  'admin_hash'  => '',
];
