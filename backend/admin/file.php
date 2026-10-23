<?php
// Download the file sent with a request (admin only).
require __DIR__ . '/../lib.php';
require_admin();
$q = db()->prepare('SELECT file FROM web_leads WHERE id = ?'); $q->execute([(int)($_GET['id'] ?? 0)]);
$rel = (string)$q->fetchColumn();
$path = realpath(data_dir() . '/' . $rel);
if ($rel === '' || !$path || strpos($path, realpath(data_dir('files')) . DIRECTORY_SEPARATOR) !== 0 || !is_file($path)) { http_response_code(404); exit('File not found'); }
header('Content-Type: application/octet-stream');
header('Content-Disposition: attachment; filename="' . basename($path) . '"');
header('Content-Length: ' . filesize($path));
readfile($path);
