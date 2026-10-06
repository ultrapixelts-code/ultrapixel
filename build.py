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


def visual(key, badge=""):
    badge = f'<span class="badge">{e(badge)}</span>' if badge else ""
    if key == "wine":
        return (f'<div class="vis">{badge}' + '<div class="obj" style="--ar:387/1026"><img src="/assets/bottle.webp" alt="" loading="lazy" width="800" height="2120">'
                '<div class="lb" style="left:11.24%;top:44.37%;width:77.52%;height:36.6%"><img src="/assets/final.webp" alt="" loading="lazy"></div></div></div>')
    pos, svg = LABELS[key]
    return (f'<div class="vis">{badge}<div class="obj"><img src="/assets/c-{key}.webp" alt="" loading="lazy" width="600" height="920">'
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
def seo_extra(C, P, path, meta):
    """hreflang alternates (once more than one language exists) and JSON-LD: Organization everywhere,
    WebSite on the homepage, BreadcrumbList on inner pages, Service on sector and landing pages."""
    s = C["site"]; base = s["url"].rstrip("/"); rel = path[len(P) - 1:]
    alts = ""
    if len(LANGS) > 1:
        alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{base}{"" if l == DEFAULT else "/" + l}{rel}">' for l in LANGS)
        alts += f'<link rel="alternate" hreflang="x-default" href="{base}{rel}">'
    org = {"@type": "Organization", "@id": base + "/#organization", "name": s["name"], "legalName": s["legalName"], "url": base + "/",
           "description": s["description"], "foundingDate": s["founded"],
           "address": {"@type": "PostalAddress", "addressLocality": s["locality"], "addressCountry": s["country"]},
           "areaServed": "Europe", "knowsAbout": [t["title"] for t in C["technologies"]["items"]]}
    if s["email"]: org["email"] = s["email"]
    if s["phone"]: org["telephone"] = s["phone"]
    same = [u for u in (s["linkedin"], s["instagram"]) if u]
    if same: org["sameAs"] = same
    graph = [org]
    if rel == "/":
        graph.append({"@type": "WebSite", "@id": base + "/#website", "url": base + "/", "name": s["name"], "inLanguage": C["lang"], "publisher": {"@id": org["@id"]}})
    else:
        name = meta["title"].split(" | ")[0]
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": C["ui"]["home"], "item": base + P},
            {"@type": "ListItem", "position": 2, "name": name, "item": base + path}]})
        svc = {x["slug"]: (x["title"] + " labels", x["copy"]) for x in C["sectors"]}
        svc.update({x["slug"]: (x["h1"], x["lead"]) for x in C["landings"]})
        slug = rel.strip("/")
        if slug in svc:
            graph.append({"@type": "Service", "name": svc[slug][0], "description": svc[slug][1], "serviceType": "Self-adhesive label printing and finishing",
                          "provider": {"@id": org["@id"]}, "areaServed": "Europe", "url": base + path})
    return alts + '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False) + "</script>"


def shell(C, P, path, meta, body, home=False, extra_head="", extra_foot=""):
    s, ui = C["site"], C["ui"]
    url = s["url"].rstrip("/") + path
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
{seo_extra(C, P, path, meta)}
{'<meta name="robots" content="noindex">' if s["noindex"] else ""}
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
  <nav id="nav">{nav}<a href="{P}partners/">{e(ui["partners"])}</a><a class="only-m" href="{P}samples/">{e(ui["requestSamples"])} →</a></nav>
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


def badge(x):
    return f'<span class="badge">{e(x["badge"])}</span>' if x.get("badge") else ""


