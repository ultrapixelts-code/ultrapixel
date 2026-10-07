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
LANGS = ["it", "en", "fr", "de"]   # every language except English is content/i18n/<lang>.json: a map from the English string to its translation
LANG_NAMES = {"en": "English", "it": "Italiano", "fr": "Français", "de": "Deutsch"}
DEFAULT = "en"   # language the content is written in
XDEF = "it"      # language used as hreflang x-default
HOME = "it"      # language served at the site root; the others live under /<lang>/
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


# Scroll-film label per language. g = bottle w,h / label centre x,y in the bottle / flat label w,h / end squeeze x,y
# (when the bottle is a photo that already wears the label, the flat label is squeezed onto it and faded out).
FILM = {"": {"a": "/assets", "vb": "0 0 1500 1000", "die": "src/die.txt", "g": [333, 1026, 167.8, 767.8, 450, 300, 0.79, 1.208], "sw": 900, "sz": "(max-width:899px) 70vw, 800px", "qc": [(30, 31), (61, 52), (27, 70)]}}
PUB = {}   # launch builds: language -> public base URL of that language (set in build())


def pub(C, l, rel):
    """Public URL of a page in language l. Before launch every language lives on this site; at launch a language
    with its own country domain (site.countryDomains) lives at that domain's root and the rest on the main domain."""
    if l in PUB:
        return PUB[l] + rel
    return C["site"]["url"].rstrip("/") + ("" if l == HOME else "/" + l) + rel


def offices(C):
    """Main address plus the other offices; the office of the root language's country comes first."""
    s = C["site"]; o = [(s["legalName"], s["address"])] + [(x["name"], x["address"]) for x in s.get("offices", [])]
    lead = [x for x in s.get("offices", []) if x.get("lang") == HOME]
    return [(x["name"], x["address"]) for x in lead] + [x for x in o if x[0] not in [y["name"] for y in lead]]


def lang_redirect(C):
    """Root-language pages only: on a first visit from outside the site, send a browser set to another language to its own
    version (unknown languages go to English). A language picked by hand is remembered and always respected; crawlers are left alone."""
    # a country domain (site.countryDomains) always opens in its own language: no automatic redirect there
    if C["lang"] != HOME or len(LANGS) < 2 or HOME in C["site"].get("countryDomains", {}):
        return ""
    others = [l for l in LANGS if l != HOME]
    return ("<script>(function(){try{var L=" + json.dumps(others) + ",s=null;try{s=localStorage.getItem('up_lang')}catch(e){}"
            "if(s||/bot|crawl|spider|slurp|preview|lighthouse|gpt|headless/i.test(navigator.userAgent))return;"
            "var r=document.referrer;if(r&&r.indexOf(location.protocol+'//'+location.host+'/')===0)return;"
            "var b=((navigator.languages&&navigator.languages[0])||navigator.language||'').slice(0,2).toLowerCase();"
            "if(!b||b==='" + HOME + "')return;var t=L.indexOf(b)>-1?b:'" + DEFAULT + "';"
            "try{if(r)sessionStorage.setItem('up_ref',r)}catch(e){}location.replace('/'+t+location.pathname+location.search+location.hash)}catch(e){}})()</script>\n")


def seo_extra(C, P, path, meta):
    """hreflang alternates (once more than one language exists) and JSON-LD: Organization everywhere,
    WebSite on the homepage, BreadcrumbList on inner pages, Service on sector and landing pages."""
    s = C["site"]; base = s["url"].rstrip("/"); rel = path[len(P) - 1:]
    alts = ""
    if len(LANGS) > 1:
        alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{pub(C, l, rel)}">' for l in LANGS)
        alts += f'<link rel="alternate" hreflang="x-default" href="{pub(C, XDEF, rel)}">'
    org = {"@type": "Organization", "@id": base + "/#organization", "name": s["name"], "legalName": s["legalName"], "url": base + "/",
           "description": s["description"], "foundingDate": s["founded"], "logo": base + "/assets/logo.png",
           "address": {"@type": "PostalAddress", "streetAddress": s["street"], "postalCode": s["postalCode"], "addressLocality": s["locality"],
                       "addressRegion": s["region"], "addressCountry": s["country"]}, "vatID": s["vatID"],
           "areaServed": "Europe", "knowsAbout": [t["title"] for t in C["technologies"]["items"]]}
    if s.get("offices"):
        org["location"] = [{"@type": "Place", "name": x["name"], "address": {"@type": "PostalAddress", "streetAddress": x["street"], "postalCode": x["postalCode"],
                            "addressLocality": x["locality"], "addressCountry": x["country"]}} for x in s["offices"]]
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
            {"@type": "ListItem", "position": 1, "name": C["ui"]["home"], "item": pub(C, C["lang"], "/")},
            {"@type": "ListItem", "position": 2, "name": name, "item": pub(C, C["lang"], rel)}]})
        svc = {x["slug"]: (x["title"] + " labels", x["copy"]) for x in C["sectors"]}
        svc.update({x["slug"]: (x["h1"], x["lead"]) for x in C["landings"]})
        slug = rel.strip("/")
        if slug in svc:
            graph.append({"@type": "Service", "name": svc[slug][0], "description": svc[slug][1], "serviceType": "Self-adhesive label printing and finishing",
                          "provider": {"@id": org["@id"]}, "areaServed": "Europe", "url": pub(C, C["lang"], rel)})
    return alts + '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False) + "</script>"


