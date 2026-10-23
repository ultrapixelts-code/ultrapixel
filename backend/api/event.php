<?php
require __DIR__ . '/../lib.php';
api_guard();
$d = body();
if (!in_array($d['event'] ?? '', EVENTS, true)) { http_response_code(400); exit; }
http_response_code(204);
if (stripos($_SERVER['HTTP_USER_AGENT'] ?? '', 'bot') !== false) exit;
if (limited('event', 300, 600)) exit;
db()->prepare('INSERT INTO web_events (created_at, event, path, lang, source, utm_source, utm_medium, utm_campaign, ref_host, landing_page, props) VALUES (?,?,?,?,?,?,?,?,?,?,?)')
  ->execute([now(), $d['event'], clip($d['path'] ?? ''), clip($d['lang'] ?? '', 10), classify($d['utm_source'] ?? '', $d['ref_host'] ?? ''), clip($d['utm_source'] ?? '', 120), clip($d['utm_medium'] ?? '', 120),
             clip($d['utm_campaign'] ?? '', 120), clip($d['ref_host'] ?? '', 200), clip($d['landing_page'] ?? ''), mb_substr(json_encode($d['props'] ?? new stdClass()), 0, 1000)]);
