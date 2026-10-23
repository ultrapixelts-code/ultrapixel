<?php
require __DIR__ . '/../lib.php';
require_admin();
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
  $s = $_POST['status'] ?? ''; if (!in_array($s, STATUSES, true)) { http_response_code(400); exit; }
  db()->prepare('UPDATE web_leads SET status = ?, notes = ?, updated_at = ? WHERE id = ?')->execute([$s, mb_substr($_POST['notes'] ?? '', 0, 5000), now(), (int)($_POST['id'] ?? 0)]);
  header('Location: index.php'); exit;
}
$st = in_array($_GET['status'] ?? '', STATUSES, true) ? $_GET['status'] : null;
$b = '<p>Filter: <a href="index.php">all</a> ' . implode(' ', array_map(fn($s) => "<a href=\"index.php?status=$s\">$s</a>", STATUSES)) . '</p><div class=w><table><tr><th>#</th><th>Date (UTC)</th><th>Who</th><th>Request</th><th>Message</th><th>Origin</th><th>Status / notes</th></tr>';
$rows = leads($st);
foreach ($rows as $r) {
  $opt = implode('', array_map(fn($s) => '<option' . ($s === $r['status'] ? ' selected' : '') . ">$s</option>", STATUSES));
  $b .= '<tr><td>' . (int)$r['id'] . '</td><td>' . h(substr($r['created_at'], 0, 16)) . '</td><td><b>' . h($r['name']) . '</b><br>' . h($r['company']) . '<br>' . h($r['country']) . '<br><a href="mailto:' . h($r['email']) . '">' . h($r['email']) . '</a></td>'
      . '<td>' . h($r['request_type']) . '<br><small>' . h($r['sector']) . ' · ' . h($r['lang']) . '</small></td><td>' . nl2br(h($r['message'])) . '</td>'
      . '<td><b>' . h($r['source']) . '</b><br><small>utm: ' . h($r['utm_source']) . ' / ' . h($r['utm_medium']) . ' / ' . h($r['utm_campaign']) . '<br>ref: ' . h($r['referrer']) . '<br>landing: ' . h($r['landing_page']) . '<br>from: ' . h($r['source_page']) . '<br>mail: ' . ($r['email_sent'] ? 'sent' : 'not sent') . '</small></td>'
      . '<td><form method=post><input type=hidden name=id value="' . (int)$r['id'] . '"><select name=status>' . $opt . '</select><br><textarea name=notes>' . h($r['notes']) . '</textarea><br><button>Save</button></form></td></tr>';
}
if (!$rows) $b .= '<tr><td colspan=7>No leads yet.</td></tr>';
page($b . '</table></div>');
