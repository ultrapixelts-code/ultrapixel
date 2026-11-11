/* Ingresso nello studio (pagina /prova) — "Starlight".
   Nero laccato, un cielo di stelle (i pixel) che si accende piano, poi le stelle scorrono e compongono ULTRAPIXEL in argento,
   con il riflesso sul pavimento lucido, una linea di luce, un riflesso che attraversa la scritta e le portiere nere con il filetto
   che si aprono sullo studio. Lento, silenzioso, essenziale. Una volta per visita; si salta con un clic o un tasto. */
(function(){
var de=document.documentElement;
function fine(){de.classList.remove('pre');try{sessionStorage.setItem('up_intro','1')}catch(e){}}
if(!de.classList.contains('pre'))return;
var LG=(window.UP&&UP.LG)||'it';
var TX={it:{g:'Benvenuti',s:'Atelier di etichette',k:'Entra'},en:{g:'Welcome',s:'The label atelier',k:'Enter'},
        fr:{g:'Bienvenue',s:'L’atelier des étiquettes',k:'Entrer'},de:{g:'Willkommen',s:'Das Etiketten-Atelier',k:'Eintreten'}}[LG]||{g:'Benvenuti',s:'Atelier di etichette',k:'Entra'};
var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
var WORD='ULTRAPIXEL';

var css=document.createElement('style');css.textContent=
'#intro{position:fixed;inset:0;z-index:100;cursor:pointer;overflow:hidden}'+
'#intro .door{position:absolute;top:0;bottom:0;width:50.2%;background:radial-gradient(120% 80% at 50% 40%,#0B0C0F,#040405 70%);transition:transform 1.6s cubic-bezier(.7,0,.15,1)}'+
'#intro .door.l{left:0}#intro .door.r{right:0}'+
/* il filetto: la linea sottile dipinta a mano lungo la fiancata */
'#intro .door i{position:absolute;left:0;right:0;top:78%;height:1px;opacity:0;transition:opacity 1.2s;background:linear-gradient(90deg,transparent,rgba(214,206,190,.28) 30%,rgba(214,206,190,.28) 70%,transparent)}'+
'#intro.ready .door i{opacity:1}'+
'#intro.open .door.l{transform:translateX(-101%)}#intro.open .door.r{transform:translateX(101%)}'+
'#intro .door.l::after,#intro .door.r::after{content:"";position:absolute;top:0;bottom:0;width:1px;background:linear-gradient(180deg,transparent,rgba(230,224,212,.5),transparent);opacity:0;transition:opacity .6s}'+
'#intro .door.l::after{right:0}#intro .door.r::after{left:0}#intro.open .door::after{opacity:1}'+
'#intro canvas{position:absolute;inset:0;width:100%;height:100%;transition:opacity 1.1s ease}'+
'#intro .ui{position:absolute;inset:0;pointer-events:none;transition:opacity .9s ease}#intro.open .ui,#intro.open canvas{opacity:0}'+
'#intro .g{position:absolute;left:0;right:0;text-align:center;font:italic 400 clamp(18px,2.2vw,26px)/1 "Bodoni Moda",Didot,serif;letter-spacing:.06em;color:#D9D2C4;opacity:0;transition:opacity 2s ease}'+
'#intro .s{position:absolute;left:0;right:0;text-align:center;font:400 clamp(9px,.9vw,11px)/1 var(--mono);letter-spacing:.55em;text-transform:uppercase;color:#9A958B;opacity:0;transition:opacity 2s ease;padding-left:.55em}'+
'#intro .on{opacity:1}'+
'#intro .line{position:absolute;left:50%;height:1px;width:0;transform:translateX(-50%);background:linear-gradient(90deg,transparent,rgba(236,231,220,.9),transparent);transition:width 2.2s cubic-bezier(.3,0,.1,1);box-shadow:0 0 12px rgba(236,231,220,.35)}'+
'#intro .line.on{width:min(62vw,720px)}'+
'#intro .cmyk{position:absolute;left:50%;transform:translateX(-50%);display:flex;gap:7px;opacity:0;transition:opacity 1.6s ease}#intro .cmyk i{width:5px;height:5px}'+
'#intro .skip{position:absolute;right:30px;bottom:30px;pointer-events:auto;border:0;border-bottom:1px solid rgba(217,210,196,.35);background:none;color:rgba(217,210,196,.75);padding:6px 0;font:400 10px var(--mono);letter-spacing:.3em;text-transform:uppercase;cursor:pointer;opacity:0;transition:opacity 1.5s 1s}'+
'#intro.ready .skip{opacity:1}';
document.head.appendChild(css);

var o=document.createElement('div');o.id='intro';o.setAttribute('aria-hidden','true');
o.innerHTML='<div class="door l"><i></i></div><div class="door r"><i></i></div><canvas></canvas><div class="ui">'+
 '<div class="g">'+TX.g+'</div><div class="line"></div><div class="s">'+TX.s+'</div>'+
 '<div class="cmyk"><i style="background:#00A0E3"></i><i style="background:#E6007E"></i><i style="background:#FFE600"></i><i style="background:#E9E4DA"></i></div>'+
 '<button class="skip" type="button">'+TX.k+'</button></div>';
document.body.appendChild(o);de.classList.remove('pre');
requestAnimationFrame(function(){o.classList.add('ready')});

var done=false,raf=0;
function chiudi(){if(done)return;done=true;o.classList.add('open');setTimeout(function(){cancelAnimationFrame(raf);o.remove();fine()},1700)}
o.addEventListener('click',chiudi);document.addEventListener('keydown',function k(){document.removeEventListener('keydown',k);chiudi()});

var cv=o.querySelector('canvas'),cx=cv.getContext('2d'),dpr=Math.min(2,window.devicePixelRatio||1),w,h,P=[],base=0,fs=0,wx0=0,wx1=0;
function layout(){
  var gEl=o.querySelector('.g'),sEl=o.querySelector('.s'),ln=o.querySelector('.line'),ck=o.querySelector('.cmyk');
  gEl.style.top=(base-fs*1.0-46)+'px';ln.style.top=(base+fs*.78)+'px';sEl.style.top=(base+fs*.78+26)+'px';ck.style.top=(base+fs*.78+58)+'px'}
function setup(){
  w=innerWidth;h=innerHeight;cv.width=w*dpr;cv.height=h*dpr;cx.setTransform(dpr,0,0,dpr,0,0);
  var off=document.createElement('canvas'),oc=off.getContext('2d');off.width=w;off.height=h;
  var track=.36;fs=Math.min(110,w*.82/(WORD.length*(.74+track)));base=h*.47+fs*.35;
  oc.font='500 '+fs+'px Cinzel, "Bodoni Moda", serif';oc.fillStyle='#fff';oc.textBaseline='alphabetic';
  var widths=[].map.call(WORD,function(c){return oc.measureText(c).width}),tot=widths.reduce(function(a,b){return a+b},0)+track*fs*(WORD.length-1);
  if(tot>w*.86){fs*=w*.86/tot;oc.font='500 '+fs+'px Cinzel, "Bodoni Moda", serif';widths=[].map.call(WORD,function(c){return oc.measureText(c).width});tot=widths.reduce(function(a,b){return a+b},0)+track*fs*(WORD.length-1);base=h*.47+fs*.35}
  var x=(w-tot)/2;wx0=x;wx1=x+tot;for(var i=0;i<WORD.length;i++){oc.fillText(WORD[i],x,base);x+=widths[i]+track*fs}
  var d=oc.getImageData(0,0,w,h).data,step=fs>60?1.6:1.2,T=[];
  for(var y=Math.max(0,Math.floor(base-fs*1.1));y<Math.min(h,base+fs*.3);y+=step)for(var xx=Math.floor(wx0)-2;xx<wx1+2;xx+=step){var a=d[((y|0)*w+(xx|0))*4+3];if(a>70)T.push([xx,y])}
  for(i=T.length-1;i>0;i--){var j=Math.random()*(i+1)|0,t=T[i];T[i]=T[j];T[j]=t}
  var nT=Math.min(T.length,w<700?3200:7000),nS=w<700?380:900;P=[];
  var TINT=['#00A0E3','#E6007E','#FFE600'];
  for(i=0;i<nT+nS;i++){var sx=Math.random()*w,sy=Math.random()*h*.92;
    P.push({x:sx,y:sy,tx:i<nT?T[i][0]:sx,ty:i<nT?T[i][1]:sy,word:i<nT,r:i<nT?(fs>60?.85:.62):.35+Math.random()*.85,
      tw:Math.random()*6.28,sp:.6+Math.random()*1.8,on:Math.random()*1.4,d:Math.random()*.9,c:Math.random()<.06?TINT[(Math.random()*3)|0]:null})}
  layout()}
function ease(t){return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2}
var t0;
function frame(now){var t=(now-t0)/1000;cx.clearRect(0,0,w,h);cx.globalCompositeOperation='lighter';
  var sweep=(t-4.3)/1.6,sx=wx0-80+(wx1-wx0+160)*sweep;
  for(var r=0;r<2;r++){   // r=1: riflesso sul pavimento lucido
    for(var i=0;i<P.length;i++){var p=P[i],a=Math.max(0,Math.min(1,(t-p.on)/1.2)),tw=.55+.45*Math.sin(t*p.sp+p.tw);
      var k=p.word?ease(Math.max(0,Math.min(1,(t-1.7-p.d)/1.9))):0,x=p.x+(p.tx-p.x)*k,y=p.y+(p.ty-p.y)*k,al=a*(p.word?(tw*(1-k)+k*1.15):tw*.8);
      if(p.word&&k>=1&&sweep>0&&sweep<1){var dx=Math.abs(x-sx);if(dx<60)al=Math.min(1.6,al+(1-dx/60)*.9)}
      if(r===1){if(!p.word||k<.6)continue;y=2*base+fs*.12-y;al*=.2*Math.max(0,1-(y-base)/(fs*.62))}
      if(al<=.01)continue;cx.globalAlpha=Math.min(1,al);cx.fillStyle=p.c&&k<1?p.c:'#ECE7DC';
      var rr=p.r*(p.word&&k<1?1+(1-k)*.6:1);cx.fillRect(x-rr,y-rr,rr*2,rr*2)}}
  cx.globalCompositeOperation='source-over';cx.globalAlpha=1;
  if(o.isConnected)raf=requestAnimationFrame(frame)}
function start(){setup();t0=performance.now();raf=requestAnimationFrame(frame);
  var q=function(s){return o.querySelector(s)};
  setTimeout(function(){q('.g').classList.add('on')},3300);
  setTimeout(function(){q('.line').classList.add('on')},3500);
  setTimeout(function(){q('.s').classList.add('on')},4300);
  setTimeout(function(){q('.cmyk').classList.add('on')},5000);
  setTimeout(chiudi,7400)}
if(RM){o.querySelector('.g').classList.add('on');o.querySelector('.s').classList.add('on');setTimeout(chiudi,1600);return}
addEventListener('resize',function(){if(!done)setup()});
(document.fonts&&document.fonts.load?Promise.race([document.fonts.load('500 80px Cinzel'),new Promise(function(r){setTimeout(r,900)})]):Promise.resolve()).then(start,start);
})();
