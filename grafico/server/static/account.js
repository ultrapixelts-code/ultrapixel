/* Account aziendale per lo studio (pagina /prova): registrazione con dati di fatturazione e P.IVA verificata, accesso con codice via mail, giri gratuiti. */
(function(){
var UP=window.UP;if(!UP)return;var LG=UP.LG,el=UP.el,$=function(s,r){return(r||document).querySelector(s)};
var A={
it:{signin:'Accedi',signup:'Registrati',out:'Esci',title:'Entra nello studio',sub:'Registra la tua azienda: i primi {n} giri di proposte sono gratuiti. I dati servono per il preventivo e l’eventuale fattura.',
 tabNew:'Nuova azienda',tabOld:'Ho già un account',email:'Email di lavoro',ref:'Nome e cognome',country:'Paese',vat:'Partita IVA',vatOk:'Verificata nel registro europeo VIES',vatKo:'Partita IVA non trovata nel registro europeo VIES: controlla il numero',vatNa:'Registro VIES non raggiungibile ora: la verifichiamo noi',
 comp:'Ragione sociale',addr:'Indirizzo',cap:'CAP',city:'Città',sdi:'Codice SDI',pec:'oppure PEC',phone:'Telefono (facoltativo)',
 terms:'Accetto l’informativa privacy e le condizioni dello studio: {n} giri gratuiti, poi i giri successivi sono a pagamento (scalati dall’eventuale ordine di stampa).',
 go:'Ricevi il codice',codeT:'Controlla la mail',codeS:'Ti abbiamo mandato un codice di 6 cifre a {e}. Vale 15 minuti.',code:'Codice',enter:'Entra',again:'Rimanda il codice',test:'Modalità prova (mail non ancora attiva): il codice è',
 errEmail:'Email non valida.',errFields:'Compila i campi obbligatori.',errVat:'Partita IVA non valida nel registro europeo.',errSdi:'Per l’Italia serve il codice SDI (7 caratteri) o una PEC.',errCode:'Codice errato o scaduto.',errNone:'Nessun account con questa email: registrati.',errGen:'Qualcosa non ha funzionato: riprova.',errMany:'Troppi tentativi: riprova tra un po’.',
 left:'{n} giri gratuiti rimasti',left1:'1 giro rimasto',left0:'Giri esauriti',unlock:'Richiedi lo sblocco di altri giri',unlockSent:'Richiesta inviata: ti scriviamo noi a breve.',needAcc:'Per iniziare registra la tua azienda o accedi.'},
en:{signin:'Sign in',signup:'Sign up',out:'Sign out',title:'Enter the studio',sub:'Register your company: the first {n} rounds of proposals are free. We use your details for the quote and any invoice.',
 tabNew:'New company',tabOld:'I have an account',email:'Work email',ref:'Full name',country:'Country',vat:'VAT number',vatOk:'Verified in the EU VIES register',vatKo:'VAT number not found in the EU VIES register: please check it',vatNa:'VIES register unavailable right now: we will check it',
 comp:'Company name',addr:'Address',cap:'Postcode',city:'City',sdi:'SDI code',pec:'or PEC',phone:'Phone (optional)',
 terms:'I accept the privacy notice and studio terms: {n} free rounds, further rounds are paid (deducted from any print order).',
 go:'Get the code',codeT:'Check your email',codeS:'We sent a 6-digit code to {e}. It is valid for 15 minutes.',code:'Code',enter:'Enter',again:'Send the code again',test:'Test mode (email not active yet): the code is',
 errEmail:'Invalid email.',errFields:'Please fill in the required fields.',errVat:'VAT number not valid in the EU register.',errSdi:'For Italy we need the SDI code (7 characters) or a PEC address.',errCode:'Wrong or expired code.',errNone:'No account with this email: please sign up.',errGen:'Something went wrong: please try again.',errMany:'Too many attempts: please try again later.',
 left:'{n} free rounds left',left1:'1 round left',left0:'No rounds left',unlock:'Request more rounds',unlockSent:'Request sent: we will get back to you shortly.',needAcc:'To start, register your company or sign in.'},
fr:{signin:'Se connecter',signup:'S’inscrire',out:'Se déconnecter',title:'Entrer dans le studio',sub:'Enregistrez votre entreprise : les {n} premiers tours de propositions sont gratuits. Vos données servent au devis et à une éventuelle facture.',
 tabNew:'Nouvelle entreprise',tabOld:'J’ai déjà un compte',email:'E-mail professionnel',ref:'Prénom et nom',country:'Pays',vat:'Numéro de TVA',vatOk:'Vérifié dans le registre européen VIES',vatKo:'Numéro de TVA introuvable dans VIES : vérifiez-le',vatNa:'Registre VIES indisponible : nous le vérifierons',
 comp:'Raison sociale',addr:'Adresse',cap:'Code postal',city:'Ville',sdi:'Code SDI',pec:'ou PEC',phone:'Téléphone (facultatif)',
 terms:'J’accepte la politique de confidentialité et les conditions du studio : {n} tours gratuits, les suivants sont payants (déduits d’une éventuelle commande).',
 go:'Recevoir le code',codeT:'Vérifiez vos e-mails',codeS:'Nous avons envoyé un code à 6 chiffres à {e}. Il est valable 15 minutes.',code:'Code',enter:'Entrer',again:'Renvoyer le code',test:'Mode test (e-mail pas encore actif) : le code est',
 errEmail:'E-mail non valide.',errFields:'Remplissez les champs obligatoires.',errVat:'Numéro de TVA non valide dans le registre européen.',errSdi:'Pour l’Italie, il faut le code SDI (7 caractères) ou une PEC.',errCode:'Code erroné ou expiré.',errNone:'Aucun compte avec cet e-mail : inscrivez-vous.',errGen:'Une erreur est survenue : réessayez.',errMany:'Trop de tentatives : réessayez plus tard.',
 left:'{n} tours gratuits restants',left1:'1 tour restant',left0:'Tours épuisés',unlock:'Demander d’autres tours',unlockSent:'Demande envoyée : nous vous répondons rapidement.',needAcc:'Pour commencer, enregistrez votre entreprise ou connectez-vous.'},
de:{signin:'Anmelden',signup:'Registrieren',out:'Abmelden',title:'Ins Studio',sub:'Registrieren Sie Ihr Unternehmen: Die ersten {n} Vorschlagsrunden sind kostenlos. Ihre Daten dienen für Angebot und eventuelle Rechnung.',
 tabNew:'Neues Unternehmen',tabOld:'Ich habe ein Konto',email:'Geschäftliche E-Mail',ref:'Vor- und Nachname',country:'Land',vat:'USt-IdNr.',vatOk:'Im EU-Register VIES bestätigt',vatKo:'USt-IdNr. im EU-Register VIES nicht gefunden: bitte prüfen',vatNa:'VIES-Register gerade nicht erreichbar: wir prüfen sie',
 comp:'Firmenname',addr:'Adresse',cap:'PLZ',city:'Ort',sdi:'SDI-Code',pec:'oder PEC',phone:'Telefon (optional)',
 terms:'Ich akzeptiere Datenschutzhinweise und Studio-Bedingungen: {n} kostenlose Runden, weitere Runden sind kostenpflichtig (werden mit einem Druckauftrag verrechnet).',
 go:'Code erhalten',codeT:'E-Mail prüfen',codeS:'Wir haben einen 6-stelligen Code an {e} gesendet. Er gilt 15 Minuten.',code:'Code',enter:'Einloggen',again:'Code erneut senden',test:'Testmodus (E-Mail noch nicht aktiv): der Code lautet',
 errEmail:'Ungültige E-Mail.',errFields:'Bitte Pflichtfelder ausfüllen.',errVat:'USt-IdNr. im EU-Register ungültig.',errSdi:'Für Italien wird der SDI-Code (7 Zeichen) oder eine PEC benötigt.',errCode:'Code falsch oder abgelaufen.',errNone:'Kein Konto mit dieser E-Mail: bitte registrieren.',errGen:'Etwas hat nicht geklappt: bitte erneut versuchen.',errMany:'Zu viele Versuche: bitte später erneut.',
 left:'{n} kostenlose Runden übrig',left1:'1 Runde übrig',left0:'Keine Runden mehr',unlock:'Weitere Runden anfragen',unlockSent:'Anfrage gesendet: wir melden uns in Kürze.',needAcc:'Registrieren Sie Ihr Unternehmen oder melden Sie sich an, um zu starten.'}
}[LG]||null;if(!A)return;
var GRATIS=2,acc=null,mode='new',stage='form',sentTo='',testCode='';
var PAESI=['IT','FR','DE','AT','BE','BG','HR','CY','CZ','DK','EE','FI','GR','IE','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE','CH','GB','NO','US'];
var NAMES;try{NAMES=new Intl.DisplayNames([LG],{type:'region'})}catch(e){NAMES=null}
function pname(c){try{return NAMES?NAMES.of(c):c}catch(e){return c}}
function vcode(c){return c==='GR'?'EL':c}
function post(u,b){return fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(b)}).then(function(r){return r.json().then(function(j){return{ok:r.ok,status:r.status,j:j}})})}

