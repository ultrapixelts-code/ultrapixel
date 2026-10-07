/* UltraPixel — "What does your label cost?"
   Sends the photo or file to the server to read size, material and finishes, then asks the server for the price.
   Nothing is calculated here: the browser only shows what the server returns. */
(function(){
  var d=document,$=function(i){return d.getElementById(i)},S=$('quote');if(!S)return;
  var T=JSON.parse($('q-t').textContent),lang=S.dataset.lang||'en',rm=matchMedia('(prefers-reduced-motion:reduce)').matches;
  var nf=new Intl.NumberFormat(lang),eur=function(x,dec){return new Intl.NumberFormat(lang,{style:'currency',currency:'EUR',minimumFractionDigits:dec||0,maximumFractionDigits:dec||0}).format(x)};
  var st={foil_cov:0.2,busy:false,seq:0,shown:0},timer,scanT=[];
  var show=function(el,on){el.hidden=!on},err=function(k){var e=$('q-err');if(!k){e.hidden=true;return}e.textContent=T['e_'+k]||T.e_net;e.hidden=false;show($('q-price'),false);st.shown=0};
  var wait=function(ms){return new Promise(function(r){setTimeout(r,ms)})};
  /* numbers settle instead of jumping */
  function tween(from,to,ms,put){
    if(rm||from===to){put(to);return}
    var t0=performance.now();(function tick(now){var k=Math.max(0,Math.min(1,(now-t0)/ms));k=1-Math.pow(1-k,3);put(from+(to-from)*k);if(k<1)requestAnimationFrame(tick)})(t0);
  }
  [].forEach.call(d.querySelectorAll('#q-chips button'),function(b){b.textContent=nf.format(+b.dataset.q);b.addEventListener('click',function(){$('q-qty').value=b.dataset.q;price()})});
  if(!(window.matchMedia&&matchMedia('(pointer:coarse)').matches)){S.classList.add('mouse')}

  /* phones send large photos: shrink them before upload */
  function shrink(file){
    return new Promise(function(res){
      if(!/^image\//.test(file.type)||file.size<900000)return res(file);
      var img=new Image(),u=URL.createObjectURL(file);
      img.onload=function(){var m=1600,k=Math.min(1,m/Math.max(img.width,img.height)),c=d.createElement('canvas');c.width=Math.round(img.width*k);c.height=Math.round(img.height*k);
        c.getContext('2d').drawImage(img,0,0,c.width,c.height);URL.revokeObjectURL(u);c.toBlob(function(b){res(b||file)},'image/jpeg',.85)};
      img.onerror=function(){URL.revokeObjectURL(u);res(file)};img.src=u;
    });
  }
  function scanning(on){
    var P=$('q-prev'),li=d.querySelectorAll('#q-reading li');scanT.forEach(clearTimeout);scanT=[];
    P.classList.toggle('scan',on);[].forEach.call(li,function(l){l.classList.remove('on','ok')});
    if(on)[].forEach.call(li,function(l,i){scanT.push(setTimeout(function(){l.classList.add('on')},rm?0:150+i*480));scanT.push(setTimeout(function(){l.classList.add('ok')},rm?0:620+i*480))});
  }
  function take(file){
    if(!file||st.busy)return;st.busy=true;err();
    var isPdf=file.type==='application/pdf'||/\.pdf$/i.test(file.name||'');
    var im=$('q-img');if(im.src&&im.src.indexOf('blob:')===0)URL.revokeObjectURL(im.src);
    if(isPdf){im.removeAttribute('src');im.alt=file.name||'PDF';$('q-prev').classList.add('pdf')}else{im.src=URL.createObjectURL(file);$('q-prev').classList.remove('pdf')}
    show($('q-pick'),false);show($('q-prev'),true);show($('q-form'),false);show($('q-dim'),false);$('q-prev').classList.remove('done');show($('q-reading'),true);scanning(true);
    if(!S.classList.contains('mouse')){try{$('q-drop').scrollIntoView({behavior:rm?'auto':'smooth',block:'start'})}catch(e){}}
    var min=wait(rm?0:1900);
    shrink(file).then(function(b){var fd=new FormData();fd.append('file',b,isPdf?'label.pdf':'label.jpg');return fetch('/api/quote/analyze',{method:'POST',body:fd})})
      .then(function(r){return r.json().then(function(j){return{ok:r.ok,status:r.status,j:j}})})
      .then(function(x){if(x.ok&&x.j.preview){$('q-img').src=x.j.preview;$('q-prev').classList.remove('pdf')}return min.then(function(){return x})})
      .then(function(x){
        st.busy=false;scanning(false);show($('q-reading'),false);
        if(!x.ok){reset();err(x.j&&x.j.error==='rate'?'rate':x.j&&x.j.error==='badfile'?'badfile':'net');return}
        fill(x.j);
      }).catch(function(){st.busy=false;scanning(false);show($('q-reading'),false);fill({recognised:false})});
  }
  function dim(){var w=int($('q-w').value),h=int($('q-h').value),e=$('q-dim');if(w&&h){e.textContent=w+' × '+h+' mm';show(e,true)}else show(e,false)}
  function fill(a){
    var sub=T.fix,note='';
    if(!a.recognised)sub=a.w?T.fix:T.manual;else if(a.is_label===false)sub=T.noLabel;
    if(a.size_confidence==='die')note=T.sizeDie;else if(a.size_confidence==='exact')note=T.sizeExact;else if(a.recognised&&a.w)note=a.size_confidence==='low'?T.sizeLow:T.sizeEst;
    $('q-sizenote').textContent=note;show($('q-sizenote'),!!note);
    $('q-sub').textContent=sub;
    $('q-mat').value=a.material||'coated';
    $('q-varnish').checked=a.recognised?!!a.varnish:true;$('q-foil').checked=(a.foil||0)>0;$('q-foil2').checked=(a.foil||0)>1;$('q-relief').checked=!!a.relief;
    st.foil_cov=a.foil_cov||0.2;st.shown=0;sync();
    var F=$('q-form');F.classList.remove('in');show(F,true);show($('q-price'),false);void F.offsetWidth;F.classList.add('in');$('q-prev').classList.add('done');
    ['w','h'].forEach(function(k){var el=$('q-'+k);if(a[k])tween(0,a[k],900,function(v){el.value=Math.round(v);dim()});else el.value=''});dim();
    window.upTrack&&upTrack('quote_read',{kind:a.kind||'',recognised:!!a.recognised});
    var q=$('q-qty');if(q.value)price();else if(S.classList.contains('mouse'))q.focus();else{try{F.parentNode.scrollIntoView({behavior:rm?'auto':'smooth',block:'start'})}catch(e){}}
  }
  function sync(){var f2=$('q-foil2');f2.disabled=!$('q-foil').checked;if(f2.disabled)f2.checked=false;f2.parentNode.classList.toggle('off',f2.disabled)}
  function reset(){show($('q-prev'),false);show($('q-pick'),true);show($('q-form'),false);show($('q-price'),false);st.shown=0;$('q-photo').value='';$('q-file').value=''}
  var int=function(v){return parseInt(String(v).replace(/[^\d]/g,''),10)||0};
  function price(){
    clearTimeout(timer);timer=setTimeout(function(){
      var w=int($('q-w').value),h=int($('q-h').value),q=int($('q-qty').value);
      if(!q){show($('q-price'),false);st.shown=0;err();return}
      if(!w||!h)return err('size');
      var body={w:w,h:h,qty:q,material:$('q-mat').value,varnish:$('q-varnish').checked,foil:$('q-foil').checked?($('q-foil2').checked?2:1):0,relief:$('q-relief').checked,foil_cov:st.foil_cov},n=++st.seq;
      fetch('/api/quote/price',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
        .then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j}})})
        .then(function(x){if(n!==st.seq)return;if(!x.ok)return err(x.j.error);render(x.j)}).catch(function(){if(n===st.seq)err('net')});
    },350);
  }
  function cfg(c){
    var p=[nf.format(c.qty)+' '+T.labels,c.w+' × '+c.h+' mm',T['m_'+c.material]];
    if(c.varnish)p.push(T.varnish);if(c.foil)p.push(c.foil>1?T.foil+' × 2':T.foil);if(c.relief)p.push(T.relief);
    return p.join(' · ');
  }
  function render(j){
    var P=$('q-price'),first=P.hidden,from=st.shown;err();st.shown=j.total;
    $('q-per').textContent=eur(j.per1000,2)+' '+T.per;$('q-cfg').textContent=cfg(j.config);
    var t=$('q-table');t.textContent='';j.table.forEach(function(r,i){var a=d.createElement('dt'),b=d.createElement('dd'),sm=d.createElement('small');a.textContent=nf.format(r.qty)+' '+T.labels;b.textContent=eur(r.total);sm.textContent=eur(r.per1000,2)+' '+T.per;b.appendChild(sm);
      a.style.setProperty('--i',i);b.style.setProperty('--i',i);if(r.qty===j.config.qty){a.className=b.className='cur'}t.appendChild(a);t.appendChild(b)});
    $('q-cta').href=S.dataset.contact+'?topic=quote&msg='+encodeURIComponent(T.msg+'\n'+cfg(j.config)+'\n'+T.from+' '+eur(j.total)+' '+T.vat);
    if(first){P.classList.remove('in');show(P,true);void P.offsetWidth;P.classList.add('in')}
    tween(first?0:from,j.total,first?1300:700,function(v){$('q-total').textContent=eur(Math.round(v))});
    if(first&&!S.classList.contains('mouse')){try{P.scrollIntoView({behavior:rm?'auto':'smooth',block:'start'})}catch(e){}}
    window.upTrack&&upTrack('quote_price',{qty:j.config.qty,material:j.config.material,total:j.total});
  }
  $('q-bphoto').addEventListener('click',function(){$('q-photo').click()});$('q-bfile').addEventListener('click',function(){$('q-file').click()});
  ['q-photo','q-file'].forEach(function(i){$(i).addEventListener('change',function(e){take(e.target.files[0])})});
  $('q-again').addEventListener('click',function(){err();reset()});
  ['q-w','q-h','q-qty'].forEach(function(i){$(i).addEventListener('input',function(){dim();price()})});
  ['q-mat','q-varnish','q-foil','q-foil2','q-relief'].forEach(function(i){$(i).addEventListener('change',function(){sync();price()})});
  var dz=$('q-drop');
  ['dragenter','dragover'].forEach(function(n){dz.addEventListener(n,function(e){e.preventDefault();dz.classList.add('over')})});
  ['dragleave','drop'].forEach(function(n){dz.addEventListener(n,function(e){e.preventDefault();dz.classList.remove('over')})});
  dz.addEventListener('drop',function(e){var f=e.dataTransfer&&e.dataTransfer.files[0];if(f)take(f)});
})();
