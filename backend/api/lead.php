<?php
require __DIR__ . '/../lib.php';
api_guard();
$d = body();
header('Content-Type: application/json');
if (!empty($d['website'])) { echo '{"ok":true}'; exit; }          // honeypot: pretend success, store nothing
if (limited('lead', 5, 600)) { http_response_code(429); exit; }
$r = [];
foreach (LEAD_FIELDS as $f) $r[$f] = clip($d[$f] ?? '', $f === 'message' ? 5000 : ($f === 'referrer' ? 1000 : 300));
if ($r['name'] === '' || $r['company'] === '' || $r['message'] === '' || !filter_var($r['email'], FILTER_VALIDATE_EMAIL)) { http_response_code(400); exit; }
$host = parse_url($r['referrer'], PHP_URL_HOST) ?: '';
$r['source'] = classify($r['utm_source'], $host);
$cols = array_merge(LEAD_FIELDS, ['source', 'created_at', 'client_ts', 'status']);
$vals = array_merge(array_map(fn($f) => $r[$f], LEAD_FIELDS), [$r['source'], now(), clip($d['timestamp'] ?? '', 40), 'new']);
$p = db();
$p->prepare('INSERT INTO web_leads (' . implode(',', $cols) . ') VALUES (' . implode(',', array_fill(0, count($cols), '?')) . ')')->execute($vals);
$id = (int)$p->lastInsertId();
try { if (notify($r, $id)) $p->prepare('UPDATE web_leads SET email_sent = 1 WHERE id = ?')->execute([$id]); } catch (Throwable $e) { error_log('UltraPixel lead mail failed: ' . $e->getMessage()); }
echo '{"ok":true}';
