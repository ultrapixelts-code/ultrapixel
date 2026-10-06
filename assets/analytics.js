/* UltraPixel — first-party, cookieless statistics.
   Sends page views and a few named events to our own backend (data-endpoint on this script tag).
   No cookies, no persistent identifier, nothing stored for analytics. With no endpoint configured it does nothing. */
(function(){
  var sc=document.currentScript,ep=sc&&sc.dataset.endpoint,lang=sc&&sc.dataset.lang;
  function source(){
    var a={};try{a=JSON.parse(sessionStorage.getItem('up_attr')||'{}')}catch(e){}
    var u=(a.utm_source||'').toLowerCase(),r='';try{r=a.referrer?new URL(a.referrer).hostname.toLowerCase():''}catch(e){}
    var s=u+' '+r;
    var cat=/chatgpt|openai/.test(s)?'chatgpt':/perplexity|copilot|gemini|claude/.test(s)?'ai_other':/linkedin|lnkd/.test(s)?'linkedin':/google\./.test(r)||u==='google'?'google':/bing|duckduckgo|yahoo|ecosia|qwant/.test(s)?'search_other':/instagram|facebook|fb\./.test(s)?'social_other':(!u&&!r)?'direct':'referral';
    return {source:cat,utm_source:a.utm_source||'',utm_medium:a.utm_medium||'',utm_campaign:a.utm_campaign||'',ref_host:r,landing_page:a.landing_page||''};
  }
  window.upTrack=function(name,props){
    if(!ep)return;
    var s=source(),d={event:name,path:location.pathname,lang:lang,ts:new Date().toISOString(),props:props||{}};for(var k in s)d[k]=s[k];
    try{var b=new Blob([JSON.stringify(d)],{type:'text/plain'});if(!(navigator.sendBeacon&&navigator.sendBeacon(ep,b)))fetch(ep,{method:'POST',body:JSON.stringify(d),keepalive:true})}catch(e){}
  };
  upTrack('page_view');
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a[href]');if(!a)return;var h=a.getAttribute('href');
    var kind=/\/samples\//.test(h)?'sample':/topic=quote/.test(h)?'quote':/\/contact\//.test(h)?'contact':/\/partners\//.test(h)?'partner':/^mailto:/.test(h)?'email':/^tel:/.test(h)?'phone':'';
    if(kind)upTrack('cta_click',{kind:kind,label:(a.textContent||'').trim().slice(0,60)});
  },true);
})();
