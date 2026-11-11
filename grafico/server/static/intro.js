/* Ingresso nello studio (pagina /prova) — "Il gesto del grafico".
   Carta avorio e inchiostro. Una linea sottilissima, con la punta della penna, entra con un ghirigoro e disegna la sagoma
   dell'etichetta; poi le lettere e i dettagli; l'etichetta si riempie (carta, inchiostro, foil); l'inquadratura si allarga
   e la stessa mano disegna la bottiglia intorno. Infine la frase: L'arte di vestire un prodotto.
   Circa 10 secondi; una volta per visita; si salta con un clic o un tasto. */
(function(){
var de=document.documentElement;
function fine(){de.classList.remove('pre');try{sessionStorage.setItem('up_intro','1')}catch(e){}}
if(!de.classList.contains('pre'))return;
var LG=(window.UP&&UP.LG)||'it';
var TX={it:{c:'L’arte di vestire un prodotto.',a:'Atelier di etichette',k:'Entra'},en:{c:'The art of dressing a product.',a:'Label atelier',k:'Enter'},
        fr:{c:'L’art d’habiller un produit.',a:'Atelier d’étiquettes',k:'Entrer'},de:{c:'Die Kunst, ein Produkt zu kleiden.',a:'Etiketten-Atelier',k:'Eintreten'}}[LG]||{c:'L’arte di vestire un prodotto.',a:'Atelier di etichette',k:'Entra'};
var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
var INK='#1C1A17';

var css=document.createElement('style');css.textContent=
'#intro{position:fixed;inset:0;z-index:100;cursor:pointer;overflow:hidden;background:#F3EFE6;transition:opacity 1.1s ease,transform 1.4s cubic-bezier(.3,0,.2,1)}'+
'#intro::before{content:"";position:absolute;inset:0;opacity:.5;background-image:url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'220\' height=\'220\'><filter id=\'n\'><feTurbulence type=\'fractalNoise\' baseFrequency=\'.85\' numOctaves=\'3\' seed=\'4\'/><feColorMatrix values=\'0 0 0 0 .42 0 0 0 0 .38 0 0 0 0 .30 0 0 0 .22 0\'/></filter><rect width=\'220\' height=\'220\' filter=\'url(%23n)\'/></svg>")}'+
'#intro::after{content:"";position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse 80% 75% at 50% 45%,transparent 55%,rgba(120,100,70,.18))}'+
'#intro.out{opacity:0;transform:scale(1.03)}'+
'#intro svg.art{position:absolute;left:50%;top:46%;height:min(78vh,860px);width:auto;max-width:94vw;transform:translate(-50%,-50%);overflow:visible;z-index:1}'+
'#intro .ln{fill:none;stroke:'+INK+';stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1}'+
'#intro .dr{animation:idr var(--d,1.4s) cubic-bezier(.55,.05,.25,1) forwards}'+
'#intro .tx{fill:transparent;stroke:'+INK+';stroke-width:.35;stroke-dasharray:420;stroke-dashoffset:420}'+
'#intro .tx.dr{animation:itx var(--d,1.6s) ease-in-out forwards}'+
'#intro .fill{opacity:0;transition:opacity 1.4s ease}#intro .fill.on{opacity:1}'+
'#intro .ink.on{fill:'+INK+';transition:fill 1.2s ease}'+
'#intro .zoom{transform-box:view-box;transform-origin:300px 572px;transform:scale(2.15);transition:transform 2.6s cubic-bezier(.65,0,.2,1)}#intro .zoom.wide{transform:scale(1)}'+
'#intro .tip{fill:'+INK+'}'+
'#intro .c{position:absolute;left:0;right:0;bottom:calc(5vh + 34px);text-align:center;z-index:2;font:italic 400 clamp(20px,2.6vw,34px)/1.2 "Bodoni Moda",Didot,serif;color:'+INK+';opacity:0;transform:translateY(10px);transition:opacity 1.6s ease,transform 1.6s ease;padding:0 20px}'+
'#intro .a{position:absolute;left:0;right:0;bottom:5vh;text-align:center;z-index:2;font:400 10px var(--mono);letter-spacing:.5em;text-transform:uppercase;color:#7A7163;opacity:0;transition:opacity 1.4s ease;padding-left:.5em}'+
'#intro .on2{opacity:1;transform:none}'+
'#intro .skip{position:absolute;right:28px;top:24px;z-index:3;border:0;border-bottom:1px solid rgba(28,26,23,.3);background:none;color:#5E574C;padding:6px 0;font:400 10px var(--mono);letter-spacing:.3em;text-transform:uppercase;cursor:pointer}'+
'#intro .mark{position:absolute;left:28px;top:26px;z-index:3;font:400 10px var(--mono);letter-spacing:.3em;text-transform:uppercase;color:#8A8274}'+
'@keyframes idr{to{stroke-dashoffset:0}}@keyframes itx{to{stroke-dashoffset:0}}';
document.head.appendChild(css);

/* disegno: etichetta sagomata sul corpo di una bordolese */
var LAB='M237 450H363A12 12 0 0 0 375 462V678A12 12 0 0 0 363 690H237A12 12 0 0 0 225 678V462A12 12 0 0 0 237 450Z';
var LAB2='M241 457H359A9 9 0 0 0 368 466V674A9 9 0 0 0 359 683H241A9 9 0 0 0 232 674V466A9 9 0 0 0 241 457Z';
var MAIN='M150 640C176 618 168 586 190 566C212 546 236 560 232 584C228 606 204 600 206 578C209 548 224 470 237 450'+LAB.slice(8);
var BOT='M228 762Q210 762 210 744L210 362C210 302 270 292 270 232L270 92L267 74L333 74L330 92L330 232C330 292 390 302 390 362L390 744Q390 762 372 762Z';
var D=function(s,d){return 'style="animation-delay:'+s+'s;--d:'+d+'s"'};
var svg='<svg class="art" viewBox="0 0 600 800" xmlns="http://www.w3.org/2000/svg"><defs>'+
 '<linearGradient id="igl" x1="0" x2="1"><stop offset="0" stop-color="#0E0B08"/><stop offset=".2" stop-color="#2A241B"/><stop offset=".32" stop-color="#14110D"/><stop offset=".8" stop-color="#0D0B09"/><stop offset="1" stop-color="#050403"/></linearGradient>'+
 '<linearGradient id="iau" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9C7630"/><stop offset=".45" stop-color="#E9CF8A"/><stop offset=".55" stop-color="#F7E7B8"/><stop offset="1" stop-color="#A47C33"/></linearGradient>'+
 '<radialGradient id="ish" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#3a2e1c" stop-opacity=".28"/><stop offset="1" stop-color="#3a2e1c" stop-opacity="0"/></radialGradient>'+
 '<filter id="ipp"><feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" seed="9"/><feColorMatrix values="0 0 0 0 .5 0 0 0 0 .45 0 0 0 0 .36 0 0 0 .18 0"/><feComposite in2="SourceGraphic" operator="in"/></filter>'+
 '<filter id="iblur"><feGaussianBlur stdDeviation="1.4"/></filter></defs>'+
 '<g class="zoom">'+
  /* la bottiglia (atto finale) */
  '<ellipse class="fill f3" cx="300" cy="766" rx="120" ry="9" fill="url(#ish)"/>'+
  '<path class="fill f3" d="'+BOT+'" fill="url(#igl)"/><path class="fill f3" d="M268 74h64v40h-64z" fill="#2a2018"/>'+
  '<rect class="fill f3" x="219" y="372" width="4" height="70" rx="2" fill="#fff" opacity=".07"/><rect class="fill f3" x="219" y="700" width="4" height="40" rx="2" fill="#fff" opacity=".05"/>'+
  '<path class="ln b1" pathLength="1" d="'+BOT+'" stroke-width=".9"/>'+
  /* l'etichetta: riempimenti */
  '<path class="fill f1" d="'+LAB+'" fill="#FBF8F0"/><path class="fill f1" d="'+LAB+'" fill="#EDE5D3" filter="url(#ipp)"/>'+
  '<path class="fill f1" d="'+LAB+'" fill="none" stroke="'+INK+'" stroke-width=".9"/>'+
  '<path class="fill f2" d="'+LAB2+'" fill="none" stroke="url(#iau)" stroke-width=".9"/>'+
  '<circle class="fill f2" cx="300" cy="497" r="15" fill="none" stroke="url(#iau)" stroke-width="1"/>'+
  '<path class="fill f2" d="M262 603h30l8-4 8 4h30" fill="none" stroke="url(#iau)" stroke-width=".9"/><path class="fill f2" d="M300 597l3 5-3 5-3-5z" fill="url(#iau)"/>'+
  /* l'etichetta: il disegno a mano */
  '<path class="ln m" pathLength="1" d="'+MAIN+'" stroke-width="1.1"/>'+
  '<path class="ln dr tf" pathLength="1" d="'+LAB2+'" stroke-width=".5" '+D(2.5,1.3)+'/>'+
  '<circle class="ln dr tf" pathLength="1" cx="300" cy="497" r="15" stroke-width=".55" '+D(2.9,.9)+'/>'+
  '<path class="ln dr tf" pathLength="1" d="M262 603h30l8-4 8 4h30" stroke-width=".6" '+D(4.1,.8)+'/>'+
  '<text class="tx dr ink" x="300" y="503" text-anchor="middle" font-family="Bodoni Moda,Didot,serif" font-size="15" font-weight="500" '+D(3.2,1)+'>U<tspan font-style="italic">P</tspan></text>'+
  '<text class="tx dr ink" x="300" y="585" text-anchor="middle" font-family="Bodoni Moda,Didot,serif" font-style="italic" font-size="27" font-weight="500" '+D(3.4,1.7)+'>UltraPixel</text>'+
  '<text class="tx dr ink" x="300" y="628" text-anchor="middle" font-family="Cinzel,serif" font-size="7.6" letter-spacing="2.6" '+D(4.4,1)+'>'+TX.a.toUpperCase()+'</text>'+
  '<text class="tx dr ink" x="300" y="666" text-anchor="middle" font-family="Cinzel,serif" font-size="6.4" letter-spacing="2.4" '+D(4.7,.9)+'>TRIESTE · MMXIII</text>'+
  '<g class="tipg" opacity="0"><circle r="7" fill="'+INK+'" opacity=".10" filter="url(#iblur)"/><circle class="tip" r="1.6"/></g>'+
 '</g></svg>';

var o=document.createElement('div');o.id='intro';o.setAttribute('aria-hidden','true');
o.innerHTML='<span class="mark">UltraPixel · Atelier</span><button class="skip" type="button">'+TX.k+'</button>'+svg+'<div class="c">'+TX.c+'</div><div class="a">UltraPixel · '+TX.a+'</div>';
document.body.appendChild(o);de.classList.remove('pre');
var q=function(s){return o.querySelector(s)},all=function(s){return o.querySelectorAll(s)};

var done=false,timers=[],raf=0;
function at(ms,f){timers.push(setTimeout(function(){if(!done)f()},ms))}
function chiudi(){if(done)return;done=true;timers.forEach(clearTimeout);cancelAnimationFrame(raf);o.classList.add('out');setTimeout(function(){o.remove();fine()},1150)}
o.addEventListener('click',chiudi);document.addEventListener('keydown',function k(){document.removeEventListener('keydown',k);chiudi()});
function on(sel){[].forEach.call(all(sel),function(e){e.classList.add('on')})}
if(RM){[].forEach.call(all('.ln,.tx'),function(e){e.style.strokeDashoffset=0});on('.fill');on('.ink');q('.zoom').classList.add('wide');q('.c').classList.add('on2');setTimeout(chiudi,2600);return}

/* il tratto principale con la punta della penna, guidato a mano (stessa curva per linea e punta) */
var m=q('.m'),tipg=q('.tipg'),L=m.getTotalLength(),T0=0,DUR=2600;
function eas(t){return t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2}
function penna(now){if(!T0)T0=now;var k=Math.min(1,(now-T0)/DUR),e=eas(k);m.style.strokeDashoffset=1-e;
  var p=m.getPointAtLength(L*e);tipg.setAttribute('transform','translate('+p.x+' '+p.y+')');tipg.setAttribute('opacity',k<1?1:Math.max(0,1-(now-T0-DUR)/400));
  if(k<1||now-T0<DUR+400)raf=requestAnimationFrame(penna)}
at(450,function(){raf=requestAnimationFrame(penna)});
at(5500,function(){on('.f1');m.style.transition='opacity 1.3s';m.style.opacity=0});                 // la carta
at(5900,function(){on('.ink')});                // l'inchiostro
at(6300,function(){on('.f2');[].forEach.call(all('.tf'),function(e){e.style.transition='opacity 1.2s';e.style.opacity=0})});                 // il foil
at(6900,function(){q('.zoom').classList.add('wide')});      // l'inquadratura si allarga
at(7600,function(){var b=q('.b1');b.style.setProperty('--d','1.7s');b.classList.add('dr')});   // la mano disegna la bottiglia
at(9000,function(){on('.f3')});
at(9300,function(){q('.c').classList.add('on2')});
at(9900,function(){q('.a').classList.add('on2')});
at(12200,chiudi);
})();