def work_tiles(C, items):
    return '<div class="works">' + "".join(
        f'<figure class="wk rv" data-light>{badge(w)}<img src="/assets/{e(w["image"])}" alt="{e(w["title"])}" loading="lazy" width="720" height="900">'
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
        f'<a class="card rv" href="{P}{x["slug"]}/" data-k="{x["key"]}">{visual(x["key"], ui["conceptLabel"] if x["key"] == "wine" else ui["illustrative"])}<div class="txt"><h3>{e(x["title"])}</h3><p>{e(x["copy"])}</p><span class="go">{e(ui["explore"])} →</span></div></a>'
        for x in C["sectors"])
    nums = "".join(f"<div><b>{e(a)}</b><span>{e(b)}</span></div>" for a, b in h["numbers"])
    social = "".join(
        (f'<a href="{e(t["url"])}" rel="noopener">' if t["url"] else "<div>") + f'{badge(t)}<img src="/assets/{e(t["image"])}" alt="" loading="lazy" width="720" height="900"><span class="cap">{e(t["caption"])}</span>' + ("</a>" if t["url"] else "</div>")
        for t in C["social"])
    body = f'''{film}
<section class="sec deep">{head(an["eyebrow"], an["h2"], an["p"])}
 <div class="anat" id="anat"><figure><img src="/assets/final.webp" alt="UltraPixel showcase label with numbered callouts" loading="lazy" width="1120" height="1402">{pins}</figure><ol>{lis}</ol></div>
</section>
<section class="sec" id="sectors">{head(h["sectors"]["eyebrow"], h["sectors"]["h2"], h["sectors"]["p"])}
 <div class="cards">{cards}</div>
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
    body = (phero(ui["sectors"], x["title"], x["copy"], visual(x["key"], ui["conceptLabel"] if x["key"] == "wine" else ui["illustrative"])) +
            f'<section class="sec"><ul class="plist">{"".join(f"<li class=rv>{e(p)}</li>" for p in x["points"])}</ul></section>'
            f'<section class="sec deep tight"><span class="eyebrow" style="margin-bottom:22px">{e(ui["technologies"])}</span>{tech_chips(C, P, x["tech"])}</section>' + cta_band(C, P))
    return shell(C, P, f'{P}{x["slug"]}/', x["meta"], body)


def slot(C, code, caption, image=""):
    """A photo position. Set image to a file in /assets to fill it; the code matches the shot list."""
    if image:
        return f'<figure class="slot"><img src="/assets/{e(image)}" alt="{e(caption)}" loading="lazy"></figure>'
    return f'<figure class="slot empty"><b>{e(code)}</b><span>{e(caption)}</span><em>{e(C["wine"]["slot"])}</em></figure>'


def wine_page(C, P, x):
    w, ui = C["wine"], C["ui"]
    q = f'{P}samples/?sector={x["title"].replace("&", "%26").replace(" ", "+")}'
    hero = (f'<section class="phero"><div><span class="eyebrow">{e(x["title"])}</span><h1>{e(w["hero"]["h1"])}</h1><p class="lead">{e(w["hero"]["lead"])}</p>'
            f'<div class="cta-row" style="margin-top:28px"><a class="btn" href="{q}">{e(w["hero"]["cta1"])}</a><a class="btn line" href="{P}contact/?topic=quote&sector={x["title"].replace("&", "%26").replace(" ", "+")}">{e(w["hero"]["cta2"])}</a></div></div>'
            f'{visual("wine", ui["conceptLabel"])}</section>')
    who = "".join(f'<div class="rv"><h3>{e(a)}</h3><p>{e(b)}</p></div>' for a, b in w["for"]["items"])
    fin = "".join(f'<article class="fin rv">{slot(C, i["shot"], i["title"], i.get("image", ""))}<h3>{e(i["title"])}</h3><p>{e(i["text"])}</p></article>' for i in w["finish"]["items"])
    m, r, pr, g, fq = w["materials"], w["runs"], w["process"], w["gallery"], w["faq"]
    body = (hero +
            f'<section class="sec">{head(w["for"]["eyebrow"], w["for"]["h2"])}<div class="trio">{who}</div></section>'
            f'<section class="sec deep">{head(w["finish"]["eyebrow"], w["finish"]["h2"])}<div class="fins">{fin}</div>'
            f'<p class="more"><a class="tlink" href="{P}technologies/">{e(ui["allTechnologies"])} →</a></p></section>'
            f'<section class="sec"><div class="two"><div>{head(m["eyebrow"], m["h2"], m["p"])}<ul class="plist">{"".join(f"<li>{e(i)}</li>" for i in m["items"])}</ul></div>{slot(C, m["shot"], m["h2"], m.get("image", ""))}</div></section>'
            f'<section class="sec deep"><div class="two">{slot(C, r["shot"], r["h2"], r.get("image", ""))}<div>{head(r["eyebrow"], r["h2"])}<div class="rows">{"".join(f"<div><h3>{e(a)}</h3><p>{e(b)}</p></div>" for a, b in r["items"])}</div></div></div></section>'
            f'<section class="sec">{head(pr["eyebrow"], pr["h2"])}<ol class="steps">{"".join(f"<li class=rv><h3>{e(a)}</h3><p>{e(b)}</p></li>" for a, b in pr["steps"])}</ol></section>'
            f'<section class="sec deep">{head(g["eyebrow"], g["h2"])}<div class="gal">{"".join(slot(C, s[0], s[1], s[2] if len(s) > 2 else "") for s in g["shots"])}</div></section>'
            f'<section class="sec call"><div class="bg" style="--img:url(/assets/macro-2.webp)"></div><div class="in rv"><h2>{e(w["kit"]["h2"])}</h2><p>{e(w["kit"]["p"])}</p><a class="btn" href="{q}">{e(w["kit"]["cta"])}</a></div></section>'
            f'<section class="sec">{head(fq["eyebrow"], fq["h2"])}<div class="faq">{"".join(f"<details><summary>{e(a)}</summary><p>{e(b)}</p></details>" for a, b in fq["items"])}</div></section>'
            + cta_band(C, P))
    ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": a, "acceptedAnswer": {"@type": "Answer", "text": b}} for a, b in fq["items"]]}, ensure_ascii=False)
    return shell(C, P, f'{P}{x["slug"]}/', w["meta"], body, extra_head=f'<script type="application/ld+json">{ld}</script>')


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
    w = C["work"]; f = w["caseFields"]; s = w["showcase"]
    show = (f'<article class="case"><img src="/assets/{e(s["image"])}" alt="{e(s["title"])}" loading="lazy" width="720" height="900"><div><span class="eyebrow">{e(s["tag"])}</span><h3>{e(s["title"])}</h3><dl>'
            + "".join(f"<dt>{e(a)}</dt><dd>{e(b)}</dd>" for a, b in s["rows"]) + "</dl></div></article>")
    cases = "".join(
        f'<article class="case"><img src="/assets/{e(c["image"])}" alt="{e(c["title"])}" loading="lazy" width="720" height="900"><div><h3>{e(c["title"])}</h3><dl>'
        + "".join(f"<dt>{e(f[k])}</dt><dd>{e(c[k])}</dd>" for k in ("challenge", "solution", "materials", "technologies", "result")) + "</dl></div></article>"
        for c in w["cases"]) or f'<p class="empty">{e(w["caseEmpty"])}</p>'
    body = (phero(C["ui"]["work"], w["h1"], w["lead"]) + f'<section class="sec">{work_tiles(C, w["items"])}</section>'
            f'<section class="sec deep" id="showcase"><header class="shead"><h2>{e(s["h2"])}</h2></header>{show}</section>'
            f'<section class="sec" id="case-studies"><header class="shead"><h2>{e(w["caseH2"])}</h2></header>{cases}</section>' + cta_band(C, P))
    return shell(C, P, f"{P}work/", w["meta"], body)


def form_page(C, P, key, topic):
    p = C["pages"][key]
    return shell(C, P, f"{P}{key}/", p["meta"], phero(C["ui"]["contact"], p["h1"], p["lead"]) + f'<section class="sec">{form(C, P, topic)}</section>')


def about_page(C, P):
    p, h = C["pages"]["about"], C["home"]
    facts = "".join(f"<dt>{e(a)}</dt><dd>{e(b)}</dd>" for a, b in p["facts"])
    body = (phero(C["ui"]["about"], p["h1"], "") + f'<section class="sec about"><p>{e(h["about"]["p1"])}</p><p>{e(h["about"]["p2"])}</p></section>'
            f'<section class="sec tight"><header class="shead"><h2>{e(p["factsH2"])}</h2></header><dl class="facts">{facts}</dl></section>'
            f'<section class="sec deep"><div class="two"><div><h2 style="font-size:clamp(30px,4vw,54px);line-height:1.05;margin-bottom:20px">{e(h["position"]["h2"])}</h2><p class="lead">{e(h["position"]["p"])}</p></div>{europe_map()}</div></section>'
            f'<section class="sec tight"><div class="nums">{"".join(f"<div><b>{e(a)}</b><span>{e(b)}</span></div>" for a, b in h["numbers"])}</div></section>' + cta_band(C, P))
    return shell(C, P, f"{P}about/", p["meta"], body)


def build(launch=False):
    """launch=True (python3 build.py --launch) removes noindex and switches every URL to site.launchUrl."""
    paths = []
    for lang in LANGS:
        C = json.loads(rd(f"content/{lang}.json")); P = "/" if lang == DEFAULT else f"/{lang}/"
        if launch:
            if not C["site"]["launchUrl"]:
                raise SystemExit("Set site.launchUrl in content/en.json before a launch build.")
            C["site"]["noindex"] = False; C["site"]["url"] = C["site"]["launchUrl"]
        if lang == DEFAULT:
            C0 = C
        out = {P: home(C, P), f"{P}technologies/": tech_page(C, P), f"{P}work/": work_page(C, P), f"{P}about/": about_page(C, P),
               f"{P}samples/": form_page(C, P, "samples", "samples"), f"{P}contact/": form_page(C, P, "contact", "quote"), f"{P}partners/": form_page(C, P, "partners", "partner")}
        for x in C["sectors"]:
            out[f'{P}{x["slug"]}/'] = wine_page(C, P, x) if x["key"] == "wine" and "wine" in C else sector_page(C, P, x)
        for x in C["landings"]:
            out[f'{P}{x["slug"]}/'] = landing_page(C, P, x)
        for path, s in out.items():
            wr(path.lstrip("/") + "index.html", s); paths.append(path)
        site = C["site"]["url"].rstrip("/")
    wr("assets/film.css", rd("src/film.css")); wr("assets/film.js", rd("src/film.js"))
    wr("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{site}{p}</loc></url>\n" for p in paths) + "</urlset>\n")
    bots = "User-agent: OAI-SearchBot\nAllow: /\n\nUser-agent: ChatGPT-User\nAllow: /\n\n"
    if C0["site"]["blockAiTraining"]:
        bots += "User-agent: GPTBot\nDisallow: /\n\n"
    wr("robots.txt", bots + f"User-agent: *\nAllow: /\n\nSitemap: {site}/sitemap.xml\n")
    wr("404.html", shell(C0, "/", "/404.html", {"title": "Page not found | UltraPixel", "description": C0["ui"]["notFound"]},
                         phero("404", C0["ui"]["notFound"], "") + f'<section class="sec"><a class="btn" href="/">{e(C0["ui"]["backHome"])}</a></section>'))
    print(f"built {len(paths)} pages")


# ================================================================ MATERIAL INTELLIGENCE (home + wine & spirits)
def shell_ml(C, P, path, meta, body, extra_head="", extra_foot=""):
    s, ui = C["site"], C["ui"]; url = s["url"].rstrip("/") + path
    nav = "".join(f'<a href="{h}">{e(ui[k])}</a>' for k, h in (("sectors", f"{P}#sectors"), ("technologies", f"{P}technologies/"), ("work", f"{P}work/"), ("about", f"{P}about/"), ("contact", f"{P}contact/")))
    contact = "".join(f"<li>{x}</li>" for x in (
        e(s["address"]), f'<a href="mailto:{e(s["email"])}">{e(s["email"])}</a>' if s["email"] else "", f'<a href="tel:{e(s["phone"].replace(" ", ""))}">{e(s["phone"])}</a>' if s["phone"] else "",
        f'<a href="{e(s["linkedin"])}" rel="noopener">LinkedIn</a>' if s["linkedin"] else "", f'<a href="{e(s["instagram"])}" rel="noopener">Instagram</a>' if s["instagram"] else "") if x)
    secs = "".join(f'<li><a href="{P}{x["slug"]}/">{e(x["title"])}</a></li>' for x in C["sectors"])
    return f'''<!doctype html>