var css=document.createElement('style');css.textContent=
'.accb{display:flex;align-items:center;gap:10px}.accb .who2{font:400 10px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--gra);text-align:right;line-height:1.35}.accb .who2 b{display:block;color:var(--ink);font-weight:500;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'+
'.accb button{border:1px solid var(--hair);background:none;border-radius:999px;padding:7px 12px;font:400 10px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--tgt);cursor:pointer}.accb button.pri{background:var(--ink);color:var(--cer);border-color:var(--ink)}'+
'#accd{max-width:min(760px,96vw)}.atabs{display:flex;gap:18px;border-bottom:1px solid var(--hair)}.atabs button{border:0;background:none;padding:10px 0;font:400 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--tgt);cursor:pointer}.atabs button[aria-pressed=true]{color:var(--ink);box-shadow:inset 0 -1px 0 var(--ink)}'+
'.vat{font-size:12.5px;margin-top:2px}.vat.ok{color:#2d7a4b}.vat.ko{color:#9b1c1c}.vat.na{color:var(--tgt)}.form label.chk{display:flex;gap:10px;align-items:flex-start;font:400 13px/1.45 var(--body);text-transform:none;letter-spacing:0;color:var(--gra)}.paywall .btn{justify-self:start}.chk input{margin-top:3px}.aerr{color:#9b1c1c;font-size:13px;min-height:18px}'+
'.codein{font:500 28px var(--mono)!important;letter-spacing:.4em!important;text-align:center;max-width:260px}.testc{background:#fff6d6;border:1px solid #ecd27a;padding:10px 12px;font-size:13px}.testc b{font-family:var(--mono);letter-spacing:.2em}'+
'.paywall{border:1px solid var(--ink);background:var(--white);padding:16px;max-width:780px;display:grid;gap:12px}'+
'@media(max-width:700px){.accb .who2{display:none}}';
document.head.appendChild(css);

