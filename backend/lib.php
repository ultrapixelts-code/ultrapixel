<?php
// UltraPixel website backend (PHP + MySQL). No IP address is stored, in leads or in events.
declare(strict_types=1);

const STATUSES = ['new', 'contacted', 'samples_sent', 'quoted', 'won', 'lost', 'spam'];
const LEAD_FIELDS = ['name', 'company', 'country', 'email', 'sector', 'request_type', 'message', 'lang', 'source_page', 'landing_page', 'referrer', 'utm_source', 'utm_medium', 'utm_campaign'];
const EVENTS = ['page_view', 'cta_click', 'form_start', 'form_success', 'form_error'];
const EXPORT = ['id', 'created_at', 'status', 'name', 'company', 'country', 'email', 'sector', 'request_type', 'message', 'lang', 'source', 'utm_source', 'utm_medium', 'utm_campaign', 'referrer', 'landing_page', 'source_page', 'notes', 'updated_at'];

function cfg(): array {
  static $c; if ($c === null) { $f = getenv('UP_CONFIG') ?: __DIR__ . '/config.php'; if (!is_file($f)) { http_response_code(500); exit('Not configured'); } $c = require $f; }
  return $c;
}

/** Private folder for the database and the files people send (blocked from the web by its own .htaccess). */
function data_dir(string $sub = ''): string {
  $d = __DIR__ . '/data' . ($sub !== '' ? "/$sub" : '');
  if (!is_dir($d)) @mkdir($d, 0750, true);
  return $d;
}