<html lang="{C["lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(meta["title"])}</title>
<meta name="description" content="{e(meta["description"])}">
<link rel="canonical" href="{url}">
{seo_extra(C, P, path, meta)}
{'<meta name="robots" content="noindex">' if s["noindex"] else ""}
<meta property="og:type" content="website"><meta property="og:title" content="{e(meta["title"])}"><meta property="og:description" content="{e(meta["description"])}"><meta property="og:url" content="{url}"><meta property="og:image" content="{s["url"].rstrip("/")}/assets/macro-1.webp">
<meta name="theme-color" content="#F4F4F0">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=DM+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="/assets/ml.css">
{extra_head}
</head>
<body>
<header class="nav2" id="nav2">
  <a class="logo" href="{P}">UltraPixel<sup>TS / IT</sup></a>
  <nav id="nav">{nav}<a class="only-m" href="{P}samples/">{e(ui["requestSamples"])} ↗</a></nav>
  <a class="cta" href="{P}samples/">{e(ui["requestSamples"])} ↗</a>
  <button class="burger" id="burger" aria-expanded="false" aria-controls="nav">{e(ui["menu"])}</button>
</header>
<main>
{body}
</main>
<hr class="spl">
<div class="partner2"><p class="mi">{e(C["home"]["partner"]["q"])}</p><a class="cta" href="{P}partners/">{e(C["home"]["partner"]["cta"])} →</a></div>
<hr class="spl">
<footer class="ftr2">
  <div class="cols">
    <div><span class="mi">{e(s["name"])}</span><ul>{contact}</ul></div>
    <div><span class="mi">{e(ui["sectors"])}</span><ul>{secs}</ul></div>
    <div><span class="mi">Index</span><ul><li><a href="{P}technologies/">{e(ui["technologies"])}</a></li><li><a href="{P}work/">{e(ui["work"])}</a></li><li><a href="{P}about/">{e(ui["about"])}</a></li><li><a href="{P}contact/">{e(ui["contact"])}</a></li></ul></div>
    <div><span class="mi">{e(ui["contact"])}</span><ul><li><a href="{P}samples/">{e(ui["requestSamples"])}</a></li><li><a href="{P}contact/?topic=quote">{e(ui["requestQuote"])}</a></li><li><a href="{P}partners/">{e(ui["partners"])}</a></li></ul></div>
  </div>
  <div class="wm" aria-hidden="true">UltraPixel</div>
  <p class="mi dim legal">© UltraPixel / {e(s["address"])}</p>