# ---------------------------------------------------------------- MATERIAL INTELLIGENCE design system
def shell_ml(C, P, path, meta, body, extra_head="", extra_foot="", cls=""):
    s, ui = C["site"], C["ui"]; url = pub(C, C["lang"], path[len(P) - 1:]) if path.endswith("/") else s["url"].rstrip("/") + path
    ui = dict(ui, sustain=C["sustainability"]["nav"])
    nav = f'<a class="price" href="{P}quote/">{e(ui["priceNav"])}</a>' + "".join(f'<a href="{h}">{e(ui[k])}</a>' for k, h in (("sectors", f"{P}#sectors"), ("technologies", f"{P}technologies/"), ("work", f"{P}work/"), ("sustain", f"{P}sustainability/"), ("about", f"{P}about/"), ("contact", f"{P}contact/")))
    contact = "".join(f"<li>{x}</li>" for x in (
        *[(f'{e(n)}<br>' if i or n != s["legalName"] else "") + e(a) for i, (n, a) in enumerate(offices(C))], f'{e(ui["vat"])} {e(s["vatID"][2:] if C["lang"] == "it" else s["vatID"])}', f'<a href="mailto:{e(s["email"])}">{e(s["email"])}</a>' if s["email"] else "", f'<a href="tel:{e(s["phone"].replace(" ", ""))}">{e(s["phone"])}</a>' if s["phone"] else "",
        f'<a href="{e(s["linkedin"])}" rel="noopener">LinkedIn</a>' if s["linkedin"] else "", f'<a href="{e(s["instagram"])}" rel="noopener">Instagram</a>' if s["instagram"] else "") if x)
    secs = "".join(f'<li><a href="{P}{x["slug"]}/">{e(x["title"])}</a></li>' for x in C["sectors"])
    return f'''<!doctype html>
<html lang="{C["lang"]}">
<head>
<meta charset="utf-8">
{lang_redirect(C)}<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(meta["title"])}</title>
<meta name="description" content="{e(meta["description"])}">
<link rel="canonical" href="{url}">
{seo_extra(C, P, path, meta)}
{'<meta name="robots" content="noindex">' if s["noindex"] else ""}
<meta property="og:type" content="website"><meta property="og:title" content="{e(meta["title"])}"><meta property="og:description" content="{e(meta["description"])}"><meta property="og:url" content="{url}"><meta property="og:image" content="{s["url"].rstrip("/")}/assets/macro-1.webp">
<meta name="theme-color" content="#F4F4F0">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/Archivo-100-900-latin.woff2" crossorigin>
<style>{rd("assets/fonts.css")}</style>
<link rel="stylesheet" href="/assets/ml.css">
{extra_head}
</head>
<body class="{cls}">
<header class="nav2" id="nav2">
  <a class="logo" href="{P}" aria-label="UltraPixel"><img src="/assets/logo.png" alt="UltraPixel" width="370" height="133"></a>
  <nav id="nav">{nav}<a class="only-m" href="{P}samples/">{e(ui["requestSamples"])} ↗</a></nav>
  <div class="right"><div class="lsw" aria-label="{e(ui["language"])}">{"".join(f"""<a href="{"/" if l == HOME else "/" + l + "/"}{path[len(P):]}" hreflang="{l}" lang="{l}"{' aria-current="true"' if l == C["lang"] else ""}>{l.upper()}</a>""" for l in LANGS)}</div>
  <a class="cta" href="{P}samples/">{e(ui["requestSamples"])} ↗</a></div>
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
    <div><span class="mi">{e(ui["index"])}</span><ul><li><a href="{P}technologies/">{e(ui["technologies"])}</a></li><li><a href="{P}work/">{e(ui["work"])}</a></li><li><a href="{P}sustainability/">{e(C["sustainability"]["nav"])}</a></li><li><a href="{P}about/">{e(ui["about"])}</a></li><li><a href="{P}contact/">{e(ui["contact"])}</a></li></ul></div>
    <div><span class="mi">{e(ui["contact"])}</span><ul><li><a href="{P}samples/">{e(ui["requestSamples"])}</a></li><li><a href="{P}contact/?topic=quote">{e(ui["requestQuote"])}</a></li><li><a href="{P}partners/">{e(ui["partners"])}</a></li></ul></div>
  </div>
  <img class="flogo" src="/assets/logo.png" alt="UltraPixel" width="370" height="133" loading="lazy">
  <p class="mi dim legal">© {e(s["legalName"])} / {e(s["address"])} / <a href="{P}privacy/">{e(ui["privacy"])}</a> / <a href="{P}cookies/">{e(ui["cookies"])}</a></p>
  <p class="mi dim legal langs">{" / ".join(f"""<a href="{"/" if l == HOME else "/" + l + "/"}{path[len(P):]}" hreflang="{l}"{' aria-current="true"' if l == C["lang"] else ""}>{LANG_NAMES[l]}</a>""" for l in LANGS)}</p>
</footer>
<script src="/assets/ml.js" defer></script><script src="/assets/lead.js" defer></script><script src="/assets/analytics.js" defer data-endpoint="{e(s["analyticsEndpoint"])}" data-lang="{C["lang"]}"></script>
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
    hi = C.get("sectorPages", {}).get(x["key"], {}).get("heroImg")
    if hi:
        return f'<div class="viz photo" data-light data-k="{x["key"]}"><img class="cover" src="/assets/{e(hi)}" alt="" loading="lazy" data-par><span class="mi tagc">{e(ui["illustrative"])}</span><span class="mi code">{e(x["matter"])}</span></div>'
    if x["key"] == "wine":
        inner = '<img class="flat" src="/assets/final.webp" alt="" loading="lazy" width="1500" height="1000" data-par>'; tag = ui["conceptLabel"]
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
    fm = C["film"]; panels = ""
    for i, (mono, h2, pp, small) in enumerate(fm["panels"]):
        extra = (f'<span class="mat" id="mat">{e(fm["mats"][0])}</span>' if i == 0 else '<div class="chips" id="chips"></div>' if i == 1 else "")
        text = "<br>".join(e(x) for x in fm["measure"]) if i == 6 else e(pp)
        panels += f'<div class="panel" data-c="{i+1}"><span class="mono">{e(mono)}</span><h2>{e(h2)}</h2><p>{text}</p>{extra}{f"<small>{e(small)}</small>" if small else ""}</div>\n  '
    fv = FILM.get(C["lang"], FILM[""])
    geo = (f'<style>#film .rig{{width:{fv["g"][0]}px;height:{fv["g"][1]}px;transform-origin:{fv["g"][2]}px {fv["g"][3]}px}}'
           f'#film .label{{left:{fv["g"][2] - fv["g"][4] / 2}px;top:{fv["g"][3] - fv["g"][5] / 2}px;width:{fv["g"][4]}px;height:{fv["g"][5]}px}}'
           f'#film .shadow{{left:{fv["g"][2] - fv["g"][4] * .4}px;top:{fv["g"][3] - fv["g"][5] * .38}px;width:{fv["g"][4] * .8}px;height:{fv["g"][5] * .8}px;border-radius:46%;filter:blur(30px)}}'
           f'#film.rdy #m0{{background-image:url({fv["a"]}/sheet.jpg)}}#film.rdy .relit{{-webkit-mask-image:url({fv["a"]}/final.webp);mask-image:url({fv["a"]}/final.webp)}}#film.rdy .glint{{-webkit-mask-image:url({fv["a"]}/gold.webp);mask-image:url({fv["a"]}/gold.webp)}}'
           f'#film.rdy .curve{{-webkit-mask-image:url({fv["a"]}/final.webp);mask-image:url({fv["a"]}/final.webp)}}</style>')
    film = (rd("src/film.html").replace("{{SRCSET}}", f'{fv["a"]}/final-s.webp {fv["sw"]}w, {fv["a"]}/final.webp {fv["vb"].split()[2]}w').replace("{{SIZES}}", fv["sz"]).replace("{{QC}}", "".join(f'<div class="qc" style="left:{x}%;top:{y}%" data-y="{y / 100}"></div>' for x, y in fv["qc"])).replace("{{A}}", fv["a"]).replace("{{VB}}", fv["vb"]).replace("{{DIE}}", rd(fv["die"]).strip())
            .replace("{{G}}", ",".join(str(x) for x in fv["g"])).replace("{{GEO}}", geo).replace("{{HERO}}", hero).replace("{{RAIL}}", rail).replace("{{PANELS}}", panels)
            .replace("{{SCROLL}}", e(ui["scroll"])).replace("{{MATS}}", e(json.dumps(fm["mats"] + fm["mats"][:1], ensure_ascii=False))))
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
        for i, w in enumerate(C["work"]["items"][:h.get("workCount", 6)]))
    soc = "".join(f'<figure><img src="/assets/{e(t["image"])}" alt="" loading="lazy" width="720" height="900"><figcaption><span class="mi">{e(t["caption"])}</span><span class="mi dim">{e(t.get("badge", ""))}</span></figcaption></figure>' for t in C["social"])
    po = h["position"]
    body = f'''{film}
