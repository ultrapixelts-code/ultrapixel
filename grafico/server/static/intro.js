/* Ingresso nello studio (pagina /prova) — "Starlight", in due atti.
   I.  Nero laccato, un cielo di stelle (i pixel) che si accende piano e compone ULTRAPIXEL in argento, con il riflesso sul pavimento lucido.
   II. Le stelle si ricompongono in un'etichetta sagomata a doppio filetto; il foil oro la attraversa come una stampa a caldo;
       compare la promessa: le etichette più belle del mondo. Poi le portiere nere con il filetto si aprono sullo studio.
   Circa 10 secondi; una volta per visita; si salta con un clic o un tasto. */
(function(){
var de=document.documentElement;
function fine(){de.classList.remove('pre');try{sessionStorage.setItem('up_intro','1')}catch(e){}}
if(!de.classList.contains('pre'))return;
var LG=(window.UP&&UP.LG)||'it';
var TX={it:{g:'Benvenuti',s:'Atelier di etichette',c:'Stampiamo le etichette più belle del mondo.',f:['Foil a caldo','Rilievo','Serigrafia'],k:'Entra'},
        en:{g:'Welcome',s:'The label atelier',c:'We print the most beautiful labels in the world.',f:['Hot foil','Embossing','Screen printing'],k:'Enter'},
        fr:{g:'Bienvenue',s:'L’atelier des étiquettes',c:'Nous imprimons les plus belles étiquettes du monde.',f:['Dorure à chaud','Gaufrage','Sérigraphie'],k:'Entrer'},
        de:{g:'Willkommen',s:'Das Etiketten-Atelier',c:'Wir drucken die schönsten Etiketten der Welt.',f:['Heißfolie','Prägung','Siebdruck'],k:'Eintreten'}}[LG];
if(!TX)TX={g:'Benvenuti',s:'Atelier di etichette',c:'Stampiamo le etichette più belle del mondo.',f:['Foil a caldo','Rilievo','Serigrafia'],k:'Entra'};
var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
var WORD='ULTRAPIXEL',FONT='Cinzel, "Bodoni Moda", serif';

var css=document.createElement('style');css.textContent=
'#intro{position:fixed;inset:0;z-index:100;cursor:pointer;overflow:hidden}'+
'#intro .door{position:absolute;top:0;bottom:0;width:50.2%;background:radial-gradient(120% 80% at 50% 40%,#0B0C0F,#040405 70%);transition:transform 1.8s cubic-bezier(.7,0,.15,1)}'+
'#intro .door.l{left:0}#intro .door.r{right:0}'+
'#intro .door i{position:absolute;left:0;right:0;top:86%;height:1px;opacity:0;transition:opacity 1.2s;background:linear-gradient(90deg,transparent,rgba(214,206,190,.25) 30%,rgba(214,206,190,.25) 70%,transparent)}'+
'#intro.ready .door i{opacity:1}#intro.open .door.l{transform:translateX(-101%)}#intro.open .door.r{transform:translateX(101%)}'+
'#intro .door.l::after,#intro .door.r::after{content:"";position:absolute;top:0;bottom:0;width:1px;background:linear-gradient(180deg,transparent,rgba(236,214,160,.6),transparent);opacity:0;transition:opacity .6s}'+
'#intro .door.l::after{right:0}#intro .door.r::after{left:0}#intro.open .door::after{opacity:1}'+
'#intro canvas{position:absolute;inset:0;width:100%;height:100%;transition:opacity 1.2s ease}'+
'#intro .ui{position:absolute;inset:0;pointer-events:none;transition:opacity 1s ease}#intro.open .ui,#intro.open canvas{opacity:0}'+
'#intro .x{position:absolute;left:0;right:0;text-align:center;opacity:0;transition:opacity 1.6s ease,transform 1.6s ease}#intro .x.on{opacity:1}#intro .x.off{opacity:0!important;transition-duration:.8s}'+
'#intro .g{font:italic 400 clamp(18px,2.2vw,26px)/1 "Bodoni Moda",Didot,serif;letter-spacing:.06em;color:#D9D2C4}'+
'#intro .s{font:400 clamp(9px,.9vw,11px)/1 var(--mono);letter-spacing:.55em;text-transform:uppercase;color:#9A958B;padding-left:.55em}'+
'#intro .c{font:italic 400 clamp(17px,2.1vw,28px)/1.25 "Bodoni Moda",Didot,serif;color:#EADBB4;letter-spacing:.02em;padding:0 20px;transform:translateY(8px)}#intro .c.on{transform:none}'+
'#intro .f{display:flex;justify-content:center;gap:clamp(14px,3vw,40px);font:400 clamp(9px,.85vw,11px)/1 var(--mono);letter-spacing:.42em;text-transform:uppercase;color:#A89B7E;opacity:1}'+
'#intro .f span{opacity:0;transition:opacity 1.2s ease}#intro .f span.on{opacity:1}#intro .f b{font-weight:400;color:#6E6656;opacity:0;transition:opacity 1.2s}#intro .f b.on{opacity:1}'+
'#intro .line{position:absolute;left:50%;height:1px;width:0;transform:translateX(-50%);background:linear-gradient(90deg,transparent,rgba(236,231,220,.9),transparent);transition:width 2.2s cubic-bezier(.3,0,.1,1),opacity .8s;box-shadow:0 0 12px rgba(236,231,220,.35)}'+
'#intro .line.on{width:min(62vw,720px)}#intro .line.off{opacity:0}'+
'#intro .cmyk{position:absolute;left:50%;bottom:34px;transform:translateX(-50%);display:flex;gap:7px;opacity:0;transition:opacity 1.6s ease}#intro .cmyk.on{opacity:1}#intro .cmyk i{width:5px;height:5px}'+
'#intro .skip{position:absolute;right:30px;bottom:30px;pointer-events:auto;border:0;border-bottom:1px solid rgba(217,210,196,.35);background:none;color:rgba(217,210,196,.75);padding:6px 0;font:400 10px var(--mono);letter-spacing:.3em;text-transform:uppercase;cursor:pointer;opacity:0;transition:opacity 1.5s 1s}'+
'#intro.ready .skip{opacity:1}';
document.head.appendChild(css);

var o=document.createElement('div');o.id='intro';o.setAttribute('aria-hidden','true');
o.innerHTML='<div class="door l"><i></i></div><div class="door r"><i></i></div><canvas></canvas><div class="ui">'+
 '<div class="x g">'+TX.g+'</div><div class="line"></div><div class="x s">'+TX.s+'</div>'+
 '<div class="x c">'+TX.c+'</div><div class="x f on"><span>'+TX.f[0]+'</span><b>·</b><span>'+TX.f[1]+'</span><b>·</b><span>'+TX.f[2]+'</span></div>'+
 '<div class="cmyk"><i style="background:#00A0E3"></i><i style="background:#E6007E"></i><i style="background:#FFE600"></i><i style="background:#E9E4DA"></i></div>'+
 '<button class="skip" type="button">'+TX.k+'</button></div>';
document.body.appendChild(o);de.classList.remove('pre');
requestAnimationFrame(function(){o.classList.add('ready')});
var q=function(s){return o.querySelector(s)};

var done=false,raf=0,timers=[];
function at(ms,f){timers.push(setTimeout(function(){if(!done)f()},ms))}
function chiudi(){if(done)return;done=true;timers.forEach(clearTimeout);o.classList.add('open');setTimeout(function(){cancelAnimationFrame(raf);o.remove();fine()},1900)}
o.addEventListener('click',chiudi);document.addEventListener('keydown',function k(){document.removeEventListener('keydown',k);chiudi()});

var cv=q('canvas'),cx=cv.getContext('2d'),dpr=Math.min(2,window.devicePixelRatio||1),w,h,P=[],N=0;
var A={},B={};   // A: la scritta; B: l'etichetta (asse del riflesso, ingombri)
function sample(draw,y0,y1,x0,x1,step){var off=document.createElement('canvas'),oc=off.getContext('2d');off.width=w;off.height=h;oc.fillStyle='#fff';oc.strokeStyle='#fff';draw(oc);
  var d=oc.getImageData(0,0,w,h).data,T=[];for(var y=Math.max(0,y0|0);y<Math.min(h,y1);y+=step)for(var x=Math.max(0,x0|0);x<Math.min(w,x1);x+=step)if(d[((y|0)*w+(x|0))*4+3]>70)T.push([x,y]);
  for(var i=T.length-1;i>0;i--){var j=Math.random()*(i+1)|0,t=T[i];T[i]=T[j];T[j]=t}return T}
function spaced(oc,txt,cxm,base,fs,track){oc.font='500 '+fs+'px '+FONT;var ws=[].map.call(txt,function(c){return oc.measureText(c).width}),tot=ws.reduce(function(a,b){return a+b},0)+track*fs*(txt.length-1),x=cxm-tot/2;
  for(var i=0;i<txt.length;i++){oc.fillText(txt[i],x,base);x+=ws[i]+track*fs}return tot}
function setup(){
  w=innerWidth;h=innerHeight;cv.width=w*dpr;cv.height=h*dpr;cx.setTransform(dpr,0,0,dpr,0,0);
  /* atto I: la scritta */
  var mc=document.createElement('canvas').getContext('2d'),track=.36,fs=Math.min(110,w*.82/(WORD.length*(.74+track)));mc.font='500 '+fs+'px '+FONT;
  var tot=[].reduce.call(WORD,function(a,c){return a+mc.measureText(c).width},0)+track*fs*(WORD.length-1);if(tot>w*.86)fs*=w*.86/tot;
  A={fs:fs,base:h*.47+fs*.35};A.axis=A.base+fs*.06;
  var TA=sample(function(oc){spaced(oc,WORD,w/2,A.base,fs,track)},A.base-fs*1.1,A.base+fs*.3,0,w,fs>60?1.6:1.2);
  /* atto II: l'etichetta sagomata a doppio filetto */
  var lh=Math.min(h*.56,560),lw=Math.min(lh*.78,w*.8);lh=Math.min(lh,lw/.78);var lx=(w-lw)/2,ly=h*.40-lh/2,rc=lw*.075;
  B={x:lx,y:ly,w:lw,h:lh,axis:ly+lh+2};
  function cart(oc,ins){var x0=lx+ins,y0=ly+ins,x1=lx+lw-ins,y1=ly+lh-ins,r=Math.max(4,rc-ins*.4);oc.beginPath();
    oc.moveTo(x0+r,y0);oc.lineTo(x1-r,y0);oc.arc(x1,y0,r,Math.PI,Math.PI/2,true);oc.lineTo(x1,y1-r);oc.arc(x1,y1,r,-Math.PI/2,Math.PI,true);
    oc.lineTo(x0+r,y1);oc.arc(x0,y1,r,0,-Math.PI/2,true);oc.lineTo(x0,y0+r);oc.arc(x0,y0,r,Math.PI/2,0,true);oc.closePath();oc.stroke()}
  var fsB=Math.min(lw*.68/(WORD.length*(.74+.3)),48);
  var TB=sample(function(oc){oc.lineWidth=2.2;cart(oc,0);oc.lineWidth=1;cart(oc,lw*.035);
      var cy=ly+lh*.5;spaced(oc,WORD,w/2,cy+fsB*.35,fsB,.3);
      oc.lineWidth=1.2;oc.beginPath();oc.moveTo(w/2-lw*.22,cy+fsB*1.05);oc.lineTo(w/2-10,cy+fsB*1.05);oc.moveTo(w/2+10,cy+fsB*1.05);oc.lineTo(w/2+lw*.22,cy+fsB*1.05);oc.stroke();
      oc.beginPath();oc.moveTo(w/2,cy+fsB*1.05-6);oc.lineTo(w/2+6,cy+fsB*1.05);oc.lineTo(w/2,cy+fsB*1.05+6);oc.lineTo(w/2-6,cy+fsB*1.05);oc.closePath();oc.fill();
      oc.beginPath();oc.arc(w/2,ly+lh*.24,lw*.075,0,6.283);oc.lineWidth=1.6;oc.stroke();oc.beginPath();oc.arc(w/2,ly+lh*.24,lw*.062,0,6.283);oc.lineWidth=.8;oc.stroke();
      spaced(oc,'UP',w/2,ly+lh*.24+lw*.03,lw*.075,.02);spaced(oc,'MMXIII',w/2,ly+lh*.77,Math.max(16,fsB*.5),.45)},
    ly-4,ly+lh+4,lx-4,lx+lw+4,lw>380?1.15:1.0);
  N=Math.min(Math.max(TA.length,TB.length),w<700?5200:13000);var nA=TA.length,nB=TB.length;var nS=w<700?380:900,TINT=['#00A0E3','#E6007E','#FFE600'];P=[];
  for(var i=0;i<N+nS;i++){var sx=Math.random()*w,sy=Math.random()*h*.95,wd=i<N;
    P.push({x:sx,y:sy,ax:wd?TA[i%nA][0]:sx,ay:wd?TA[i%nA][1]:sy,bx:wd?TB[i%nB][0]:sx,by:wd?TB[i%nB][1]:sy,word:wd,r:wd?(fs>60?.85:.62):.35+Math.random()*.85,
      tw:Math.random()*6.28,sp:.6+Math.random()*1.8,on:Math.random()*1.8,d:Math.random()*.9,d2:Math.random()*.6,gv:Math.random(),c:Math.random()<.06?TINT[(Math.random()*3)|0]:null})}
  var g=q('.g'),ln=q('.line'),s=q('.s'),c=q('.c'),f=q('.f');
  g.style.top=(A.base-A.fs*1.0-46)+'px';ln.style.top=(A.base+A.fs*.78)+'px';s.style.top=(A.base+A.fs*.78+26)+'px';
  c.style.top=Math.min(h-120,B.y+B.h+30)+'px';f.style.top=Math.min(h-70,B.y+B.h+30+(w<700?62:52))+'px'}
function ease(t){return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2}
function cl(v){return v<0?0:v>1?1:v}
function mix(a,b,t){return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t]}
var SIL=[236,231,220],GOLD1=[201,160,82],GOLD2=[247,226,166],GLINT=[255,248,226];
var GLOW='filter' in CanvasRenderingContext2D.prototype,t0,T1=2.0,T2=5.6,TF=7.0;   // inizio scritta, inizio etichetta, inizio foil
function frame(now){var t=(now-t0)/1000;cx.clearRect(0,0,w,h);cx.globalCompositeOperation='lighter';
  var mA=cl((t-T1)/2.4),m2=ease(cl((t-T2)/1.8)),axis=A.axis+(B.axis-A.axis)*m2,refl=1-Math.abs(m2-.5)*2;
  var sw1=(t-4.3)/1.3,sx1=-100+(w+200)*sw1,fo=(t-TF)/1.5,fx=B.x-60+(B.w+120)*ease(cl(fo));
  for(var r=0;r<2;r++){
    for(var i=0;i<P.length;i++){var p=P[i],a=cl((t-p.on)/1.4),tw=.55+.45*Math.sin(t*p.sp+p.tw),x,y,al,col=null;
      if(p.word){var k=ease(cl((t-T1-p.d)/1.9)),k2=ease(cl((t-T2-p.d2)/1.8));
        var ax=p.x+(p.ax-p.x)*k,ay=p.y+(p.ay-p.y)*k;   // dal cielo alla scritta
        var mx=(ax+p.bx)/2+Math.sin(p.tw)*40*(1-Math.abs(k2-.5)*2),my=(ay+p.by)/2-60*Math.sin(Math.PI*k2)*(.4+p.gv);
        x=k2>0?(1-k2)*(1-k2)*ax+2*(1-k2)*k2*mx+k2*k2*p.bx:ax;y=k2>0?(1-k2)*(1-k2)*ay+2*(1-k2)*k2*my+k2*k2*p.by:ay;
        al=a*(tw*(1-k)+k*1.15);if(k2>0&&k2<1)al*=.75+.25*tw;
        if(t>4.3&&t<5.6&&k2===0){var dx=Math.abs(x-sx1);if(dx<70)al+=(1-dx/70)*.9}
        if(fo>0){var fd=fx-x;if(fd>0){var gold=mix(GOLD1,GOLD2,.35+.65*p.gv*(.7+.3*Math.sin(t*2+p.tw)));col=mix(SIL,gold,cl(fd/40));if(fd<26)col=mix(col,GLINT,1-fd/26),al+=.6*(1-fd/26)}}
        if(k<.98&&p.c)col=null;
      }else{x=p.x;y=p.y;al=a*tw*.8*(1-.35*m2)}
      if(r===1){if(!p.word||t<T1+1)continue;y=2*axis-y;al*=.2*Math.max(0,1-(y-axis)/((m2>.5?B.h*.18:A.fs*.62)))*(.4+.6*(1-refl*.8));if(y<axis)continue}
      if(al<=.01)continue;cx.globalAlpha=Math.min(1,al);
      cx.fillStyle=col?'rgb('+(col[0]|0)+','+(col[1]|0)+','+(col[2]|0)+')':(p.c&&p.word&&t<T1+1.2?p.c:(p.c&&!p.word?p.c:'#ECE7DC'));
      var rr=p.word?p.r*(1-.35*m2):p.r;cx.fillRect(x-rr,y-rr,rr*2,rr*2)}}
  if(GLOW){cx.globalAlpha=.55;cx.filter='blur('+(3*dpr/dpr)+'px)';cx.drawImage(cv,0,0,w,h);cx.filter='none'}
  cx.globalCompositeOperation='source-over';cx.globalAlpha=1;if(o.isConnected)raf=requestAnimationFrame(frame)}
function start(){setup();t0=performance.now();raf=requestAnimationFrame(frame);
  at(3500,function(){q('.g').classList.add('on')});at(3800,function(){q('.line').classList.add('on')});at(4400,function(){q('.s').classList.add('on')});
  at(5300,function(){q('.g').classList.add('off');q('.line').classList.add('off');q('.s').classList.add('off')});
  at(7900,function(){q('.c').classList.add('on')});
  var sp=o.querySelectorAll('.f span'),bb=o.querySelectorAll('.f b');
  at(8500,function(){sp[0].classList.add('on')});at(8800,function(){bb[0].classList.add('on');sp[1].classList.add('on')});at(9100,function(){bb[1].classList.add('on');sp[2].classList.add('on')});
  at(9300,function(){q('.cmyk').classList.add('on')});
  at(10600,chiudi)}
if(RM){q('.c').classList.add('on');[].forEach.call(o.querySelectorAll('.f span,.f b'),function(e){e.classList.add('on')});setTimeout(chiudi,2400);return}
addEventListener('resize',function(){if(!done)setup()});
(document.fonts&&document.fonts.load?Promise.race([Promise.all([document.fonts.load('500 80px Cinzel'),document.fonts.load('italic 400 26px "Bodoni Moda"')]),new Promise(function(r){setTimeout(r,1000)})]):Promise.resolve()).then(start,start);
})();
