/* UltraPixel — lead attribution and request forms.
   Keeps, for this browser session only (sessionStorage, no cookies), where the visit came from:
   landing page, external referrer and utm_source / utm_medium / utm_campaign (e.g. utm_source=chatgpt.com).
   The request form adds them, with a timestamp and the page the visitor came from, to what is sent. */
(function(){
  var K='up_attr',d=document,ss;try{ss=sessionStorage;ss.getItem(K)}catch(e){ss=null}
  var get=function(k){try{return ss?JSON.parse(ss.getItem(k)||'null'):null}catch(e){return null}},put=function(k,v){try{ss&&ss.setItem(k,JSON.stringify(v))}catch(e){}};
  var q=new URLSearchParams(location.search),a=get(K);
  var ext=d.referrer&&d.referrer.indexOf(location.origin)!==0?d.referrer:'';
  if(!a||q.get('utm_source')){a={landing_page:location.pathname,referrer:ext||(a&&a.referrer)||'',utm_source:q.get('utm_source')||'',utm_medium:q.get('utm_medium')||'',utm_campaign:q.get('utm_campaign')||''};put(K,a)}
  var forms=d.querySelectorAll('form[data-form]');
  if(!forms.length){put('up_prev',location.pathname);return}
  var prev=get('up_prev')||'';
  forms.forEach(function(f){
    var set=function(n,v){var i=f.querySelector('[name="'+n+'"]');if(i)i.value=v||''};
    set('source_page',prev);set('lang',document.documentElement.lang);set('landing_page',a.landing_page);set('referrer',a.referrer);set('utm_source',a.utm_source);set('utm_medium',a.utm_medium);set('utm_campaign',a.utm_campaign);
    var t=q.get('topic'),sel=f.querySelector('[name=request_type]');if(t&&sel&&sel.querySelector('option[value="'+t+'"]'))sel.value=t;
    var sq=q.get('sector'),sc=f.querySelector('[name=sector]');if(sq&&sc)[].forEach.call(sc.options,function(o){if(o.text===sq||o.value===sq)sc.value=o.value});
    var started=false;f.addEventListener('input',function(){if(!started){started=true;window.upTrack&&upTrack('form_start',{form:location.pathname})}});
    var msg=f.querySelector('.form-msg'),say=function(k){msg.textContent=f.dataset[k];msg.hidden=false};
    f.addEventListener('submit',function(e){
      e.preventDefault();if(!f.reportValidity())return;
      set('timestamp',new Date().toISOString());
      var data={};new FormData(f).forEach(function(v,k){data[k]=v});
      if(f.dataset.endpoint){
        fetch(f.dataset.endpoint,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(data)})
          .then(function(r){if(!r.ok)throw 0;f.reset();say('sent');window.upTrack&&upTrack('form_success',{request_type:data.request_type,sector:data.sector})}).catch(function(){say('error');window.upTrack&&upTrack('form_error',{request_type:data.request_type})});
      }else if(f.dataset.email){
        var body=Object.keys(data).map(function(k){return k+': '+data[k]}).join('\n');
        location.href='mailto:'+f.dataset.email+'?subject='+encodeURIComponent('UltraPixel website — '+data.request_type+' — '+data.company)+'&body='+encodeURIComponent(body);say('mail');
      }else say('none');
    });
  });
})();