<hr class="spl">
<section class="sec w">{top(an["eyebrow"], an["h2"], an["p"])}
 <div class="anat" id="anat"><figure><img src="{fv["a"]}/final.webp" alt="UltraPixel label with numbered callouts" loading="lazy" width="{fv["vb"].split()[2]}" height="{fv["vb"].split()[3]}">{pins}</figure><ol>{lis}</ol></div>
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
<section class="sec t"><div class="split"><div class="a"><span class="mi">{e(C["sustainability"]["home"]["eyebrow"])}</span><h2 class="h2 rv" style="margin-top:16px;font-size:clamp(30px,3.8vw,60px)">{e(C["sustainability"]["home"]["h2"])}</h2></div>
 <div class="b"><p class="lead">{e(C["sustainability"]["home"]["p"])}</p><p style="margin-top:22px"><a class="cta" href="{P}sustainability/">{e(C["sustainability"]["home"]["cta"])} →</a></p></div></div></section>
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
                    extra_head=f'<style>{rd("src/film.css")}</style><link rel="preload" as="image" href="{fv["a"]}/final.webp" imagesrcset="{fv["a"]}/final-s.webp {fv["sw"]}w, {fv["a"]}/final.webp {fv["vb"].split()[2]}w" imagesizes="{fv["sz"]}" fetchpriority="high">',
                    extra_foot='<script src="/assets/film.js" defer></script>')


def frame(C, code, caption, image="", note=""):
    if image:
        return f'<figure class="frame has"><img src="/assets/{e(image)}" alt="{e(caption)}" loading="lazy">{f"""<figcaption class="mi">{e(code)} · {e(note)}</figcaption>""" if note else ""}</figure>'
    return f'<figure class="frame"><b>{e(code)}</b><span>{e(caption)}</span><span class="mi dim">{e(C["wine"]["slot"])}</span></figure>'


def wine_ml(C, P, x):
    w, ui = C["wine"], C["ui"]; he = w["hero"]
    sq = x["title"].replace("&", "%26").replace(" ", "+")
    fl = (f'<div class="wphoto" data-light><img src="/assets/{e(he["image"])}" alt="Wine and spirits bottles with textured, foiled labels" width="1800" height="1200" data-par></div>' if he.get("image")
          else '<div class="float" id="float"><div class="tilt"><img src="/assets/final.webp" alt="UltraPixel wine label" width="1500" height="1000"><div class="gl"></div></div></div>')
    hero = (f'<section class="whero{" ph" if he.get("image") else ""}">{fl}'
            f'<div class="say"><span class="mi">{e(he["sector"])}</span><h1><span class="xl">{e(he["xl"])}</span><span class="sub">{e(he["subh"])}</span></h1><p class="lead">{e(he["lead"])}</p>'
            f'<div class="ctas"><a class="cta pill" href="{P}samples/?sector={sq}">{e(he["cta1"])} ↗</a><a class="cta pill ghost" href="{P}contact/?topic=quote&sector={sq}">{e(he["cta2"])} ↗</a></div></div>'
            f'<div class="meta"><span class="mi">{e(he["system"])}</span><span class="mi dim">{e(ui["conceptLabel"])}</span></div></section>')
    who = "".join(f'<div><h3 class="rv">{e(a)}</h3><p>{e(b)}</p></div>' for a, b in w["for"]["items"])
    scenes = ""
    for i, it in enumerate(w["finish"]["items"]):
        real = it.get("image", ""); note = ""
        codes = f'<div class="codes"><span class="mi">{e(it["shot"])}</span>{note}</div>'
        ov = f'<div class="ov"><span class="mi">{e(ui["material"])} {i+1:02d} / {len(w["finish"]["items"]):02d}</span><h2 class="rv">{e(it["title"])}</h2><p>{e(it["text"])}</p></div>'
        if it["fx"] == "cut" and not real:
            scenes += (f'<section class="ms cut">{codes}<div class="dieb"><img src="/assets/final.webp" alt="" loading="lazy"><svg viewBox="0 0 1500 1000" aria-hidden="true"><defs><linearGradient id="specd" gradientUnits="userSpaceOnUse" x1="0" x2="1500" y1="0" y2="1000"><stop offset="0" stop-color="#22B8D6"/><stop offset=".4" stop-color="#6F5BE8"/><stop offset=".7" stop-color="#D9438F"/><stop offset="1" stop-color="#EBA43A"/></linearGradient></defs>'
                       f'<path pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" d="{rd("src/die.txt")}"/></svg></div>{ov}</section>')
        else:
            scenes += f'<section class="ms {it["fx"]}" data-light>{codes}<img class="bgi" src="/assets/{e(real or it["macro"])}" alt="{e(it["title"])}" loading="lazy">{ov}</section>'
    m, r, pr, g, fq = w["materials"], w["runs"], w["process"], w["gallery"], w["faq"]
    body = (hero + '<hr class="spl">'
            f'<section class="sec w">{top(w["for"]["eyebrow"], w["for"]["h2"])}<div class="trio">{who}</div></section><hr class="spl">'
            f'<section class="sec">{top(w["finish"]["eyebrow"], w["finish"]["h2"])}</section>{scenes}'
            f'<section class="sec"><div class="split"><div class="a"><span class="mi">{e(m["eyebrow"])}</span><h2 class="h2 rv" style="margin:18px 0 22px">{e(m["h2"])}</h2><p class="lead">{e(m["p"])}</p>'
            f'<ul class="rows big" style="margin-top:34px">{"".join(f"<li>{e(i)}</li>" for i in m["items"])}</ul></div><div class="b">{frame(C, m["shot"], m["h2"], m.get("image", ""), m.get("note", ""))}</div></div></section><hr class="spl">'
            f'<section class="sec w"><div class="split r"><div class="a"><span class="mi">{e(r["eyebrow"])}</span><h2 class="h2 rv" style="margin:18px 0 30px">{e(r["h2"])}</h2><div class="rows">{"".join(f"<div><h3>{e(a)}</h3><p>{e(b)}</p></div>" for a, b in r["items"])}</div></div>'
            f'<div class="b">{frame(C, r["shot"], r["h2"], r.get("image", ""), r.get("note", ""))}</div></div></section><hr class="spl">'
            f'<section class="sec">{top(pr["eyebrow"], pr["h2"])}<ol class="steps">{"".join(f"<li><h3>{e(a)}</h3><p>{e(b)}</p></li>" for a, b in pr["steps"])}</ol></section><hr class="spl">'
            f'<section class="sec w">{top(g["eyebrow"], g["h2"])}<div class="hang">{"".join(frame(C, *s) for s in g["shots"])}</div></section><hr class="spl">'
            f'<section class="sec callx"><h2 class="mega rv">{e(w["kit"]["h2"])}</h2><p class="lead">{e(w["kit"]["p"])}</p><div><a class="cta pill" href="{P}samples/?sector={sq}">{e(w["kit"]["cta"])} ↗</a></div></section><hr class="spl">'
            f'<section class="sec w">{top(fq["eyebrow"], fq["h2"])}<div class="faq">{"".join(f"<details><summary>{e(a)}</summary><p>{e(b)}</p></details>" for a, b in fq["items"])}</div></section>'
            + talk_ml(C, P))
    ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": a, "acceptedAnswer": {"@type": "Answer", "text": b}} for a, b in fq["items"]]}, ensure_ascii=False)
    return shell_ml(C, P, f'{P}{x["slug"]}/', w["meta"], body, extra_head=f'<script type="application/ld+json">{ld}</script>')