</footer>
<script src="/assets/ml.js" defer></script>
{extra_foot}
</body>
</html>
'''


def top(eyebrow, h2, p="", cls="h2"):
    return f'<header class="top"><span class="mi">{e(eyebrow)}</span><h2 class="{cls} rv">{e(h2)}</h2>{f"<p class=lead>{e(p)}</p>" if p else ""}</header>'


def talk_ml(C, P):
    ui, h = C["ui"], C["home"]
    return (f'<hr class="spl"><section class="sec talk"><h2 class="mega rv">{e(h["contact"]["h2a"])}<span>{e(h["contact"]["h2b"])}</span></h2>'
            f'<div class="ctas" style="margin-top:clamp(28px,4vw,56px)"><a class="cta pill" href="{P}contact/?topic=quote">{e(ui["requestQuote"])} ↗</a><a class="cta pill ghost" href="{P}samples/">{e(ui["requestSamples"])} ↗</a>'
            f'<a class="cta" href="{P}contact/?topic=specialist">{e(ui["talkSpecialist"])} →</a></div></section>')


def viz(C, x):
    ui = C["ui"]
    if x["key"] == "wine":
        inner = '<img class="flat" src="/assets/final.webp" alt="" loading="lazy" width="1120" height="1402" data-par>'; tag = ui["conceptLabel"]
    else:
        pos, svg = LABELS[x["key"]]; tag = ui["illustrative"]
        inner = f'<div class="obj" data-par><img src="/assets/c-{x["key"]}.webp" alt="" loading="lazy" width="600" height="920"><div class="lb wrapc" style="{pos}">{svg}</div></div>'
    return f'<div class="viz mat-{x["key"]}" data-light data-k="{x["key"]}">{inner}<span class="mi tagc">{e(tag)}</span><span class="mi code">{e(x["matter"])}</span></div>'


def net_map(C):
    import math
    m = json.loads(rd("src/map-fine.json")); tx, ty = m["tx"], m["ty"]; out = ""
    for i, (ang, L, bend) in enumerate(((178, 300, 22), (152, 330, -26), (124, 300, 20), (96, 250, -16), (62, 320, 24), (32, 300, -22), (-24, 260, 18), (-52, 210, -14), (206, 290, -20))):
        a = math.radians(ang); x2, y2 = tx + L * math.cos(a), ty - L * math.sin(a)
        cx, cy = (tx + x2) / 2 - bend * math.sin(a), (ty + y2) / 2 - bend * math.cos(a)
        dd = f"M{tx} {ty}Q{cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}"
        out += f'<path class="path" d="{dd}"/><path class="pulse" d="{dd}" style="animation-delay:{-i*0.47:.2f}s"/>'
    return (f'<svg viewBox="0 0 {m["W"]} {m["H"]}" role="img" aria-label="Europe drawn in points, with Trieste as the node of origin">'
            f'<defs><linearGradient id="specg" gradientUnits="userSpaceOnUse" x1="{tx-330}" x2="{tx+330}" y1="0" y2="0"><stop offset="0" stop-color="#22B8D6"/><stop offset=".4" stop-color="#6F5BE8"/><stop offset=".65" stop-color="#D9438F"/><stop offset="1" stop-color="#EBA43A"/></linearGradient></defs>'
            f'<path class="dots" d="{m["d"]}"/>{out}<circle class="node" cx="{tx}" cy="{ty}" r="7"/><circle cx="{tx}" cy="{ty}" r="3.4" fill="#101214"/>'
            f'<text x="{tx+12}" y="{ty+20}" font-family="DM Mono,monospace" font-size="11" letter-spacing="1.6" fill="#101214">TRIESTE</text></svg>')


def home_ml(C, P):
    h, ui = C["home"], C["ui"]; he = h["hero"]
    hero = (f'<div class="panel hero on" data-c="0"><span class="mono">{e(he["tag"])}</span><h1>{e(he["h1a"])} <em>{e(he["h1b"])}</em></h1><p>{e(he["sub"])}</p>'
            f'<div class="ctas"><a class="cta pill" href="{P}work/">{e(ui["exploreWork"])} ↗</a><a class="cta pill ghost" href="{P}samples/">{e(ui["requestSamples"])} ↗</a><a class="cta" href="{P}contact/">{e(ui["talkToUs"])} →</a></div>'
            f'<div class="sys"><span class="mi">{e(he["chain"])}</span><span class="mi dim">{e(he["sectors"])}</span></div></div>')
    rail = '<div class="rail" id="rail">' + "".join(f'<span data-c="{i+1}">{i+1:02d} {e(n.upper())}</span>' for i, n in enumerate(h["rail"])) + '</div><span class="mi tag-sys">UP / SEQ 01–08</span>'
    film = rd("src/film.html").replace("{{HERO}}", hero).replace("{{RAIL}}", rail)
    an = h["anatomy"]
    pins = "".join(f'<span class="pin" data-i="{i}" style="left:{x}%;top:{y}%">{i+1}</span>' for i, (_, _, x, y) in enumerate(an["items"]))
    lis = "".join(f'<li data-i="{i}"><b>{i+1:02d}</b><strong>{e(a)}</strong><span>{e(b)}</span></li>' for i, (a, b, _, _) in enumerate(an["items"]))
    scenes = "".join(
        f'<a class="scene" href="{P}{x["slug"]}/">{viz(C, x)}<div class="say"><span class="mi">{i+1:02d}</span><h3 class="rv">{e(x["title"])}</h3><p>{e(x["copy"])}</p><span class="cta">{e(h["sectors"]["enter"])} →</span></div></a>'
        for i, x in enumerate(C["sectors"]))
    def num(a):
        d = "".join(ch for ch in a if ch.isdigit())
        return f'<b data-count="{d}" data-suf="{e(a[len(d):])}">{e(a)}</b>' if a[:1].isdigit() else f"<b>{e(a)}</b>"
    nums = "".join(f'<div>{num(a)}<span class="mi">{e(b)}</span></div>' for a, b in h["numbers"])
    tech = {t["id"]: t for t in C["technologies"]["items"]}; lab = h["lab"]; r = random.Random(4)
    datam = "".join(f'<b>N° {i:04d}</b> / LOT 000000 / SN {r.randrange(16**4):04X}-{r.randrange(16**4):04X} / ' for i in range(1, 90))
    tabs = "".join(f'<button role="tab" data-t="{i}" data-cap="LAB / {i+1:02d} — {e(g[0].upper())}" aria-selected="{"true" if i == 0 else "false"}">{e(g[0])}<i>{len(g[1]):02d}</i></button>' for i, g in enumerate(lab["groups"]))
    macros = "".join((f'<img data-t="{i}" class="{"on" if i == 0 else ""}" src="/assets/{g[2]}" alt="{e(g[0])} macro" loading="lazy" width="1400" height="1050">' if g[2] else f'<div data-t="{i}" class="datam">{datam}</div>') for i, g in enumerate(lab["groups"]))
    lists = "".join(f'<div data-t="{i}" class="{"on" if i == 0 else ""}">' + "".join(f'<div class="row" id="{k}"><strong>{e(tech[k]["title"])}</strong><span>{e(tech[k]["text"])}</span></div>' for k in g[1]) + "</div>" for i, g in enumerate(lab["groups"]))
    c = h["colour"]
    flow = "".join(f'<span class="mi">{e(x)}</span>' + ('<span class="mi">→</span>' if i < len(c["flow"]) - 1 else "") for i, x in enumerate(c["flow"]))
    curve = ('<svg class="curve" viewBox="0 0 1200 300" role="img" aria-label="A measured spectral curve drawn over its reference">'
             '<defs><linearGradient id="specc" gradientUnits="userSpaceOnUse" x1="40" x2="1160" y1="0" y2="0"><stop offset="0" stop-color="#6F5BE8"/><stop offset=".3" stop-color="#22B8D6"/><stop offset=".62" stop-color="#EBA43A"/><stop offset="1" stop-color="#D9438F"/></linearGradient></defs>'
             '<path class="ref" d="M40 250C200 246 300 236 420 200S600 70 760 52S1000 44 1160 40"/><path class="mea" pathLength="1" d="M40 252C200 247 300 239 420 204S600 74 760 55S1000 46 1160 43"/>'
             + "".join(f'<text x="{40+i*373.3:.0f}" y="290" text-anchor="{"start" if i == 0 else "end" if i == 3 else "middle"}">{400+i*100} NM</text>' for i in range(4)) + "</svg>")
    show = "".join(
        f'<figure class="rv"><div class="im" data-light><img src="/assets/{e(w["image"])}" alt="{e(w["title"])}" loading="lazy" width="720" height="900" data-par></div>'
        f'<figcaption><span class="mi">UP / {i+1:03d}</span><span class="t">{e(w["title"])}</span><span class="mi c">{e(" + ".join(w["finishes"]))}{" · " + e(w["badge"]) if w.get("badge") else ""}</span></figcaption></figure>'
        for i, w in enumerate(C["work"]["items"]))
    soc = "".join(f'<figure><img src="/assets/{e(t["image"])}" alt="" loading="lazy" width="720" height="900"><figcaption><span class="mi">{e(t["caption"])}</span><span class="mi dim">{e(t.get("badge", ""))}</span></figcaption></figure>' for t in C["social"])
    po = h["position"]
    body = f'''{film}
