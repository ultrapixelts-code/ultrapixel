/* Ingresso nello studio (pagina /prova): un atelier di etichette di classe.
   Luce calda dall'alto, pulviscolo dorato, un'etichetta in carta cotone che sale nella luce, cornice e monogramma in foil oro
   che si stampano, testo in rilievo, riflesso sull'oro, un solo passaggio della scansione AI, poi la luce si apre sullo studio.
   Una volta per visita; si salta con un clic o un tasto. */
(function(){
var de=document.documentElement;
function fine(){de.classList.remove('pre');try{sessionStorage.setItem('up_intro','1')}catch(e){}}
if(!de.classList.contains('pre'))return;
var LG=(window.UP&&UP.LG)||'it';
var TX={it:{a:'Benvenuti',b:'nell’atelier',c:'Etichette d’autore',d:'San Dorligo della Valle · Trieste',s:'Entra'},
        en:{a:'Welcome',b:'to the atelier',c:'Labels of distinction',d:'San Dorligo della Valle · Trieste · Italy',s:'Enter'},
        fr:{a:'Bienvenue',b:'à l’atelier',c:'Étiquettes d’exception',d:'San Dorligo della Valle · Trieste · Italie',s:'Entrer'},
        de:{a:'Willkommen',b:'im Atelier',c:'Etiketten mit Klasse',d:'San Dorligo della Valle · Triest · Italien',s:'Eintreten'}}[LG]||null;
if(!TX)TX={a:'Benvenuti',b:'nell’atelier',c:'Etichette d’autore',d:'San Dorligo della Valle · Trieste',s:'Entra'};
var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;

var css=document.createElement('style');css.textContent=
'#intro{position:fixed;inset:0;z-index:100;cursor:pointer;background:#0C0A08;overflow:hidden;transition:opacity 1s ease}'+
'#intro.out{opacity:0}'+
'#intro .lamp{position:absolute;left:50%;top:-30vh;width:150vmax;height:130vh;transform:translateX(-50%);opacity:0;animation:ifade 1.6s .1s ease forwards;'+
' background:radial-gradient(ellipse 30% 55% at 50% 30%,rgba(255,226,170,.30),rgba(255,214,150,.10) 45%,transparent 70%)}'+
'#intro .vig{position:absolute;inset:0;background:radial-gradient(ellipse 75% 70% at 50% 45%,transparent 40%,rgba(0,0,0,.65))}'+
'#intro canvas{position:absolute;inset:0;width:100%;height:100%}'+
'#intro .stage{position:absolute;left:50%;top:50%;width:min(64vmin,430px);aspect-ratio:34/46;transform:translate(-50%,-44%) perspective(1200px) rotateX(9deg);opacity:0;'+
' animation:irise 1.6s .5s cubic-bezier(.2,.8,.2,1) forwards;filter:drop-shadow(0 30px 40px rgba(0,0,0,.55)) drop-shadow(0 6px 10px rgba(0,0,0,.4))}'+
'#intro.out .stage{transform:translate(-50%,-50%) scale(1.06);transition:transform 1.1s cubic-bezier(.4,0,.2,1)}'+
'#intro svg{width:100%;height:100%;display:block;overflow:visible}'+
'#intro .draw{stroke-dasharray:1;stroke-dashoffset:1;animation:idraw 1.5s cubic-bezier(.6,0,.2,1) forwards}'+
'#intro .st{opacity:0;animation:istamp .7s cubic-bezier(.2,.9,.3,1) forwards;transform-box:fill-box;transform-origin:center}'+
'#intro .ai{opacity:0}#intro .ai.go{animation:iscan 1.3s cubic-bezier(.5,0,.5,1) forwards}'+
'#intro .sig{position:absolute;left:50%;bottom:34px;transform:translateX(-50%);display:flex;gap:9px;opacity:0;animation:ifade 1s 3.4s forwards}#intro .sig i{width:8px;height:8px}'+
'#intro .skip{position:absolute;right:26px;bottom:26px;border:1px solid rgba(232,212,170,.35);background:none;color:rgba(232,212,170,.8);border-radius:999px;padding:8px 16px;font:400 10px var(--mono);letter-spacing:.2em;text-transform:uppercase;cursor:pointer}'+
'#intro .bloom{position:absolute;inset:0;background:radial-gradient(circle at 50% 50%,#FFF8EA,#F4F4F0 60%);opacity:0;transition:opacity .9s ease}#intro.light .bloom{opacity:1}'+
'@keyframes ifade{to{opacity:1}}@keyframes idraw{to{stroke-dashoffset:0}}'+
'@keyframes irise{from{opacity:0;transform:translate(-50%,-38%) perspective(1200px) rotateX(18deg)}to{opacity:1;transform:translate(-50%,-50%) perspective(1200px) rotateX(0)}}'+
'@keyframes istamp{0%{opacity:0;transform:scale(1.035)}60%{opacity:1}100%{opacity:1;transform:scale(1)}}'+
'@keyframes iscan{0%{opacity:0;transform:translateY(0)}15%{opacity:.85}85%{opacity:.85}100%{opacity:0;transform:translateY(440px)}}';
document.head.appendChild(css);

/* l'etichetta: carta cotone, foil oro, testi in rilievo */
var G='url(#ugold)',D=function(s){return 'style="animation-delay:'+s+'s"'};
var svg='<svg viewBox="0 0 340 460" xmlns="http://www.w3.org/2000/svg"><defs>'+
 '<linearGradient id="ugold" gradientUnits="userSpaceOnUse" x1="-340" y1="0" x2="0" y2="460">'+
  '<stop offset="0" stop-color="#8A6424"/><stop offset=".30" stop-color="#C79A45"/><stop offset=".44" stop-color="#F6E3A8"/><stop offset=".50" stop-color="#FFF6D8"/><stop offset=".56" stop-color="#E9CB7C"/><stop offset=".72" stop-color="#B98A3A"/><stop offset="1" stop-color="#7C5A20"/>'+
  '<animateTransform attributeName="gradientTransform" type="translate" from="-120 0" to="560 0" begin="2.6s" dur="2.2s" fill="freeze" calcMode="spline" keySplines=".4 0 .2 1"/></linearGradient>'+
 '<linearGradient id="uspec" x1="0" x2="1"><stop offset="0" stop-color="#22B8D6" stop-opacity="0"/><stop offset=".2" stop-color="#22B8D6"/><stop offset=".45" stop-color="#6F5BE8"/><stop offset=".7" stop-color="#D9438F"/><stop offset=".85" stop-color="#EBA43A"/><stop offset="1" stop-color="#EBA43A" stop-opacity="0"/></linearGradient>'+
 '<filter id="upaper" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 .45 0 0 0 0 .40 0 0 0 0 .32 0 0 0 -1.2 .9"/><feComposite in2="SourceGraphic" operator="in"/></filter>'+
 '<filter id="uemb" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur in="SourceAlpha" stdDeviation=".5" result="b"/><feOffset in="b" dx="-.6" dy="-.6" result="h"/><feOffset in="b" dx=".8" dy=".9" result="s"/>'+
  '<feFlood flood-color="#fff" flood-opacity=".9"/><feComposite in2="h" operator="in" result="hi"/><feFlood flood-color="#4a3a20" flood-opacity=".45"/><feComposite in2="s" operator="in" result="sh"/>'+
  '<feMerge><feMergeNode in="sh"/><feMergeNode in="hi"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'+
 '<filter id="ufoil"><feDropShadow dx=".4" dy=".6" stdDeviation=".35" flood-color="#3b2a0c" flood-opacity=".55"/></filter>'+
 '<clipPath id="ulab"><rect x="0" y="0" width="340" height="460" rx="14"/></clipPath></defs>'+
 '<g clip-path="url(#ulab)"><rect width="340" height="460" fill="#F3EDE0"/><rect width="340" height="460" fill="#EFE7D6" filter="url(#upaper)" opacity=".55"/>'+
  '<rect width="340" height="460" fill="url(#ugold)" opacity=".05"/>'+
 /* cornici in foil */
 '<g fill="none" stroke="'+G+'" filter="url(#ufoil)"><rect class="draw" pathLength="1" x="18" y="18" width="304" height="424" rx="6" stroke-width="2.2" '+D(1.1)+'/>'+
  '<rect class="draw" pathLength="1" x="25" y="25" width="290" height="410" rx="3" stroke-width=".7" '+D(1.35)+'/>'+
  '<path class="draw" pathLength="1" d="M25 70h290M25 390h290" stroke-width=".6" '+D(1.6)+'/></g>'+
 /* monogramma */
 '<g filter="url(#ufoil)"><circle class="draw" pathLength="1" cx="170" cy="118" r="30" fill="none" stroke="'+G+'" stroke-width="1.6" '+D(1.7)+'/>'+
  '<circle class="draw" pathLength="1" cx="170" cy="118" r="25" fill="none" stroke="'+G+'" stroke-width=".5" '+D(1.85)+'/>'+
  '<text class="st" x="170" y="129" text-anchor="middle" font-family="Bodoni Moda,Didot,serif" font-size="30" font-weight="600" fill="'+G+'" '+D(2.2)+'>U<tspan font-style="italic" font-weight="500" dx="-3">P</tspan></text></g>'+
 '<text class="st" x="170" y="54" text-anchor="middle" font-family="DM Mono,monospace" font-size="8.5" letter-spacing="5" fill="#7A6A4E" '+D(2.0)+'>ULTRAPIXEL</text>'+
 /* saluto: rilievo a secco + foil */
 '<g filter="url(#uemb)"><text class="st" x="170" y="222" text-anchor="middle" font-family="Bodoni Moda,Didot,serif" font-style="italic" font-size="'+(TX.a.length>9?38:44)+'" font-weight="500" fill="#2B2620" '+D(2.4)+'>'+TX.a+'</text>'+
  '<text class="st" x="170" y="256" text-anchor="middle" font-family="Bodoni Moda,Didot,serif" font-size="19" font-weight="500" letter-spacing="1.5" fill="#2B2620" '+D(2.6)+'>'+TX.b+'</text></g>'+
 '<g filter="url(#ufoil)"><path class="draw" pathLength="1" d="M108 286h46l16-7 16 7h46" fill="none" stroke="'+G+'" stroke-width="1.2" '+D(2.7)+'/>'+
  '<path class="st" d="M170 279l4 7-4 7-4-7z" fill="'+G+'" '+D(3.0)+'/></g>'+
 '<text class="st" x="170" y="326" text-anchor="middle" font-family="Archivo,sans-serif" font-size="10" letter-spacing="4.2" fill="#5E5241" '+D(2.9)+'>'+TX.c.toUpperCase()+'</text>'+
 '<text class="st" x="170" y="414" text-anchor="middle" font-family="DM Mono,monospace" font-size="6.6" letter-spacing="2.2" fill="#8B7D63" '+D(3.1)+'>'+TX.d.toUpperCase()+'</text>'+
 '<text class="st" x="170" y="363" text-anchor="middle" font-family="Bodoni Moda,Didot,serif" font-style="italic" font-size="14" font-weight="600" fill="#A97C2E" filter="url(#ufoil)" '+D(3.2)+'>MMXIII</text>'+
 /* un solo passaggio della scansione AI */
 '<g class="ai"><rect x="0" y="6" width="340" height="1.4" fill="url(#uspec)"/><rect x="0" y="-16" width="340" height="22" fill="url(#uspec)" opacity=".10"/></g>'+
 '</g></svg>';

var o=document.createElement('div');o.id='intro';o.setAttribute('aria-hidden','true');
o.innerHTML='<div class="lamp"></div><canvas></canvas><div class="stage">'+svg+'</div><div class="vig"></div>'+
 '<div class="sig"><i style="background:#00A0E3"></i><i style="background:#E6007E"></i><i style="background:#FFE600"></i><i style="background:#F4F4F0"></i></div>'+
 '<div class="bloom"></div><button class="skip" type="button">'+TX.s+' →</button>';
document.body.appendChild(o);de.classList.remove('pre');

var done=false,raf=0;
function chiudi(){if(done)return;done=true;o.classList.add('light');
  setTimeout(function(){o.classList.add('out')},650);setTimeout(function(){cancelAnimationFrame(raf);o.remove();fine()},1700)}
o.addEventListener('click',chiudi);document.addEventListener('keydown',function k(){document.removeEventListener('keydown',k);chiudi()});
if(RM){[].forEach.call(o.querySelectorAll('.draw,.st'),function(e){e.style.animation='none';e.style.opacity=1;e.style.strokeDashoffset=0});o.querySelector('.stage').style.cssText+='animation:none;opacity:1;transform:translate(-50%,-50%)';setTimeout(chiudi,2200);return}

/* pulviscolo dorato nel fascio di luce */
var cv=o.querySelector('canvas'),cx=cv.getContext('2d'),dpr=Math.min(2,window.devicePixelRatio||1),w,h,M=[];
function setup(){w=innerWidth;h=innerHeight;cv.width=w*dpr;cv.height=h*dpr;cx.setTransform(dpr,0,0,dpr,0,0);M=[];
  var n=w<700?70:150;for(var i=0;i<n;i++)M.push({x:w/2+(Math.random()-.5)*w*.7,y:Math.random()*h,r:.4+Math.random()*1.6,v:.08+Math.random()*.25,p:Math.random()*6.3,a:.15+Math.random()*.55})}
setup();addEventListener('resize',function(){if(!done)setup()});
var t0=performance.now();
function frame(now){var t=(now-t0)/1000;cx.clearRect(0,0,w,h);
  for(var i=0;i<M.length;i++){var m=M[i];m.y-=m.v;m.x+=Math.sin(t*.6+m.p)*.18;if(m.y<-5){m.y=h+5}
    var cone=Math.max(0,1-Math.abs(m.x-w/2)/(w*.33)),fl=.6+.4*Math.sin(t*1.7+m.p*3);
    cx.globalAlpha=m.a*cone*fl*Math.min(1,t/1.2);cx.fillStyle='#F4D99A';cx.beginPath();cx.arc(m.x,m.y,m.r,0,6.283);cx.fill()}
  cx.globalAlpha=1;if(!done||o.isConnected)raf=requestAnimationFrame(frame)}
raf=requestAnimationFrame(frame);
setTimeout(function(){var a=o.querySelector('.ai');if(a)a.classList.add('go')},3700);
(document.fonts&&document.fonts.load?Promise.all([document.fonts.load('italic 500 40px "Bodoni Moda"'),document.fonts.load('500 20px "Bodoni Moda"')]).catch(function(){}):Promise.resolve());
setTimeout(chiudi,5900);
})();