# the master design system is applied to the homepage and Wine & Spirits first


# ---------------------------------------------------------------- pages
def faq_block(C, items):
    return '<div class="faq">' + "".join(f"<details><summary>{e(a)}</summary><p>{e(b)}</p></details>" for a, b in items) + "</div>"


def faq_ld(items):
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": a, "acceptedAnswer": {"@type": "Answer", "text": b}} for a, b in items]}, ensure_ascii=False) + "</script>"


def tech_links(C, P, names):
    ids = {t["title"]: t["id"] for t in C["technologies"]["items"]}
    return '<div class="tl">' + "".join(f'<a class="cta" href="{P}technologies/#{ids[n]}">{e(n)} →</a>' for n in names) + "</div>"


def kit(C, P, sector=""):
    h, ui = C["home"], C["ui"]; q = f'?sector={sector.replace("&", "%26").replace(" ", "+")}' if sector else ""
    return (f'<section class="sec callx"><h2 class="mega rv">{e(h["samples"]["h2"])}</h2><p class="lead">{e(h["samples"]["p"])}</p>'
            f'<div><a class="cta pill" href="{P}samples/{q}">{e(ui["requestSamples"])} ↗</a></div></section>')


def sector_ml(C, P, x, n):
    """Food, Cosmetics, Industrial and Pharma: one structure, a different visual physics each (body class phys-<key>)."""
    ui, d = C["ui"], C["sectorPages"][x["key"]]; sq = x["title"].replace("&", "%26").replace(" ", "+")
    hero = (f'<section class="shero"><div class="say"><span class="mi">{e(ui["sector"])} / {n:02d}</span>'
            f'<h1><span class="xl">{e(d["xl"])}</span><span class="sub">{e(d["sub"])}</span></h1><p class="lead">{e(d["answer"])}</p>'
            f'<div class="ctas"><a class="cta pill" href="{P}samples/?sector={sq}">{e(ui["requestSamples"])} ↗</a><a class="cta pill ghost" href="{P}contact/?topic=quote&sector={sq}">{e(ui["requestQuote"])} ↗</a></div></div>'
            f'{viz(C, x)}<div class="motif" aria-hidden="true"></div></section>')
    body = (hero + '<hr class="spl">'
            f'<section class="sec w">{top(ui["applications"], d["appsH"])}<ul class="rows big">{"".join(f"<li>{e(i)}</li>" for i in d["apps"])}</ul></section><hr class="spl">'
            f'<section class="sec"><div class="split"><div class="a"><span class="mi">{e(ui["materials"])}</span><h2 class="h2 rv" style="margin:18px 0 22px">{e(d["matsH"])}</h2><p class="lead">{e(d["matsP"])}</p>'
            f'<ul class="rows big" style="margin-top:34px">{"".join(f"<li>{e(i)}</li>" for i in d["mats"])}</ul></div><div class="b">{frame(C, *d["shots"][1])}</div></div></section><hr class="spl">'
            f'<section class="sec w">{top(ui["problems"], x["title"] + ".")}<div class="rows two">{"".join(f"<div><h3>{e(a)}</h3><p>{e(b)}</p></div>" for a, b in d["problems"])}</div>'
            f'<div style="margin-top:clamp(34px,5vw,70px)"><span class="mi">{e(ui["technologies"])}</span>{tech_links(C, P, d["tech"])}</div></section><hr class="spl">'
            f'<section class="sec">{top(ui["specify"], ui["specifyH"])}<ol class="check">{"".join(f"<li>{e(i)}</li>" for i in d["specify"])}</ol></section><hr class="spl">'
            f'<section class="sec w">{top(ui["proof"], ui["proofH"])}<div class="hang">{"".join(frame(C, *s) for s in d["shots"])}</div></section><hr class="spl">'
            f'<section class="sec">{top(ui["questions"], C["wine"]["faq"]["h2"])}{faq_block(C, d["faq"])}</section><hr class="spl">'
            + kit(C, P, x["title"]) + talk_ml(C, P))
    return shell_ml(C, P, f'{P}{x["slug"]}/', x["meta"], body, extra_head=faq_ld(d["faq"]), cls=f'phys-{x["key"]}')


