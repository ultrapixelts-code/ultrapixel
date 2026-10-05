/* UltraPixel site behaviour: header, light on tiles, anatomy pins, forms, gentle reveal. */
(function(){
  var d=document, hdr=d.getElementById('hdr'), film=d.getElementById('film');

  // header: dark ink while the light film is under it, warm on anthracite elsewhere
  if(film&&hdr){
    var upd=function(){hdr.classList.toggle('light',film.getBoundingClientRect().bottom>64&&!hdr.classList.contains('open'))};
    addEventListener('scroll',upd,{passive:true});addEventListener('resize',upd);upd();
  }
  var bg=d.getElementById('burger');
  if(bg)bg.addEventListener('click',function(){var o=hdr.classList.toggle('open');bg.setAttribute('aria-expanded',o);if(o)hdr.classList.remove('light');else if(film)dispatchEvent(new Event('scroll'))});

  // light that follows the pointer on work tiles
  d.querySelectorAll('[data-light]').forEach(function(t){t.addEventListener('pointermove',function(e){var b=t.getBoundingClientRect();
    t.style.setProperty('--mx',((e.clientX-b.left)/b.width*100).toFixed(1)+'%');t.style.setProperty('--my',((e.clientY-b.top)/b.height*100).toFixed(1)+'%')},{passive:true})});

  // anatomy: list rows and pins highlight each other
  var A=d.getElementById('anat');
  if(A){var set=function(i,on){A.querySelectorAll('[data-i="'+i+'"]').forEach(function(e){e.classList.toggle('on',on)})};
    A.querySelectorAll('[data-i]').forEach(function(e){e.addEventListener('pointerenter',function(){set(e.dataset.i,true)});e.addEventListener('pointerleave',function(){set(e.dataset.i,false)})})}

  // reveal on scroll (content is visible without JS)
  if('IntersectionObserver' in window&&!matchMedia('(prefers-reduced-motion:reduce)').matches){
    d.documentElement.classList.add('js');
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}})},{rootMargin:'0px 0px -8% 0px'});
    d.querySelectorAll('.rv').forEach(function(e){io.observe(e)});
  }

  // forms: POST to data-endpoint when set, otherwise open the visitor's mail app when data-email is set
  d.querySelectorAll('form[data-form]').forEach(function(f){
    var q=new URLSearchParams(location.search).get('topic'), sel=f.querySelector('[name=topic]');
    if(q&&sel&&sel.querySelector('option[value="'+q+'"]'))sel.value=q;
    var msg=f.querySelector('.form-msg'), say=function(k){msg.textContent=f.dataset[k];msg.hidden=false};
    f.addEventListener('submit',function(e){
      e.preventDefault(); if(!f.reportValidity())return;
      var data={};new FormData(f).forEach(function(v,k){data[k]=v});
      if(f.dataset.endpoint){
        fetch(f.dataset.endpoint,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(data)})
          .then(function(r){if(!r.ok)throw 0;f.reset();say('sent')}).catch(function(){say('error')});
      }else if(f.dataset.email){
        var body=Object.keys(data).map(function(k){return k+': '+data[k]}).join('\n');
        location.href='mailto:'+f.dataset.email+'?subject='+encodeURIComponent('UltraPixel website: '+(data.topic||'request'))+'&body='+encodeURIComponent(body);
      }else say('none');
    });
  });
})();
