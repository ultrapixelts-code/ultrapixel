/* UltraPixel Studio — cookie banner (Google Consent Mode v2), Google click ID and virtual page views for Google Tag Manager.
   Same container and same choice as ultrapixel.it: the cookie up_consent (6 months) lives on .ultrapixel.it, so a choice made
   on either site is not asked again on the other. The defaults (everything denied) and the stored choice are applied inline
   at the top of <head>, before Tag Manager; this file shows the banner and records the visitor's choice. */
(function(){
  var d=document,w=window;
  w.dataLayer=w.dataLayer||[];if(typeof w.gtag!=='function'){w.gtag=function(){w.dataLayer.push(arguments)}}
  var host=location.hostname,main=/(^|\.)ultrapixel\.it$/.test(host),dom=main?'; Domain=.ultrapixel.it':'',sec=location.protocol==='https:'?'; Secure':'';
  function setc(n,v,age){d.cookie=n+'='+v+'; Max-Age='+age+'; Path=/'+dom+'; SameSite=Lax'+sec}
  function getc(n){var m=d.cookie.match(new RegExp('(?:^|; )'+n+'=([^;]*)'));return m?decodeURIComponent(m[1]):''}
  function read(){var v=getc('up_consent');if(!v)return null;try{var c=JSON.parse(v);return typeof c==='object'&&c?c:null}catch(e){return null}}
  w.upConsent=read;

  /* virtual page views: the studio is one page, these are its screens */
  var lastVp='';
  w.upPage=function(path,title){if(path===lastVp)return;lastVp=path;w.dataLayer.push({event:'virtual_page_view',page_path:path,page_title:title})};
  /* one helper for the conversion events (assets read it as window.upEvent) */
  w.upEvent=function(o){w.dataLayer.push(o)};

  /* Google click ID: kept 90 days only with marketing consent; the server stores it with the account */
  var gclid=(new URLSearchParams(location.search).get('gclid')||'').replace(/[^\w-]/g,'').slice(0,200);
  function keepGclid(c){if(gclid&&c&&c.marketing)setc('up_gclid',encodeURIComponent(gclid),7776000)}
  function wipe(c){
    var names=d.cookie.split('; ').map(function(x){return x.split('=')[0]}),dead=[];
    names.forEach(function(n){if((!c.analytics&&/^_ga(_|$)/.test(n))||(!c.marketing&&(/^_gcl_/.test(n)||n==='up_gclid')))dead.push(n)});
    var ds=['',main?'.ultrapixel.it':'','.'+host];
    dead.forEach(function(n){ds.forEach(function(x){d.cookie=n+'=; Max-Age=0; Path=/'+(x?'; Domain='+x:'')})});
  }
  function saveConsent(analytics,marketing){
    analytics=!!analytics;marketing=!!marketing;
    var c={analytics:analytics,marketing:marketing,ts:Date.now()};
    setc('up_consent',encodeURIComponent(JSON.stringify(c)),15552000);
    gtag('consent','update',{analytics_storage:analytics?'granted':'denied',ad_storage:marketing?'granted':'denied',ad_user_data:marketing?'granted':'denied',ad_personalization:marketing?'granted':'denied'});
    w.dataLayer.push({event:'consent_updated',consent_analytics:analytics,consent_marketing:marketing});
    keepGclid(c);wipe(c);
  }
  w.saveConsent=saveConsent;
  keepGclid(read());

  /* banner texts: the same as on ultrapixel.it */
  var T={
   it:{title:'Cookie su questo sito',text:'Usiamo i cookie solo se sei d’accordo: cookie di statistica per capire come viene usato il sito e cookie di marketing per misurare i nostri annunci Google. I cookie necessari sono sempre attivi. Puoi cambiare la tua scelta in qualsiasi momento da “Impostazioni cookie” in fondo alla pagina.',
       accept:'Accetta tutti',reject:'Rifiuta tutti',customise:'Personalizza',save:'Salva le scelte',close:'Chiudi e rifiuta tutti',policy:'Cookie policy',settings:'Impostazioni cookie',
       necessary:'Necessari',necessaryP:'Sempre attivi. Ricordano la tua scelta sui cookie, il tuo accesso allo studio e fanno funzionare il sito.',
       analytics:'Statistica',analyticsP:'Google Analytics: quante persone visitano il sito, quali pagine leggono e da dove arrivano.',
       marketing:'Marketing',marketingP:'Google Ads: misura quali annunci portano a una richiesta e permette a Google di mostrare i nostri annunci a chi ha già visitato il sito.'},
   en:{title:'Cookies on this website',text:'We use cookies only if you agree: analytics cookies to understand how the site is used, and marketing cookies to measure our Google ads. Necessary cookies are always on. You can change your choice at any time from “Cookie settings” at the bottom of the page.',
       accept:'Accept all',reject:'Reject all',customise:'Customise',save:'Save choices',close:'Close and reject all',policy:'Cookie policy',settings:'Cookie settings',
       necessary:'Necessary',necessaryP:'Always on. They remember your cookie choice, keep you signed in to the studio and keep the site working.',
       analytics:'Analytics',analyticsP:'Google Analytics: how many people visit, which pages they read and where they come from.',
       marketing:'Marketing',marketingP:'Google Ads: measures which ads lead to a request and lets Google show our ads to people who have visited this site.'},
   fr:{title:'Cookies sur ce site',text:'Nous utilisons des cookies uniquement avec votre accord : des cookies de mesure d’audience pour comprendre l’utilisation du site, et des cookies marketing pour mesurer nos annonces Google. Les cookies nécessaires sont toujours actifs. Vous pouvez modifier votre choix à tout moment via « Paramètres des cookies » en bas de la page.',
       accept:'Tout accepter',reject:'Tout refuser',customise:'Personnaliser',save:'Enregistrer mes choix',close:'Fermer et tout refuser',policy:'Politique de cookies',settings:'Paramètres des cookies',
       necessary:'Nécessaires',necessaryP:'Toujours actifs. Ils mémorisent votre choix sur les cookies, vous gardent connecté au studio et assurent le fonctionnement du site.',
       analytics:'Mesure d’audience',analyticsP:'Google Analytics : combien de personnes visitent le site, quelles pages elles lisent et d’où elles viennent.',
       marketing:'Marketing',marketingP:'Google Ads : mesure quelles annonces mènent à une demande et permet à Google de montrer nos annonces aux personnes ayant déjà visité ce site.'},
   de:{title:'Cookies auf dieser Website',text:'Wir verwenden Cookies nur mit Ihrer Zustimmung: Statistik-Cookies, um zu verstehen, wie die Website genutzt wird, und Marketing-Cookies, um unsere Google-Anzeigen zu messen. Notwendige Cookies sind immer aktiv. Sie können Ihre Wahl jederzeit über „Cookie-Einstellungen“ unten auf der Seite ändern.',
       accept:'Alle akzeptieren',reject:'Alle ablehnen',customise:'Anpassen',save:'Auswahl speichern',close:'Schließen und alle ablehnen',policy:'Cookie-Richtlinie',settings:'Cookie-Einstellungen',
       necessary:'Notwendig',necessaryP:'Immer aktiv. Sie speichern Ihre Cookie-Auswahl, halten Sie im Studio angemeldet und halten die Website funktionsfähig.',
       analytics:'Statistik',analyticsP:'Google Analytics: wie viele Personen die Website besuchen, welche Seiten sie lesen und woher sie kommen.',
       marketing:'Marketing',marketingP:'Google Ads: misst, welche Anzeigen zu einer Anfrage führen, und ermöglicht Google, unsere Anzeigen Personen zu zeigen, die diese Website bereits besucht haben.'}};
  var lg=(d.documentElement.lang||'en').slice(0,2),t=T[lg]||T.en;
  var pol='https://ultrapixel.it/'+(lg==='it'?'':(T[lg]?lg:'en')+'/')+'cookies/';

  function el(tag,cls,txt){var e=d.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
  var css=el('style');css.textContent=
   '.ckb{position:fixed;left:16px;right:16px;bottom:16px;z-index:200;max-width:640px;margin:0 auto;padding:22px 22px 18px;background:var(--white);color:var(--ink);border:1px solid var(--hair);border-radius:14px;box-shadow:0 18px 50px rgba(16,18,20,.18);max-height:calc(100vh - 32px);overflow:auto}'+
   '.ckb[hidden]{display:none}.ckb .mi{display:block;margin:0 34px 10px 0}.ckb-p{margin:0;font:400 14.5px/1.5 var(--body);color:var(--gra)}.ckb-p a{color:var(--ink);text-decoration:underline;text-underline-offset:3px}'+
   '.ckb-x{position:absolute;top:10px;right:10px;width:34px;height:34px;border:0;background:none;color:var(--ink);font:300 24px/1 var(--body);cursor:pointer;border-radius:50%}.ckb-x:hover,.ckb-x:focus-visible{background:var(--hair)}'+
   '.ckb-opts{display:grid;margin:16px 0 0;border-top:1px solid var(--hair)}.ckb-opts[hidden]{display:none}.ckb-o{display:flex;align-items:center;gap:16px;padding:12px 0;border-bottom:1px solid var(--hair);cursor:pointer}'+
   '.ckb-o span{flex:1}.ckb-o b{display:block;font:500 14.5px/1.3 var(--body)}.ckb-o small{display:block;margin-top:3px;font:400 13px/1.4 var(--body);color:var(--gra)}.ckb-o input{position:absolute;opacity:0;width:1px;height:1px}'+
   '.ckb-o i{flex:none;position:relative;width:40px;height:22px;border-radius:22px;background:var(--hair);transition:background .2s}.ckb-o i::after{content:"";position:absolute;top:3px;left:3px;width:16px;height:16px;border-radius:50%;background:var(--white);box-shadow:0 1px 3px rgba(0,0,0,.25);transition:transform .2s}'+
   '.ckb-o input:checked+i{background:var(--ink)}.ckb-o input:checked+i::after{transform:translateX(18px)}.ckb-o input:disabled+i{opacity:.45}.ckb-o input:focus-visible+i{outline:2px solid var(--ink);outline-offset:2px}'+
   '.ckb-b{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px;align-items:center}.ckb-btn{flex:1 1 150px;padding:13px 18px;border-radius:999px;border:1px solid var(--ink);background:var(--ink);color:var(--cer);font:500 11.5px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;cursor:pointer}'+
   '.ckb-btn[hidden]{display:none}.ckb-btn:hover,.ckb-btn:focus-visible{background:var(--white);color:var(--ink)}.ckb-btn.ckb-l{flex:0 0 100%;background:none;border-color:transparent;color:var(--ink);text-decoration:underline;text-underline-offset:4px;padding:8px 0 2px}'+
   '.cks{display:block;text-align:center;margin:6px auto 0;font:400 9.5px/1.4 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--tgt);text-decoration:none;cursor:pointer;background:none;border:0}.cks:hover{color:var(--ink);text-decoration:underline}';
  d.head.appendChild(css);

  var B=el('div','ckb');B.id='ckb';B.setAttribute('role','dialog');B.setAttribute('aria-labelledby','ckb-t');B.hidden=true;
  var x=el('button','ckb-x','×');x.type='button';x.setAttribute('data-ck','close');x.setAttribute('aria-label',t.close);x.title=t.close;B.appendChild(x);
  var h=el('p','mi',t.title);h.id='ckb-t';B.appendChild(h);
  var p=el('p','ckb-p',t.text+' ');var a=el('a',null,t.policy);a.href=pol;a.target='_blank';a.rel='noopener';p.appendChild(a);B.appendChild(p);
  var opts=el('div','ckb-opts');opts.hidden=true;
  function opt(k,on){var l=el('label','ckb-o'),s=el('span');s.appendChild(el('b',null,t[k]));s.appendChild(el('small',null,t[k+'P']));l.appendChild(s);
    var i=el('input');i.type='checkbox';if(on){i.checked=true;i.disabled=true}else i.id='ck-'+k.slice(0,2);l.appendChild(i);var sw=el('i');sw.setAttribute('aria-hidden','true');l.appendChild(sw);opts.appendChild(l);return i}
  opt('necessary',true);var an=opt('analytics'),mk=opt('marketing');B.appendChild(opts);
  var bb=el('div','ckb-b'),btn={};
  [['reject',''],['accept',''],['custom',' ckb-l'],['save','']].forEach(function(b){var e=el('button','ckb-btn'+b[1],t[b[0]==='custom'?'customise':b[0]]);e.type='button';e.setAttribute('data-ck',b[0]);if(b[0]==='save')e.hidden=true;btn[b[0]]=e;bb.appendChild(e)});
  B.appendChild(bb);

  function open(custom){var c=read();an.checked=!!(c&&c.analytics);mk.checked=!!(c&&c.marketing);opts.hidden=!custom;btn.custom.hidden=!!custom;btn.save.hidden=!custom;B.hidden=false}
  function close(){B.hidden=true}
  d.addEventListener('click',function(e){
    var k=e.target.closest&&e.target.closest('[data-ck]');if(!k)return;k=k.getAttribute('data-ck');
    if(k==='open'){e.preventDefault();open(true);return}
    if(!B.contains(e.target))return;
    if(k==='accept'){saveConsent(true,true);close()}
    else if(k==='reject'||k==='close'){saveConsent(false,false);close()}   /* the X counts as Reject all */
    else if(k==='custom')open(true);
    else if(k==='save'){saveConsent(an.checked,mk.checked);close()}
  });
  B.addEventListener('keydown',function(e){if(e.key==='Escape'){saveConsent(false,false);close()}});
  function mount(){
    d.body.appendChild(B);
    /* permanent "Cookie settings" link under the message box (the studio has no footer) */
    var bar=d.querySelector('.bar .box')||d.querySelector('footer')||d.body,s=el('button','cks',t.settings);s.type='button';s.setAttribute('data-ck','open');
    if(bar.parentNode&&bar!==d.body)bar.parentNode.insertBefore(s,bar.nextSibling);else d.body.appendChild(s);
    if(!read())open(false);
  }
  d.readyState==='loading'?d.addEventListener('DOMContentLoaded',mount):mount();
})();
