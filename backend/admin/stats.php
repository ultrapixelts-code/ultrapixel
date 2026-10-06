<?php
require __DIR__ . '/../lib.php';
require_admin();
$days = max(1, min(365, (int)($_GET['days'] ?? 30))); $since = gmdate('Y-m-d H:i:s', time() - $days * 86400); $p = db();
$grp = function (string $tbl, string $col, ?string $ev = null) use ($p, $since) {
  $q = $p->prepare("SELECT $col AS k, COUNT(*) AS n FROM $tbl WHERE created_at >= ?" . ($ev ? ' AND event = ?' : '') . " GROUP BY $col ORDER BY n DESC"); $q->execute($ev ? [$since, $ev] : [$since]);
  return array_map(fn($r) => [$r['k'], (int)$r['n']], $q->fetchAll());
};
$tbl = function (string $t, array $rows, array $head) {
  $o = '<h2>' . h($t) . '</h2><div class=w><table><tr>' . implode('', array_map(fn($x) => '<th>' . h($x) . '</th>', $head)) . '</tr>';
  foreach ($rows as $r) $o .= '<tr>' . implode('', array_map(fn($v) => '<td>' . h($v) . '</td>', $r)) . '</tr>';
  return $o . '</table></div>';
};
$ev = array_column($grp('web_events', 'event'), 1, 0); $views = $grp('web_events', 'source', 'page_view'); $vmap = array_column($views, 1, 0);
$clicks = [];
$q = $p->prepare("SELECT props FROM web_events WHERE created_at >= ? AND event = 'cta_click'"); $q->execute([$since]);
foreach ($q as $r) { $k = json_decode($r['props'] ?: '{}', true)['kind'] ?? '?'; $clicks[$k] = ($clicks[$k] ?? 0) + 1; } arsort($clicks);
$conv = array_map(fn($r) => [$r[0], $r[1], $vmap[$r[0]] ?? 0, !empty($vmap[$r[0]]) ? number_format($r[1] / $vmap[$r[0]] * 100, 1) . '%' : '–'], $grp('web_leads', 'source'));
$b = "<p>Last $days days. <a href='?days=7'>7</a> <a href='?days=30'>30</a> <a href='?days=90'>90</a></p><div class=k>";
foreach (EVENTS as $k) $b .= '<div><b>' . (int)($ev[$k] ?? 0) . "</b>$k</div>";
$b .= '</div>' . $tbl('Visits by origin (page views)', $views, ['Origin', 'Page views']) . $tbl('Requests by origin', $conv, ['Origin', 'Requests', 'Page views', 'Requests / page views'])
    . $tbl('Requests by sector', $grp('web_leads', 'sector'), ['Sector', 'Requests']) . $tbl('Requests by type', $grp('web_leads', 'request_type'), ['Type', 'Requests']) . $tbl('Requests by status', $grp('web_leads', 'status'), ['Status', 'Requests'])
    . $tbl('Clicks on request buttons', array_map(null, array_keys($clicks), array_values($clicks)), ['Button', 'Clicks']) . $tbl('Pages viewed', array_slice($grp('web_events', 'path', 'page_view'), 0, 40), ['Page', 'Views']);
page($b);