/* intestazione: chi è entrato e quanti giri restano */
var hb=el('div','accb'),hdr=document.querySelector('header');hdr.insertBefore(hb,hdr.querySelector('.lgs'));
function giriTxt(a){var n=a.giri_rimasti;return n<=0?A.left0:n===1?A.left1:A.left.replace('{n}',n)}
function head(){hb.innerHTML='';if(acc){var w=el('span','who2');w.appendChild(el('b',null,acc.ragione||acc.email));w.appendChild(document.createTextNode(giriTxt(acc)));hb.appendChild(w);
    var o=el('button',null,A.out);o.type='button';o.onclick=function(){post('/api/account/esci',{}).then(function(){acc=null;head()})};hb.appendChild(o)}
  else{var b=el('button','pri',A.signin);b.type='button';b.onclick=function(){open('old')};hb.appendChild(b)}}

var dlg=el('dialog');dlg.id='accd';var box=el('div','dlg');dlg.appendChild(box);document.body.appendChild(dlg);
var F={email:'',referente:'',paese:{it:'IT',fr:'FR',de:'DE',en:'GB'}[LG]||'IT',piva:'',ragione:'',indirizzo:'',cap:'',citta:'',sdi:'',pec:'',telefono:'',ok:false},vatState=null,vatT=null,err='';
function open(m){mode=m||'new';stage='form';err='';draw();if(!dlg.open)dlg.showModal()}
function inp(lbl,k,opt){var l=el('label',opt&&opt.full?'full':'');l.appendChild(el('span',null,lbl+(opt&&opt.req?' *':'')));var i=el('input');i.value=F[k]||'';if(opt&&opt.type)i.type=opt.type;if(opt&&opt.ac)i.autocomplete=opt.ac;
  i.oninput=function(){F[k]=i.value;if(k==='piva'||k==='paese')checkVat()};l.appendChild(i);return l}