def landing_ml(C, P, x):
    ui = C["ui"]; sec = next(s for s in C["sectors"] if s["key"] == x["sector"])
    media = (f'<figure class="lmedia" data-light><img src="/assets/{e(x["macro"])}" alt="" loading="lazy" width="1400" height="1050" data-par></figure>'
             if x["macro"] else frame(C, x["shots"][0][0], x["shots"][0][1]))
    cta = (f'<a class="cta pill" href="{P}samples/">{e(ui["requestSamples"])} ↗</a><a class="cta pill ghost" href="{P}contact/?topic=quote">{e(ui["requestQuote"])} ↗</a>' if x["cta"] == "samples"
           else f'<a class="cta pill" href="{P}contact/?topic=quote">{e(ui["requestQuote"])} ↗</a><a class="cta pill ghost" href="{P}samples/">{e(ui["requestSamples"])} ↗</a>')
    col = lambda t, items: f'<div><span class="mi">{e(t)}</span><ul class="rows">{"".join(f"<li>{e(i)}</li>" for i in items)}</ul></div>'
    body = (f'<section class="lhero"><div class="say"><span class="mi">{e(sec["title"])} / {e(ui["answer"])}</span><h1 class="h2">{e(x["h1"])}</h1><p class="lead">{e(x["lead"])}</p><div class="ctas">{cta}</div></div>'
            f'<div class="med">{media}</div><div class="motif" aria-hidden="true"></div></section><hr class="spl">'
            f'<section class="sec w"><div class="tri">{col(ui["capability"], x["cap"])}{col(ui["applications"], x["apps"])}{col(ui["materials"], x["mats"])}</div>'
            f'<div style="margin-top:clamp(34px,5vw,70px)"><span class="mi">{e(ui["technologies"])}</span>{tech_links(C, P, x["tech"])}</div></section><hr class="spl">'
            f'<section class="sec">{top(ui["questions"], C["wine"]["faq"]["h2"])}{faq_block(C, x["faq"])}</section><hr class="spl">'
            f'<section class="sec w">{top(ui["proof"], ui["proofH"])}<div class="hang pair">{"".join(frame(C, *s) for s in x["shots"])}</div>'
            f'<div style="margin-top:clamp(34px,5vw,70px)"><span class="mi">{e(ui["related"])}</span><div class="tl">{"".join(f"""<a class="cta" href="{P}{h}">{e(l)} →</a>""" for l, h in x["links"])}</div></div></section>'
            + talk_ml(C, P))
    return shell_ml(C, P, f'{P}{x["slug"]}/', x["meta"], body, extra_head=faq_ld(x["faq"]), cls=f'phys-{x["sector"]}')


def phead(eyebrow, h1, lead="", mega=True):
    return f'<section class="phead"><span class="mi">{e(eyebrow)}</span><h1 class="{"mega" if mega else "h2"}">{e(h1)}</h1>{f"<p class=lead>{e(lead)}</p>" if lead else ""}</section>'


def tech_ml(C, P):
    t, h, ui = C["technologies"], C["home"], C["ui"]; tech = {i["id"]: i for i in t["items"]}; r = random.Random(4); out = ""
    datam = "".join(f'<b>N° {i:04d}</b> / LOT 000000 / SN {r.randrange(16**4):04X}-{r.randrange(16**4):04X} / ' for i in range(1, 90))
    for i, g in enumerate(h["lab"]["groups"]):
        media = (f'<figure class="lmedia" data-light><img src="/assets/{g[2]}" alt="{e(g[0])} macro" loading="lazy" width="1400" height="1050" data-par><figcaption class="mi">{e(h["lab"]["macro"])}</figcaption></figure>'
                 if g[2] else f'<figure class="lmedia"><div class="datam">{datam}</div><figcaption class="mi">{e(h["lab"]["data"])}</figcaption></figure>')
        rows = "".join(f'<div class="row" id="{k}"><strong>{e(tech[k]["title"])}</strong><span>{e(tech[k]["text"])}</span></div>' for k in g[1])
        out += (f'<section class="sec labsec{" w" if i % 2 else ""}"><div class="split{" r" if i % 2 else ""}"><div class="a">{media}</div>'
                f'<div class="b"><span class="mi">LAB / {i+1:02d}</span><h2 class="mega rv" style="font-size:clamp(46px,8vw,150px);margin:14px 0 26px">{e(g[0])}</h2><div class="lrows">{rows}</div></div></div></section><hr class="spl">')
    return shell_ml(C, P, f"{P}technologies/", t["meta"], phead(h["lab"]["eyebrow"], t["h1"], t["lead"]) + '<hr class="spl">' + out + talk_ml(C, P))


def work_ml(C, P):
    w, ui = C["work"], C["ui"]; s = w["showcase"]
    show = "".join(
        f'<figure class="rv"><div class="im" data-light><img src="/assets/{e(i["image"])}" alt="{e(i["title"])}" loading="lazy" width="720" height="900" data-par></div>'
        f'<figcaption><span class="mi">UP / {n+1:03d}</span><span class="t">{e(i["title"])}</span><span class="mi c">{e(" + ".join(i["finishes"]))}{" · " + e(i["badge"]) if i.get("badge") else ""}</span></figcaption></figure>'
        for n, i in enumerate(w["items"]))
    f = w["caseFields"]
    cases = "".join(
        f'<article class="split"><div class="a"><img src="/assets/{e(c["image"])}" alt="{e(c["title"])}" loading="lazy"></div><div class="b"><h3 class="h2">{e(c["title"])}</h3><dl class="facts">'
        + "".join(f"<dt>{e(f[k])}</dt><dd>{e(c[k])}</dd>" for k in ("challenge", "solution", "materials", "technologies", "result")) + "</dl></div></article>"
        for c in w["cases"]) or f'<p class="lead">{e(w["caseEmpty"])}</p>'
    body = (phead(ui["work"], w["h1"], w["lead"]) + f'<section class="sec w"><div class="show">{show}</div></section><hr class="spl">'
            f'<section class="sec" id="showcase">{top(s["tag"], s["h2"])}<div class="split"><div class="a"><figure class="lmedia" data-light><img src="/assets/{e(s["image"])}" alt="{e(s["title"])}" loading="lazy" width="720" height="900"></figure></div>'
            f'<div class="b"><h3 class="h2" style="font-size:clamp(28px,3.4vw,54px);margin-bottom:22px">{e(s["title"])}</h3><dl class="facts">{"".join(f"<dt>{e(a)}</dt><dd>{e(b)}</dd>" for a, b in s["rows"])}</dl></div></div></section><hr class="spl">'
            f'<section class="sec w" id="case-studies">{top(ui["work"], w["caseH2"])}{cases}</section>' + talk_ml(C, P))
    return shell_ml(C, P, f"{P}work/", w["meta"], body)