<hr class="spl">
<section class="sec w">{top(an["eyebrow"], an["h2"], an["p"])}
 <div class="anat" id="anat"><figure><img src="/assets/final.webp" alt="UltraPixel concept label with numbered callouts" loading="lazy" width="1120" height="1402">{pins}</figure><ol>{lis}</ol></div>
</section>
<hr class="spl">
<section class="sec" id="sectors">{top(h["sectors"]["eyebrow"], h["sectors"]["h2"], h["sectors"]["p"])}{scenes}</section>
<hr class="spl">
<section class="sec w"><div class="net"><h2 class="mega rv">{e(po["mega"])}</h2>
 <div class="txt"><span class="mi">{e(po["chain"])}</span><p class="lead" style="color:var(--ink)">{e(po["h2"])}</p><p class="lead">{e(po["p"])}</p><span class="mi dim">{e(po["tag"])}</span></div>{net_map(C)}</div></section>
<hr class="spl">
<section class="sec t"><div class="nums">{nums}</div></section>
<hr class="spl">
<section class="sec w">{top(lab["eyebrow"], h["tech"]["h2"])}
 <div class="lab"><div class="tabs" role="tablist">{tabs}</div><div class="stage2" data-light>{macros}</div>
 <div class="cap"><span class="mi">LAB / 01 — {e(lab["groups"][0][0].upper())}</span><span class="mi dim">{e(lab["macro"])}</span></div><div class="list">{lists}</div></div>
 <p style="margin-top:clamp(28px,4vw,56px)"><a class="cta" href="{P}technologies/">{e(ui["allTechnologies"])} →</a></p>
