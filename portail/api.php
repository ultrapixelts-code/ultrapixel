<?php
// Portale clienti UltraPixel — API (PHP, nessun database: file in data/, protetti anche senza .htaccess).
// Ogni file salvato in data/ ha estensione .php e inizia con un blocco che lo rende illeggibile dal web:
// i contenuti escono solo da qui, dopo il login.
declare(strict_types=1);
define('UPX_PORTAL', 1);

const GUARD = "<?php http_response_code(404); exit; ?>\n";
const PDF_MAX = 20 * 1024 * 1024;
const ART_MAX = 4 * 1024 * 1024;

$CFG = require __DIR__ . '/config.php';

header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

// ---------- storage ----------
function ddir(string $sub = ''): string {
  $d = getenv('UPX_PORTAL_DATA') ?: __DIR__ . '/data';
  if ($sub !== '') $d .= '/' . $sub;
  if (!is_dir($d)) { @mkdir($d, 0750, true); @file_put_contents("$d/index.html", ''); }   // no folder listing even where .htaccess is not uploaded
  return $d;
}
function put_blob(string $path, string $bytes): void {
  $tmp = $path . '.tmp' . bin2hex(random_bytes(3));
  if (file_put_contents($tmp, GUARD . $bytes) === false || !rename($tmp, $path)) { @unlink($tmp); fail(500, 'write'); }
}
function get_blob(string $path): ?string {
  if (!is_file($path)) return null;
  $s = (string)file_get_contents($path);
  return str_starts_with($s, GUARD) ? substr($s, strlen(GUARD)) : $s;
}
/** Read-modify-write of a JSON document under an exclusive lock. */
function with_doc(string $name, callable $fn, $default = []) {
  $path = ddir() . "/$name.php";
  $fh = fopen($path, 'c+'); if (!$fh) fail(500, 'open');
  flock($fh, LOCK_EX);
  $raw = stream_get_contents($fh);
  if (str_starts_with($raw, GUARD)) $raw = substr($raw, strlen(GUARD));
  $doc = $raw !== '' ? json_decode($raw, true) : null;
  if (!is_array($doc)) $doc = $default;
  $out = $fn($doc);
  if ($out !== null) {
    [$doc, $ret] = $out;
    ftruncate($fh, 0); rewind($fh);
    fwrite($fh, GUARD . json_encode($doc, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    fflush($fh);
  } else $ret = $doc;
  flock($fh, LOCK_UN); fclose($fh);
  return $ret;
}
function read_doc(string $name, $default = []) { return with_doc($name, fn($d) => null, $default); }

/** First run: the labels already confirmed in the prototype become the starting catalogue. */
function labels(): array {
  return with_doc('labels', function ($d) {
    if ($d !== [] || is_file(ddir() . '/.seeded')) return null;
    $seed = get_blob(__DIR__ . '/seed.php');
    $list = $seed ? (json_decode($seed, true) ?: []) : [];
    $out = [];
    foreach ($list as $r) {
      if (!empty($r['art']) && preg_match('#^data:image/(webp|png|jpeg);base64,(.+)$#', $r['art'], $m)) {
        put_blob(ddir('art') . '/' . safe_id($r['id']) . '.php', base64_decode($m[2]));
        $r['artType'] = 'image/' . $m[1];
      }
      unset($r['art']);
      $r['uploadedAt'] = gmdate('c'); $r['uploadedBy'] = 'prototipo';
      $out[$r['id']] = $r;
    }
    touch(ddir() . '/.seeded');
    return [$out, $out];
  });
}

// ---------- helpers ----------
function fail(int $code, string $msg) { http_response_code($code); header('Content-Type: application/json'); echo json_encode(['error' => $msg]); exit; }
function ok($data) { header('Content-Type: application/json; charset=utf-8'); echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit; }
function safe_id($id): string { $id = preg_replace('/[^0-9A-Za-z_-]/', '', (string)$id); if ($id === '' || strlen($id) > 40) fail(400, 'id'); return $id; }
function s($v, int $n = 300): string { return mb_substr(trim(str_replace("\0", '', (string)($v ?? ''))), 0, $n); }
function num($v): float { return is_numeric($v) ? (float)$v : 0.0; }
function body(): array { $d = json_decode((string)file_get_contents('php://input'), true); return is_array($d) ? $d : []; }

function me(): ?array {
  global $CFG;
  $u = $_SESSION['u'] ?? null;
  if (!$u || empty($CFG['users'][$u])) return null;
  return ['user' => $u] + $CFG['users'][$u];
}
function need(string $role = ''): array {
  $m = me(); if (!$m) fail(401, 'login');
  if ($role === 'staff' && $m['role'] !== 'staff') fail(403, 'staff');
  return $m;
}
/** What a person may see: staff everything, a client only their customer code. */
function visible(array $me, array $l): bool { return $me['role'] === 'staff' || (string)($l['customerCode'] ?? '') === (string)($me['customer'] ?? '-'); }
function public_label(array $l): array {
  $v = substr(md5(($l['uploadedAt'] ?? '') . $l['id']), 0, 8);
  $l['art'] = is_file(ddir('art') . '/' . $l['id'] . '.php') ? 'api.php?a=art&id=' . rawurlencode($l['id']) . '&v=' . $v : '';
  $l['pdf'] = is_file(ddir('pdf') . '/' . $l['id'] . '.php') ? 'api.php?a=pdf&id=' . rawurlencode($l['id']) . '&v=' . $v : '';
  unset($l['artType']);
  return $l;
}
function settings(): array { global $CFG; return read_doc('settings', []) + ['orderEmail' => $CFG['order_email']]; }

/** Too many wrong passwords from one address: wait. The address is kept only as a daily salted hash. */
function throttled(bool $failed = false): bool {
  $k = hash('sha256', gmdate('Y-m-d') . '|' . ($_SERVER['REMOTE_ADDR'] ?? '') . '|' . __DIR__);
  return with_doc('throttle', function ($d) use ($k, $failed) {
    $now = time();
    $d = array_filter($d, fn($t) => is_array($t) && $t && max($t) > $now - 900);
    $hits = array_values(array_filter($d[$k] ?? [], fn($t) => $t > $now - 900));
    if ($failed) $hits[] = $now;
    $d[$k] = $hits;
    return [$d, count($hits) >= 8];
  });
}

function mail_utf8(string $to, string $subject, string $text, string $replyTo = ''): bool {
  global $CFG;
  $from = $CFG['mail_from'];
  $h = ['From: UltraPixel <' . $from . '>', 'MIME-Version: 1.0', 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: base64'];
  if ($replyTo !== '' && filter_var($replyTo, FILTER_VALIDATE_EMAIL)) $h[] = 'Reply-To: ' . $replyTo;
  $subj = '=?UTF-8?B?' . base64_encode(str_replace(["\r", "\n"], ' ', $subject)) . '?=';
  if ($f = getenv('UPX_TEST_MAIL')) { file_put_contents($f, "To: $to\nSubject: $subject\n\n$text\n\n-----\n", FILE_APPEND); return true; }
  return @mail($to, $subj, chunk_split(base64_encode($text)), implode("\r\n", $h), '-f' . $from);
}
function recipients(string $list): array {
  return array_values(array_filter(array_map('trim', preg_split('/[,;\s]+/', $list)), fn($e) => filter_var($e, FILTER_VALIDATE_EMAIL)));
}
function it_n($n): string { return number_format((float)$n, 0, ',', '.'); }

function order_text(array $o): string {
  $L = [];
  foreach ($o['lines'] as $i => $li) {
    $L[] = ($i + 1) . ". {$li['id']} — {$li['desc']}\n   Quantità: " . it_n($li['qty']) . " etichette (≈ " . it_n($li['rolls']) . " rotoli da " . it_n($li['perRoll']) . ")\n"
         . "   Formato {$li['w']}×{$li['h']} mm · anima {$li['core']} mm · Ø max {$li['outer']} mm · {$li['winding']}";
  }
  $tot = array_sum(array_column($o['lines'], 'qty')); $tr = array_sum(array_column($o['lines'], 'rolls'));
  return "Nuovo ordine dal portale clienti.\n\nCliente: {$o['customer']} - {$o['customerName']}\nInviato da: {$o['contact']} <{$o['email']}> (utente {$o['user']})\n"
       . "Rif. ordine cliente: " . ($o['po'] ?: '—') . "\nConsegna richiesta: {$o['delivery']}\n\nRighe:\n" . implode("\n\n", $L)
       . "\n\nTotale: " . it_n($tot) . " etichette (≈ " . it_n($tr) . " rotoli)\n\nIndirizzo di consegna:\n{$o['address']}\n"
       . ($o['notes'] !== '' ? "\nNote del cliente:\n{$o['notes']}\n" : '') . "\nOrdine {$o['no']} · " . (new DateTime($o['created']))->format('d/m/Y H:i') . "\n";
}
function client_text(array $o, string $lang): string {
  $T = [
    'fr' => ['h' => "Bonjour,\n\nUltraPixel a bien reçu votre commande %s. Nous vous confirmons rapidement la date de livraison.\n", 'q' => 'étiquettes', 'r' => 'rouleaux', 'po' => 'Votre n° de commande', 'd' => 'Livraison souhaitée', 'a' => 'Adresse de livraison', 'n' => 'Remarques', 'end' => "\nCordialement,\nUltraPixel · +39 040 817222 · info@ultrapixel.it\n"],
    'it' => ['h' => "Buongiorno,\n\nUltraPixel ha ricevuto il vostro ordine %s. Vi confermiamo a breve la data di consegna.\n", 'q' => 'etichette', 'r' => 'rotoli', 'po' => 'Vostro n° ordine', 'd' => 'Consegna richiesta', 'a' => 'Indirizzo di consegna', 'n' => 'Note', 'end' => "\nCordiali saluti,\nUltraPixel · +39 040 817222 · info@ultrapixel.it\n"],
    'en' => ['h' => "Hello,\n\nUltraPixel has received your order %s. We will confirm the delivery date shortly.\n", 'q' => 'labels', 'r' => 'rolls', 'po' => 'Your PO number', 'd' => 'Requested delivery', 'a' => 'Delivery address', 'n' => 'Notes', 'end' => "\nKind regards,\nUltraPixel · +39 040 817222 · info@ultrapixel.it\n"],
  ][$lang] ?? null;
  if (!$T) return client_text($o, 'fr');
  $L = array_map(fn($li) => "- {$li['id']} · {$li['desc']}: " . it_n($li['qty']) . " {$T['q']} (≈ " . it_n($li['rolls']) . " {$T['r']})", $o['lines']);
  return sprintf($T['h'], $o['no']) . "\n" . implode("\n", $L) . "\n\n{$T['po']}: " . ($o['po'] ?: '—') . "\n{$T['d']}: {$o['delivery']}\n{$T['a']}:\n{$o['address']}\n"
       . ($o['notes'] !== '' ? "{$T['n']}: {$o['notes']}\n" : '') . $T['end'];
}

// ---------- session ----------
session_name('upxportal');
session_set_cookie_params(['lifetime' => 60 * 60 * 24 * 30, 'path' => dirname($_SERVER['SCRIPT_NAME'] ?? '/portail/api.php') . '/', 'secure' => !empty($_SERVER['HTTPS']) || ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https', 'httponly' => true, 'samesite' => 'Lax']);
ini_set('session.gc_maxlifetime', (string)(60 * 60 * 24 * 30));
session_start();

$a = $_GET['a'] ?? '';
$post = ($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST';
// Writes come only from the portal page itself (a custom header forces a CORS preflight from any other site).
if ($post && ($_SERVER['HTTP_X_UPX'] ?? '') !== '1') fail(403, 'origin');

switch ($a) {
  case 'login':
    if (!$post) fail(405, 'method');
    if (throttled()) fail(429, 'wait');
    $d = body(); $u = strtolower(s($d['u'] ?? '', 60)); $p = (string)($d['p'] ?? '');
    $rec = $CFG['users'][$u] ?? null;
    if (!$rec || !password_verify($p, $rec['hash'])) { throttled(true); usleep(400000); fail(401, 'bad'); }
    session_regenerate_id(true); $_SESSION['u'] = $u;
    ok(['ok' => true] + array_diff_key(me(), ['hash' => 1]));

  case 'logout':
    $_SESSION = []; session_destroy(); ok(['ok' => true]);

  case 'me':
    $m = need(); $staff = $m['role'] === 'staff';
    ok(array_diff_key($m, ['hash' => 1]) + ['orderEmail' => $staff ? settings()['orderEmail'] : null, 'customers' => $staff ? $CFG['customers'] : null]);

  case 'labels':
    $m = need();
    $out = [];
    foreach (labels() as $l) if (visible($m, $l)) $out[] = public_label($l);
    ok($out);

  case 'art': case 'pdf':
    $m = need(); $id = safe_id($_GET['id'] ?? '');
    $l = labels()[$id] ?? null; if (!$l || !visible($m, $l)) fail(404, 'none');
    $bytes = get_blob(ddir($a) . "/$id.php"); if ($bytes === null) fail(404, 'none');
    if ($a === 'art') { header('Content-Type: ' . ($l['artType'] ?? 'image/webp')); header('Cache-Control: private, max-age=31536000, immutable'); }
    else { header('Content-Type: application/pdf'); header('Content-Disposition: inline; filename="' . preg_replace('/[^A-Za-z0-9._-]/', '_', $l['source'] ?: "$id.pdf") . '"'); }
    header('Content-Length: ' . strlen($bytes)); echo $bytes; exit;

  case 'sheet':   // staff: a technical sheet read in the browser, sent with its PDF and the cropped artwork
    if (!$post) fail(405, 'method');
    $m = need('staff');
    $r = json_decode((string)($_POST['rec'] ?? ''), true); if (!is_array($r)) fail(400, 'rec');
    $id = safe_id($r['id'] ?? '');
    $pdf = $_FILES['pdf'] ?? null; $art = $_FILES['art'] ?? null;
    if (!$pdf || $pdf['error'] !== UPLOAD_ERR_OK || $pdf['size'] > PDF_MAX) fail(400, 'pdf');
    $pb = (string)file_get_contents($pdf['tmp_name']); if (!str_starts_with($pb, '%PDF')) fail(400, 'pdf');
    $artType = null;
    if ($art && $art['error'] === UPLOAD_ERR_OK && $art['size'] <= ART_MAX) {
      $ab = (string)file_get_contents($art['tmp_name']);
      $artType = str_starts_with($ab, 'RIFF') ? 'image/webp' : (str_starts_with($ab, "\x89PNG") ? 'image/png' : (str_starts_with($ab, "\xFF\xD8") ? 'image/jpeg' : null));
    }
    $code = s($r['customerCode'] ?? '', 20) ?: (string)$CFG['default_customer'];
    $rec = [
      'id' => $id, 'customerCode' => $code, 'customer' => $CFG['customers'][$code] ?? trim(str_replace(s($r['desc'] ?? '', 500), '', s($r['customer'] ?? ''))),
      'desc' => s($r['desc'] ?? '', 500) ?: $id, 'date' => preg_match('/^\d{4}-\d{2}-\d{2}$/', (string)($r['date'] ?? '')) ? $r['date'] : gmdate('Y-m-d'),
      'w' => num($r['w'] ?? 0), 'h' => num($r['h'] ?? 0), 'gapC' => num($r['gapC'] ?? 0), 'pitchE' => num($r['pitchE'] ?? 0),
      'material' => s($r['material'] ?? ''), 'materialId' => s($r['materialId'] ?? ''), 'perRoll' => max(1, (int)($r['perRoll'] ?? 1000)),
      'rollLength' => s($r['rollLength'] ?? '', 20), 'lanes' => max(1, (int)($r['lanes'] ?? 1)), 'core' => (int)($r['core'] ?? 76), 'outer' => (int)($r['outer'] ?? 0),
      'inks' => array_slice(array_map(fn($x) => s($x, 40), is_array($r['inks'] ?? null) ? $r['inks'] : []), 0, 12),
      'finish' => s($r['finish'] ?? '', 300), 'winding' => s($r['winding'] ?? '', 200), 'source' => s($pdf['name'] ?? '', 150),
      'uploadedAt' => gmdate('c'), 'uploadedBy' => $m['user'],
    ];
    put_blob(ddir('pdf') . "/$id.php", $pb);
    if ($artType) { put_blob(ddir('art') . "/$id.php", $ab); $rec['artType'] = $artType; }
    labels();   // make sure the starting catalogue is in place before adding
    $saved = with_doc('labels', function ($d) use ($rec, $id) {
      if (empty($rec['artType']) && !empty($d[$id]['artType'])) $rec['artType'] = $d[$id]['artType'];   // new PDF without artwork: keep the old image
      $d[$id] = $rec; return [$d, $rec];
    });
    ok(public_label($saved));

  case 'remove':
    if (!$post) fail(405, 'method');
    need('staff'); $id = safe_id(body()['id'] ?? '');
    labels();
    with_doc('labels', function ($d) use ($id) { unset($d[$id]); return [$d, true]; });
    @unlink(ddir('art') . "/$id.php"); @unlink(ddir('pdf') . "/$id.php");
    ok(['ok' => true]);

  case 'settings':
    if (!$post) fail(405, 'method');
    need('staff'); $to = recipients(s(body()['orderEmail'] ?? '', 500));
    if (!$to) fail(400, 'email');
    with_doc('settings', function ($d) use ($to) { $d['orderEmail'] = implode(', ', $to); return [$d, true]; });
    ok(['orderEmail' => implode(', ', $to)]);

  case 'orders':
    $m = need();
    $all = read_doc('orders', []);
    $mine = array_values(array_filter($all, fn($o) => $m['role'] === 'staff' || $o['customer'] === ($m['customer'] ?? '-')));
    foreach ($mine as &$o) $o['text'] = $m['role'] === 'staff' ? order_text($o) : client_text($o, $o['lang'] ?? 'fr');
    ok($mine);

  case 'order':
    if (!$post) fail(405, 'method');
    $m = need(); $d = body();
    $cust = $m['role'] === 'client' ? $m['customer'] : (string)$CFG['default_customer'];
    $o = ['contact' => s($d['contact'] ?? '', 120), 'email' => s($d['email'] ?? '', 200), 'po' => s($d['po'] ?? '', 80), 'delivery' => s($d['delivery'] ?? '', 20),
          'address' => s($d['address'] ?? '', 600), 'notes' => s($d['notes'] ?? '', 3000), 'lang' => in_array($d['lang'] ?? '', ['fr', 'it', 'en'], true) ? $d['lang'] : 'fr'];
    if ($o['contact'] === '' || $o['address'] === '' || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $o['delivery']) || !filter_var($o['email'], FILTER_VALIDATE_EMAIL)) fail(400, 'fields');
    $labels = labels(); $lines = [];
    foreach (is_array($d['lines'] ?? null) ? array_slice($d['lines'], 0, 100) : [] as $li) {
      $l = $labels[(string)($li['id'] ?? '')] ?? null; $q = (int)($li['qty'] ?? 0);
      if (!$l || $q <= 0 || $q > 99999999 || !visible($m, $l)) continue;
      $lines[] = ['id' => $l['id'], 'desc' => $l['desc'], 'qty' => $q, 'rolls' => (int)ceil($q / max(1, $l['perRoll'])), 'perRoll' => $l['perRoll'],
                  'w' => $l['w'], 'h' => $l['h'], 'core' => $l['core'], 'outer' => $l['outer'], 'winding' => $l['winding']];
    }
    if (!$lines) fail(400, 'lines');
    $now = new DateTime('now', new DateTimeZone('Europe/Rome'));
    $o = ['no' => 'DEB-' . $now->format('ymd-His'), 'created' => $now->format('c'), 'user' => $m['user'], 'customer' => $cust,
          'customerName' => $CFG['customers'][$cust] ?? $cust, 'lines' => $lines] + $o;
    if ($cust !== '887') $o['no'] = 'WEB-' . $now->format('ymd-His');
    with_doc('orders', function ($all) use (&$o) {
      while (in_array($o['no'], array_column($all, 'no'), true)) $o['no'] .= 'b';
      $all[] = $o; return [$all, true];
    });
    $txt = order_text($o); $sent = false;
    foreach (recipients(settings()['orderEmail']) as $to)
      $sent = mail_utf8($to, "Ordine {$o['no']} — {$o['customerName']} ({$o['customer']})" . ($o['po'] ? " — rif. {$o['po']}" : ''), $txt, $o['email']) || $sent;
    $subj = ['fr' => 'Votre commande', 'it' => 'Il vostro ordine', 'en' => 'Your order'][$o['lang']] . " {$o['no']} — UltraPixel";
    mail_utf8($o['email'], $subj, client_text($o, $o['lang']), 'info@ultrapixel.it');
    $o['text'] = $m['role'] === 'staff' ? $txt : client_text($o, $o['lang']); $o['mailed'] = $sent;
    ok($o);

  default:
    fail(404, 'action');
}
