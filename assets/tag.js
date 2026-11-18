/* UltraPixel — cookie banner (Google Consent Mode v2), Google click ID and click events for Google Tag Manager.
   Loaded only on sites that carry Tag Manager (ultrapixel.it). The defaults (everything denied) and the stored choice
   are applied inline at the top of <head>, before Tag Manager; this file shows the banner and records the visitor's choice.
   Choice: cookie up_consent, 6 months, Domain=.ultrapixel.it so that studio.ultrapixel.it reads the same choice. */
(function(){
  var d=document,w=window,B=d.getElementById('ckb');
  w.dataLayer=w.dataLayer||[];if(typeof w.gtag!=='function'){w.gtag=function(){w.dataLayer.push(arguments)}}
  var host=location.hostname,dom=/(^|\.)ultrapixel\.it$/.test(host)?'; Domain=.ultrapixel.it':'',sec=location.protocol==='https:'?'; Secure':'';
  function setc(n,v,age){d.cookie=n+'='+v+'; Max-Age='+age+'; Path=/'+dom+'; SameSite=Lax'+sec}
  function getc(n){var m=d.cookie.match(new RegExp('(?:^|; )'+n+'=([^;]*)'));return m?decodeURIComponent(m[1]):''}
  function read(){var v=getc('up_consent');if(!v)return null;try{var c=JSON.parse(v);return typeof c==='object'&&c?c:null}catch(e){return null}}
  w.upConsent=read;

  /* Google click ID: kept for 90 days only with marketing consent, then sent with every request (assets/lead.js) */
  var gclid=(new URLSearchParams(location.search).get('gclid')||'').replace(/[^\w-]/g,'').slice(0,200);
  function keepGclid(c){if(gclid&&c&&c.marketing)setc('up_gclid',encodeURIComponent(gclid),7776000)}
  /* consent withdrawn: remove what Google and we had set on this site */
  function wipe(c){
    var names=d.cookie.split('; ').map(function(x){return x.split('=')[0]}),dead=[];
    names.forEach(function(n){if((!c.analytics&&/^_ga(_|$)/.test(n))||(!c.marketing&&(/^_gcl_/.test(n)||n==='up_gclid')))dead.push(n)});
    var ds=['',/(^|\.)ultrapixel\.it$/.test(host)?'.ultrapixel.it':'','.'+host];
    dead.forEach(function(n){ds.forEach(function(x){d.cookie=n+'=; Max-Age=0; Path=/'+(x?'; Domain='+x:'')})});
  }
  function saveConsent(analytics,marketing){
    analytics=!!analytics;marketing=!!marketing;
    var c={analytics:analytics,marketing:marketing,ts:Date.now()};
    setc('up_consent',encodeURIComponent(JSON.stringify(c)),15552000);   /* 6 months */
    gtag('consent','update',{analytics_storage:analytics?'granted':'denied',ad_storage:marketing?'granted':'denied',ad_user_data:marketing?'granted':'denied',ad_personalization:marketing?'granted':'denied'});
    w.dataLayer.push({event:'consent_updated',consent_analytics:analytics,consent_marketing:marketing});
    keepGclid(c);wipe(c);
  }
  w.saveConsent=saveConsent;
  keepGclid(read());

  /* banner */
  if(B){
    var opts=d.getElementById('ckb-opts'),an=d.getElementById('ck-an'),mk=d.getElementById('ck-ma'),q=function(k){return B.querySelector('[data-ck="'+k+'"]')};
    var open=function(custom){
      var c=read();an.checked=!!(c&&c.analytics);mk.checked=!!(c&&c.marketing);
      opts.hidden=!custom;q('custom').hidden=!!custom;q('save').hidden=!custom;
      B.hidden=false;d.body.classList.add('ck-open');
    };
    var close=function(){B.hidden=true;d.body.classList.remove('ck-open')};
    d.addEventListener('click',function(e){
      var t=e.target.closest&&e.target.closest('[data-ck]');if(!t)return;var k=t.getAttribute('data-ck');
      if(k==='open'){e.preventDefault();open(true);var f=B.querySelector('input:not([disabled])');f&&f.focus();return}
      if(!B.contains(t))return;
      if(k==='accept'){saveConsent(true,true);close()}
      else if(k==='reject'||k==='close'){saveConsent(false,false);close()}   /* closing with the X counts as Reject all */
      else if(k==='custom'){open(true)}
      else if(k==='save'){saveConsent(an.checked,mk.checked);close()}
    });
    B.addEventListener('keydown',function(e){if(e.key==='Escape'){saveConsent(false,false);close()}});
    if(!read())open(false);
    if(location.hash==='#settings')open(true);
  }

  /* clicks Google can count: phone, WhatsApp, email, links to the studio */
  d.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a[href]');if(!a)return;var h=a.getAttribute('href')||'',ev=null;
    if(/^tel:/i.test(h))ev={event:'phone_click'};
    else if(/^https?:\/\/(wa\.me|api\.whatsapp\.com|web\.whatsapp\.com)\//i.test(h))ev={event:'whatsapp_click'};
    else if(/^mailto:/i.test(h))ev={event:'email_click'};
    else if(a.hostname==='studio.ultrapixel.it'){
      var p=location.pathname;
      ev={event:'studio_click',link_location:a.closest('#nav2,.nav2')?'header':a.closest('footer')?'footer':/\/label-design\//.test(p)?'label-design':/\/blog\//.test(p)?'blog':'other'};
    }
    if(ev)w.dataLayer.push(ev);
  },true);
})();