def about_ml(C, P):
    p, h, ui = C["pages"]["about"], C["home"], C["ui"]; po = h["position"]
    def num(a):
        d = "".join(ch for ch in a if ch.isdigit())
        return f'<b data-count="{d}" data-suf="{e(a[len(d):])}">{e(a)}</b>' if a[:1].isdigit() else f"<b>{e(a)}</b>"
    body = (phead(ui["about"], p["h1"]) + f'<section class="sec w about"><p class="rv">{e(h["about"]["p1"])}</p><p class="rv">{e(h["about"]["p2"])}</p></section><hr class="spl">'
            f'<section class="sec">{top(ui["about"], p["factsH2"])}<dl class="facts wide">{"".join(f"<dt>{e(a)}</dt><dd>{e(b)}</dd>" for a, b in p["facts"])}</dl></section><hr class="spl">'
            f'<section class="sec w"><div class="net"><h2 class="mega rv">{e(po["mega"])}</h2><div class="txt"><span class="mi">{e(po["chain"])}</span><p class="lead" style="color:var(--ink)">{e(po["h2"])}</p><p class="lead">{e(po["p"])}</p></div>{net_map(C)}</div></section><hr class="spl">'
            f'<section class="sec t"><div class="nums">{"".join(f"""<div>{num(a)}<span class="mi">{e(b)}</span></div>""" for a, b in h["numbers"])}</div></section>' + talk_ml(C, P))
    return shell_ml(C, P, f"{P}about/", p["meta"], body)


def form_ml(C, P, key, topic):
    """Request form. Besides the visible fields it records timestamp, source page, landing page, referrer and UTM values (assets/lead.js)."""
    p, f, s, ui = C["pages"][key], C["form"], C["site"], C["ui"]
    opts = "".join(f'<option value="{k}"{" selected" if k == topic else ""}>{e(v)}</option>' for k, v in f["topics"].items())
    secs = "".join(f"<option value=\"{x['key']}\">{e(x['title'])}</option>" for x in C["sectors"]) + f"<option value=\"other\">{e(ui['other'])}</option>"
    hidden = "".join(f'<input type="hidden" name="{n}">' for n in ("website", "lang", "timestamp", "source_page", "landing_page", "referrer", "utm_source", "utm_medium", "utm_campaign"))
    form = (f'<form class="form" data-form data-endpoint="{e(s["formEndpoint"])}" data-email="{e(s["email"])}" data-none="{e(ui["formNotConnected"])}" data-sent="{e(ui["formSent"])}" data-error="{e(ui["formError"])}" data-mail="{e(ui["formMail"])}">'
            f'<label>{e(f["name"])}<input id="f-name" name="name" autocomplete="name" required></label><label>{e(f["company"])}<input id="f-company" name="company" autocomplete="organization" required></label>'
            f'<label>{e(f["country"])}<input id="f-country" name="country" autocomplete="country-name" required></label><label>{e(f["email"])}<input id="f-email" name="email" type="email" autocomplete="email" required></label>'
            f'<label>{e(f["sector"])}<select id="f-sector" name="sector">{secs}</select></label><label>{e(f["topic"])}<select id="f-topic" name="request_type">{opts}</select></label>'
            f'<label class="full">{e(f["message"])}<textarea id="f-message" name="message" required></textarea></label>{hidden}'
            f'<div class="full"><button class="cta pill" type="submit">{e(ui["send"])} ↗</button></div><p class="form-msg mi" hidden></p></form>')
    direct = f'<div class="direct"><span class="mi">{e(s["legalName"])}</span>{"".join(f"<p>{e(n) + '<br>' if n != s['legalName'] else ''}{e(a)}</p>" for n, a in offices(C))}<p><a href="mailto:{e(s["email"])}">{e(s["email"])}</a></p><p><a href="tel:{e(s["phone"].replace(" ", ""))}">{e(s["phone"])}</a></p></div>'
    return shell_ml(C, P, f"{P}{key}/", p["meta"], phead(ui["contact"], p["h1"], p["lead"], mega=False) + f'<hr class="spl"><section class="sec w"><div class="split"><div class="a">{form}</div><div class="b">{direct}</div></div></section>')


