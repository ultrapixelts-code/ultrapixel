#!/usr/bin/env python3
"""Builds the UltraPixel static site.

  python3 build.py

All copy lives in content/<lang>.json. English is written to the site root;
any other language listed in LANGS is written under /<lang>/.
To change a work tile, a case study or a social tile, edit content/en.json
(image file name in /assets, title, finishes) and run this script again.
The scroll sequence on the homepage lives in src/film.* and is not generated.
"""
import html, json, os, random

ROOT = os.path.dirname(os.path.abspath(__file__))
LANGS = ["en"]            # add "it", "fr", "de" once content/<lang>.json exists
DEFAULT = "en"
e = html.escape


def rd(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()


def wr(p, s):
    p = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


# ---------------------------------------------------------------- visuals
def pattern(x, y, size, n, seed, finder=False):
    """A code-like module grid (decorative, not scannable)."""
    r = random.Random(seed); c = size / n; out = []
    for i in range(n):
        for j in range(n):
            edge = i == 0 or j == n - 1
            if edge or r.random() < .48:
                out.append(f'<rect x="{x+i*c:.2f}" y="{y+j*c:.2f}" width="{c:.2f}" height="{c:.2f}"/>')
    if finder:
        for fx, fy in ((0, 0), (n - 5, 0), (0, n - 5)):
            out.append(f'<rect x="{x+fx*c:.2f}" y="{y+fy*c:.2f}" width="{5*c:.2f}" height="{5*c:.2f}" fill="#fff"/>'
                       f'<rect x="{x+fx*c:.2f}" y="{y+fy*c:.2f}" width="{5*c:.2f}" height="{5*c:.2f}" fill="none" stroke="#111" stroke-width="{c:.2f}"/>'
                       f'<rect x="{x+(fx+1.5)*c:.2f}" y="{y+(fy+1.5)*c:.2f}" width="{2*c:.2f}" height="{2*c:.2f}"/>')
    return '<g fill="#111">' + "".join(out) + "</g>"


SERIF = "font-family=\"Bodoni Moda,Didot,serif\""
MONO = "font-family=\"IBM Plex Mono,monospace\""
SANS = "font-family=\"Hanken Grotesk,Arial,sans-serif\""
LABELS = {
    "food": ("left:18.3%;top:41.3%;width:63.4%;height:39.1%", f'''<svg viewBox="0 0 190 180" preserveAspectRatio="none" aria-hidden="true"><rect width="190" height="180" fill="#F6F1E7"/><rect width="190" height="32" fill="#9E1B1B"/>
<text x="95" y="20" text-anchor="middle" {MONO} font-size="7.5" letter-spacing="3" fill="#F6F1E7">TRADITIONAL RECIPE</text>
<text x="95" y="82" text-anchor="middle" {SERIF} font-style="italic" font-size="31" fill="#1b1b1b">Rosso Vivo</text>
<path d="M50 94H140" stroke="#9E1B1B" stroke-width=".8"/><text x="95" y="110" text-anchor="middle" {MONO} font-size="8" letter-spacing="2.5" fill="#1b1b1b">TOMATO PASSATA</text>
<circle cx="95" cy="138" r="13" fill="#9E1B1B"/><path d="M95 124c-3-5 4-7 6-3" stroke="#2f5d2a" stroke-width="2" fill="none"/>
<text x="95" y="170" text-anchor="middle" {MONO} font-size="7" fill="#555">500 g</text></svg>'''),
    "cosmetic": ("left:32%;top:52.2%;width:36%;height:32.6%", f'''<svg viewBox="0 0 108 150" preserveAspectRatio="none" aria-hidden="true"><rect x="5" y="5" width="98" height="140" fill="none" stroke="#fff" stroke-width=".8" opacity=".85"/>
<text x="54" y="62" text-anchor="middle" {SERIF} font-size="34" fill="#fff">N°4</text><text x="54" y="84" text-anchor="middle" {MONO} font-size="7" letter-spacing="3" fill="#fff">FACE OIL</text>
<path d="M34 98H74" stroke="#fff" stroke-width=".7"/><text x="54" y="130" text-anchor="middle" {MONO} font-size="6" fill="#fff">30 ml · 1 fl oz</text></svg>'''),
    "pharma": ("left:23.3%;top:41.3%;width:53.4%;height:43.5%", f'''<svg viewBox="0 0 160 200" preserveAspectRatio="none" aria-hidden="true"><rect width="160" height="200" fill="#fff"/><rect width="160" height="30" fill="#1F4E8C"/>
<text x="12" y="19" {MONO} font-size="7.5" letter-spacing="2" fill="#fff">FOOD SUPPLEMENT</text><text x="12" y="74" {SANS} font-weight="600" font-size="25" fill="#14233a">Vitamin D3</text>
<text x="12" y="92" {SANS} font-size="11" fill="#14233a">60 capsules</text><path d="M12 106H148" stroke="#1F4E8C" stroke-width="1"/>
<g {MONO} font-size="7" fill="#14233a"><text x="12" y="150">LOT 000000</text><text x="12" y="162">EXP 00/0000</text><text x="12" y="186" font-size="5.5" fill="#667">Variable data per label</text></g>{pattern(104, 136, 44, 12, 7)}</svg>'''),
    "industrial": ("left:16.7%;top:40.4%;width:66.6%;height:23.1%", f'''<svg viewBox="0 0 200 106" preserveAspectRatio="none" aria-hidden="true"><rect width="200" height="106" fill="#fff"/><rect width="14" height="106" fill="#E2671B"/>
<text x="24" y="34" {SANS} font-weight="700" font-size="17" fill="#111">HYDRAULIC OIL</text><text x="24" y="52" {SANS} font-size="12" fill="#111">ISO VG 46 · 200 L</text>
<g {MONO} font-size="7" fill="#111"><text x="24" y="80">BATCH 000000</text><text x="24" y="92">SN 0000-0000</text></g>{pattern(138, 44, 52, 21, 11, True)}</svg>'''),
}


def visual(key):
    if key == "wine":
        return ('<div class="vis"><div class="obj" style="--ar:387/1026"><img src="/assets/bottle.webp" alt="" loading="lazy" width="800" height="2120">'
                '<div class="lb" style="left:11.24%;top:44.37%;width:77.52%;height:36.6%"><img src="/assets/final.webp" alt="" loading="lazy"></div></div></div>')
    pos, svg = LABELS[key]
    return (f'<div class="vis"><div class="obj"><img src="/assets/c-{key}.webp" alt="" loading="lazy" width="600" height="920">'
            f'<div class="lb wrapc" style="{pos}">{svg}</div></div></div>')


def europe_map(label="Trieste"):
    m = json.loads(rd("src/map.json")); tx, ty = m["tx"], m["ty"]
    import math
    rays = ""
    for ang, L, bend in ((178, 300, 22), (152, 330, -26), (124, 300, 20), (96, 250, -16), (62, 320, 24), (32, 300, -22), (-24, 260, 18), (-52, 210, -14), (206, 290, -20)):
        a = math.radians(ang); x2, y2 = tx + L * math.cos(a), ty - L * math.sin(a)
        cx, cy = (tx + x2) / 2 - bend * math.sin(a), (ty + y2) / 2 - bend * math.cos(a)
        rays += f'<path class="ray" d="M{tx} {ty}Q{cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}"/>'
    return (f'<svg class="map" viewBox="0 0 {m["W"]} {m["H"]}" role="img" aria-label="Europe, with Trieste as the point of origin">'
            f'<defs><radialGradient id="rayfade" gradientUnits="userSpaceOnUse" cx="{tx}" cy="{ty}" r="330"><stop offset="0" stop-color="#101418" stop-opacity=".8"/><stop offset=".7" stop-color="#101418" stop-opacity=".22"/><stop offset="1" stop-color="#101418" stop-opacity="0"/></radialGradient></defs>'
            f'<path class="dots" d="{m["d"]}"/>{rays}<circle class="pulse" cx="{tx}" cy="{ty}" r="12"/><circle cx="{tx}" cy="{ty}" r="5" fill="#1B2FBF"/>'
            f'<text x="{tx+14}" y="{ty+22}" font-family="Bodoni Moda,Didot,serif" font-size="24" fill="#101418">{e(label)}</text></svg>')


def colour_chart(c):
    return (f'<svg viewBox="0 0 440 260" role="img" aria-label="Spectral curve of a measured colour against its reference">'
            '<g stroke="#C5CBD0" stroke-width="1">' + "".join(f'<path d="M{60+i*110} 30V200"/>' for i in range(4)) + '<path d="M60 200H390"/></g>'
            '<path d="M60 176C120 172 150 168 190 150S250 70 300 56S360 50 390 48" fill="none" stroke="#101418" stroke-width="2"/>'
            '<path d="M60 178C120 173 150 170 190 153S250 73 300 58S360 51 390 50" fill="none" stroke="#1B2FBF" stroke-width="1.5" stroke-dasharray="5 5"/>'
            '<g font-family="IBM Plex Mono,monospace" font-size="10" fill="#56606A">' + "".join(f'<text x="{60+i*110}" y="218" text-anchor="middle">{400+i*100}</text>' for i in range(4)) +
            f'<text x="225" y="242" text-anchor="middle">{e(c["axis"])}</text>'
            f'<path d="M290 96H314" stroke="#101418" stroke-width="2"/><text x="322" y="100">{e(c["ref"])}</text>'
            f'<path d="M290 114H314" stroke="#1B2FBF" stroke-width="1.5" stroke-dasharray="5 5"/><text x="322" y="118">{e(c["meas"])}</text></g></svg>')


# ---------------------------------------------------------------- chrome
def shell(C, P, path, meta, body, home=False, extra_head="", extra_foot=""):
    s, ui = C["site"], C["ui"]
    url = s["url"].rstrip("/") + path
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{s["url"].rstrip("/")}{"" if l == DEFAULT else "/" + l}{path[len(P)-1:] if P != "/" else path}">' for l in LANGS) if len(LANGS) > 1 else ""
    nav = "".join(f'<a href="{P}{h}">{e(ui[k])}</a>' for k, h in (("sectors", "#sectors" if home else "#sectors"), ("technologies", "technologies/"), ("work", "work/"), ("about", "about/"), ("contact", "contact/")))
    nav = nav.replace(f'href="{P}#sectors"', f'href="{"" if home else P}#sectors"')
    contact = "".join(f"<li>{x}</li>" for x in (
        e(s["address"]),
        f'<a href="mailto:{e(s["email"])}">{e(s["email"])}</a>' if s["email"] else "",
        f'<a href="tel:{e(s["phone"].replace(" ", ""))}">{e(s["phone"])}</a>' if s["phone"] else "",
        f'<a href="{e(s["linkedin"])}" rel="noopener">LinkedIn</a>' if s["linkedin"] else "",
        f'<a href="{e(s["instagram"])}" rel="noopener">Instagram</a>' if s["instagram"] else "") if x)
    secs = "".join(f'<li><a href="{P}{x["slug"]}/">{e(x["title"])}</a></li>' for x in C["sectors"])
    return f'''<!doctype html>
<html lang="{C["lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(meta["title"])}</title>
<meta name="description" content="{e(meta["description"])}">
<link rel="canonical" href="{url}">
{'<meta name="robots" content="noindex">' if s["noindex"] else ""}{alts}
<meta property="og:type" content="website"><meta property="og:title" content="{e(meta["title"])}"><meta property="og:description" content="{e(meta["description"])}"><meta property="og:url" content="{url}"><meta property="og:image" content="{s["url"].rstrip("/")}/assets/macro-1.webp">
<meta name="theme-color" content="#ECEEEF">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400;0,6..96,500;1,6..96,400&family=Hanken+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="/assets/site.css">
{extra_head}
</head>
<body>
<header class="hdr{' light' if home else ''}" id="hdr">
  <a class="brand" href="{P}">Ultra<i>Pixel</i></a>
  <nav id="nav">{nav}<a href="{P}partners/">{e(ui["partners"])}</a></nav>
  <a class="btn sm" href="{P}samples/">{e(ui["requestSamples"])}</a>
  <button class="burger" id="burger" aria-expanded="false" aria-controls="nav">{e(ui["menu"])}</button>
</header>
<main>
{body}
</main>
<div class="partner"><p>{e(C["home"]["partner"]["q"])}</p><a class="tlink" href="{P}partners/">{e(C["home"]["partner"]["cta"])} →</a></div>
<footer class="ftr">
  <div class="cols">
    <div><a class="brand" href="{P}">Ultra<i>Pixel</i></a><ul style="margin-top:18px">{contact}</ul></div>
    <div><h4>{e(ui["sectors"])}</h4><ul>{secs}</ul></div>
    <div><h4>{e(s["name"])}</h4><ul><li><a href="{P}technologies/">{e(ui["technologies"])}</a></li><li><a href="{P}work/">{e(ui["work"])}</a></li><li><a href="{P}about/">{e(ui["about"])}</a></li><li><a href="{P}contact/">{e(ui["contact"])}</a></li></ul></div>
    <div><h4>{e(ui["contact"])}</h4><ul><li><a href="{P}samples/">{e(ui["requestSamples"])}</a></li><li><a href="{P}contact/?topic=quote">{e(ui["requestQuote"])}</a></li><li><a href="{P}partners/">{e(ui["partners"])}</a></li></ul></div>
  </div>
  <p class="legal">© UltraPixel · {e(s["address"])}</p>
</footer>
<script src="/assets/site.js" defer></script>
{extra_foot}
</body>
</html>
'''


def head(eyebrow, h2, p=""):
    return f'<header class="shead rv"><span class="eyebrow">{e(eyebrow)}</span><h2>{e(h2)}</h2>{f"<p>{e(p)}</p>" if p else ""}</header>'


def cta_band(C, P):
    ui, h = C["ui"], C["home"]
    return (f'<section class="sec deep talk"><h2 class="rv">{e(h["contact"]["h2a"])}<span>{e(h["contact"]["h2b"])}</span></h2>'
            f'<div class="cta-row"><a class="btn" href="{P}contact/?topic=quote">{e(ui["requestQuote"])}</a><a class="btn line" href="{P}samples/">{e(ui["requestSamples"])}</a>'
            f'<a class="btn line" href="{P}contact/?topic=specialist">{e(ui["talkSpecialist"])}</a></div></section>')


def tech_list(C, P, link=False):
    return '<div class="techs">' + "".join(
        f'<div class="tech" id="{t["id"]}"><i class="sw sw-{t["id"]}"></i><strong>{e(t["title"])}</strong><span>{e(t["text"])}</span></div>'
        for t in C["technologies"]["items"]) + "</div>"


def tech_chips(C, P, names):
    ids = {t["title"]: t["id"] for t in C["technologies"]["items"]}
    return '<div class="chips">' + "".join(f'<a href="{P}technologies/#{ids[n]}">{e(n)}</a>' for n in names) + "</div>"


def work_tiles(C, items):
    return '<div class="works">' + "".join(
        f'<figure class="wk rv" data-light><img src="/assets/{e(w["image"])}" alt="{e(w["title"])}" loading="lazy" width="720" height="900">'
        f'<figcaption><span>{e(w["sector"])}</span><strong>{e(w["title"])}</strong><em>{e(" · ".join(w["finishes"]))}</em></figcaption></figure>'
        for w in items) + "</div>"


def form(C, P, topic):
    f, s, ui = C["form"], C["site"], C["ui"]
    opts = "".join(f'<option value="{k}"{" selected" if k == topic else ""}>{e(v)}</option>' for k, v in f["topics"].items())
    secs = "".join(f"<option>{e(x['title'])}</option>" for x in C["sectors"]) + "<option>Other</option>"
    return (f'<form class="form" data-form data-endpoint="{e(s["formEndpoint"])}" data-email="{e(s["email"])}" data-none="{e(ui["formNotConnected"])}" data-sent="{e(ui["formSent"])}" data-error="{e(ui["formError"])}">'
            f'<label>{e(f["name"])}<input id="f-name" name="name" autocomplete="name" required></label>'
            f'<label>{e(f["company"])}<input id="f-company" name="company" autocomplete="organization" required></label>'
            f'<label>{e(f["country"])}<input id="f-country" name="country" autocomplete="country-name" required></label>'
            f'<label>{e(f["email"])}<input id="f-email" name="email" type="email" autocomplete="email" required></label>'
            f'<label>{e(f["sector"])}<select id="f-sector" name="sector">{secs}</select></label>'
            f'<label>{e(f["topic"])}<select id="f-topic" name="topic">{opts}</select></label>'
            f'<label class="full">{e(f["message"])}<textarea id="f-message" name="message" required></textarea></label>'
            f'<div class="full"><button class="btn" type="submit">{e(ui["send"])}</button></div><p class="form-msg" hidden></p></form>')


# ---------------------------------------------------------------- pages
def home(C, P):
    h, ui = C["home"], C["ui"]
    hero = (f'<div class="panel hero on" data-c="0"><h1>{e(h["hero"]["h1"])}</h1><p>{e(h["hero"]["sub"])}</p>'
            f'<div class="cta-row"><a class="btn ink" href="{P}work/">{e(ui["exploreWork"])}</a><a class="btn line-ink" href="{P}samples/">{e(ui["requestSamples"])}</a>'
            f'<a class="tlink" href="{P}contact/">{e(ui["talkToUs"])} →</a></div><div class="hero-sectors mono">{e(h["hero"]["sectors"])}</div></div>')
    film = rd("src/film.html").replace("{{HERO}}", hero)
    an = h["anatomy"]
    pins = "".join(f'<span class="pin" data-i="{i}" style="left:{x}%;top:{y}%">{i+1}</span>' for i, (_, _, x, y) in enumerate(an["items"]))
    lis = "".join(f'<li data-i="{i}"><b>{i+1:02d}</b><strong>{e(a)}</strong><span>{e(b)}</span></li>' for i, (a, b, _, _) in enumerate(an["items"]))
    cards = "".join(
        f'<a class="card rv" href="{P}{x["slug"]}/" data-k="{x["key"]}">{visual(x["key"])}<div class="txt"><h3>{e(x["title"])}</h3><p>{e(x["copy"])}</p><span class="go">{e(ui["explore"])} →</span></div></a>'
        for x in C["sectors"])
    nums = "".join(f"<div><b>{e(a)}</b><span>{e(b)}</span></div>" for a, b in h["numbers"])
    social = "".join(
        (f'<a href="{e(t["url"])}" rel="noopener">' if t["url"] else "<div>") + f'<img src="/assets/{e(t["image"])}" alt="" loading="lazy" width="720" height="900"><span>{e(t["caption"])}</span>' + ("</a>" if t["url"] else "</div>")
        for t in C["social"])
    body = f'''{film}
<section class="sec deep">{head(an["eyebrow"], an["h2"], an["p"])}
 <div class="anat" id="anat"><figure><img src="/assets/final.webp" alt="UltraPixel showcase label with numbered callouts" loading="lazy" width="1120" height="1402">{pins}</figure><ol>{lis}</ol></div>
</section>
<section class="sec" id="sectors">{head(h["sectors"]["eyebrow"], h["sectors"]["h2"], h["sectors"]["p"])}
 <div class="cards">{cards}</div><p class="note">{e(ui["illustrative"])}</p>
</section>
<section class="sec deep"><div class="two">
 <div class="rv"><span class="eyebrow">{e(h["position"]["eyebrow"])}</span><h2 style="font-size:clamp(34px,4.6vw,62px);line-height:1.05;margin:16px 0 22px">{e(h["position"]["h2"])}</h2><p class="lead">{e(h["position"]["p"])}</p><p class="tagline">{e(h["position"]["tag"])}</p></div>
 {europe_map()}
</div></section>
<section class="sec tight"><div class="nums">{nums}</div></section>
<section class="sec deep">{head(h["tech"]["eyebrow"], h["tech"]["h2"])}{tech_list(C, P)}
 <p class="more"><a class="tlink" href="{P}technologies/">{e(ui["allTechnologies"])} →</a></p>
</section>
<section class="sec"><div class="two cc">
 <div class="rv"><span class="eyebrow">{e(h["colour"]["eyebrow"])}</span><h2 style="font-size:clamp(34px,4.6vw,62px);line-height:1.05;margin-top:16px">{e(h["colour"]["h2"])}</h2><ul>{"".join(f"<li>{e(x)}</li>" for x in h["colour"]["points"])}</ul></div>
 {colour_chart(h["colour"])}
</div></section>
<section class="sec deep">{head(h["work"]["eyebrow"], h["work"]["h2"])}{work_tiles(C, C["work"]["items"])}
 <p class="more"><a class="tlink" href="{P}work/">{e(ui["allWork"])} →</a></p>
</section>
<section class="sec call"><div class="bg" style="--img:url(/assets/macro-2.webp)"></div><div class="in rv"><h2>{e(h["samples"]["h2"])}</h2><p>{e(h["samples"]["p"])}</p><a class="btn" href="{P}samples/">{e(ui["requestSamples"])}</a></div></section>
{cta_band(C, P)}
<section class="sec about"><span class="eyebrow" style="margin-bottom:26px">{e(h["about"]["eyebrow"])}</span><p class="rv">{e(h["about"]["p1"])}</p><p class="rv">{e(h["about"]["p2"])}</p><a class="tlink" href="{P}about/">{e(ui["discover"])} →</a></section>
<section class="sec deep tight"><span class="eyebrow" style="margin-bottom:26px">{e(h["social"]["eyebrow"])}</span><div class="social">{social}</div></section>'''
    return shell(C, P, P, h["meta"], body, home=True,
                 extra_head='<link rel="stylesheet" href="/assets/film.css"><link rel="preload" as="image" href="/assets/bottle.webp"><link rel="preload" as="image" href="/assets/final.webp">',
                 extra_foot='<script src="/assets/film.js" defer></script>')


def phero(eyebrow, h1, lead, right=""):
    return f'<section class="phero"><div><span class="eyebrow">{e(eyebrow)}</span><h1>{e(h1)}</h1>{f"<p class=lead>{e(lead)}</p>" if lead else ""}</div>{right}</section>'


def sector_page(C, P, x):
    ui = C["ui"]
    body = (phero(ui["sectors"], x["title"], x["copy"], visual(x["key"])) +
            f'<section class="sec"><ul class="plist">{"".join(f"<li class=rv>{e(p)}</li>" for p in x["points"])}</ul></section>'
            f'<section class="sec deep tight"><span class="eyebrow" style="margin-bottom:22px">{e(ui["technologies"])}</span>{tech_chips(C, P, x["tech"])}</section>' + cta_band(C, P))
    return shell(C, P, f'{P}{x["slug"]}/', x["meta"], body)


def landing_page(C, P, x):
    ui = C["ui"]
    body = (phero(ui["technologies"], x["h1"], x["lead"]) +
            f'<section class="sec"><span class="eyebrow" style="margin-bottom:22px">{e(ui["technologies"])}</span>{tech_chips(C, P, x["tech"])}</section>'
            f'<section class="sec deep">{work_tiles(C, C["work"]["items"][:3])}</section>' + cta_band(C, P))
    return shell(C, P, f'{P}{x["slug"]}/', x["meta"], body)


def tech_page(C, P):
    t = C["technologies"]
    return shell(C, P, f"{P}technologies/", t["meta"], phero(C["ui"]["technologies"], t["h1"], t["lead"]) + f'<section class="sec">{tech_list(C, P)}</section>' + cta_band(C, P))


def work_page(C, P):
    w = C["work"]; f = w["fields"]
    cases = "".join(
        f'<article class="case"><img src="/assets/{e(c["image"])}" alt="{e(c["title"])}" loading="lazy" width="720" height="900"><div><span class="eyebrow">{e(c.get("tag", ""))}</span><h3>{e(c["title"])}</h3><dl>'
        + "".join(f"<dt>{e(f[k])}</dt><dd>{e(c[k])}</dd>" for k in ("challenge", "solution", "materials", "technologies", "result")) + "</dl></div></article>"
        for c in w["cases"])
    body = (phero(C["ui"]["work"], w["h1"], w["lead"]) + f'<section class="sec">{work_tiles(C, w["items"])}</section>'
            f'<section class="sec deep" id="case-studies"><header class="shead"><h2>{e(w["caseH2"])}</h2></header>{cases}</section>' + cta_band(C, P))
    return shell(C, P, f"{P}work/", w["meta"], body)


def form_page(C, P, key, topic):
    p = C["pages"][key]
    return shell(C, P, f"{P}{key}/", p["meta"], phero(C["ui"]["contact"], p["h1"], p["lead"]) + f'<section class="sec">{form(C, P, topic)}</section>')


def about_page(C, P):
    p, h = C["pages"]["about"], C["home"]
    body = (phero(C["ui"]["about"], p["h1"], "") + f'<section class="sec about"><p>{e(h["about"]["p1"])}</p><p>{e(h["about"]["p2"])}</p></section>'
            f'<section class="sec deep"><div class="two"><div><h2 style="font-size:clamp(30px,4vw,54px);line-height:1.05;margin-bottom:20px">{e(h["position"]["h2"])}</h2><p class="lead">{e(h["position"]["p"])}</p></div>{europe_map()}</div></section>'
            f'<section class="sec tight"><div class="nums">{"".join(f"<div><b>{e(a)}</b><span>{e(b)}</span></div>" for a, b in h["numbers"])}</div></section>' + cta_band(C, P))
    return shell(C, P, f"{P}about/", p["meta"], body)


def build():
    paths = []
    for lang in LANGS:
        C = json.loads(rd(f"content/{lang}.json")); P = "/" if lang == DEFAULT else f"/{lang}/"
        out = {P: home(C, P), f"{P}technologies/": tech_page(C, P), f"{P}work/": work_page(C, P), f"{P}about/": about_page(C, P),
               f"{P}samples/": form_page(C, P, "samples", "samples"), f"{P}contact/": form_page(C, P, "contact", "quote"), f"{P}partners/": form_page(C, P, "partners", "partner")}
        for x in C["sectors"]:
            out[f'{P}{x["slug"]}/'] = sector_page(C, P, x)
        for x in C["landings"]:
            out[f'{P}{x["slug"]}/'] = landing_page(C, P, x)
        for path, s in out.items():
            wr(path.lstrip("/") + "index.html", s); paths.append(path)
        site = C["site"]["url"].rstrip("/")
    wr("assets/film.css", rd("src/film.css")); wr("assets/film.js", rd("src/film.js"))
    wr("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{site}{p}</loc></url>\n" for p in paths) + "</urlset>\n")
    wr("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {site}/sitemap.xml\n")
    print(f"built {len(paths)} pages")


if __name__ == "__main__":
    build()