</section>
<hr class="spl">
<section class="sec"><span class="mi">{e(c["eyebrow"])}</span><h2 class="mega rv" style="margin-top:18px">{e(c["mega"])}</h2><p class="lead" style="margin-top:18px;color:var(--ink)">{e(c["h2"])}</p>
 <div class="flow">{flow}</div>{curve}<ul class="pts">{"".join(f'<li class="mi">{e(x)}</li>' for x in c["points"])}</ul></section>
<hr class="spl">
<section class="sec w">{top(h["work"]["eyebrow"], h["work"]["h2"])}<div class="show">{show}</div>
 <p style="margin-top:clamp(40px,6vw,90px)"><a class="cta" href="{P}work/">{e(ui["allWork"])} →</a></p></section>
<hr class="spl">
<section class="sec callx"><h2 class="mega rv">{e(h["samples"]["h2"])}</h2><p class="lead">{e(h["samples"]["p"])}</p><div><a class="cta pill" href="{P}samples/">{e(ui["requestSamples"])} ↗</a></div></section>
{talk_ml(C, P)}
<hr class="spl">
<section class="sec w about"><span class="mi" style="display:block;margin-bottom:26px">{e(h["about"]["eyebrow"])}</span><p class="rv">{e(h["about"]["p1"])}</p><p class="rv">{e(h["about"]["p2"])}</p><p style="margin-top:30px"><a class="cta" href="{P}about/">{e(ui["discover"])} →</a></p></section>
<hr class="spl">
<section class="sec t"><span class="mi" style="display:block;margin-bottom:26px">{e(h["social"]["eyebrow"])}</span><div class="soc">{soc}</div></section>'''
    return shell_ml(C, P, P, h["meta"], body,
                    extra_head='<link rel="stylesheet" href="/assets/film.css"><link rel="preload" as="image" href="/assets/final.webp">',
                    extra_foot='<script src="/assets/film.js" defer></script>')


def frame(C, code, caption, image=""):
    if image:
        return f'<figure class="frame has"><img src="/assets/{e(image)}" alt="{e(caption)}" loading="lazy"></figure>'
    return f'<figure class="frame"><b>{e(code)}</b><span>{e(caption)}</span><span class="mi dim">{e(C["wine"]["slot"])}</span></figure>'


def wine_ml(C, P, x):
    w, ui = C["wine"], C["ui"]; he = w["hero"]
    sq = x["title"].replace("&", "%26").replace(" ", "+")
    hero = (f'<section class="whero"><div class="float" id="float"><div class="tilt"><img src="/assets/final.webp" alt="UltraPixel concept wine label" width="1120" height="1402"><div class="gl"></div></div></div>'
            f'<div class="say"><span class="mi">{e(he["sector"])}</span><h1><span class="xl">{e(he["xl"])}</span><span class="sub">{e(he["subh"])}</span></h1><p class="lead">{e(he["lead"])}</p>'
            f'<div class="ctas"><a class="cta pill" href="{P}samples/?sector={sq}">{e(he["cta1"])} ↗</a><a class="cta pill ghost" href="{P}contact/?topic=quote&sector={sq}">{e(he["cta2"])} ↗</a></div></div>'
            f'<div class="meta"><span class="mi">{e(he["system"])}</span><span class="mi dim">{e(ui["conceptLabel"])}</span></div></section>')
    who = "".join(f'<div><h3 class="rv">{e(a)}</h3><p>{e(b)}</p></div>' for a, b in w["for"]["items"])
    scenes = ""
    for i, it in enumerate(w["finish"]["items"]):
        real = it.get("image", ""); note = "" if real else f'<span class="mi">{e(w["macroNote"])} · {e(w["slot"])}</span>'
        codes = f'<div class="codes"><span class="mi">{e(it["shot"])}</span>{note}</div>'
        ov = f'<div class="ov"><span class="mi">Material {i+1:02d} / {len(w["finish"]["items"]):02d}</span><h2 class="rv">{e(it["title"])}</h2><p>{e(it["text"])}</p></div>'
        if it["fx"] == "cut" and not real:
            scenes += (f'<section class="ms cut">{codes}<div class="dieb"><img src="/assets/final.webp" alt="" loading="lazy"><svg viewBox="0 0 1120 1402" aria-hidden="true"><defs><linearGradient id="specd" gradientUnits="userSpaceOnUse" x1="0" x2="1120" y1="0" y2="1402"><stop offset="0" stop-color="#22B8D6"/><stop offset=".4" stop-color="#6F5BE8"/><stop offset=".7" stop-color="#D9438F"/><stop offset="1" stop-color="#EBA43A"/></linearGradient></defs>'
                       f'<path pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" d="{rd("src/die.txt")}"/></svg></div>{ov}</section>')
        else:
            scenes += f'<section class="ms {it["fx"]}" data-light>{codes}<img class="bgi" src="/assets/{e(real or it["macro"])}" alt="{e(it["title"])}" loading="lazy">{ov}</section>'
    m, r, pr, g, fq = w["materials"], w["runs"], w["process"], w["gallery"], w["faq"]
    body = (hero + '<hr class="spl">'
            f'<section class="sec w">{top(w["for"]["eyebrow"], w["for"]["h2"])}<div class="trio">{who}</div></section><hr class="spl">'
            f'<section class="sec">{top(w["finish"]["eyebrow"], w["finish"]["h2"])}</section>{scenes}'
            f'<section class="sec"><div class="split"><div class="a"><span class="mi">{e(m["eyebrow"])}</span><h2 class="h2 rv" style="margin:18px 0 22px">{e(m["h2"])}</h2><p class="lead">{e(m["p"])}</p>'
            f'<ul class="rows big" style="margin-top:34px">{"".join(f"<li>{e(i)}</li>" for i in m["items"])}</ul></div><div class="b">{frame(C, m["shot"], m["h2"], m.get("image", ""))}</div></div></section><hr class="spl">'
            f'<section class="sec w"><div class="split r"><div class="a"><span class="mi">{e(r["eyebrow"])}</span><h2 class="h2 rv" style="margin:18px 0 30px">{e(r["h2"])}</h2><div class="rows">{"".join(f"<div><h3>{e(a)}</h3><p>{e(b)}</p></div>" for a, b in r["items"])}</div></div>'
            f'<div class="b">{frame(C, r["shot"], r["h2"], r.get("image", ""))}</div></div></section><hr class="spl">'
            f'<section class="sec">{top(pr["eyebrow"], pr["h2"])}<ol class="steps">{"".join(f"<li><h3>{e(a)}</h3><p>{e(b)}</p></li>" for a, b in pr["steps"])}</ol></section><hr class="spl">'
            f'<section class="sec w">{top(g["eyebrow"], g["h2"])}<div class="hang">{"".join(frame(C, s[0], s[1], s[2] if len(s) > 2 else "") for s in g["shots"])}</div></section><hr class="spl">'
            f'<section class="sec callx"><h2 class="mega rv">{e(w["kit"]["h2"])}</h2><p class="lead">{e(w["kit"]["p"])}</p><div><a class="cta pill" href="{P}samples/?sector={sq}">{e(w["kit"]["cta"])} ↗</a></div></section><hr class="spl">'
            f'<section class="sec w">{top(fq["eyebrow"], fq["h2"])}<div class="faq">{"".join(f"<details><summary>{e(a)}</summary><p>{e(b)}</p></details>" for a, b in fq["items"])}</div></section>'
            + talk_ml(C, P))
    ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": a, "acceptedAnswer": {"@type": "Answer", "text": b}} for a, b in fq["items"]]}, ensure_ascii=False)
    return shell_ml(C, P, f'{P}{x["slug"]}/', w["meta"], body, extra_head=f'<script type="application/ld+json">{ld}</script><link rel="preload" as="image" href="/assets/final.webp">')


# the master design system is applied to the homepage and Wine & Spirits first
home, wine_page = home_ml, wine_ml

if __name__ == "__main__":
    import sys
    build(launch="--launch" in sys.argv)