function checkVat(){clearTimeout(vatT);var p=F.piva.replace(/[^A-Za-z0-9]/g,'');if(p.length<8){vatState=null;showVat();return}
  vatT=setTimeout(function(){post('/api/account/vies',{paese:vcode(F.paese),piva:p}).then(function(x){var j=x.j;vatState=j.valida;
    if(j.valida){if(!F.ragione&&j.ragione)F.ragione=j.ragione;if(!F.indirizzo&&j.indirizzo)F.indirizzo=j.indirizzo;draw()}else showVat()})},600)}
function showVat(){var v=$('#vatmsg',box);if(!v)return;v.className='vat '+(vatState===true?'ok':vatState===false?'ko':vatState===null&&F.piva.length>=8?'na':'');
  v.textContent=vatState===true?'✓ '+A.vatOk:vatState===false?A.vatKo:'';}
function draw(){box.innerHTML='';var x=el('button','close','×');x.type='button';x.onclick=function(){dlg.close()};box.appendChild(x);
  box.appendChild(el('span','mi','UltraPixel Studio · AI'));box.appendChild(el('h2',null,stage==='code'?A.codeT:A.title));
  if(stage==='code'){box.appendChild(el('p','note',A.codeS.replace('{e}',sentTo)));
    if(testCode){var t=el('p','testc');t.appendChild(document.createTextNode(A.test+' '));t.appendChild(el('b',null,testCode));box.appendChild(t)}
    var f=el('form','form'),l=el('label','full'),i=el('input','codein');i.inputMode='numeric';i.autocomplete='one-time-code';i.maxLength=6;i.value=testCode||'';l.appendChild(el('span',null,A.code));l.appendChild(i);f.appendChild(l);
    var e=el('p','aerr full',err);f.appendChild(e);var row=el('div','full'),b=el('button','btn',A.enter),ag=el('button','btn ghost',A.again);ag.type='button';row.appendChild(b);row.appendChild(document.createTextNode(' '));row.appendChild(ag);f.appendChild(row);
    ag.onclick=function(){send(mode==='old')};
    f.onsubmit=function(ev){ev.preventDefault();b.disabled=true;post('/api/account/verifica',{email:sentTo,codice:i.value}).then(function(r){b.disabled=false;
      if(!r.ok){err=A.errCode;draw();return}acc=r.j.account;head();dlg.close();if(r.j.lead)lead(r.j.lead);if(pending){var p=pending;pending=null;p()}})};
    box.appendChild(f);setTimeout(function(){i.focus()},50);return}
  box.appendChild(el('p','note',A.sub.replace('{n}',GRATIS)));
  var tb=el('div','atabs');[['new',A.tabNew],['old',A.tabOld]].forEach(function(t){var b=el('button',null,t[1]);b.type='button';b.setAttribute('aria-pressed',mode===t[0]);b.onclick=function(){mode=t[0];err='';draw()};tb.appendChild(b)});box.appendChild(tb);
  var f=el('form','form');
  f.appendChild(inp(A.email,'email',{type:'email',ac:'email',req:1,full:mode==='old'}));
  if(mode==='new'){f.appendChild(inp(A.ref,'referente',{ac:'name',req:1}));
    var lp=el('label');lp.appendChild(el('span',null,A.country+' *'));var s=el('select');s.style.cssText='border:0;border-bottom:1px solid var(--ink);background:transparent;padding:8px 0;font:400 16px var(--body)';
    PAESI.forEach(function(c){var o=el('option',null,pname(c));o.value=c;s.appendChild(o)});s.value=F.paese;s.onchange=function(){F.paese=s.value;draw();checkVat()};lp.appendChild(s);f.appendChild(lp);
    var lv=inp(A.vat,'piva',{req:1});lv.appendChild(el('span','vat'));lv.lastChild.id='vatmsg';f.appendChild(lv);
    f.appendChild(inp(A.comp,'ragione',{ac:'organization',req:1,full:1}));f.appendChild(inp(A.addr,'indirizzo',{ac:'street-address',req:1,full:1}));
    f.appendChild(inp(A.cap,'cap',{ac:'postal-code'}));f.appendChild(inp(A.city,'citta',{ac:'address-level2',req:1}));
    if(F.paese==='IT'){f.appendChild(inp(A.sdi,'sdi',{req:1}));f.appendChild(inp(A.pec,'pec',{type:'email'}))}
    f.appendChild(inp(A.phone,'telefono',{type:'tel',ac:'tel'}));
    var c=el('label','chk full'),cb=el('input');cb.type='checkbox';cb.checked=F.ok;cb.onchange=function(){F.ok=cb.checked};c.appendChild(cb);
    var ct=el('span');ct.innerHTML=A.terms.replace('{n}',GRATIS)+' <a href="https://ultrapixel.it/privacy/" target="_blank" rel="noopener">Privacy</a>';c.appendChild(ct);f.appendChild(c)}
  f.appendChild(el('p','aerr full',err));var row=el('div','full'),b=el('button','btn',A.go);row.appendChild(b);f.appendChild(row);
  f.onsubmit=function(ev){ev.preventDefault();send(mode==='old')};box.appendChild(f);showVat()}
