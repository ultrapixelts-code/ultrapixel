/* UltraPixel — Material Intelligence: small, precise movements. No bounce. */
(function(){
  var d=document,root=d.documentElement,nav=d.getElementById('nav2'),rm=matchMedia('(prefers-reduced-motion:reduce)').matches;
  var cl=function(x){return Math.max(0,Math.min(1,x))};
  var spl=[].slice.call(d.querySelectorAll('.spl')),par=[].slice.call(d.querySelectorAll('[data-par]')),
      rail=d.getElementById('rail'),cut=d.querySelector('.ms.cut'),graze=[].slice.call(d.querySelectorAll('.ms.graze')),q=false;
  function frame(){
    q=false;var vh=innerHeight;
    nav.classList.toggle('on',scrollY>40);
    spl.forEach(function(e){var r=e.getBoundingClientRect();if(r.top<vh&&r.bottom>0)e.style.setProperty('--p',(8+84*cl(1-r.top/vh)).toFixed(1)+'%')});
    if(!rm)par.forEach(function(e){var r=e.getBoundingClientRect();if(r.top<vh&&r.bottom>0)e.style.transform='translate3d(0,'+((r.top+r.height/2-vh/2)*-0.022).toFixed(1)+'px,0)'});
    if(rail){var on=d.querySelector('#film .panel.on');var c=on?on.dataset.c:'';[].forEach.call(rail.children,function(s){s.classList.toggle('on',s.dataset.c===c)})}
    if(cut){var r=cut.getBoundingClientRect(),k=rm?1:cl((vh*.85-r.top)/(vh*.85)),b=cut.querySelector('.dieb');
      cut.querySelector('path').setAttribute('stroke-dashoffset',1-cl(k/.8));b.style.setProperty('--k',cl((k-.75)/.25).toFixed(2))}
    graze.forEach(function(g){var r=g.getBoundingClientRect();if(r.top<vh&&r.bottom>0)g.style.setProperty('--py',((r.top/vh)*9).toFixed(2)+'%')});
  }
  function ask(){if(!q){q=true;requestAnimationFrame(frame)}}
  addEventListener('scroll',ask,{passive:true});addEventListener('resize',ask);frame();

  var bg=d.getElementById('burger');
  if(bg)bg.addEventListener('click',function(){var o=nav.classList.toggle('open');bg.setAttribute('aria-expanded',o)});

  // light follows the pointer across material surfaces
  d.querySelectorAll('[data-light]').forEach(function(t){t.addEventListener('pointermove',function(e){var b=t.getBoundingClientRect();
    t.style.setProperty('--mx',((e.clientX-b.left)/b.width*100).toFixed(1)+'%');t.style.setProperty('--my',((e.clientY-b.top)/b.height*100).toFixed(1)+'%')},{passive:true})});
  var tilt=d.querySelector('.whero .float');
  if(tilt&&!rm)addEventListener('pointermove',function(e){tilt.style.setProperty('--mx-n',(e.clientX/innerWidth).toFixed(3));tilt.style.setProperty('--my-n',(e.clientY/innerHeight).toFixed(3))},{passive:true});

  // calls to action lean a few pixels toward the cursor
  if(!rm&&matchMedia('(pointer:fine)').matches)d.querySelectorAll('.cta').forEach(function(c){
    c.addEventListener('pointermove',function(e){var b=c.getBoundingClientRect();c.style.transform='translate('+((e.clientX-b.left-b.width/2)*.14).toFixed(1)+'px,'+((e.clientY-b.top-b.height/2)*.28).toFixed(1)+'px)'});
    c.addEventListener('pointerleave',function(){c.style.transform=''})});

  // reveal by mask, curves that draw, numbers that settle
  if('IntersectionObserver' in window&&!rm){
    root.classList.add('js');
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(!e.isIntersecting)return;var t=e.target;t.classList.add('in');io.unobserve(t);
      if(t.dataset.count){var n=+t.dataset.count,from=n>100?n-13:0,t0=performance.now(),suf=t.dataset.suf||'';
        (function tick(now){var k=cl((now-t0)/1700);k=1-Math.pow(1-k,3);t.textContent=Math.round(from+(n-from)*k)+suf;if(k<1)requestAnimationFrame(tick)})(t0)}})},{rootMargin:'0px 0px -8% 0px'});
    d.querySelectorAll('.rv,.curve,[data-count]').forEach(function(e){io.observe(e)});
  }else d.querySelectorAll('.curve').forEach(function(e){e.classList.add('in')});

  // material lab
  d.querySelectorAll('.lab').forEach(function(lab){var bs=lab.querySelectorAll('.tabs button'),cap=lab.querySelector('.cap .mi');
    function pick(t){bs.forEach(function(b){b.setAttribute('aria-selected',b.dataset.t===t)});
      lab.querySelectorAll('.stage2 [data-t],.list [data-t]').forEach(function(e){e.classList.toggle('on',e.dataset.t===t)});
      var b=lab.querySelector('.tabs button[data-t="'+t+'"]');cap.textContent=b.dataset.cap}
    bs.forEach(function(b){b.addEventListener('click',function(){pick(b.dataset.t)});b.addEventListener('pointerenter',function(){if(matchMedia('(pointer:fine)').matches)pick(b.dataset.t)})})});

  // anatomy: rows and pins answer each other
  var A=d.getElementById('anat');
  if(A){var set=function(i,on){A.querySelectorAll('[data-i="'+i+'"]').forEach(function(e){e.classList.toggle('on',on)})};
    A.querySelectorAll('[data-i]').forEach(function(e){e.addEventListener('pointerenter',function(){set(e.dataset.i,true)});e.addEventListener('pointerleave',function(){set(e.dataset.i,false)})})}
})();