function db(): PDO {
  static $p; if ($p) return $p;
  $c = cfg();
  $dsn = $c['db_dsn'] ?: 'sqlite:' . data_dir() . '/leads.sqlite';
  $p = new PDO($dsn, $c['db_user'] ?? null, $c['db_pass'] ?? null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
  $my = $p->getAttribute(PDO::ATTR_DRIVER_NAME) === 'mysql';
  $id = $my ? 'INT AUTO_INCREMENT PRIMARY KEY' : 'INTEGER PRIMARY KEY AUTOINCREMENT';
  $tail = $my ? ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4' : '';
  $p->exec("CREATE TABLE IF NOT EXISTS web_leads (id $id, created_at DATETIME NOT NULL, client_ts VARCHAR(40), name VARCHAR(300), company VARCHAR(300), country VARCHAR(300), email VARCHAR(300),
    sector VARCHAR(300), request_type VARCHAR(300), message TEXT, lang VARCHAR(10), source_page VARCHAR(300), landing_page VARCHAR(300), referrer TEXT, utm_source VARCHAR(300), utm_medium VARCHAR(300),
    utm_campaign VARCHAR(300), source VARCHAR(30), status VARCHAR(20) NOT NULL DEFAULT 'new', notes TEXT, updated_at DATETIME NULL, email_sent INT DEFAULT 0)$tail");
  try { $p->exec('ALTER TABLE web_leads ADD COLUMN file VARCHAR(300) NULL'); } catch (Throwable $e) {}   // already there
  $p->exec("CREATE TABLE IF NOT EXISTS web_events (id $id, created_at DATETIME NOT NULL, event VARCHAR(30), path VARCHAR(300), lang VARCHAR(10), source VARCHAR(30), utm_source VARCHAR(120),
    utm_medium VARCHAR(120), utm_campaign VARCHAR(120), ref_host VARCHAR(200), landing_page VARCHAR(300), props TEXT)$tail");
  $p->exec("CREATE TABLE IF NOT EXISTS web_rate (k VARCHAR(64) NOT NULL, t INT NOT NULL)$tail");
  return $p;
}

function classify(?string $utm, ?string $ref): string {
  $u = strtolower((string)$utm); $s = $u . ' ' . strtolower((string)$ref);
  if (str_contains($s, 'chatgpt') || str_contains($s, 'openai')) return 'chatgpt';
  foreach (['perplexity', 'copilot', 'gemini', 'claude'] as $x) if (str_contains($s, $x)) return 'ai_other';
  if (str_contains($s, 'linkedin') || str_contains($s, 'lnkd')) return 'linkedin';
  if (str_contains($s, 'google.') || $u === 'google') return 'google';
  foreach (['bing', 'duckduckgo', 'yahoo', 'ecosia', 'qwant'] as $x) if (str_contains($s, $x)) return 'search_other';
  foreach (['instagram', 'facebook'] as $x) if (str_contains($s, $x)) return 'social_other';
  return trim($s) === '' ? 'direct' : 'referral';
}

function clip($v, int $n = 300): string { return mb_substr(trim((string)($v ?? '')), 0, $n); }
function h($v): string { return htmlspecialchars((string)($v ?? ''), ENT_QUOTES, 'UTF-8'); }
function now(): string { return gmdate('Y-m-d H:i:s'); }

/** CORS + origin check for the public endpoints. Ends the request on OPTIONS or a foreign origin. */
function api_guard(): void {
  $o = $_SERVER['HTTP_ORIGIN'] ?? '';
  $ok = in_array($o, cfg()['origins'], true);
  if ($ok) { header("Access-Control-Allow-Origin: $o"); header('Vary: Origin'); header('Access-Control-Allow-Headers: Content-Type, Accept'); header('Access-Control-Allow-Methods: POST, OPTIONS'); }
  if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') { http_response_code(204); exit; }
  if (!$ok) { http_response_code(403); exit; }
  if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') { http_response_code(405); exit; }
}

/** Request fields: JSON body, or multipart form fields when the request carries a file. */
function body(): array {
  if (stripos($_SERVER['CONTENT_TYPE'] ?? '', 'multipart/form-data') === 0) {
    if (!$_POST && (int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 0) { http_response_code(413); header('Content-Type: application/json'); exit('{"error":"too_big"}'); }   // over post_max_size: PHP dropped everything
    return $_POST;
  }
  $raw = (string)file_get_contents(getenv('UP_TEST_BODY') ?: 'php://input', false, null, 0, 32768);
  $d = json_decode($raw, true);
  if (!is_array($d)) { http_response_code(400); exit; }
  return $d;
}

/** Rate limit keyed on a salted daily hash of the caller; the address itself is never stored. */
function limited(string $scope, int $max, int $per): bool {
  $k = hash('sha256', $scope . '|' . gmdate('Y-m-d') . '|' . ($_SERVER['REMOTE_ADDR'] ?? '') . '|' . (cfg()['db_dsn'] ?: __DIR__));
  $t = time(); $p = db();
  $p->prepare('DELETE FROM web_rate WHERE t < ?')->execute([$t - 86400]);
  $q = $p->prepare('SELECT COUNT(*) FROM web_rate WHERE k = ? AND t > ?'); $q->execute([$k, $t - $per]);
  if ((int)$q->fetchColumn() >= $max) return true;
  $p->prepare('INSERT INTO web_rate (k, t) VALUES (?, ?)')->execute([$k, $t]);
  return false;
}

const FILE_EXT = ['pdf', 'ai', 'eps', 'svg', 'jpg', 'jpeg', 'png', 'webp', 'heic', 'heif', 'tif', 'tiff', 'zip'];
const FILE_MAX = 30 * 1024 * 1024;     // what the site lets people send
const MAIL_MAX = 12 * 1024 * 1024;     // larger files stay on the server and the email says where

/** Keeps the file sent with a request. Returns [stored path, original name, size, problem]; problem is '' when all went well. */
function save_upload(): array {
  $f = $_FILES['file'] ?? null;
  if (!$f || ($f['error'] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) return ['', '', 0, ''];
  $name = clip(basename(str_replace('\\', '/', (string)$f['name'])), 150);
  if ($f['error'] === UPLOAD_ERR_INI_SIZE || $f['error'] === UPLOAD_ERR_FORM_SIZE || $f['size'] > FILE_MAX) return ['', $name, (int)$f['size'], 'too large'];
  if ($f['error'] !== UPLOAD_ERR_OK) return ['', $name, 0, 'upload error ' . $f['error']];
  $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
  if (!in_array($ext, FILE_EXT, true)) return ['', $name, (int)$f['size'], 'file type not accepted'];
  $safe = trim(preg_replace('/[^A-Za-z0-9._-]+/', '-', pathinfo($name, PATHINFO_FILENAME)), '-.') ?: 'file';
  $dest = data_dir('files/' . gmdate('Y-m')) . '/' . gmdate('Ymd-His') . '-' . bin2hex(random_bytes(3)) . '-' . substr($safe, 0, 60) . '.' . $ext;
  $ok = getenv('UP_TEST_MAIL') ? rename($f['tmp_name'], $dest) : move_uploaded_file($f['tmp_name'], $dest);
  return $ok ? [$dest, $name, (int)$f['size'], ''] : ['', $name, (int)$f['size'], 'could not be saved'];
}

function notify(array $r, int $id, array $file = ['', '', 0, '']): bool {
  $c = cfg(); if (empty($c['notify_to'])) return false;
  $nl = fn($s) => str_replace(["\r", "\n"], ' ', (string)$s);
  $lines = [];
  foreach (['name', 'company', 'country', 'email', 'sector', 'request_type', 'lang'] as $k) $lines[] = "$k: " . ($r[$k] ?? '');
  $lines[] = ''; $lines[] = $r['message']; $lines[] = ''; $lines[] = 'source: ' . $r['source'];
  foreach (['utm_source', 'utm_medium', 'utm_campaign', 'referrer', 'landing_page', 'source_page'] as $k) $lines[] = "$k: " . ($r[$k] ?? '');
  [$path, $fname, $fsize, $fprob] = $file;
  $attach = $path !== '' && $fsize <= MAIL_MAX;
  if ($fname !== '') {
    $mb = number_format($fsize / 1048576, 1) . ' MB';
    $lines[] = ''; $lines[] = 'file: ' . $fname . " ($mb) — " . ($fprob !== '' ? "NOT RECEIVED: $fprob. Ask the customer to send it by email." : ($attach ? 'attached' : 'too large for email, saved on the server: backend/data/files/' . basename(dirname($path)) . '/' . basename($path)));
  }
  $lines[] = ''; $lines[] = $id ? "Lead #$id" : 'Lead not saved in the database (email only)';
  $subject = '=?UTF-8?B?' . base64_encode($nl('[Website] ' . ($r['request_type'] ?: 'request') . ' — ' . $r['company'] . ' (' . $r['country'] . ')')) . '?=';
  $text = implode("\r\n", $lines);
  $headers = ['From: ' . $nl($c['mail_from']), 'MIME-Version: 1.0'];
  if (filter_var($r['email'], FILTER_VALIDATE_EMAIL)) $headers[] = 'Reply-To: ' . $r['email'];
  if ($attach) {
    $b = 'up' . bin2hex(random_bytes(12));
    $ascii = trim(preg_replace('/[^A-Za-z0-9._-]+/', '-', (function_exists('iconv') ? (string)@iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $nl($fname)) : $nl($fname))), '-') ?: 'label-file';
    $headers[] = "Content-Type: multipart/mixed; boundary=\"$b\"";
    $msg = "--$b\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($text))
         . "--$b\r\nContent-Type: application/octet-stream; name=\"$ascii\"\r\nContent-Disposition: attachment; filename=\"$ascii\"; filename*=UTF-8''" . rawurlencode($nl($fname)) . "\r\nContent-Transfer-Encoding: base64\r\n\r\n"
         . chunk_split(base64_encode((string)file_get_contents($path))) . "--$b--\r\n";
  } else {
    $headers[] = 'Content-Type: text/plain; charset=UTF-8'; $headers[] = 'Content-Transfer-Encoding: base64';
    $msg = chunk_split(base64_encode($text));
  }
  if (getenv('UP_TEST_MAIL')) { file_put_contents(getenv('UP_TEST_MAIL'), 'To: ' . $c['notify_to'] . "\r\nSubject: $subject\r\n" . implode("\r\n", $headers) . "\r\n\r\n" . $msg); return true; }
  return @mail($c['notify_to'], $subject, $msg, implode("\r\n", $headers), '-f' . $nl($c['mail_from']));
}

function require_admin(): void {
  $c = cfg(); $u = $_SERVER['PHP_AUTH_USER'] ?? ''; $p = $_SERVER['PHP_AUTH_PW'] ?? '';
  if ($u === '' && !empty($_SERVER['HTTP_AUTHORIZATION']) && stripos($_SERVER['HTTP_AUTHORIZATION'], 'basic ') === 0) {
    [$u, $p] = array_pad(explode(':', (string)base64_decode(substr($_SERVER['HTTP_AUTHORIZATION'], 6)), 2), 2, '');
  }
  if ($c['admin_hash'] === '' || !hash_equals($c['admin_user'], $u) || !password_verify($p, $c['admin_hash'])) {
    header('WWW-Authenticate: Basic realm="UltraPixel leads"'); http_response_code(401); exit('Authentication required');
  }
  header('X-Robots-Tag: noindex'); header('Cache-Control: no-store');
}

function leads(?string $status = null): array {
  if ($status) { $q = db()->prepare('SELECT * FROM web_leads WHERE status = ? ORDER BY id DESC'); $q->execute([$status]); return $q->fetchAll(); }
  return db()->query('SELECT * FROM web_leads ORDER BY id DESC')->fetchAll();
}

function page(string $body): void {
  echo '<!doctype html><meta charset=utf-8><meta name=robots content=noindex><meta name=viewport content="width=device-width,initial-scale=1"><title>UltraPixel leads</title>
<style>body{font:14px/1.45 system-ui,sans-serif;margin:24px;color:#101214;background:#F4F4F0}table{border-collapse:collapse;width:100%;background:#fff}td,th{border:1px solid #d8dadb;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#eceeef;font-size:12px}nav a{margin-right:14px}h1{font-size:20px}h2{font-size:16px;margin-top:26px}.k{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}.k div{background:#fff;border:1px solid #d8dadb;padding:10px 14px}.k b{display:block;font-size:22px}
textarea{width:220px;height:44px}small{color:#56606a}.w{overflow-x:auto}</style>
<h1>UltraPixel — website leads</h1><nav><a href="index.php">Leads</a><a href="stats.php">Statistics</a><a href="export.php?f=csv">Export CSV</a><a href="export.php?f=xlsx">Export XLSX</a></nav>' . $body;
}
