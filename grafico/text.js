// Testi in tracciati. stdin: [{font:"famiglia:peso:stile", text, size, x, y, anchor, track, maxW}] (mm) -> stdout: [{d, w, size}]
// font es. "bodoni-moda:500:normal", "cormorant-garamond:500:italic". track in em. maxW riduce il corpo finché il testo ci sta.
const o = require('opentype.js'), path = require('path'), fs = require('fs'), F = {};
const load = (spec) => {
  if (F[spec]) return F[spec];
  const [fam, w = '400', st = 'normal'] = spec.split(':');
  const p = path.join(__dirname, 'node_modules/@fontsource', fam, 'files', `${fam}-latin-${w}-${st}.woff`);
  if (!fs.existsSync(p)) throw new Error('carattere non trovato: ' + spec);
  return (F[spec] = o.loadSync(p));
};
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
console.log(JSON.stringify(req.map((r) => {
  const f = load(r.font), opt = { kerning: true, letterSpacing: r.track || 0 }, t = String(r.text);
  let size = r.size, w = f.getAdvanceWidth(t, size, opt) - (r.track || 0) * size;
  if (r.maxW && w > r.maxW) { size *= r.maxW / w; w = r.maxW; }
  const x = r.anchor === 'middle' ? r.x - w / 2 : r.anchor === 'end' ? r.x - w : r.x;
  return { d: f.getPath(t, x, r.y, size, opt).toPathData(3), w, size };
})));
