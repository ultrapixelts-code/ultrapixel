"""Pagina dello studio resa sul server in ogni lingua: /it/, /en/, /fr/, /de/.

Google e gli assistenti AI leggono l'HTML così come arriva dal server, senza eseguire JavaScript:
per questo titolo, descrizione, titoli, testi del servizio, FAQ e dati strutturati sono già nella lingua dell'URL.
Il modello è static/index.html con i segnaposto {{...}}; i testi dell'area del servizio (.info-l) sono nel modello
in tutte e 4 le lingue e qui restano solo quelli della lingua della pagina. FAQ e offerte dei dati strutturati
sono lette da quei testi, così le due cose non possono divergere.
"""
import html, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = "https://studio.ultrapixel.it"
LINGUE = ("it", "en", "fr", "de")
X_DEFAULT = "it"

# il francese vive su ultrapixel.fr, le altre lingue su ultrapixel.it
SITO = {"it": "https://ultrapixel.it/", "en": "https://ultrapixel.it/en/", "fr": "https://ultrapixel.fr/", "de": "https://ultrapixel.it/de/"}
DOMINIO = {"it": "ultrapixel.it", "en": "ultrapixel.it", "fr": "ultrapixel.fr", "de": "ultrapixel.it"}
OG_LOCALE = {"it": "it_IT", "en": "en_GB", "fr": "fr_FR", "de": "de_DE"}

T = {
    "it": {
        "title": "Disegna la tua etichetta online e stampala | UltraPixel Studio",
        "desc": "Descrivi il prodotto e in pochi minuti vedi tre proposte di etichetta sul tuo contenitore. Poi UltraPixel prepara il file e stampa le etichette in Italia. Si inizia gratis.",
        "cta": "Disegna la tua etichetta",
        "h1b": "Noi la prepariamo per la stampa e la stampiamo.",
        "eyebrow": "Il tuo grafico, adesso",
        "answer": "UltraPixel Studio è il servizio online di progettazione etichette di UltraPixel, etichettificio italiano, per aziende e professionisti che non hanno un grafico. "
                  "Descrivi il prodotto e in pochi minuti vedi tre proposte sul tuo contenitore, con i primi 2 giri gratuiti; poi UltraPixel prepara il file di stampa e stampa le etichette.",
        "sub": "Scrivi come lo diresti a un grafico: cosa vendi, che contenitore usi, che stile ti piace. Carica foto del flacone, il logo o una bozza. Vedrai le proposte sul tuo contenitore.",
        "back": "Torna al sito",
    },
    "en": {
        "title": "Design your label online and get it printed | UltraPixel Studio",
        "desc": "Describe your product and see three label designs on your own bottle or jar in minutes. Then UltraPixel prepares the print file and prints the labels in Italy. Free to start.",
        "cta": "Design your label",
        "h1b": "We make it print-ready and print it.",
        "eyebrow": "Your label designer, right now",
        "answer": "UltraPixel Studio is an online label design service from the Italian label printer UltraPixel, for companies and professionals without a designer. "
                  "You describe your product and see three label designs on your own container in a few minutes, with the first 2 rounds free; UltraPixel then prepares the print file and prints the labels.",
        "sub": "Write it as you would to a designer: what you sell, which container, the style you like. Upload photos of the bottle, your logo or a sketch. You will see the proposals on your own container.",
        "back": "Back to the site",
    },
    "fr": {
        "title": "Dessinez votre étiquette en ligne et faites-la imprimer | UltraPixel Studio",
        "desc": "Décrivez votre produit et voyez en quelques minutes trois propositions d'étiquette sur votre contenant. UltraPixel prépare ensuite le fichier et imprime les étiquettes. Gratuit pour commencer.",
        "cta": "Dessinez votre étiquette",
        "h1b": "Nous la préparons pour l'impression et l'imprimons.",
        "eyebrow": "Votre graphiste, tout de suite",
        "answer": "UltraPixel Studio est le service en ligne de création d'étiquettes d'UltraPixel, imprimeur d'étiquettes italien, pour les entreprises et professionnels sans graphiste. "
                  "Vous décrivez votre produit et voyez en quelques minutes trois propositions sur votre contenant, les 2 premiers tours étant gratuits ; UltraPixel prépare ensuite le fichier d'impression et imprime les étiquettes.",
        "sub": "Écrivez comme vous le diriez à un graphiste : ce que vous vendez, le contenant, le style qui vous plaît. Ajoutez des photos du flacon, votre logo ou une esquisse. Vous verrez les propositions sur votre propre contenant.",
        "back": "Retour au site",
    },
    "de": {
        "title": "Etikett online gestalten und drucken lassen | UltraPixel Studio",
        "desc": "Beschreiben Sie Ihr Produkt und sehen Sie in wenigen Minuten drei Etikettenentwürfe auf Ihrem Behälter. Danach erstellt UltraPixel die Druckdatei und druckt die Etiketten in Italien. Kostenlos starten.",
        "cta": "Gestalten Sie Ihr Etikett",
        "h1b": "Wir machen es druckfertig und drucken es.",
        "eyebrow": "Ihr Grafiker, jetzt sofort",
        "answer": "UltraPixel Studio ist der Online-Service der italienischen Etikettendruckerei UltraPixel für die Gestaltung von Etiketten, für Unternehmen und Selbstständige ohne Grafiker. "
                  "Sie beschreiben Ihr Produkt und sehen in wenigen Minuten drei Entwürfe auf Ihrem Behälter, die ersten 2 Runden sind kostenlos; danach erstellt UltraPixel die Druckdatei und druckt die Etiketten.",
        "sub": "Schreiben Sie es so, wie Sie es einem Grafiker sagen würden: was Sie verkaufen, welcher Behälter, welcher Stil Ihnen gefällt. Laden Sie Fotos der Flasche, Ihr Logo oder einen Entwurf hoch. Sie sehen die Vorschläge auf Ihrem eigenen Behälter.",
        "back": "Zurück zur Website",
    },
}