function send(old){err='';var em=F.email.trim().toLowerCase();if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(em)){err=A.errEmail;draw();return}
  if(!old){if(!F.referente.trim()||!F.piva.trim()||!F.ragione.trim()||!F.indirizzo.trim()||!F.citta.trim()||!F.ok){err=A.errFields;draw();return}
    if(F.paese==='IT'&&!/^[A-Za-z0-9]{7}$/.test(F.sdi.trim())&&!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(F.pec.trim())){err=A.errSdi;draw();return}}
  var b={lang:LG,email:em};if(!old){for(var k in F)if(k!=='ok')b[k]=F[k];b.paese=vcode(F.paese)}
  post(old?'/api/account/accedi':'/api/account/registra',b).then(function(r){var j=r.j;
    if(!r.ok){err=r.status===429?A.errMany:j.error==='piva'?A.errVat:j.error==='sdi'?A.errSdi:j.error==='nessuno'?A.errNone:j.error==='email'?A.errEmail:j.error==='campi'?A.errFields:A.errGen;draw();return}
    sentTo=j.email;testCode=j.prova_codice||'';stage='code';if(j.esiste)mode='old';draw()}).catch(function(){err=A.errGen;draw()})}
/* nuova azienda registrata: avviso a info@ (lo manda il browser, come le altre richieste del sito) */
function lead(l){if(!l||!l.endpoint)return;var fd=new FormData();fd.append('name',acc.referente||acc.email);fd.append('company',acc.ragione||'-');fd.append('email',acc.email);fd.append('country',acc.paese||'');
  fd.append('sector','other');fd.append('request_type','studio-registrazione');fd.append('lang',LG);fd.append('message',l.testo);fd.append('source_page',location.origin+location.pathname);
  fd.append('landing_page',location.pathname);fd.append('referrer',document.referrer||'');fd.append('timestamp',new Date().toISOString());fd.append('website','');
  fetch(l.endpoint,{method:'POST',body:fd}).catch(function(){})}

/* collegamenti con la pagina */
var pending=null;
UP.extra={studio:'account'};
UP.gate=function(){if(acc)return true;pending=function(){$('#f').requestSubmit()};open('new');return false};
UP.after=function(x){var j=x.j;if(j.account){acc=j.account;head()}
  if(x.status===401){acc=null;head();open('new')}
  if(x.status===402){var p=el('div','paywall');p.appendChild(el('p','note',A.left0+' · '+(acc&&acc.ragione||'')));var b=el('button','btn',A.unlock);b.type='button';
    b.onclick=function(){b.disabled=true;lead({endpoint:'https://ultrapixel.it/backend/api/lead.php',testo:'Richiesta di sblocco giri allo studio AI.\nAzienda: '+(acc&&acc.ragione)+'\nEmail: '+(acc&&acc.email)+'\nP.IVA: '+(acc&&acc.paese)+' '+(acc&&acc.piva)+'\nGiri usati: '+(acc&&acc.giri_usati)});p.appendChild(el('p','note',A.unlockSent))};
    p.appendChild(b);UP.log.appendChild(p);UP.scroll()}};
/* "Scelgo questa": i dati li abbiamo già, restano solo quantità, telefono e note */
var pick=$('#pick');new MutationObserver(function(){if(!pick.open||!acc)return;var f=$('#pf');
  [['name',acc.referente],['company',acc.ragione],['email',acc.email],['country',acc.paese]].forEach(function(p){var i=f.elements[p[0]];if(i){i.value=p[1]||'';i.closest('label').style.display='none'}})}).observe(pick,{attributes:true,attributeFilter:['open']});
/* il brief guidato parte solo da registrati */
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('.bstart');if(t&&!acc){e.stopImmediatePropagation();e.preventDefault();pending=function(){t.click()};open('new')}},true);

fetch('/api/account/me',{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(j){acc=j.account;if(acc)GRATIS=acc.giri_totali;head()}).catch(head);
head();
})();
