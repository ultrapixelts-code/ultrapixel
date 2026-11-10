/* UltraPixel — wine label designer (prototype).
   The visitor picks a style, uploads a logo, writes the texts and chooses bottle, size, paper, foil and embossing.
   Every text is drawn as outlines with opentype.js, so the preview and the file sent to UltraPixel are the same drawing.
   The file sent is an SVG in millimetres with separate layers: print (CMYK), foil, embossing, die line (green) and 2 mm bleed.
   The draft is kept in this browser only (localStorage), nothing leaves the page until the visitor sends the request. */
(function () {
  var root = document.getElementById('ld'); if (!root) return;
  var T = JSON.parse(document.getElementById('ld-t').textContent);
  var A = '/assets/designer/', B = 2;   // bleed, mm
  var red = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (s) { return root.querySelector(s) }, $$ = function (s) { return [].slice.call(root.querySelectorAll(s)) };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] }) };
  var r2 = function (v) { return Math.round(v * 1000) / 1000 };

  var FONTS = { cinzel: 'cinzel-latin-600-normal.woff', cg: 'cormorant-garamond-latin-600-normal.woff', cgi: 'cormorant-garamond-latin-500-italic.woff',
                bod: 'bodoni-moda-latin-500-normal.woff', ar: 'archivo-latin-400-normal.woff', arb: 'archivo-latin-700-normal.woff' }, F = {};
  var INKS = { burgundy: ['#6B1F2E', '#41583B'], black: ['#1C1B1A', '#7A6A55'], navy: ['#1F2C48', '#8C6A3E'], green: ['#2E4A33', '#7A1F2B'] };
  var PAPERS = { ivory: { bg: '#F1E6CE', tex: 1 }, white: { bg: '#F6F4EE', tex: 1 }, cream: { bg: '#F2EAD8', tex: 0 }, bright: { bg: '#FBFBF8', tex: 0 } };
  var FOILS = { gold: ['#7d5d1a', '#c9a54a', '#fff1b8', '#b8902f', '#6f5216'], silver: ['#6d7377', '#c4c9cc', '#ffffff', '#a3a9ad', '#5c6266'],
                copper: ['#6b3a1f', '#b8683d', '#ffd2b0', '#a2552d', '#5a2f18'] };
  // bottle: diameter, height, cylindrical body (from / to, mm from the base), tallest label that stays on the body (indicative), suggested sizes
  var BOTTLES = { bordolese: { d: 75, h: 300, body: [18, 192], max: 140, sizes: [[90, 120], [100, 130], [80, 110]] },
                  borgognotta: { d: 82, h: 295, body: [15, 132], max: 110, sizes: [[90, 110], [100, 115], [80, 100]] },
                  champagnotta: { d: 90, h: 300, body: [15, 140], max: 115, sizes: [[100, 90], [90, 110], [110, 100]] } };
  var STYLES = { classico: { shape: 'round', foil: { name: 1, frame: 1 } }, nobile: { shape: 'arch', foil: { logo: 1, name: 1 } },
                 moderno: { shape: 'rect', foil: { wine: 1 } }, minimal: { shape: 'rect', foil: { vintage: 1 } } };
  var DEN = { docg: 'Denominazione di Origine Controllata e Garantita', doc: 'Denominazione di Origine Controllata', dop: 'Denominazione di Origine Protetta',
              igt: 'Indicazione Geografica Tipica', igp: 'Indicazione Geografica Protetta', vino: '' };

  var S = { style: 'classico', shape: 'round', bottle: 'bordolese', w: 90, h: 120, paper: 'ivory', ink: 'burgundy', foil: 'gold', foilOn: { name: 1, frame: 1 },
            emb: 'none', varnish: 'none', logo: null, la: 1, lraster: 0, lmode: 'ink' };
  for (var k in T.def) S[k] = T.def[k];
  try { var saved = JSON.parse(localStorage.getItem('up_ld') || 'null'); if (saved && saved.v === 1) { for (k in saved.s) S[k] = saved.s[k] } } catch (e) {}
  var save = function () { try { var c = {}; for (var k in S) c[k] = S[k]; if (c.logo && c.logo.length > 1500000) c.logo = null; localStorage.setItem('up_ld', JSON.stringify({ v: 1, s: c })) } catch (e) {} };

  // ------------------------------------------------------------ geometry (mm, origin = top left of the finished label)
  function rr(x, y, w, h, r) {
    r = Math.max(0, Math.min(r, w / 2, h / 2));
    return 'M' + r2(x + r) + ' ' + r2(y) + 'H' + r2(x + w - r) + (r ? 'A' + r + ' ' + r + ' 0 0 1 ' + r2(x + w) + ' ' + r2(y + r) : '') + 'V' + r2(y + h - r) +
      (r ? 'A' + r + ' ' + r + ' 0 0 1 ' + r2(x + w - r) + ' ' + r2(y + h) : '') + 'H' + r2(x + r) + (r ? 'A' + r + ' ' + r + ' 0 0 1 ' + r2(x) + ' ' + r2(y + h - r) : '') +
      'V' + r2(y + r) + (r ? 'A' + r + ' ' + r + ' 0 0 1 ' + r2(x + r) + ' ' + r2(y) : '') + 'Z';
  }
  function rise(W, H) { return Math.min(W * .22, H * .2) }
  function shape(i, W, H, sh) {   // die line (i = 0) or a line inset by i mm
    if (sh === 'oval') { var rx = W / 2 - i, ry = H / 2 - i; return 'M' + r2(W / 2 - rx) + ' ' + r2(H / 2) + 'A' + r2(rx) + ' ' + r2(ry) + ' 0 1 0 ' + r2(W / 2 + rx) + ' ' + r2(H / 2) + 'A' + r2(rx) + ' ' + r2(ry) + ' 0 1 0 ' + r2(W / 2 - rx) + ' ' + r2(H / 2) + 'Z' }
    if (sh === 'arch') { var R = rise(W, H); return 'M' + r2(i) + ' ' + r2(H - i) + 'V' + r2(R) + 'A' + r2(W / 2 - i) + ' ' + r2(Math.max(.5, R - i * .6)) + ' 0 0 1 ' + r2(W - i) + ' ' + r2(R) + 'V' + r2(H - i) + 'Z' }
    return rr(i, i, W - 2 * i, H - 2 * i, (sh === 'round' ? 6 : 1.2) - i);
  }
  function box(W, H, sh, m) {     // area where the texts go
    if (sh === 'oval') return { x: W * .17, y: H * .13, w: W * .66, h: H * .74 };
    if (sh === 'arch') { var R = rise(W, H) * .8; return { x: m, y: R + m * .6, w: W - 2 * m, h: H - R - m * 1.6 } }
    return { x: m, y: m, w: W - 2 * m, h: H - 2 * m };
  }

  // ------------------------------------------------------------ drawing one label into layers
  function initials(s) { var w = (s || '').replace(/[^\p{L}\s]/gu, '').trim().split(/\s+/).filter(function (x) { return /^\p{Lu}/u.test(x) }); return ((w[0] || '')[0] || 'U') + ((w[1] || '')[0] || '') }
  function draw(st, W, H) {
    var ink = INKS[st.ink] || INKS.burgundy, sh = st.shape, L = { print: [], foil: [], emb: [] }, logoDefs = '';
    var foilOn = function (t) { return st.foil !== 'none' && st.foilOn && st.foilOn[t] };
    var put = function (d, col, t, rule) {
      var fr = rule ? ' fill-rule="evenodd"' : '';
      if (foilOn(t)) L.foil.push('<path d="' + d + '"' + fr + '/>'); else L.print.push('<path d="' + d + '" fill="' + col + '"' + fr + '/>');
      if (st.emb === t) L.emb.push('<path d="' + d + '"' + fr + '/>');
    };
    var text = function (fk, s, size, x, y, anchor, maxW, track, col, t) {
      var f = F[fk]; s = (s == null ? '' : String(s)).trim(); if (!f || !s) return 0;
      var o = { kerning: true, letterSpacing: track || 0 }, w1 = f.getAdvanceWidth(s, 1, o) - (track || 0), sz = Math.min(size, maxW / Math.max(w1, .01)), w = w1 * sz;
      var x0 = anchor === 'middle' ? x - w / 2 : anchor === 'end' ? x - w : x;
      put(f.getPath(s, x0, y, sz, o).toPathData(3), col, t); return w;
    };
    var ring = function (i, t, col, tg) { put(shape(i, W, H, sh) + shape(i + t, W, H, sh), col, tg, 1) };
    var logo = function (cx, cy, mw, mh, col) {
      if (st.logo) {
        var a = st.la || 1, lw = mw, lh = mw / a; if (lh > mh) { lh = mh; lw = mh * a }
        var x = r2(cx - lw / 2), y = r2(cy - lh / 2), img = '<image href="' + st.logo + '" x="' + x + '" y="' + y + '" width="' + r2(lw) + '" height="' + r2(lh) + '" preserveAspectRatio="xMidYMid meet"';
        var masked = '<rect x="' + x + '" y="' + y + '" width="' + r2(lw) + '" height="' + r2(lh) + '" mask="url(#@lm)"';
        logoDefs = '<mask id="@lm" maskUnits="userSpaceOnUse" x="' + x + '" y="' + y + '" width="' + r2(lw) + '" height="' + r2(lh) + '">' + img + ' filter="url(#@inv)"/></mask>';
        if (foilOn('logo')) L.foil.push(masked + '/>'); else if (st.lmode === 'orig') L.print.push(img + '/>'); else L.print.push(masked + ' fill="' + col + '"/>');
        if (st.emb === 'logo') L.emb.push(masked + '/>');
        return;
      }
      var r = Math.min(mw, mh) / 2; put('M' + r2(cx - r) + ' ' + r2(cy) + 'a' + r2(r) + ' ' + r2(r) + ' 0 1 0 ' + r2(2 * r) + ' 0a' + r2(r) + ' ' + r2(r) + ' 0 1 0 ' + r2(-2 * r) + ' 0Z' +
        'M' + r2(cx - r * .9) + ' ' + r2(cy) + 'a' + r2(r * .9) + ' ' + r2(r * .9) + ' 0 1 0 ' + r2(1.8 * r) + ' 0a' + r2(r * .9) + ' ' + r2(r * .9) + ' 0 1 0 ' + r2(-1.8 * r) + ' 0Z', col, 'logo', 1);
      text('cinzel', initials(st.winery), r * .82, cx, cy + r * .29, 'middle', r * 1.4, .04, col, 'logo');
    };
    var den = (st.denText || '').trim(), denFull = DEN[st.den] || '', alc = (st.alc || '').trim() ? st.alc + '% vol' : '', vol = st.vol || '';
    var p = ink[0], a = ink[1], cx = W / 2, b, y;

    if (st.style === 'classico') {
      ring(2.4, .3, a, 'frame'); ring(3.4, .8, a, 'frame');
      b = box(W, H, sh, Math.max(7, W * .085)); y = function (f) { return b.y + b.h * f };
      logo(cx, y(.14), b.h * .22, b.h * .2, p);
      text('cinzel', st.winery, b.h * .07, cx, y(.39), 'middle', b.w * .92, .12, p, 'name');
      var ow = Math.min(b.w * .22, 18), oy = y(.445);
      put(rr(cx - ow - 2.2, oy - .14, ow, .28, 0) + rr(cx + 2.2, oy - .14, ow, .28, 0) + 'M' + r2(cx) + ' ' + r2(oy - 1.1) + 'L' + r2(cx + 1.1) + ' ' + r2(oy) + 'L' + r2(cx) + ' ' + r2(oy + 1.1) + 'L' + r2(cx - 1.1) + ' ' + r2(oy) + 'Z', a, 'frame');
      text('cgi', st.wine, b.h * .15, cx, y(.6), 'middle', b.w * .96, 0, p, 'wine');
      text('cinzel', den, b.h * .045, cx, y(.7), 'middle', b.w * .92, .08, p, 'den');
      text('cg', denFull.toUpperCase(), b.h * .03, cx, y(.75), 'middle', b.w * .96, .06, a, 'den');
      text('cg', st.vintage, b.h * .08, cx, y(.86), 'middle', b.w * .5, .04, p, 'vintage');
      text('cgi', st.area, b.h * .042, cx, y(.985), 'middle', b.w * .44, 0, a, 'den');
      text('cinzel', alc, b.h * .036, b.x, y(.985), 'start', b.w * .27, .04, p, 'den');
      text('cinzel', vol, b.h * .036, b.x + b.w, y(.985), 'end', b.w * .27, .04, p, 'den');
    } else if (st.style === 'nobile') {
      ring(2.6, .35, a, 'frame');
      b = box(W, H, sh, Math.max(6.5, W * .08)); y = function (f) { return b.y + b.h * f };
      logo(cx, y(.17), b.w * .5, b.h * .3, p);
      text('cg', (st.winery || '').toUpperCase(), b.h * .07, cx, y(.44), 'middle', b.w * .94, .14, p, 'name');
      text('cgi', st.wine, b.h * .16, cx, y(.63), 'middle', b.w * .96, 0, p, 'wine');
      put(rr(b.x + b.w * .12, y(.675), b.w * .76, .3, 0) + rr(b.x + b.w * .12, y(.8), b.w * .76, .3, 0), a, 'frame');
      text('cg', den.toUpperCase(), b.h * .045, cx, y(.735), 'middle', b.w * .74, .08, p, 'den');
      text('cg', denFull.toUpperCase(), b.h * .03, cx, y(.78), 'middle', b.w * .8, .05, a, 'den');
      text('cg', st.vintage, b.h * .085, cx, y(.9), 'middle', b.w * .5, .06, p, 'vintage');
      text('cgi', [alc, vol, st.area].filter(Boolean).join('  ·  '), b.h * .042, cx, y(.99), 'middle', b.w * .9, 0, a, 'den');
    } else if (st.style === 'moderno') {
      var band = W * .14; put(rr(-B, -B, band + B, H + 2 * B, 0), a, 'frame');
      var m = Math.max(5, W * .06); b = { x: band + m, y: m, w: W - band - 2 * m, h: H - 2 * m }; y = function (f) { return b.y + b.h * f };
      text('arb', (st.winery || '').toUpperCase(), b.h * .045, b.x, y(.08), 'start', b.w, .18, p, 'name');
      put(rr(b.x, y(.13), Math.min(12, b.w * .2), .5, 0), a, 'frame');
      text('arb', st.wine, b.h * .16, b.x, y(.42), 'start', b.w, -.01, p, 'wine');
      text('ar', st.vintage, b.h * .12, b.x, y(.59), 'start', b.w * .6, 0, a, 'vintage');
      var lg = Math.min(b.w * .3, b.h * .17);
      text('arb', den.toUpperCase(), b.h * .04, b.x, y(.72), 'start', b.w, .08, p, 'den');
      text('ar', denFull.toUpperCase(), b.h * .026, b.x, y(.765), 'start', b.w, .06, a, 'den');
      logo(b.x + b.w - lg / 2, y(.88) - lg / 2 + b.h * .02, lg, lg, p);
      text('ar', [alc, vol].filter(Boolean).join('   '), b.h * .034, b.x, y(.985), 'start', b.w - lg - 2, .06, p, 'den');
      text('ar', st.area, b.h * .03, b.x, y(.93), 'start', b.w - lg - 2, .04, a, 'den');
    } else {
      b = box(W, H, sh, Math.max(6, W * .07)); y = function (f) { return b.y + b.h * f };
      logo(cx, y(.07), b.h * .13, b.h * .11, p);
      text('ar', (st.winery || '').toUpperCase(), b.h * .032, cx, y(.22), 'middle', b.w * .96, .3, p, 'name');
      text('bod', st.vintage, b.h * .34, cx, y(.6), 'middle', b.w * .96, -.02, p, 'vintage');
      text('bod', st.wine, b.h * .085, cx, y(.74), 'middle', b.w * .96, 0, p, 'wine');
      text('ar', den.toUpperCase(), b.h * .03, cx, y(.82), 'middle', b.w * .9, .14, a, 'den');
      text('ar', denFull.toUpperCase(), b.h * .022, cx, y(.86), 'middle', b.w * .96, .08, a, 'den');
      text('ar', [alc, vol, st.area].filter(Boolean).join('  ·  ').toUpperCase(), b.h * .026, cx, y(.99), 'middle', b.w * .9, .12, p, 'den');
    }
    return { L: L, defs: logoDefs };
  }

  // ------------------------------------------------------------ assembling: preview, separations, file to send
  var INV = '<filter id="@inv" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="-.3 -1 -.1 0 1.4 -.3 -1 -.1 0 1.4 -.3 -1 -.1 0 1.4 0 0 0 1 0"/></filter>';
  function defs(id, st, W, H, live) {
    var fo = FOILS[st.foil] || FOILS.gold, g = '<linearGradient id="@foil" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="' + r2(W) + '" y2="' + r2(H * .6) + '">' +
      fo.map(function (c, i) { return '<stop offset="' + (i / (fo.length - 1)) + '" stop-color="' + c + '"/>' }).join('') +
      (live && !red ? '<animateTransform attributeName="gradientTransform" type="translate" values="' + r2(-W * .5) + ' 0;' + r2(W * .5) + ' 0;' + r2(-W * .5) + ' 0" dur="6s" repeatCount="indefinite"/>' : '') + '</linearGradient>';
    var emb = '<filter id="@emb" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur in="SourceAlpha" stdDeviation=".18" result="b"/>' +
      '<feOffset in="b" dx="-.22" dy="-.22" result="h0"/><feComposite in="h0" in2="SourceAlpha" operator="out" result="h1"/><feFlood flood-color="#fff" flood-opacity=".95"/><feComposite in2="h1" operator="in" result="hi"/>' +
      '<feOffset in="b" dx=".26" dy=".26" result="s0"/><feComposite in="s0" in2="SourceAlpha" operator="out" result="s1"/><feFlood flood-color="#3a2a12" flood-opacity=".55"/><feComposite in2="s1" operator="in" result="sh"/>' +
      '<feMerge><feMergeNode in="sh"/><feMergeNode in="hi"/></feMerge></filter>';
    var tex = '<filter id="@tex" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="2.4" numOctaves="2" seed="7"/>' +
      '<feColorMatrix values="0 0 0 0 .35 0 0 0 0 .28 0 0 0 0 .18 0 0 0 -1.6 1.05"/></filter>';
    return (g + emb + tex + INV).replace(/@/g, id);
  }
  function layers(id, st, W, H, opt) {   // opt: {only: 'print'|'foil'|'emb'|'die', die: bool, bleed: bool}
    var d = draw(st, W, H), L = d.L, pp = PAPERS[st.paper] || PAPERS.ivory, die = shape(0, W, H, st.shape), o = '', only = opt.only;
    var lc = function (s) { return s.replace(/@/g, id) };
    o += '<defs>' + defs(id, st, W, H, !only) + lc(d.defs) + '<clipPath id="' + id + 'die"><path d="' + die + '"/></clipPath></defs>';
    if (!only) {
      o += '<g' + (opt.bleed ? '' : ' clip-path="url(#' + id + 'die)"') + '><rect x="' + -B + '" y="' + -B + '" width="' + (W + 2 * B) + '" height="' + (H + 2 * B) + '" fill="' + pp.bg + '"/>' +
        (pp.tex ? '<rect x="' + -B + '" y="' + -B + '" width="' + (W + 2 * B) + '" height="' + (H + 2 * B) + '" filter="url(#' + id + 'tex)" opacity=".55"/>' : '') +
        lc(L.print.join('')) + '<g fill="url(#' + id + 'foil)">' + lc(L.foil.join('')) + '</g>' +
        (L.emb.length ? '<g fill="#000" filter="url(#' + id + 'emb)">' + lc(L.emb.join('')) + '</g>' : '') + '</g>';
      if (opt.bleed) o += '<path d="M' + -B + ' ' + -B + 'h' + (W + 2 * B) + 'v' + (H + 2 * B) + 'h' + -(W + 2 * B) + 'Z' + die + '" fill="#F4F4F0" fill-opacity=".72" fill-rule="evenodd"/>';
      if (opt.die) o += '<path d="' + die + '" fill="none" stroke="#00A651" stroke-width=".3"/>';
      return o;
    }
    var faint = '<path d="' + die + '" fill="#fff" stroke="#A7ADB0" stroke-width=".25"/>';
    if (only === 'print') return o + faint + '<g clip-path="url(#' + id + 'die)">' + lc(L.print.join('')) + '</g>';
    if (only === 'foil') return o + faint + '<g fill="#B8902F">' + lc(L.foil.join('')) + '</g>';
    if (only === 'emb') return o + faint + '<g fill="#6F5BE8">' + lc(L.emb.join('')) + '</g>';
    return o + '<path d="' + die + '" fill="none" stroke="#00A651" stroke-width=".45"/><rect x="' + -B + '" y="' + -B + '" width="' + (W + 2 * B) + '" height="' + (H + 2 * B) + '" fill="none" stroke="#A7ADB0" stroke-width=".25" stroke-dasharray="1 1"/>';
  }
  var vb = function (W, H, pad) { return (-B - pad) + ' ' + (-B - pad) + ' ' + (W + 2 * B + 2 * pad) + ' ' + (H + 2 * B + 2 * pad) };

  function bottle(st) {
    var bt = BOTTLES[st.bottle] || BOTTLES.bordolese, R = bt.d / 2, base = 312, cx = 75, W = st.w, H = st.h, nr = st.bottle === 'champagnotta' ? 15 : 14.5;
    var sh0 = base - bt.body[1], top = base - bt.h, neck = st.bottle === 'bordolese' ? base - 232 : base - 222;
    var c1 = st.bottle === 'bordolese' ? sh0 - 24 : sh0 - 42, c2 = st.bottle === 'bordolese' ? neck + 16 : neck + 30;
    var path = 'M' + r2(cx - R + 6) + ' ' + base + 'Q' + r2(cx - R) + ' ' + base + ' ' + r2(cx - R) + ' ' + (base - 6) + 'L' + r2(cx - R) + ' ' + sh0 +
      'C' + r2(cx - R) + ' ' + c1 + ' ' + r2(cx - nr) + ' ' + c2 + ' ' + r2(cx - nr) + ' ' + neck + 'L' + r2(cx - nr) + ' ' + (top + 12) + 'L' + r2(cx - nr - 1.6) + ' ' + (top + 9) + 'L' + r2(cx - nr - 1.6) + ' ' + top +
      'L' + r2(cx + nr + 1.6) + ' ' + top + 'L' + r2(cx + nr + 1.6) + ' ' + (top + 9) + 'L' + r2(cx + nr) + ' ' + (top + 12) + 'L' + r2(cx + nr) + ' ' + neck +
      'C' + r2(cx + nr) + ' ' + c2 + ' ' + r2(cx + R) + ' ' + c1 + ' ' + r2(cx + R) + ' ' + sh0 + 'L' + r2(cx + R) + ' ' + (base - 6) + 'Q' + r2(cx + R) + ' ' + base + ' ' + r2(cx + R - 6) + ' ' + base + 'Z';
    var cap = 'M' + r2(cx - nr - 1.9) + ' ' + (top - .5) + 'H' + r2(cx + nr + 1.9) + 'V' + (top + 10) + 'L' + r2(cx + nr + .4) + ' ' + (top + 13) + 'V' + (neck - 4) + 'H' + r2(cx - nr - .4) + 'V' + (top + 13) + 'L' + r2(cx - nr - 1.9) + ' ' + (top + 10) + 'Z';
    var ang = Math.min(W / (2 * R), 1.42), dw = 2 * R * Math.sin(ang), lx = cx - dw / 2, lyc = base - (bt.body[0] + bt.body[1]) / 2 - 4, ly = lyc - H / 2;
    var id = 'b', art = layers(id, st, W, H, {});
    var shade = '<linearGradient id="bsh" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".42"/><stop offset=".18" stop-color="#000" stop-opacity=".1"/><stop offset=".42" stop-color="#fff" stop-opacity=".12"/>' +
      '<stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset=".85" stop-color="#000" stop-opacity=".16"/><stop offset="1" stop-color="#000" stop-opacity=".48"/></linearGradient>';
    var ink = INKS[st.ink] || INKS.burgundy;
    return '<svg viewBox="' + r2(cx - R - 22) + ' 0 ' + r2(2 * R + 44) + ' 322" role="img" aria-label="' + esc(T.ariaBottle) + '"><defs><linearGradient id="glass" x1="0" x2="1"><stop offset="0" stop-color="#07110b"/><stop offset=".22" stop-color="#1d3524"/>' +
      '<stop offset=".5" stop-color="#14261a"/><stop offset="1" stop-color="#050a07"/></linearGradient>' + shade +
      '<linearGradient id="capg" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".45"/><stop offset=".35" stop-color="#fff" stop-opacity=".18"/><stop offset="1" stop-color="#000" stop-opacity=".5"/></linearGradient>' +
      '<radialGradient id="flo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#101214" stop-opacity=".22"/><stop offset="1" stop-color="#101214" stop-opacity="0"/></radialGradient></defs>' +
      '<ellipse cx="' + cx + '" cy="' + (base + 1.5) + '" rx="' + (R + 14) + '" ry="5" fill="url(#flo)"/>' +
      '<path d="' + path + '" fill="url(#glass)"/>' +
      '<path d="' + cap + '" fill="' + ink[0] + '"/><path d="' + cap + '" fill="url(#capg)"/>' +
      '<svg x="' + r2(lx) + '" y="' + r2(ly) + '" width="' + r2(dw) + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" overflow="visible">' + art +
      '<rect width="' + W + '" height="' + H + '" fill="url(#bsh)" clip-path="url(#bdie)"/></svg>' +
      '<rect x="' + r2(cx - R * .62) + '" y="' + (sh0 + 6) + '" width="' + r2(R * .09) + '" height="' + (bt.body[1] - bt.body[0] - 12) + '" rx="1.5" fill="#fff" opacity=".13"/>' +
      '<rect x="' + r2(cx - R * .48) + '" y="' + (sh0 + 10) + '" width="' + r2(R * .03) + '" height="' + (bt.body[1] - bt.body[0] - 24) + '" rx="1" fill="#fff" opacity=".1"/></svg>';
  }

  function fileSVG(st) {
    var W = st.w, H = st.h, d = draw(st, W, H), L = d.L, lc = function (s) { return s.replace(/@/g, 'x') };
    var spec = specLines(st);
    return '<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="' + (W + 2 * B) + 'mm" height="' + (H + 2 * B) + 'mm" viewBox="' + vb(W, H, 0) + '">\n' +
      '<title>UltraPixel – ' + esc(st.wine || 'label') + ' – ' + W + ' × ' + H + ' mm</title>\n<desc>' + esc(spec.join('\n')) + '</desc>\n' +
      '<defs>' + INV.replace(/@/g, 'x') + lc(d.defs) + '</defs>\n' +
      '<g id="stampa" inkscape:groupmode="layer" inkscape:label="Stampa CMYK (carta: nessun fondo stampato)">' + lc(L.print.join('')) + '</g>\n' +
      '<g id="foil" inkscape:groupmode="layer" inkscape:label="Foil ' + esc(st.foil) + ' (' + esc(T.foils[st.foil] || '') + ') – colore speciale" fill="#E3A21A">' + lc(L.foil.join('')) + '</g>\n' +
      '<g id="rilievo" inkscape:groupmode="layer" inkscape:label="Rilievo – colore speciale" fill="#6F5BE8">' + lc(L.emb.join('')) + '</g>\n' +
      '<g id="fustella" inkscape:groupmode="layer" inkscape:label="Fustella" fill="none" stroke="#00A651" stroke-width=".1"><path d="' + shape(0, W, H, st.shape) + '"/></g>\n' +
      '<g id="abbondanza" inkscape:groupmode="layer" inkscape:label="Abbondanza 2 mm (riferimento)" fill="none" stroke="#A7ADB0" stroke-width=".1" stroke-dasharray="1 1"><rect x="' + -B + '" y="' + -B + '" width="' + (W + 2 * B) + '" height="' + (H + 2 * B) + '"/></g>\n</svg>\n';
  }

  // ------------------------------------------------------------ checks shown to the visitor
  function specLines(st) {
    var t = T.spec, fo = st.foil === 'none' ? t.none : T.foils[st.foil] + ' – ' + Object.keys(st.foilOn || {}).filter(function (k) { return st.foilOn[k] }).map(function (k) { return T.targets[k] }).join(', ');
    return [t.title, t.format + ': ' + st.w + ' × ' + st.h + ' mm (' + T.shapes[st.shape] + ')', t.material + ': ' + T.papers[st.paper], t.print + ': CMYK (' + T.inks[st.ink] + ')',
      t.finish + ': ' + t.foil + ' ' + fo + '; ' + t.emb + ' ' + (st.emb === 'none' ? t.none : T.targets[st.emb]) + '; ' + t.varnish + ' ' + T.varnishes[st.varnish],
      t.bottle + ': ' + T.bottles[st.bottle] + ', ' + (st.vol || ''), t.style + ': ' + T.styles[st.style],
      t.texts + ': ' + [st.winery, st.wine, st.vintage, st.denText, DEN[st.den], st.area, st.alc ? st.alc + '% vol' : '', st.vol].filter(Boolean).join(' | '),
      t.logo + ': ' + (st.logo ? (st.lraster ? t.logoRaster : t.logoVector) : t.logoNone)];
  }
  function warnings(st) {
    var bt = BOTTLES[st.bottle], w = [], fill = function (s) { return s.replace('{h}', st.h).replace('{w}', st.w).replace('{max}', bt.max).replace('{half}', Math.round(Math.PI * bt.d / 2)) };
    if (st.h > bt.max) w.push(['warn', fill(T.w.tall)]);
    if (st.w > Math.PI * bt.d / 2) w.push(['warn', fill(T.w.wide)]);
    if (st.w < 50 || st.h < 45) w.push(['warn', T.w.small]);
    if (st.foil !== 'none' && !Object.keys(st.foilOn || {}).some(function (k) { return st.foilOn[k] })) w.push(['info', T.w.foilNone]);
    if (st.emb !== 'none') w.push(['info', T.w.emb]);
    if (st.logo && st.lraster) w.push(['info', T.w.raster]);
    if (!st.logo) w.push(['info', T.w.monogram]);
    return w;
  }
  function checks(st) {
    var c = T.chk, ok = function (v) { return !!String(v || '').trim() };
    return [[ok(st.denText) || st.den !== 'vino', c.den], [ok(st.alc), c.alc], [ok(st.vol), c.vol], [ok(st.denText) || st.den !== 'vino' ? ok(st.alc) && ok(st.vol) : false, c.field]];
  }

  // ------------------------------------------------------------ form <-> state
  var f = $('#ld-f'), view = 'bottle', raf = 0;
  function fromForm() {
    var g = function (n) { var el = f.elements[n]; return el ? el.value : '' };
    ['winery', 'wine', 'vintage', 'den', 'denText', 'area', 'alc', 'vol', 'paper', 'ink', 'foil', 'emb', 'varnish', 'shape', 'bottle', 'lmode'].forEach(function (n) {
      var el = f.elements[n]; if (!el) return; S[n] = el.length && el[0] && el[0].type === 'radio' ? (f.querySelector('[name=' + n + ']:checked') || {}).value || S[n] : g(n);
    });
    var w = parseFloat(g('w').replace(',', '.')), h = parseFloat(g('h').replace(',', '.'));
    if (w >= 20 && w <= 320) S.w = w; if (h >= 20 && h <= 320) S.h = h;
    S.foilOn = {}; $$('[name=foilOn]').forEach(function (c) { if (c.checked) S.foilOn[c.value] = 1 });
  }
  function toForm() {
    ['winery', 'wine', 'vintage', 'den', 'denText', 'area', 'alc', 'vol', 'paper', 'ink', 'foil', 'emb', 'varnish', 'shape', 'bottle', 'lmode'].forEach(function (n) {
      $$('[name=' + n + ']').forEach(function (el) { if (el.type === 'radio') el.checked = el.value === S[n]; else el.value = S[n] == null ? '' : S[n] });
    });
    f.elements.w.value = S.w; f.elements.h.value = S.h;
    $$('[name=foilOn]').forEach(function (c) { c.checked = !!(S.foilOn || {})[c.value] });
    $$('[data-style]').forEach(function (bn) { bn.setAttribute('aria-pressed', bn.getAttribute('data-style') === S.style) });
    $('#ld-ftg').hidden = S.foil === 'none'; $('#ld-lm').hidden = !S.logo; $('#ld-lx').hidden = !S.logo;
  }
  function sizes() {
    var bt = BOTTLES[S.bottle], el = $('#ld-sizes');
    el.innerHTML = bt.sizes.map(function (s, i) { return '<button type="button" class="ld-chip' + (s[0] === S.w && s[1] === S.h ? ' on' : '') + '" data-w="' + s[0] + '" data-h="' + s[1] + '">' + s[0] + ' × ' + s[1] + (i ? '' : ' · ' + esc(T.suggested)) + '</button>' }).join('');
  }
  function render() {
    raf = 0; if (!F.cinzel) return;
    var W = S.w, H = S.h, out = $('#ld-view');
    if (view === 'bottle') out.innerHTML = bottle(S);
    else if (view === 'flat') out.innerHTML = '<svg viewBox="' + vb(W, H, 7) + '" role="img" aria-label="' + esc(T.ariaFlat) + '">' + layers('f', S, W, H, { bleed: 1, die: 1 }) +
      '<g font-family="DM Mono,monospace" font-size="2.6" fill="#686D71" letter-spacing=".2"><path d="M0 ' + (H + B + 3) + 'H' + W + 'M0 ' + (H + B + 1.8) + 'v2.4M' + W + ' ' + (H + B + 1.8) + 'v2.4M' + (W + B + 3) + ' 0V' + H + 'M' + (W + B + 1.8) + ' 0h2.4M' + (W + B + 1.8) + ' ' + H + 'h2.4" stroke="#686D71" stroke-width=".2"/>' +
      '<text x="' + W / 2 + '" y="' + (H + B + 6.4) + '" text-anchor="middle">' + W + ' MM</text><text transform="translate(' + (W + B + 6.2) + ' ' + H / 2 + ') rotate(90)" text-anchor="middle">' + H + ' MM</text></g></svg>';
    else out.innerHTML = '<div class="ld-sep">' + [['print', T.sep.print], ['foil', T.sep.foil], ['emb', T.sep.emb], ['die', T.sep.die]].map(function (x) {
      return '<figure><svg viewBox="' + vb(W, H, 2) + '">' + layers('s' + x[0], S, W, H, { only: x[0] }) + '</svg><figcaption class="mi">' + esc(x[1]) + '</figcaption></figure>' }).join('') + '</div>';
    $('#ld-dim').textContent = W + ' × ' + H + ' mm · ' + T.shapes[S.shape] + ' · ' + T.bottles[S.bottle] + ' · ' + T.papers[S.paper];
    $('#ld-warn').innerHTML = warnings(S).map(function (w) { return '<li class="' + w[0] + '">' + esc(w[1]) + '</li>' }).join('');
    $('#ld-chk').innerHTML = checks(S).map(function (c) { return '<li class="' + (c[0] ? 'ok' : 'no') + '"><span aria-hidden="true">' + (c[0] ? '✓' : '–') + '</span>' + esc(c[1]) + '</li>' }).join('');
    $$('[data-style]').forEach(function (bn) {
      var k = bn.getAttribute('data-style'), st = {}; for (var x in S) st[x] = S[x]; st.style = k; st.shape = STYLES[k].shape; st.foilOn = STYLES[k].foil; st.w = 90; st.h = 120; st.emb = 'none';
      bn.querySelector('.th').innerHTML = '<svg viewBox="' + vb(90, 120, 1) + '" aria-hidden="true">' + layers('t' + k, st, 90, 120, {}) + '</svg>';
    });
    sizes(); save();
  }
  var later = function () { if (!raf) raf = requestAnimationFrame(render) };

  f.addEventListener('input', function (ev) {
    if (ev.target.name === 'logo') return;
    fromForm(); if (ev.target.name === 'bottle') { var s = BOTTLES[S.bottle].sizes[0]; S.w = s[0]; S.h = s[1]; f.elements.w.value = S.w; f.elements.h.value = S.h }
    if (ev.target.name === 'w' || ev.target.name === 'h') $$('.ld-chip').forEach(function (c) { c.classList.remove('on') });
    toForm(); later();
  });
  f.addEventListener('change', function (ev) { if (ev.target.name !== 'logo') { fromForm(); toForm(); later() } });
  root.addEventListener('click', function (ev) {
    var t = ev.target.closest('button'); if (!t || !root.contains(t)) return;
    if (t.hasAttribute('data-style')) { var k = t.getAttribute('data-style'); S.style = k; S.shape = STYLES[k].shape; S.foilOn = {}; for (var x in STYLES[k].foil) S.foilOn[x] = 1; toForm(); later() }
    else if (t.hasAttribute('data-w')) { S.w = +t.getAttribute('data-w'); S.h = +t.getAttribute('data-h'); toForm(); later() }
    else if (t.hasAttribute('data-v')) { view = t.getAttribute('data-v'); $$('[data-v]').forEach(function (b) { b.setAttribute('aria-selected', b === t) }); later() }
    else if (t.id === 'ld-lx') { S.logo = null; S.lraster = 0; f.elements.logo.value = ''; toForm(); later() }
  });
  f.elements.logo.addEventListener('change', function () {
    var file = this.files && this.files[0], msg = $('#ld-lmsg'); msg.hidden = true; if (!file) return;
    if (file.size > 4 * 1048576 || !/^image\/(png|jpeg|svg\+xml|webp)$/.test(file.type)) { msg.textContent = T.logoBad; msg.hidden = false; return }
    var rd = new FileReader(); rd.onload = function () {
      var url = rd.result, im = new Image(); im.onload = function () { S.la = im.naturalWidth && im.naturalHeight ? im.naturalWidth / im.naturalHeight : 1; S.logo = url; S.lraster = file.type !== 'image/svg+xml' ? 1 : 0; toForm(); later() };
      im.onerror = function () { msg.textContent = T.logoBad; msg.hidden = false }; im.src = url;
    }; rd.readAsDataURL(file);
  });

  // ------------------------------------------------------------ request: the drawing travels with the form as one SVG file
  var rq = document.getElementById('ld-rq');
  if (rq) rq.upExtra = function (fd) {
    fromForm(); var g = function (n) { return (rq.elements[n] && rq.elements[n].value || '').trim() };
    var lines = specLines(S).concat([T.spec.qty + ': ' + (g('qty') || '–'), T.spec.apply + ': ' + (rq.querySelector('[name=apply]') || {}).value, T.spec.notes + ': ' + (g('notes') || '–')]);
    fd.set('message', lines.join('\n')); fd.delete('qty'); fd.delete('notes'); fd.delete('apply');
    var name = 'etichetta-' + ((S.winery || 'vino') + '-' + (S.wine || '')).toLowerCase().normalize('NFD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) + '.svg';
    fd.set('file', new Blob([fileSVG(S)], { type: 'image/svg+xml' }), name);
  };

  // ------------------------------------------------------------ start: fonts first, then the first drawing
  toForm(); sizes();
  var nav = document.getElementById('nav2'), top = function () { if (nav) root.style.setProperty('--ldtop', Math.round(nav.getBoundingClientRect().height) + 'px') };
  top(); window.addEventListener('resize', top);
  var names = Object.keys(FONTS), n = 0;
  names.forEach(function (k) {
    opentype.load(A + FONTS[k], function (err, font) {
      if (!err) F[k] = font; if (++n === names.length) { root.classList.add('ready'); if (!F.cinzel) { $('#ld-view').textContent = T.fontErr; return } render() }
    });
  });
})();