def url(lg):
    return f"{ORIGIN}/{lg}/"


def scegli_lingua(accept_language):
    """Lingua per "/" dall'intestazione Accept-Language; senza indicazioni: italiano."""
    best, bq = None, -1.0
    for i, part in enumerate((accept_language or "").split(",")):
        bits = part.strip().split(";")
        code = bits[0].strip().lower()[:2]
        q = 1.0
        for b in bits[1:]:
            if b.strip().startswith("q="):
                try:
                    q = float(b.strip()[2:])
                except ValueError:
                    q = 0.0
        if code in LINGUE and q > bq:
            best, bq = code, q - i * 1e-6   # a parità di peso vince la prima
    return best or X_DEFAULT


_CACHE = {}


def _modello():
    p = os.path.join(HERE, "static", "index.html")
    m = os.path.getmtime(p)
    if _CACHE.get("m") != m:
        _CACHE["m"], _CACHE["t"] = m, open(p, encoding="utf-8").read()
        _CACHE.pop("pagine", None)
    return _CACHE["t"]


def _testo(frammento):
    return html.unescape(re.sub(r"<[^>]+>", "", frammento)).strip()


def _blocco_info(modello, lg):
    m = re.search(r'<div class="info-l" lang="%s">.*?</p></div>(?=<div class="info-l"|</section>)' % lg, modello, re.S)
    return m.group(0) if m else ""


def _jsonld(lg, info):
    t = T[lg]
    faq = [{"@type": "Question", "name": _testo(q), "acceptedAnswer": {"@type": "Answer", "text": _testo(a)}}
           for q, a in re.findall(r"<details><summary>(.*?)</summary><p>(.*?)</p></details>", info, re.S)]
    prezzo = re.search(r"<h3>[^<]*</h3>((?:<p>.*?</p>){2,3})<h3>", info, re.S)
    righe = [_testo(p) for p in re.findall(r"<p>(.*?)</p>", prezzo.group(1), re.S)] if prezzo else []
    offerte = []
    if len(righe) >= 2:
        offerte = [{"@type": "Offer", "name": righe[0], "price": "0", "priceCurrency": "EUR"},
                   {"@type": "Offer", "name": righe[1], "price": "39", "priceCurrency": "EUR", "valueAddedTaxIncluded": False}]
    app_ = {"@type": "WebApplication", "@id": ORIGIN + "/#app", "name": "UltraPixel Studio", "alternateName": t["cta"],
            "url": url(lg), "description": t["desc"], "applicationCategory": "DesignApplication", "operatingSystem": "Any",
            "inLanguage": lg, "isAccessibleForFree": True, "offers": offerte, "provider": {"@id": "https://ultrapixel.it/#organization"}}
    pagina = {"@type": "WebPage", "@id": url(lg) + "#page", "url": url(lg), "name": t["title"], "description": t["desc"],
              "inLanguage": lg, "about": {"@id": ORIGIN + "/#app"}, "isPartOf": {"@type": "WebSite", "@id": ORIGIN + "/#site", "name": "UltraPixel Studio", "url": ORIGIN + "/"}}
    org = {"@type": "Organization", "@id": "https://ultrapixel.it/#organization", "name": "UltraPixel", "legalName": "UltraPixel Srl",
           "url": "https://ultrapixel.it/", "logo": "https://ultrapixel.it/assets/logo.png"}
    graph = [app_, pagina, org]
    if faq:
        graph.append({"@type": "FAQPage", "@id": url(lg) + "#faq", "inLanguage": lg, "mainEntity": faq})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def _head(lg, info, indicizza=True):
    t, e = T[lg], html.escape
    r = [f"<title>{e(t['title'])}</title>",
         f'<meta name="description" content="{e(t["desc"])}">']
    if not indicizza:
        r.append('<meta name="robots" content="noindex">')
    r.append(f'<link rel="canonical" href="{url(lg)}">')
    for x in LINGUE:
        r.append(f'<link rel="alternate" hreflang="{x}" href="{url(x)}">')
    r.append(f'<link rel="alternate" hreflang="x-default" href="{url(X_DEFAULT)}">')
    r += ['<meta property="og:type" content="website">', '<meta property="og:site_name" content="UltraPixel Studio">',
          f'<meta property="og:title" content="{e(t["title"])}">', f'<meta property="og:description" content="{e(t["desc"])}">',
          f'<meta property="og:url" content="{url(lg)}">', f'<meta property="og:locale" content="{OG_LOCALE[lg]}">']
    r += [f'<meta property="og:locale:alternate" content="{OG_LOCALE[x]}">' for x in LINGUE if x != lg]
    r += ['<meta property="og:image" content="https://ultrapixel.it/assets/macro-1.webp">', '<meta name="twitter:card" content="summary_large_image">',
          f'<script type="application/ld+json">{_jsonld(lg, info)}</script>']
    return "\n".join(r)