def quote_ml(C, P):
    """Instant indicative price: photo or file of the label + quantity. Reading and pricing happen on the server (/api/quote/*)."""
    p, s, ui = C["pages"]["quote"], C["site"], C["ui"]; t = p["t"]
    mats = "".join(f'<option value="{k}">{e(t["m_" + k])}</option>' for k in ("coated", "wine", "textured", "pp_white", "pp_clear"))
    chk = lambda k: f'<label class="qc"><input type="checkbox" id="q-{k}"><span>{e(t[k])}</span></label>'
    chips = "".join(f'<button type="button" class="mi" data-q="{q}"></button>' for q in (1000, 5000, 10000, 25000))
    tel = f'<a class="cta" href="tel:{e(s["phone"].replace(" ", ""))}">{e(t["call"])} {e(s["phone"])} →</a>' if s["phone"] else ""
    demo = (f'<div class="qdemo" aria-hidden="true"><svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid meet"><defs><linearGradient id="qmet" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8d9498"/><stop offset=".45" stop-color="#eef0f1"/><stop offset=".6" stop-color="#a7adb0"/><stop offset="1" stop-color="#5f666a"/></linearGradient></defs>'
            '<rect class="lb" x="135" y="42" width="130" height="216" rx="3"/><circle class="fo" cx="200" cy="104" r="26"/><circle class="fo i" cx="200" cy="104" r="17"/>'
            '<path class="tx" d="M160 156h80M170 170h60M150 206h100M150 216h100M150 226h64"/><path class="em" d="M158 186h84"/>'
            '<path class="dm" pathLength="1" d="M135 272h130M135 267v10M265 267v10M290 42v216M285 42h10M285 258h10"/>'
            '<path class="ld l2" pathLength="1" d="M135 150H92"/><path class="ld l3" pathLength="1" d="M226 104h66"/><path class="ld l4" pathLength="1" d="M242 186h50"/></svg>'
            f'<span class="tag t1 mi">80 × 130 mm</span><span class="tag t2 mi">{e(t["m_wine"])}</span><span class="tag t3 mi">{e(t["foil"])}</span><span class="tag t4 mi">{e(t["relief"])}</span><i class="beam"></i></div>')
    scan = "".join(f'<li class="mi"><i class="dot"></i>{e(t[k])}<b></b></li>' for k in ("scan1", "scan2", "scan3"))
    head = (f'<section class="phead qhero"><span class="mi">{e(p["eyebrow"])}</span><h1 class="mega rv">{e(p["h1a"])}<span>{e(p["h1b"])}</span></h1>'
            f'<p class="lead">{e(p["lead"])}</p></section>')
    body = (head + f"""<hr class="spl"><section class="sec w quote" id="quote" data-contact="{P}contact/" data-lang="{C["lang"]}">
<div class="split"><div class="a">
  <span class="mi">{e(t["s1"])}</span>
  <div class="qdrop" id="q-drop">
    <div class="qpick" id="q-pick">{demo}<p class="qdemo-cap">{e(t["demo"])}</p><div class="qbtns"><button class="cta pill only-touch" type="button" id="q-bphoto">{e(t["photo"])} ↗</button><button class="cta pill ghost" type="button" id="q-bfile">{e(t["file"])} ↗</button></div><p class="mi dim only-mouse">{e(t["drop"])}</p></div>
    <figure class="qprev" id="q-prev" hidden><div class="qshot"><img id="q-img" alt=""><i class="beam"></i><i class="cn a"></i><i class="cn b"></i><i class="cn c"></i><i class="cn d"></i><span class="qdim mi" id="q-dim" hidden></span></div><figcaption><button class="cta" type="button" id="q-again">{e(t["again"])} →</button></figcaption></figure>
  </div>
  <p class="mi dim qhint">{e(t["hint"])}</p>
  <input type="file" id="q-photo" accept="image/*" capture="environment" hidden><input type="file" id="q-file" accept="image/*,application/pdf" hidden>
</div><div class="b">
  <div class="qstate" id="q-reading" hidden><span class="mi">{e(t["reading"])}</span><ul>{scan}</ul></div>
  <div id="q-form" hidden>
    <span class="mi">{e(t["s2"])}</span><p class="qsub" id="q-sub">{e(t["fix"])}</p>
    <div class="form qf">
      <label>{e(t["w"])}<input id="q-w" inputmode="numeric" autocomplete="off"></label><label>{e(t["h"])}<input id="q-h" inputmode="numeric" autocomplete="off"></label>
      <p class="mi dim full" id="q-sizenote"></p>
      <label class="full">{e(t["mat"])}<select id="q-mat">{mats}</select></label>
      <div class="full qchecks">{chk("varnish")}{chk("foil")}{chk("foil2")}{chk("relief")}</div>
    </div>
    <span class="mi qs3">{e(t["s3"])}</span>
    <div class="form qf"><label class="full">{e(t["qty"])}<input id="q-qty" inputmode="numeric" autocomplete="off" placeholder="5000"></label>
      <div class="full qchips" id="q-chips">{chips}</div></div>
    <p class="form-msg mi" id="q-err" hidden></p>
    <div class="qprice" id="q-price" hidden aria-live="polite">
      <span class="mi">{e(t["from"])}</span>
      <p class="qbig"><b id="q-total"></b><i class="qline"></i><span class="mi">{e(t["vat"])}</span></p>
      <p class="mi" id="q-per"></p>
      <p class="qcfg"><span class="mi">{e(t["for"])}</span> <span id="q-cfg"></span></p>
      <div class="qtab"><span class="mi">{e(t["others"])}</span><dl class="facts" id="q-table"></dl></div>
      <p class="qnote">{e(t["note"])}</p>
      <div class="ctas"><a class="cta pill" id="q-cta" href="{P}contact/?topic=quote">{e(t["cta"])} ↗</a>{tel}</div>
    </div>
  </div>
</div></div></section>""")
    foot = '<script type="application/json" id="q-t">' + json.dumps(t, ensure_ascii=False).replace("</", "<\\/") + '</script><script src="/assets/quote.js" defer></script>'
    return shell_ml(C, P, f"{P}quote/", p["meta"], body, extra_head='<link rel="stylesheet" href="/assets/quote.css">', extra_foot=foot)


def sustain_ml(C, P):
    s, ui = C["sustainability"], C["ui"]
    flow = '<div class="mflow">' + "".join(f'<span class="mi">{e(x)}</span>' + ('<i></i>' if i < 3 else "") for i, x in enumerate(s["flow"])) + "</div>"
    sec = lambda n, h, inner, w=False: f'<section class="sec{" w" if w else ""}"><header class="top"><span class="mi">{n:02d} / {len(s["flow"]) + 3:02d}</span><h2 class="h2 rv">{e(h)}</h2></header>{inner}</section><hr class="spl">'
    rows = lambda items: '<div class="lrows">' + "".join(f'<div class="row"><strong>{e(a)}</strong><span>{e(b)}</span></div>' for a, b in items) + "</div>"
    a, b, c, d, f, g, r = (s[k] for k in ("s1", "s2", "s3", "s4", "s5", "s6", "s7"))
    stack = '<div class="stack" aria-hidden="true">' + "".join(f'<div class="ly ly{i}" style="--i:{i}"><span class="mi">{e(x)}</span></div>' for i, x in enumerate(d["layers"])) + "</div>"
    body = (f'<section class="phead"><span class="mi">{e(s["eyebrow"])}</span><h1 class="mega">{e(s["h1a"])}<span style="display:block;color:var(--tgl)">{e(s["h1b"])}</span></h1><p class="lead">{e(s["intro"])}</p>{flow}</section><hr class="spl">'
            + sec(1, a["h"], f'<div class="split"><div class="a"><p class="lead" style="margin-bottom:30px">{e(a["p"])}</p>{rows(a["rows"])}</div><div class="b"><figure class="lmedia" data-light><img src="/assets/{e(a["img"])}" alt="Paper fibre, macro" loading="lazy" data-par></figure></div></div>', True)
            + sec(2, b["h"], f'<p class="lead" style="color:var(--ink);max-width:54ch;font-size:clamp(20px,2.2vw,30px)">{e(b["p"])}</p><p class="mi" style="margin-top:22px">{e(b["note"])}</p>')
            + sec(3, c["h"], rows(c["rows"]), True)
            + sec(4, d["h"], f'<div class="split"><div class="a">{stack}</div><div class="b"><p class="lead" style="color:var(--ink);margin-bottom:18px">{e(d["p"])}</p><p class="lead">{e(d["p2"])}</p></div></div>')
            + sec(5, f["h"], f'<div class="mflow big">{"".join(f"""<span>{e(x)}</span>""" + ("<i></i>" if i < 2 else "") for i, x in enumerate(f["steps"]))}</div><p class="lead" style="margin-top:34px;max-width:60ch">{e(f["p"])}</p>', True)
            + sec(6, g["h"], f'<div class="net"><div class="txt"><span class="mi">{e(g["place"])}</span><p class="lead" style="color:var(--ink)">{e(g["p"])}</p></div>{net_map(C)}</div>')
            + f'<section class="sec w"><header class="top"><span class="mi">07 / 07 — {e(r["eyebrow"])}</span><h2 class="h2 rv">{e(r["h"])}</h2><p class="lead">{e(r["p"])}</p></header>'
              f'<div class="split"><div class="a"><span class="mi"><i class="dot"></i>{e(r["todayH"])}</span><ul class="rows" style="margin-top:14px">{"".join(f"<li>{e(x)}</li>" for x in r["today"])}</ul></div>'
              f'<div class="b"><span class="mi">{e(r["nextH"])}</span><div class="lrows" style="margin-top:14px">{"".join(f"""<div class="row"><strong>{e(x)}</strong><span class="mi st">{e(y)}</span></div>""" for x, y in r["next"])}</div></div></div></section>'
            + talk_ml(C, P))
    return shell_ml(C, P, f"{P}sustainability/", s["meta"], body)


