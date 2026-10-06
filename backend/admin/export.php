<?php
require __DIR__ . '/../lib.php';
require_admin();
$rows = array_map(fn($r) => array_map(fn($k) => (string)($r[$k] ?? ''), EXPORT), leads());
if (($_GET['f'] ?? 'csv') === 'csv') {
  header('Content-Type: text/csv; charset=UTF-8'); header('Content-Disposition: attachment; filename=ultrapixel-leads.csv');
  $o = fopen('php://output', 'w'); fwrite($o, "\xEF\xBB\xBF"); fputcsv($o, EXPORT, ',', '"', '');
  foreach ($rows as $r) { $r = array_map(fn($v) => preg_match('/^[=+\-@]/', $v) ? "'" . $v : $v, $r); fputcsv($o, $r, ',', '"', ''); }
  exit;
}
// Minimal XLSX: one sheet, text cells.
$x = fn($s) => htmlspecialchars(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F]/', '', $s), ENT_XML1 | ENT_QUOTES, 'UTF-8');
$col = function (int $i) { $s = ''; for ($i++; $i > 0; $i = intdiv($i - 1, 26)) $s = chr(65 + ($i - 1) % 26) . $s; return $s; };
$sheet = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews><sheetData>';
foreach (array_merge([EXPORT], $rows) as $n => $r) {
  $sheet .= '<row r="' . ($n + 1) . '">';
  foreach ($r as $i => $v) $sheet .= '<c r="' . $col($i) . ($n + 1) . '" t="inlineStr"><is><t xml:space="preserve">' . $x($v) . '</t></is></c>';
  $sheet .= '</row>';
}
$sheet .= '</sheetData></worksheet>';
$tmp = tempnam(sys_get_temp_dir(), 'upx'); $z = new ZipArchive(); $z->open($tmp, ZipArchive::OVERWRITE);
$z->addFromString('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>');
$z->addFromString('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>');
$z->addFromString('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Leads" sheetId="1" r:id="rId1"/></sheets></workbook>');
$z->addFromString('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>');
$z->addFromString('xl/worksheets/sheet1.xml', $sheet); $z->close();
header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'); header('Content-Disposition: attachment; filename=ultrapixel-leads.xlsx'); header('Content-Length: ' . filesize($tmp));
readfile($tmp); unlink($tmp);
