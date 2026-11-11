/* Ingresso nello studio (pagina /prova): pixel CMYK che compongono il benvenuto, logo, scansione e apertura delle ante dell'atelier.
   Una volta per sessione del browser; si salta con un clic o con un tasto. */
(function(){
var de=document.documentElement;
function fine(){de.classList.remove('pre');try{sessionStorage.setItem('up_intro','1')}catch(e){}}
if(!de.classList.contains('pre'))return;
var LG=(window.UP&&UP.LG)||'it';
var W={it:['Benvenuti','nello studio'],en:['Welcome','to the studio'],fr:['Bienvenue','dans l’atelier'],de:['Willkommen','im Atelier']}[LG]||['Benvenuti','nello studio'];
var SUB={it:'Atelier grafico UltraPixel · AI',en:'UltraPixel design atelier · AI',fr:'Atelier graphique UltraPixel · IA',de:'UltraPixel Grafik-Atelier · KI'}[LG];
var SKIP={it:'Salta',en:'Skip',fr:'Passer',de:'Überspringen'}[LG];
var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;

var css=document.createElement('style');css.textContent=
'#intro{position:fixed;inset:0;z-index:100;pointer-events:auto;cursor:pointer;font-family:var(--body)}'+
'#intro .door{position:absolute;top:0;bottom:0;width:50.5%;background:#0B0D0F;transition:transform 1.15s cubic-bezier(.77,0,.18,1)}#intro .door.l{left:0}#intro .door.r{right:0}'+
'#intro .door::after{content:"";position:absolute;top:0;bottom:0;width:1px;opacity:0;transition:opacity .4s;background:linear-gradient(180deg,#22B8D6,#6F5BE8,#D9438F,#EBA43A)}#intro .door.l::after{right:0}#intro .door.r::after{left:0}'+
'#intro.open .door::after{opacity:1;box-shadow:0 0 18px 2px rgba(111,91,232,.6)}#intro.open .door.l{transform:translateX(-101%)}#intro.open .door.r{transform:translateX(101%)}'+
'#intro canvas{position:absolute;inset:0;width:100%;height:100%;transition:opacity .5s}'+
'#intro .ui{position:absolute;inset:0;pointer-events:none;transition:opacity .45s}#intro.open .ui,#intro.open canvas{opacity:0}'+
'#intro .crop{position:absolute;width:26px;height:26px;border:1px solid rgba(167,173,176,.7);opacity:0;animation:ifade .6s .15s forwards}'+
'#intro .crop.a{left:22px;top:22px;border-width:1px 0 0 1px}#intro .crop.b{right:22px;top:22px;border-width:1px 1px 0 0}#intro .crop.c{left:22px;bottom:22px;border-width:0 0 1px 1px}#intro .crop.d{right:22px;bottom:22px;border-width:0 1px 1px 0}'+
'#intro .hl,#intro .vl{position:absolute;background:rgba(167,173,176,.28)}#intro .hl{left:0;right:0;top:50%;height:1px;transform:scaleX(0);animation:ix .9s .1s cubic-bezier(.6,0,.2,1) forwards}#intro .vl{top:0;bottom:0;left:50%;width:1px;transform:scaleY(0);animation:iy .9s .25s cubic-bezier(.6,0,.2,1) forwards}'+
'#intro .reg{position:absolute;width:30px;height:30px;left:50%;top:22px;margin-left:-15px;opacity:0;animation:ifade .5s .4s forwards}#intro .reg.b2{top:auto;bottom:22px}'+
'#intro .mk{position:absolute;left:50%;top:calc(50% + min(15vw,150px));transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:16px}'+
'#intro .sq{display:flex;gap:10px}#intro .sq i{width:14px;height:14px;transform:scale(0) rotate(45deg);animation:ipop .5s cubic-bezier(.3,1.6,.5,1) forwards}'+
'#intro .sub{font:400 12px var(--mono);letter-spacing:.32em;text-transform:uppercase;color:#E9E9E4;min-height:16px;white-space:nowrap}#intro .sub .cursor{background:#E9E9E4}'+
'#intro .meta{position:absolute;left:28px;top:60px;font:400 10px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:#686D71;line-height:1.8;opacity:0;animation:ifade .6s .5s forwards}'+
'#intro .meta.r{left:auto;right:28px;text-align:right}'+
'#intro .scan{position:absolute;left:0;right:0;height:2px;top:0;opacity:0;background:linear-gradient(90deg,transparent,#22B8D6 15%,#6F5BE8 40%,#D9438F 65%,#EBA43A 85%,transparent);box-shadow:0 0 24px 4px rgba(111,91,232,.45)}'+
'#intro .scan.go{animation:iscan 1.1s cubic-bezier(.5,0,.5,1) forwards}'+
'#intro .skip{position:absolute;right:26px;bottom:60px;pointer-events:auto;border:1px solid rgba(167,173,176,.4);background:none;color:#A7ADB0;border-radius:999px;padding:7px 14px;font:400 10px var(--mono);letter-spacing:.16em;text-transform:uppercase;cursor:pointer}'+
'@keyframes ifade{to{opacity:1}}@keyframes ix{to{transform:scaleX(1)}}@keyframes iy{to{transform:scaleY(1)}}@keyframes ipop{to{transform:scale(1) rotate(0)}}'+
'@keyframes iscan{0%{opacity:0;transform:translateY(18vh)}12%{opacity:1}88%{opacity:1}100%{opacity:0;transform:translateY(82vh)}}'+
'@media(max-width:640px){#intro .meta{display:none}#intro .sub{font-size:10px;letter-spacing:.2em}}';
document.head.appendChild(css);

var o=document.createElement('div');o.id='intro';o.setAttribute('aria-hidden','true');
var reg='<svg viewBox="0 0 30 30" fill="none" stroke="#A7ADB0" stroke-width=".8"><circle cx="15" cy="15" r="7"/><path d="M15 0v30M0 15h30"/><circle cx="15" cy="15" r="3" fill="#A7ADB0"/></svg>';
o.innerHTML='<div class="door l"></div><div class="door r"></div><canvas></canvas><div class="ui">'+
 '<i class="hl"></i><i class="vl"></i><i class="crop a"></i><i class="crop b"></i><i class="crop c"></i><i class="crop d"></i>'+
 '<div class="reg">'+reg+'</div><div class="reg b2">'+reg+'</div>'+
 '<div class="meta">UP / Studio AI · 001<br>CMYK · 1200 dpi<br>45.6503° N 13.8170° E</div><div class="meta r">Xeikon CX3 · Cartes<br>Foil · Rilievo · Serigrafia<br>San Dorligo della Valle</div>'+
 '<div class="scan"></div><div class="mk"><div class="sq"><i style="background:#00A0E3;animation-delay:2.05s"></i><i style="background:#E6007E;animation-delay:2.17s"></i><i style="background:#FFE600;animation-delay:2.29s"></i><i style="background:#F4F4F0;animation-delay:2.41s"></i></div><div class="sub"></div></div>'+
 '<button class="skip" type="button">'+SKIP+'</button></div>';
document.body.appendChild(o);de.classList.remove('pre');

var done=false,raf=0;
function chiudi(){if(done)return;done=true;o.classList.add('open');setTimeout(function(){cancelAnimationFrame(raf);o.remove();fine()},1250)}
o.addEventListener('click',chiudi);document.addEventListener('keydown',function k(){document.removeEventListener('keydown',k);chiudi()});
if(RM){var s=o.querySelector('.sub');s.textContent=W.join(' ');setTimeout(chiudi,900);return}

/* pixel che compongono la scritta */
var cv=o.querySelector('canvas'),cx=cv.getContext('2d'),dpr=Math.min(2,window.devicePixelRatio||1),w,h,P=[];
var COL=['#00A0E3','#E6007E','#FFE600','#F4F4F0','#6F5BE8','#22B8D6'];
function setup(){w=innerWidth;h=innerHeight;cv.width=w*dpr;cv.height=h*dpr;cx.setTransform(dpr,0,0,dpr,0,0);
  var off=document.createElement('canvas'),oc=off.getContext('2d');off.width=w;off.height=h;
  var fs=Math.min(w/(Math.max(W[0].length,W[1].length)*.56),h*.15,150);
  oc.fillStyle='#fff';oc.textAlign='center';oc.textBaseline='middle';oc.font='800 '+fs+'px Archivo, "Helvetica Neue", Arial, sans-serif';
  try{oc.font='800 '+fs+'px Archivo'}catch(e){}
  var mw=Math.max(oc.measureText(W[0].toUpperCase()).width,oc.measureText(W[1].toUpperCase()).width);if(mw>w*.86){fs*=w*.86/mw;oc.font='800 '+fs+'px Archivo, "Helvetica Neue", Arial, sans-serif'}
  oc.fillText(W[0].toUpperCase(),w/2,h/2-fs*.52);oc.fillText(W[1].toUpperCase(),w/2,h/2+fs*.46);
  var d=oc.getImageData(0,0,w,h).data,step=Math.max(3,Math.round(fs/26)),T=[];
  for(var y=0;y<h;y+=step)for(var x=0;x<w;x+=step)if(d[(y*w+x)*4+3]>130)T.push([x,y]);
  var n=Math.min(T.length,w<700?2600:5200);for(var i=T.length-1;i>0;i--){var j=Math.random()*(i+1)|0,t=T[i];T[i]=T[j];T[j]=t}
  P=[];for(i=0;i<n;i++){var a=Math.random()*Math.PI*2,r=Math.max(w,h)*(.55+Math.random()*.6);
    P.push({x:w/2+Math.cos(a)*r,y:h/2+Math.sin(a)*r,tx:T[i][0],ty:T[i][1],s:step*.62*(.7+Math.random()*.6),c:COL[(Math.random()*COL.length)|0],d:Math.random()*.55,f:Math.random()})}}
var t0=performance.now();
function ease(t){return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2}
function frame(now){var t=(now-t0)/1000;cx.clearRect(0,0,w,h);
  for(var i=0;i<P.length;i++){var p=P[i],k=Math.max(0,Math.min(1,(t-.25-p.d)/1.25)),e=ease(k),x=p.x+(p.tx-p.x)*e,y=p.y+(p.ty-p.y)*e;
    if(k>=1){x+=Math.sin(t*3+p.f*9)*.35;y+=Math.cos(t*2.6+p.f*7)*.35}
    var col=k<1?p.c:(t>1.95&&t<2.9&&Math.abs((y/h)-((t-1.95)/0.95))<.05?COL[(p.f*4)|0]:'#F4F4F0');
    cx.globalAlpha=Math.min(1,.15+k*1.1);cx.fillStyle=col;cx.fillRect(x,y,p.s*(k<1?1.4-e*.4:1),p.s*(k<1?1.4-e*.4:1))}
  cx.globalAlpha=1;if(!done)raf=requestAnimationFrame(frame)}
function start(){setup();t0=performance.now();raf=requestAnimationFrame(frame);
  setTimeout(function(){o.querySelector('.scan').classList.add('go')},1900);
  var sub=o.querySelector('.sub'),j=0;setTimeout(function ty(){if(done)return;sub.textContent=SUB.slice(0,++j);var c=document.createElement('span');c.className='cursor';sub.appendChild(c);if(j<SUB.length)setTimeout(ty,34)},2550);
  setTimeout(chiudi,4700)}
(document.fonts&&document.fonts.load?Promise.race([document.fonts.load('800 80px Archivo'),new Promise(function(r){setTimeout(r,700)})]):Promise.resolve()).then(start,start);
addEventListener('resize',function(){if(!done)setup()});
})();
