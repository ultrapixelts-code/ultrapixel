/* Brief guidato (pagina /prova): il cliente risponde a schede, l'AI scrive il brief da grafico, il cliente lo controlla e parte il disegno. */
(function(){
var UP=window.UP;if(!UP)return;var LG=UP.LG,el=UP.el,$=function(s,r){return(r||document).querySelector(s)};
var B={
it:{start:'Inizia il brief guidato',startSub:'2 minuti a schede: le proposte vengono molto più precise',or:'oppure scrivi tu, come a un grafico:',
 steps:['Il prodotto','Il contenitore','I testi','Lo stile','Atmosfera e allegati','Il tuo brief'],next:'Avanti',back:'Indietro',skip:'Non so / consigliatemi',
 sector:'Che cosa vendi?',sectors:{vino:'Vino',birra:'Birra',spirits:'Distillati',food:'Alimentare',cosm:'Cosmetica',altro:'Altro'},
 name:'Nome del prodotto',brand:'Azienda o marchio',cont:'Su che contenitore va?',conts:{bordolese:'Bordolese',borgognotta:'Borgognotta',champagnotta:'Spumante',longneck:'Birra longneck',steinie:'Birra steinie',flacone:'Flacone',cilindro:'Flacone dritto',vaso:'Vaso',lattina:'Lattina'},
 glass:'Colore del vetro o del flacone',glasses:{verde:'Verde',nero:'Scuro',trasparente:'Trasparente',ambra:'Ambrato',bianco:'Bianco',blu:'Blu'},
 size:'Misura dell’etichetta (mm)',sizeHint:'Se la sai: larghezza × altezza. Altrimenti la proponiamo noi.',qty:'Quante etichette, più o meno?',qtys:['meno di 500','500 – 2.000','2.000 – 10.000','più di 10.000'],
 texts:'Scrivi i testi esattamente come devono comparire. Lascia vuoto quello che non sai.',
 f:{den:'Denominazione / categoria (es. Terrano DOC Carso)',year:'Annata',alc:'Gradazione (% vol)',vol:'Volume (es. 75 cl)',style:'Stile di birra (es. IPA)',net:'Peso o contenuto netto (es. 500 g)',ingr:'Ingredienti (facoltativo)',type:'Tipo di prodotto (es. body wash)',desc:'Che cos’è il prodotto',other:'Altri testi da inserire (slogan, indirizzo, sito…)'},
 styleQ:'Che stile ti piace? (massimo 2)',styles:{classico:'Classico elegante',minimal:'Minimal',illustrato:'Illustrato',tipografico:'Tipografico',pop:'Pop e colorato',naturale:'Naturale, artigianale',lusso:'Lusso scuro',vintage:'Vintage'},
 colQ:'Colori',cols:{neutri:'Neutri, carta',caldi:'Caldi, terra',freddi:'Freddi, mare',pastello:'Pastello',scuri:'Scuri, profondi',vivaci:'Vivaci'},colFree:'Colori precisi (facoltativo, es. il verde del logo)',
 finQ:'Lavorazioni speciali',fins:{oro:'Foil oro',argento:'Foil argento',rame:'Foil rame',rilievo:'Rilievo',goffrata:'Carta goffrata',film:'Film trasparente',consiglio:'Consigliatemi voi'},
 mood:'Cosa deve trasmettere? A chi si rivolge?',moodPh:'es. un rosso del Carso, autentico ma moderno, per enoteche e ristoranti',avoid:'Cosa NON vuoi',avoidPh:'es. niente grappoli d’uva, niente oro pacchiano',
 att:'Logo, foto del contenitore, etichette che ti piacciono',attBtn:'Aggiungi immagini',making:'Scrivo il brief come lo scriverebbe un grafico…',
 review:'Ecco il brief per il grafico. Controllalo e correggi quello che vuoi: è da qui che partono le proposte.',draw:'Disegna le proposte',edit:'Cambia risposte',req:'Scrivi almeno il nome del prodotto.',err:'Non riesco a preparare il brief adesso: riprova tra poco.'},
en:{start:'Start the guided brief',startSub:'2 minutes, just tap: the proposals get much more precise',or:'or write it yourself, as you would to a designer:',
 steps:['The product','The container','The texts','The style','Mood and files','Your brief'],next:'Next',back:'Back',skip:'Not sure / advise me',
 sector:'What do you sell?',sectors:{vino:'Wine',birra:'Beer',spirits:'Spirits',food:'Food',cosm:'Cosmetics',altro:'Other'},
 name:'Product name',brand:'Company or brand',cont:'Which container?',conts:{bordolese:'Bordeaux',borgognotta:'Burgundy',champagnotta:'Sparkling',longneck:'Beer longneck',steinie:'Beer steinie',flacone:'Bottle',cilindro:'Straight bottle',vaso:'Jar',lattina:'Can'},
 glass:'Glass or bottle colour',glasses:{verde:'Green',nero:'Dark',trasparente:'Clear',ambra:'Amber',bianco:'White',blu:'Blue'},
 size:'Label size (mm)',sizeHint:'If you know it: width × height. Otherwise we suggest it.',qty:'How many labels, roughly?',qtys:['under 500','500 – 2,000','2,000 – 10,000','over 10,000'],
 texts:'Write the texts exactly as they must appear. Leave empty what you don’t know.',
 f:{den:'Appellation / category',year:'Vintage',alc:'Alcohol (% vol)',vol:'Volume (e.g. 75 cl)',style:'Beer style (e.g. IPA)',net:'Net weight or content (e.g. 500 g)',ingr:'Ingredients (optional)',type:'Product type (e.g. body wash)',desc:'What the product is',other:'Other texts (tagline, address, website…)'},
 styleQ:'Which style do you like? (up to 2)',styles:{classico:'Classic elegant',minimal:'Minimal',illustrato:'Illustrated',tipografico:'Typographic',pop:'Pop and colourful',naturale:'Natural, artisanal',lusso:'Dark luxury',vintage:'Vintage'},
 colQ:'Colours',cols:{neutri:'Neutral, paper',caldi:'Warm, earth',freddi:'Cool, sea',pastello:'Pastel',scuri:'Dark, deep',vivaci:'Vivid'},colFree:'Exact colours (optional, e.g. the green of the logo)',
 finQ:'Special finishes',fins:{oro:'Gold foil',argento:'Silver foil',rame:'Copper foil',rilievo:'Embossing',goffrata:'Textured paper',film:'Clear film',consiglio:'Advise me'},
 mood:'What should it convey? Who is it for?',moodPh:'e.g. an authentic but modern red, for wine shops and restaurants',avoid:'What you do NOT want',avoidPh:'e.g. no grapes, no flashy gold',
 att:'Logo, photo of the container, labels you like',attBtn:'Add images',making:'Writing the brief the way a designer would…',
 review:'Here is the brief for the designer. Check it and change anything: the proposals start from here.',draw:'Design the proposals',edit:'Change answers',req:'Please write at least the product name.',err:'I can’t prepare the brief right now: please try again shortly.'},
fr:{start:'Commencer le brief guidé',startSub:'2 minutes en quelques clics : des propositions bien plus précises',or:'ou écrivez-le vous-même, comme à un graphiste :',
 steps:['Le produit','Le contenant','Les textes','Le style','Ambiance et fichiers','Votre brief'],next:'Suivant',back:'Retour',skip:'Je ne sais pas / conseillez-moi',
 sector:'Que vendez-vous ?',sectors:{vino:'Vin',birra:'Bière',spirits:'Spiritueux',food:'Alimentaire',cosm:'Cosmétique',altro:'Autre'},
 name:'Nom du produit',brand:'Société ou marque',cont:'Sur quel contenant ?',conts:{bordolese:'Bordelaise',borgognotta:'Bourguignonne',champagnotta:'Effervescent',longneck:'Bière longneck',steinie:'Bière steinie',flacone:'Flacon',cilindro:'Flacon droit',vaso:'Pot',lattina:'Canette'},
 glass:'Couleur du verre ou du flacon',glasses:{verde:'Vert',nero:'Foncé',trasparente:'Transparent',ambra:'Ambré',bianco:'Blanc',blu:'Bleu'},
 size:'Taille de l’étiquette (mm)',sizeHint:'Si vous la connaissez : largeur × hauteur. Sinon nous la proposons.',qty:'Combien d’étiquettes, environ ?',qtys:['moins de 500','500 – 2 000','2 000 – 10 000','plus de 10 000'],
 texts:'Écrivez les textes exactement comme ils doivent apparaître. Laissez vide ce que vous ne savez pas.',
 f:{den:'Appellation / catégorie',year:'Millésime',alc:'Degré (% vol)',vol:'Volume (ex. 75 cl)',style:'Style de bière (ex. IPA)',net:'Poids ou contenu net (ex. 500 g)',ingr:'Ingrédients (facultatif)',type:'Type de produit (ex. gel douche)',desc:'Ce qu’est le produit',other:'Autres textes (slogan, adresse, site…)'},
 styleQ:'Quel style vous plaît ? (2 au maximum)',styles:{classico:'Classique élégant',minimal:'Minimal',illustrato:'Illustré',tipografico:'Typographique',pop:'Pop et coloré',naturale:'Naturel, artisanal',lusso:'Luxe sombre',vintage:'Vintage'},
 colQ:'Couleurs',cols:{neutri:'Neutres, papier',caldi:'Chaudes, terre',freddi:'Froides, mer',pastello:'Pastel',scuri:'Sombres, profondes',vivaci:'Vives'},colFree:'Couleurs précises (facultatif)',
 finQ:'Finitions spéciales',fins:{oro:'Dorure or',argento:'Dorure argent',rame:'Dorure cuivre',rilievo:'Gaufrage',goffrata:'Papier texturé',film:'Film transparent',consiglio:'Conseillez-moi'},
 mood:'Que doit-elle transmettre ? À qui s’adresse-t-elle ?',moodPh:'ex. un rouge authentique mais moderne, pour cavistes et restaurants',avoid:'Ce que vous ne voulez PAS',avoidPh:'ex. pas de grappes, pas d’or tape-à-l’œil',
 att:'Logo, photo du contenant, étiquettes qui vous plaisent',attBtn:'Ajouter des images',making:'J’écris le brief comme le ferait un graphiste…',
 review:'Voici le brief pour le graphiste. Vérifiez-le et corrigez ce que vous voulez : les propositions partent d’ici.',draw:'Dessiner les propositions',edit:'Modifier les réponses',req:'Indiquez au moins le nom du produit.',err:'Impossible de préparer le brief pour le moment : réessayez dans un instant.'},
de:{start:'Geführtes Briefing starten',startSub:'2 Minuten zum Antippen: die Vorschläge werden viel genauer',or:'oder schreiben Sie selbst, wie an einen Grafiker:',
 steps:['Das Produkt','Der Behälter','Die Texte','Der Stil','Stimmung und Dateien','Ihr Briefing'],next:'Weiter',back:'Zurück',skip:'Weiß nicht / beraten Sie mich',
 sector:'Was verkaufen Sie?',sectors:{vino:'Wein',birra:'Bier',spirits:'Spirituosen',food:'Lebensmittel',cosm:'Kosmetik',altro:'Sonstiges'},
 name:'Produktname',brand:'Firma oder Marke',cont:'Welcher Behälter?',conts:{bordolese:'Bordeaux',borgognotta:'Burgunder',champagnotta:'Sekt',longneck:'Bier Longneck',steinie:'Bier Steinie',flacone:'Flasche',cilindro:'Gerade Flasche',vaso:'Glas',lattina:'Dose'},
 glass:'Farbe von Glas oder Flasche',glasses:{verde:'Grün',nero:'Dunkel',trasparente:'Klar',ambra:'Braun',bianco:'Weiß',blu:'Blau'},
 size:'Etikettengröße (mm)',sizeHint:'Falls bekannt: Breite × Höhe. Sonst schlagen wir sie vor.',qty:'Wie viele Etiketten ungefähr?',qtys:['unter 500','500 – 2.000','2.000 – 10.000','über 10.000'],
 texts:'Schreiben Sie die Texte genau so, wie sie erscheinen sollen. Lassen Sie leer, was Sie nicht wissen.',
 f:{den:'Bezeichnung / Kategorie',year:'Jahrgang',alc:'Alkohol (% vol)',vol:'Volumen (z. B. 75 cl)',style:'Bierstil (z. B. IPA)',net:'Nettogewicht oder -inhalt (z. B. 500 g)',ingr:'Zutaten (optional)',type:'Produktart (z. B. Duschgel)',desc:'Was das Produkt ist',other:'Weitere Texte (Slogan, Adresse, Website…)'},
 styleQ:'Welcher Stil gefällt Ihnen? (höchstens 2)',styles:{classico:'Klassisch elegant',minimal:'Minimal',illustrato:'Illustriert',tipografico:'Typografisch',pop:'Pop und bunt',naturale:'Natürlich, handwerklich',lusso:'Dunkler Luxus',vintage:'Vintage'},
 colQ:'Farben',cols:{neutri:'Neutral, Papier',caldi:'Warm, Erde',freddi:'Kühl, Meer',pastello:'Pastell',scuri:'Dunkel, tief',vivaci:'Kräftig'},colFree:'Genaue Farben (optional)',
 finQ:'Veredelungen',fins:{oro:'Goldfolie',argento:'Silberfolie',rame:'Kupferfolie',rilievo:'Prägung',goffrata:'Strukturpapier',film:'Klarfolie',consiglio:'Beraten Sie mich'},
 mood:'Was soll es vermitteln? Für wen ist es?',moodPh:'z. B. ein authentischer, aber moderner Rotwein für Weinhandel und Gastronomie',avoid:'Was Sie NICHT wollen',avoidPh:'z. B. keine Trauben, kein protziges Gold',
 att:'Logo, Foto des Behälters, Etiketten, die Ihnen gefallen',attBtn:'Bilder hinzufügen',making:'Ich schreibe das Briefing, wie es ein Grafiker tun würde…',
 review:'Hier ist das Briefing für den Grafiker. Prüfen und ändern Sie es nach Belieben: Von hier aus starten die Vorschläge.',draw:'Vorschläge gestalten',edit:'Antworten ändern',req:'Bitte mindestens den Produktnamen angeben.',err:'Das Briefing kann gerade nicht erstellt werden: bitte gleich noch einmal versuchen.'}
}[LG]||null;if(!B)return;

/* miniature degli stili: piccole etichette disegnate, non fotografie */
var SW={
 classico:'<rect x="8" y="6" width="64" height="88" rx="4" fill="#F1EADB"/><rect x="13" y="11" width="54" height="78" rx="2" fill="none" stroke="#B8923E" stroke-width="1.4"/><rect x="16" y="14" width="48" height="72" fill="none" stroke="#B8923E" stroke-width=".5"/><text x="40" y="52" text-anchor="middle" font-family="Bodoni Moda,serif" font-size="13" font-weight="600" fill="#2A2722">VINO</text><path d="M26 60h28" stroke="#B8923E"/>',
 minimal:'<rect x="8" y="6" width="64" height="88" fill="#FBFBF8" stroke="#ddd"/><text x="16" y="80" font-family="Archivo,sans-serif" font-size="7" letter-spacing="1.5" fill="#101214">NOME</text><circle cx="58" cy="20" r="3" fill="#101214"/>',
 illustrato:'<rect x="8" y="6" width="64" height="88" fill="#F4EFE6"/><g fill="none" stroke="#4F6B4A" stroke-width="1.2"><path d="M40 78C38 60 42 40 40 18"/>'+[0,1,2,3,4,5].map(function(i){var y=70-i*9,d=i%2?1:-1;return '<path d="M40 '+y+'q'+(d*6)+' -3 '+(d*11)+' -9q-'+(d*4)+' 7 -'+(d*11)+' 9z" fill="#C8D5C0"/>'}).join('')+'</g><circle cx="52" cy="28" r="5" fill="#D9438F" opacity=".7"/>',
 tipografico:'<rect x="8" y="6" width="64" height="88" fill="#EDEDE8"/><text x="13" y="40" font-family="Archivo,sans-serif" font-weight="800" font-size="26" letter-spacing="-1" fill="#101214">TER</text><text x="13" y="64" font-family="Archivo,sans-serif" font-weight="800" font-size="26" letter-spacing="-1" fill="#B23A2A">RA</text><text x="13" y="86" font-family="Archivo,sans-serif" font-weight="800" font-size="20" fill="#101214">NO</text>',
 pop:'<rect x="8" y="6" width="64" height="88" fill="#FFD84D"/><circle cx="40" cy="42" r="22" fill="#E8336D"/><text x="40" y="50" text-anchor="middle" font-family="Archivo,sans-serif" font-weight="800" font-size="20" fill="#FFD84D">POP</text><rect x="8" y="74" width="64" height="20" fill="#2B59C3"/>',
 naturale:'<rect x="8" y="6" width="64" height="88" fill="#C9A77C"/><circle cx="40" cy="40" r="17" fill="none" stroke="#3B2A1A" stroke-width="1" stroke-dasharray="2 2"/><text x="40" y="45" text-anchor="middle" font-family="Caveat,cursive" font-size="15" fill="#3B2A1A">bio</text><path d="M18 72q22 -6 44 0" stroke="#3B2A1A" fill="none"/>',
 lusso:'<rect x="8" y="6" width="64" height="88" fill="#111214"/><defs><linearGradient id="swau" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#C9A24E"/><stop offset=".5" stop-color="#F1DB98"/><stop offset="1" stop-color="#A9802F"/></linearGradient></defs><path d="M40 22l6 10h-12z" fill="url(#swau)"/><text x="40" y="58" text-anchor="middle" font-family="Bodoni Moda,serif" font-size="11" letter-spacing="2" fill="url(#swau)">RÉSERVE</text><path d="M24 66h32" stroke="url(#swau)"/>',
 vintage:'<rect x="8" y="6" width="64" height="88" fill="#EADFC6"/><path d="M14 12h52v56l-26 18-26-18z" fill="none" stroke="#7A2E22" stroke-width="1.2"/><text x="40" y="44" text-anchor="middle" font-family="Bodoni Moda,serif" font-style="italic" font-size="11" fill="#7A2E22">Antica</text><text x="40" y="56" text-anchor="middle" font-family="Archivo,sans-serif" font-size="5" letter-spacing="1.5" fill="#7A2E22">DAL 1923</text>'};
var FINC={oro:'linear-gradient(135deg,#A9802F,#F1DB98 50%,#C9A24E)',argento:'linear-gradient(135deg,#8d9498,#f4f6f7 50%,#a7adb0)',rame:'linear-gradient(135deg,#6b3a1f,#ffd2b0 50%,#a2552d)',
 rilievo:'radial-gradient(circle at 40% 35%,#fff,#e9e6df 60%,#cfcac0)',goffrata:'repeating-linear-gradient(45deg,#efe9dc 0 2px,#e4dccb 2px 4px)',film:'linear-gradient(135deg,rgba(255,255,255,.2),rgba(255,255,255,.75) 50%,rgba(255,255,255,.15)),repeating-conic-gradient(#ddd 0 25%,#fff 0 50%) 0 0/10px 10px',consiglio:'conic-gradient(#22B8D6,#6F5BE8,#D9438F,#EBA43A,#22B8D6)'};
var COLC={neutri:['#F4F1EA','#D8D2C4','#8C8577'],caldi:['#B5532F','#D99A4E','#6E3B22'],freddi:['#1F4E79','#5AA0B8','#D7E8EC'],pastello:['#F6C6CF','#CFE6D6','#F8E5B5'],scuri:['#101214','#2A3B2E','#4A1E26'],vivaci:['#E8336D','#FFD84D','#2B59C3']};
var FIELDS={vino:['den','year','alc','vol'],spirits:['den','alc','vol'],birra:['style','alc','vol'],food:['den','net','ingr'],cosm:['type','net'],altro:['desc','net']};

var R={sector:'vino',cont:'bordolese',glass:'',size:'',qty:'',t:{},styles:[],cols:[],colFree:'',fins:[],mood:'',avoid:'',name:'',brand:''},imgs=[],step=0;

/* stile della procedura: coerente con la pagina */
var css=document.createElement('style');css.textContent=
'.bstart{display:flex;align-items:center;gap:16px;margin-top:26px;max-width:620px;padding:18px 20px;border:0;border-radius:4px;background:var(--ink);color:var(--cer);text-align:left;cursor:pointer;position:relative;overflow:hidden}'+
'.bstart::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:var(--spec);background-size:200% 100%;animation:sl 2s linear infinite}'+
'.bstart b{display:block;font:500 12px var(--mono);letter-spacing:.16em;text-transform:uppercase}.bstart span{font-size:14px;color:#B9BDBF}.bstart i{margin-left:auto;font:400 20px var(--mono);font-style:normal}'+
'.bor{margin:22px 0 0;font:400 11px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--tgt)}'+
'#wiz{max-width:min(980px,96vw)}#wiz .dlg{gap:20px}.wprog{display:flex;gap:6px}.wprog i{flex:1;height:2px;background:var(--hair)}.wprog i.on{background:var(--ink)}.wprog i.now{background:var(--spec)}'+
'.wq{font:400 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--gra);margin:6px 0 10px}.wsub{font-size:13px;color:var(--tgt);margin:-4px 0 10px}'+
'.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:10px}.tile{border:1px solid var(--hair);background:var(--white);padding:10px 8px 8px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:6px;font-size:13px;text-align:center;transition:border-color .2s,box-shadow .2s;border-radius:2px}'+
'.tile:hover{border-color:var(--ink)}.tile[aria-pressed=true]{border-color:var(--ink);box-shadow:inset 0 0 0 1px var(--ink),0 0 0 3px rgba(111,91,232,.15)}.tile img,.tile svg{height:96px;width:auto;max-width:100%}'+
'.tile.txt{padding:14px 8px;font-size:14px}.pills{display:flex;flex-wrap:wrap;gap:8px}.pill2{border:1px solid var(--hair);background:var(--white);border-radius:999px;padding:8px 14px;font-size:14px;cursor:pointer;display:flex;align-items:center;gap:8px}'+
'.pill2[aria-pressed=true]{border-color:var(--ink);background:var(--ink);color:var(--cer)}.pill2 .sw{width:18px;height:18px;border-radius:50%;border:1px solid rgba(0,0,0,.12);flex:none}.pill2 .pal{display:flex}.pill2 .pal i{width:10px;height:16px}'+
'.wgrid{display:grid;grid-template-columns:1fr 1fr;gap:16px 18px}.wgrid .full{grid-column:1/-1}.wf{display:grid;gap:6px;font:400 11px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--gra)}'+
'.wf input,.wf textarea,.wf select{border:0;border-bottom:1px solid var(--ink);background:transparent;padding:8px 0;font:400 16px var(--body);text-transform:none;letter-spacing:0;outline:0;color:var(--ink);border-radius:0}.wf textarea{border:1px solid var(--hair);padding:10px;min-height:76px;resize:vertical}'+
'.wnav{display:flex;justify-content:space-between;align-items:center;gap:12px;border-top:1px solid var(--hair);padding-top:16px}.wmsg{font-size:13px;color:#9b1c1c}'+
'.wbrief{width:100%;min-height:340px;border:1px solid var(--hair);background:var(--white);padding:16px;font:400 14.5px/1.55 var(--body);resize:vertical;outline:0}.wbrief:focus{border-color:var(--ink)}'+
'.wload{display:flex;align-items:center;gap:12px;min-height:200px;justify-content:center;color:var(--gra)}.watt{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.watt img{height:62px;width:62px;object-fit:cover;border:1px solid var(--hair);border-radius:6px}'+
'@media(max-width:640px){.wgrid{grid-template-columns:1fr}.tiles{grid-template-columns:repeat(3,1fr)}.tile img,.tile svg{height:72px}}';
document.head.appendChild(css);

/* bottone nella pagina iniziale */
var hero=$('#hero > div'),chips=$('#chips'),bs=el('button','bstart');bs.type='button';
var bx=el('div');bx.appendChild(el('b',null,B.start));bx.appendChild(el('span',null,B.startSub));bs.appendChild(bx);bs.appendChild(el('i',null,'→'));
hero.insertBefore(bs,chips);hero.insertBefore(el('p','bor',B.or),chips);

var dlg=el('dialog');dlg.id='wiz';var box=el('div','dlg');dlg.appendChild(box);document.body.appendChild(dlg);
dlg.addEventListener('cancel',function(e){if(step===5&&busy)e.preventDefault()});
bs.onclick=function(){step=0;draw();dlg.showModal()};
var busy=false;

function tog(arr,v,max){var i=arr.indexOf(v);if(i>=0)arr.splice(i,1);else{arr.push(v);if(max&&arr.length>max)arr.shift()}}
function tiles(map,get,set,render,cls){var w=el('div','tiles');Object.keys(map).forEach(function(k){var b=el('button','tile'+(cls?' '+cls:''));b.type='button';
  if(render)b.appendChild(render(k));b.appendChild(el('span',null,map[k]));b.setAttribute('aria-pressed',get(k));b.onclick=function(){set(k);draw()};w.appendChild(b)});return w}
function pills(map,get,set,deco){var w=el('div','pills');Object.keys(map).forEach(function(k){var b=el('button','pill2');b.type='button';if(deco)b.appendChild(deco(k));b.appendChild(document.createTextNode(map[k]));
  b.setAttribute('aria-pressed',get(k));b.onclick=function(){set(k);draw()};w.appendChild(b)});return w}
function field(lbl,key,obj,opt){var l=el('label','wf'+(opt&&opt.full?' full':''));l.appendChild(el('span',null,lbl));var i=el(opt&&opt.area?'textarea':'input');i.value=obj[key]||'';
  if(opt&&opt.ph)i.placeholder=opt.ph;i.oninput=function(){obj[key]=i.value};l.appendChild(i);return l}
function q(t){return el('p','wq',t)}

function draw(){box.innerHTML='';var x=el('button','close','×');x.type='button';x.onclick=function(){dlg.close()};box.appendChild(x);
  var pr=el('div','wprog');B.steps.forEach(function(s,i){pr.appendChild(el('i',i<step?'on':i===step?'now':''))});box.appendChild(pr);
  box.appendChild(el('span','mi',('0'+(step+1))+' / 0'+B.steps.length));box.appendChild(el('h2',null,B.steps[step]));
  var body=el('div');box.appendChild(body);
  if(step===0){body.appendChild(q(B.sector));body.appendChild(tiles(B.sectors,function(k){return R.sector===k},function(k){R.sector=k;
      if(k==='birra'&&!/longneck|steinie|lattina/.test(R.cont))R.cont='longneck';if(k==='cosm'&&!/flacone|cilindro|vaso/.test(R.cont))R.cont='flacone';if(k==='food'&&!/vaso|cilindro|lattina/.test(R.cont))R.cont='vaso';
      if((k==='vino'||k==='spirits')&&!/bordolese|borgognotta|champagnotta/.test(R.cont))R.cont='bordolese'},null,'txt'));
    var g=el('div','wgrid');g.style.marginTop='18px';g.appendChild(field(B.name,'name',R));g.appendChild(field(B.brand,'brand',R));body.appendChild(g)}
  if(step===1){body.appendChild(q(B.cont));body.appendChild(tiles(B.conts,function(k){return R.cont===k},function(k){R.cont=k},function(k){var i=el('img');i.src='/static/brief/c-'+k+'.svg';i.alt='';return i}));
    body.appendChild(q(B.glass));body.appendChild(pills(B.glasses,function(k){return R.glass===k},function(k){R.glass=R.glass===k?'':k},function(k){var s=el('i','sw');s.style.background={verde:'#2f4a2c',nero:'#1a1714',trasparente:'linear-gradient(135deg,#fff,#e6eef0)',ambra:'#7a4a16',bianco:'#f4f4f2',blu:'#24406b'}[k];return s}));
    var g=el('div','wgrid');g.style.marginTop='18px';var sz=field(B.size,'size',R,{ph:'90 × 120'});sz.appendChild(el('span','wsub',B.sizeHint));g.appendChild(sz);
    var l=el('label','wf');l.appendChild(el('span',null,B.qty));var s=el('select');['',0,1,2,3].forEach(function(v){var o=el('option',null,v===''?'—':B.qtys[v]);o.value=v===''?'':B.qtys[v];s.appendChild(o)});s.value=R.qty;s.onchange=function(){R.qty=s.value};l.appendChild(s);g.appendChild(l);body.appendChild(g)}
  if(step===2){body.appendChild(el('p','wsub',B.texts));var g=el('div','wgrid');(FIELDS[R.sector]||FIELDS.altro).forEach(function(f){g.appendChild(field(B.f[f],f,R.t,f==='ingr'?{area:1,full:1}:null))});
    g.appendChild(field(B.f.other,'other',R.t,{area:1,full:1}));body.appendChild(g)}
  if(step===3){body.appendChild(q(B.styleQ));body.appendChild(tiles(B.styles,function(k){return R.styles.indexOf(k)>=0},function(k){tog(R.styles,k,2)},function(k){var d=document.createElement('div');d.innerHTML='<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg">'+SW[k]+'</svg>';return d.firstChild}));
    body.appendChild(q(B.colQ));body.appendChild(pills(B.cols,function(k){return R.cols.indexOf(k)>=0},function(k){tog(R.cols,k,3)},function(k){var p=el('span','pal');COLC[k].forEach(function(c){var i=el('i');i.style.background=c;p.appendChild(i)});return p}));
    var g=el('div','wgrid');g.style.marginTop='12px';g.appendChild(field(B.colFree,'colFree',R,{full:1}));body.appendChild(g);
    body.appendChild(q(B.finQ));body.appendChild(pills(B.fins,function(k){return R.fins.indexOf(k)>=0},function(k){if(k==='consiglio')R.fins=R.fins.indexOf(k)>=0?[]:['consiglio'];else{R.fins=R.fins.filter(function(v){return v!=='consiglio'});tog(R.fins,k)}},function(k){var s=el('i','sw');s.style.background=FINC[k];return s}))}
  if(step===4){var g=el('div','wgrid');g.appendChild(field(B.mood,'mood',R,{area:1,full:1,ph:B.moodPh}));g.appendChild(field(B.avoid,'avoid',R,{area:1,full:1,ph:B.avoidPh}));body.appendChild(g);
    body.appendChild(q(B.att));var a=el('div','watt');imgs.forEach(function(f,i){var im=el('img');im.src=f.url;im.alt='';im.title='×';im.style.cursor='pointer';im.onclick=function(){imgs.splice(i,1);draw()};a.appendChild(im)});
    var lb=el('label','btn ghost');lb.textContent=B.attBtn;var inp=el('input');inp.type='file';inp.accept='image/*';inp.multiple=true;inp.hidden=true;lb.appendChild(inp);
    inp.onchange=function(){var fs=[].slice.call(inp.files).slice(0,4-imgs.length);Promise.all(fs.map(UP.prep)).then(function(r){r.forEach(function(f,j){if(!imgs.length&&!j&&/png|svg/.test(f.type))f.logo=true});imgs=imgs.concat(r);draw()})};
    if(imgs.length<4)a.appendChild(lb);body.appendChild(a)}
  if(step===5){var ta=el('textarea','wbrief');ta.id='wb';
    if(R._brief){body.appendChild(el('p','wsub',B.review));ta.value=R._brief;ta.oninput=function(){R._brief=ta.value};body.appendChild(ta)}
    else{var ld=el('div','wload');ld.appendChild(el('span','dot'));ld.appendChild(el('span',null,B.making));body.appendChild(ld);if(!busy)make()}}
  var nav=el('div','wnav'),bk=el('button','btn ghost',step===5?B.edit:B.back),msg=el('span','wmsg'),nx=el('button','btn',step===5?B.draw:B.next);bk.type=nx.type='button';
  bk.style.visibility=step===0?'hidden':'visible';bk.onclick=function(){if(step===5){R._brief='';step=0}else step--;draw()};
  nx.disabled=step===5&&!R._brief;
  nx.onclick=function(){if(step===0&&!R.name.trim()){msg.textContent=B.req;return}if(step<5){step++;if(step===5)R._brief='';draw();return}
    dlg.close();UP.setFiles(imgs.slice());UP.send(R._brief)};
  nav.appendChild(bk);nav.appendChild(msg);nav.appendChild(nx);box.appendChild(nav)}

function risposte(){var t={};Object.keys(R.t).forEach(function(k){if(R.t[k]&&R.t[k].trim())t[(B.f[k]||k)]=R.t[k].trim()});
  return{settore:B.sectors[R.sector],nome_prodotto:R.name,azienda:R.brand,contenitore:B.conts[R.cont]+' ('+R.cont+')',colore_contenitore:R.glass?B.glasses[R.glass]:'',
    misura_etichetta_mm:R.size||'da proporre',quantita:R.qty,testi:t,stile:R.styles.map(function(k){return B.styles[k]}),colori:R.cols.map(function(k){return B.cols[k]}).concat(R.colFree?[R.colFree]:[]),
    lavorazioni:R.fins.map(function(k){return B.fins[k]}),atmosfera:R.mood,da_evitare:R.avoid,allegati:imgs.map(function(f){return f.logo?'logo':'immagine di riferimento'})}}
function make(){busy=true;fetch('/api/brief',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lang:LG,risposte:risposte()})})
  .then(function(r){return r.json().then(function(j){if(!r.ok||!j.brief)throw 0;return j})}).then(function(j){R._brief=j.brief})
  .catch(function(){R._brief='';var m=$('.wload',box);if(m)m.textContent=B.err}).then(function(){busy=false;if(dlg.open&&step===5&&R._brief)draw()})}
})();
