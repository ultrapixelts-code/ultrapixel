<?php
// Requests from the site forms: JSON, or multipart when a file (label artwork) comes with them.
// The request is saved when the database is available and always emailed to notify_to, with the file attached.
require __DIR__ . '/../lib.php';
api_guard();
$d = body();
header('Content-Type: application/json');
if (!empty($d['website'])) { echo '{"ok":true}'; exit; }          // honeypot: pretend success, store nothing
try { if (limited('lead', 5, 600)) { http_response_code(429); exit('{"error":"rate"}'); } } catch (Throwable $e) { error_log('UltraPixel rate limit: ' . $e->getMessage()); }
$r = [];
foreach (LEAD_FIELDS as $f) $r[$f] = clip($d[$f] ?? '', $f === 'message' ? 5000 : ($f === 'referrer' ? 1000 : 300));
if ($r['name'] === '' || $r['company'] === '' || $r['message'] === '' || !filter_var($r['email'], FILTER_VALIDATE_EMAIL)) { http_response_code(400); exit('{"error":"fields"}'); }
$host = parse_url($r['referrer'], PHP_URL_HOST) ?: '';
$r['source'] = classify($r['utm_source'], $host);
$file = save_upload();

$id = 0;
try {
  $cols = array_merge(LEAD_FIELDS, ['source', 'created_at', 'client_ts', 'status', 'file']);
  $vals = array_merge(array_map(fn($f) => $r[$f], LEAD_FIELDS), [$r['source'], now(), clip($d['timestamp'] ?? '', 40), 'new', $file[0] !== '' ? substr($file[0], strlen(data_dir()) + 1) : null]);
  $p = db();
  $p->prepare('INSERT INTO web_leads (' . implode(',', $cols) . ') VALUES (' . implode(',', array_fill(0, count($cols), '?')) . ')')->execute($vals);
  $id = (int)$p->lastInsertId();
} catch (Throwable $e) { error_log('UltraPixel lead not saved: ' . $e->getMessage()); }

$sent = false;
try { $sent = notify($r, $id, $file); } catch (Throwable $e) { error_log('UltraPixel lead mail failed: ' . $e->getMessage()); }
if ($sent && $id) { try { db()->prepare('UPDATE web_leads SET email_sent = 1 WHERE id = ?')->execute([$id]); } catch (Throwable $e) {} }
if (!$sent && !$id) { http_response_code(500); exit('{"error":"server"}'); }   // nothing kept anywhere: tell the visitor
echo json_encode(['ok' => true, 'file' => $file[3] === '' ? ($file[0] !== '' ? 'ok' : 'none') : 'failed']);