def _h1(lg):
    t, e = T[lg], html.escape
    s = t["cta"].rstrip(".")
    i = s.rfind(" ")
    return f'<span>{e(s[:i + 1])}<em>{e(s[i + 1:])}.</em></span><span>{e(t["h1b"])}</span>'


def rendi(lg, indicizza=True):
    """HTML completo della pagina dello studio nella lingua lg."""
    modello = _modello()
    chiave = (lg, indicizza)
    pagine = _CACHE.setdefault("pagine", {})
    if chiave in pagine:
        return pagine[chiave]
    t, e = T[lg], html.escape
    info = _blocco_info(modello, lg)
    out = re.sub(r'<div class="info-l" lang="(it|en|fr|de)">.*?</p></div>(?=<div class="info-l"|</section>)',
                 lambda m: m.group(0) if m.group(1) == lg else "", modello, flags=re.S)
    valori = {"LANG": lg, "HEAD": _head(lg, info, indicizza), "H1": _h1(lg), "EYEBROW": e(t["eyebrow"]), "ANSWER": e(t["answer"]), "SUB": e(t["sub"]),
              "HOME": SITO[lg], "DOMINIO": DOMINIO[lg], "BACK": e(t["back"]), "CTA": e(t["cta"])}
    out = re.sub(r"\{\{([A-Z0-9]+)\}\}", lambda m: valori.get(m.group(1), m.group(0)), out)
    pagine[chiave] = out
    return out


def sitemap():
    righe = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for lg in LINGUE:
        righe.append(f"  <url><loc>{url(lg)}</loc>")
        for x in LINGUE:
            righe.append(f'    <xhtml:link rel="alternate" hreflang="{x}" href="{url(x)}"/>')
        righe.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{url(X_DEFAULT)}"/>')
        righe.append("  </url>")
    righe.append("</urlset>")
    return "\n".join(righe) + "\n"


LLMS = """# UltraPixel Studio

> UltraPixel Studio is an online label design service from UltraPixel, an Italian label printer in San Dorligo della Valle (Trieste). Design your label: a company describes its product, sees three label designs on its own container in a few minutes, and UltraPixel then prepares the print file and prints the labels. Proposals are generated with artificial intelligence and are indicative; UltraPixel sends a final proof and the price before printing.

- Who it is for: companies and professionals with a VAT number who need a product label and have no designer, or only a logo or a sketch (wine, spirits, beer, cosmetics, food, honey and jam, olive oil, supplements, technical products).
- Price: access with a business email; the first 2 rounds of proposals are free. 10 more rounds cost €39 + VAT, an advance on the graphic design that is deducted from the print order. Label printing is quoted separately with the final proof.
- Time: first proposals in about 2–3 minutes; UltraPixel replies within one working day after a proposal is chosen.
- The print file is prepared by UltraPixel's prepress designer and is not delivered without a print order.

## Pages

- [Disegna la tua etichetta (italiano)](https://studio.ultrapixel.it/it/)
- [Design your label (English)](https://studio.ultrapixel.it/en/)
- [Dessinez votre étiquette (français)](https://studio.ultrapixel.it/fr/)
- [Gestalten Sie Ihr Etikett (Deutsch)](https://studio.ultrapixel.it/de/)
- [Studio terms](https://studio.ultrapixel.it/condizioni?lang=en)

## UltraPixel

- [UltraPixel, custom self-adhesive labels](https://ultrapixel.it/en/)
- [Label design service](https://ultrapixel.it/en/label-design/)
- [Contact](https://ultrapixel.it/en/contact/) · info@ultrapixel.it · +39 040 817222
"""