def legal_ml(C, P, key):
    d = C["legal"][key]
    body = (phead(C["site"]["privacyVersion"], d["h1"], mega=False) + '<hr class="spl"><section class="sec w"><div class="legal-text">'
            + "".join(f"<h2>{e(a)}</h2><p>{e(b)}</p>" for a, b in d["sections"]) + "</div></section>")
    return shell_ml(C, P, f"{P}{key}/", d["meta"], body)


NO_TR = {"slug", "key", "image", "img", "id", "url", "lang", "macro", "fx", "shot", "heroImg", "launchUrl", "email", "phone", "linkedin", "instagram", "formEndpoint", "analyticsEndpoint",
         "vatID", "street", "postalCode", "locality", "region", "country", "address", "name", "legalName", "founded"}


def translate(o, T, k=None):
    """Replace every English string that has an entry in the language map; anything missing stays in English."""
    if isinstance(o, dict):
        return {a: (b if a in NO_TR and not isinstance(b, (dict, list)) else translate(b, T, a)) for a, b in o.items()}
    if isinstance(o, list):
        return [translate(x, T, k) for x in o]
    return T.get(o, o) if isinstance(o, str) else o


def build(launch=False):
    """launch=True (python3 build.py --launch) removes noindex and switches every URL to site.launchUrl."""
    paths = []
    for lang in LANGS:
        C = json.loads(rd(f"content/{DEFAULT}.json")); P = "/" if lang == HOME else f"/{lang}/"
        if lang != DEFAULT:
            C = translate(C, json.loads(rd(f"content/i18n/{lang}.json"))); C["lang"] = lang
        if os.path.exists(os.path.join(ROOT, f"content/film-{lang}.json")):   # texts and callout positions for this language's own film label
            ov = json.loads(rd(f"content/film-{lang}.json"))
            for i, it in ov.get("anatomy", {}).items():
                a = C["home"]["anatomy"]["items"][int(i) - 1]; a[2:] = it[-2:]
                if len(it) == 3: a[1] = it[0]
            for i, t in ov.get("panels", {}).items():
                C["film"]["panels"][int(i) - 1][2] = t
        if launch:
            if not C["site"]["launchUrl"]:
                raise SystemExit("Set site.launchUrl in content/en.json before a launch build.")
            cd = C["site"].get("countryDomains", {}); main = C["site"]["launchUrl"].rstrip("/")
            for l in LANGS:
                PUB[l] = cd[l].rstrip("/") if l in cd else main + ("" if l == C["site"]["mainLang"] else "/" + l)
            C["site"]["noindex"] = False; C["site"]["url"] = PUB[HOME] if HOME in cd or HOME == C["site"]["mainLang"] else main
        if lang == HOME:
            C0 = C
        out = {P: home_ml(C, P), f"{P}technologies/": tech_ml(C, P), f"{P}work/": work_ml(C, P), f"{P}about/": about_ml(C, P), f"{P}sustainability/": sustain_ml(C, P), f"{P}privacy/": legal_ml(C, P, "privacy"), f"{P}cookies/": legal_ml(C, P, "cookies"),
               f"{P}samples/": form_ml(C, P, "samples", "samples"), f"{P}contact/": form_ml(C, P, "contact", "quote"), f"{P}partners/": form_ml(C, P, "partners", "partner"), f"{P}quote/": quote_ml(C, P)}
        for n, x in enumerate(C["sectors"]):
            out[f'{P}{x["slug"]}/'] = wine_ml(C, P, x) if x["key"] == "wine" else sector_ml(C, P, x, n + 1)
        for x in C["landings"]:
            out[f'{P}{x["slug"]}/'] = landing_ml(C, P, x)
        for path, s in out.items():
            wr(path.lstrip("/") + "index.html", s); paths.append(path)
        site = C["site"]["url"].rstrip("/")
    wr("assets/film.css", rd("src/film.css")); wr("assets/film.js", rd("src/film.js"))
    rels = [p for p in paths if not any(p.startswith(f"/{l}/") for l in LANGS if l != HOME)]
    loc = lambda l, r: pub(C0, l, r)
    wr("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "".join(
        f"  <url><loc>{loc(l, r)}</loc>" + "".join(f'<xhtml:link rel="alternate" hreflang="{a}" href="{loc(a, r)}"/>' for a in LANGS) + f'<xhtml:link rel="alternate" hreflang="x-default" href="{loc(XDEF, r)}"/></url>\n'
        for r in rels for l in LANGS if loc(l, r).startswith(site + "/")) + "</urlset>\n")
    bots = "User-agent: OAI-SearchBot\nAllow: /\n\nUser-agent: ChatGPT-User\nAllow: /\n\n"
    if C0["site"]["blockAiTraining"]:
        bots += "User-agent: GPTBot\nDisallow: /\n\n"
    wr("robots.txt", bots + f"User-agent: *\nAllow: /\n\nSitemap: {site}/sitemap.xml\n")
    wr("404.html", shell_ml(C0, "/", "/404.html", {"title": "Page not found | UltraPixel", "description": C0["ui"]["notFound"]},
                            phead("404", C0["ui"]["notFound"], mega=False) + f'<section class="sec"><a class="cta pill" href="/">{e(C0["ui"]["backHome"])} ↗</a></section>'))
    print(f"built {len(paths)} pages")


if __name__ == "__main__":
    import sys
    # --home=fr serves another language at the root (e.g. for a country domain); the languages keep the same folders otherwise
    for a in sys.argv:
        if a.startswith("--home=") and a[7:] in LANGS:
            HOME = a[7:]; LANGS.remove(HOME); LANGS.insert(0, HOME)
    XDEF = HOME if "--launch" not in sys.argv else json.loads(rd("content/en.json"))["site"]["mainLang"]
    build(launch="--launch" in sys.argv)
