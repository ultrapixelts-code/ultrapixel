/* Ingresso nello studio (pagina /prova) — "Dal tratto alla fiera".
   Carta avorio: la penna disegna dal vivo la bottiglia, l'etichetta sagomata, la foglia, le lettere e il piedistallo.
   Poi si accendono le luci: il disegno diventa il rendering fotografico della stessa bottiglia esposta in fiera
   (i contorni sono presi dalla foto, quindi coincidono). Infine: L'arte di vestire un prodotto.
   Circa 11 secondi; una volta per visita; si salta con un clic o un tasto. */
(function(){
var de=document.documentElement;
function fine(){de.classList.remove('pre');try{sessionStorage.setItem('up_intro','1')}catch(e){}}
if(!de.classList.contains('pre'))return;
var LG=(window.UP&&UP.LG)||'it';
var TX={it:{c:'L’arte di vestire un prodotto.',a:'UltraPixel · Atelier di etichette',k:'Entra'},en:{c:'The art of dressing a product.',a:'UltraPixel · Label atelier',k:'Enter'},
        fr:{c:'L’art d’habiller un produit.',a:'UltraPixel · Atelier d’étiquettes',k:'Entrer'},de:{c:'Die Kunst, ein Produkt zu kleiden.',a:'UltraPixel · Etiketten-Atelier',k:'Eintreten'}}[LG]||{c:'L’arte di vestire un prodotto.',a:'UltraPixel · Atelier di etichette',k:'Entra'};
var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
var INK='#1C1A17',FOTO='/static/intro/fiera.jpg';
var img=new Image();img.src=FOTO;

var css=document.createElement('style');css.textContent=
'#intro{position:fixed;inset:0;z-index:100;cursor:pointer;overflow:hidden;background:#0E0C0A;transition:opacity 1.2s ease}#intro.out{opacity:0}'+
'#intro .bgb{position:absolute;inset:0;background:#0D0B09;opacity:0;transition:opacity 2.2s ease}'+
'#intro .box{position:absolute;left:50%;top:50%;width:min(100vw,66.667vh);height:min(100vh,150vw);transform:translate(-50%,-50%)}'+
'#intro .ph{position:absolute;inset:0;background:url('+FOTO+') center/cover no-repeat;opacity:0;clip-path:circle(0% at 50% 54%);transition:opacity 2.2s ease,clip-path 3s cubic-bezier(.4,0,.2,1)}'+
'#intro .edge{position:absolute;inset:-1px;pointer-events:none;background:linear-gradient(90deg,#0D0B09 0,rgba(13,11,9,0) 24%,rgba(13,11,9,0) 76%,#0D0B09 100%),linear-gradient(180deg,rgba(13,11,9,.0) 80%,rgba(13,11,9,.55));opacity:0;transition:opacity 2s ease}'+
'#intro.lit .edge{opacity:1}#intro.lit .ph{clip-path:circle(150% at 50% 54%)}'+
'#intro .paper{position:absolute;inset:0;background:#F3EFE6;transition:opacity 2.2s ease}'+
'#intro .paper::before{content:"";position:absolute;inset:0;opacity:.5;background-image:url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'220\' height=\'220\'><filter id=\'n\'><feTurbulence type=\'fractalNoise\' baseFrequency=\'.85\' numOctaves=\'3\' seed=\'4\'/><feColorMatrix values=\'0 0 0 0 .42 0 0 0 0 .38 0 0 0 0 .30 0 0 0 .22 0\'/></filter><rect width=\'220\' height=\'220\' filter=\'url(%23n)\'/></svg>")}'+
'#intro .paper::after{content:"";position:absolute;inset:0;background:radial-gradient(ellipse 80% 75% at 50% 45%,transparent 55%,rgba(120,100,70,.18))}'+
'#intro.lit .paper{opacity:0}#intro.lit .bgb{opacity:1}#intro.lit .ph{opacity:1}'+
'#intro svg{position:absolute;left:50%;top:50%;width:min(100vw,66.667vh);height:min(100vh,150vw);transform:translate(-50%,-50%);transition:opacity 1.6s ease}#intro.lit svg{opacity:0;transition-delay:.9s}'+
'@media(max-aspect-ratio:2/3){#intro .box,#intro svg{width:max(100vw,66.667vh)!important;height:max(100vh,150vw)!important}#intro .edge{background:linear-gradient(180deg,rgba(13,11,9,.0) 75%,rgba(13,11,9,.6))}}'+
'#intro .ln{fill:none;stroke:'+INK+';stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;vector-effect:non-scaling-stroke}'+
'#intro .tx{fill:none;stroke:'+INK+';stroke-width:.7;stroke-dasharray:700;stroke-dashoffset:700}'+
'#intro .c{position:absolute;left:0;right:0;bottom:calc(4vh + 30px);text-align:center;font:italic 400 clamp(20px,2.5vw,34px)/1.2 "Bodoni Moda",Didot,serif;color:#F2E9D6;text-shadow:0 2px 18px rgba(0,0,0,.6);opacity:0;transform:translateY(10px);transition:opacity 1.8s ease,transform 1.8s ease;padding:0 20px}'+
'#intro .a{position:absolute;left:0;right:0;bottom:4vh;text-align:center;font:400 10px var(--mono);letter-spacing:.5em;text-transform:uppercase;color:#B9AE98;opacity:0;transition:opacity 1.6s ease;padding-left:.5em}'+
'#intro .on2{opacity:1;transform:none}'+
'#intro .skip{position:absolute;right:28px;top:24px;z-index:3;border:0;border-bottom:1px solid rgba(28,26,23,.3);background:none;color:#5E574C;padding:6px 0;font:400 10px var(--mono);letter-spacing:.3em;text-transform:uppercase;cursor:pointer;transition:color 1.5s,border-color 1.5s}'+
'#intro .mark{position:absolute;left:28px;top:26px;z-index:3;font:400 10px var(--mono);letter-spacing:.3em;text-transform:uppercase;color:#8A8274;transition:color 1.5s}'+
'#intro.lit .skip{color:#CFC4AE;border-color:rgba(207,196,174,.35)}#intro.lit .mark{color:#9C9381}'+
'';
document.head.appendChild(css);

/* contorni presi dal rendering (coordinate in pixel della foto 1024×1536) */
var P={
 bot:'M400 1215Q386 1215 386 1196L386 600C386 520 440 500 458 462L465 362L463 200Q463 168 512 167Q561 168 562 200L560 362L566 462C584 500 640 520 640 600L640 1196Q640 1215 625 1215Z',
 cap:'M463 358H562',
 lab:'M436 636H592Q596 668 628 676V980Q596 988 592 1020H436Q432 988 398 980V676Q432 668 436 636Z',
 lab2:'M443 649H585Q590 676 616 684V972Q590 980 585 1007H443Q438 980 411 972V684Q438 676 443 649Z',
 leaf:'M514.0 817.5C514.0 815.5 519.0 811.1 521.3 811.0C522.6 811.0 522.9 810.5 522.4 808.6C521.9 806.5 522.2 806.1 524.7 805.8C527.3 805.5 527.5 805.2 527.2 801.6C526.9 797.8 526.9 797.7 529.9 798.3C532.7 798.9 533.0 798.7 533.0 796.6C533.0 795.2 533.6 793.9 534.2 793.7C535.2 793.3 535.2 792.9 534.1 792.1C532.9 791.3 532.8 790.6 533.7 788.7C534.4 787.3 534.6 785.3 534.3 784.2C533.8 782.2 534.2 782.1 541.7 782.5C548.4 782.8 549.7 782.6 551.3 780.9C553.7 778.3 554.5 766.4 552.4 765.6C549.8 764.6 550.7 761.0 553.5 761.0C557.4 761.0 556.9 756.9 552.8 755.1C551.0 754.3 549.2 753.3 548.9 752.8C548.6 752.3 545.6 751.5 542.2 750.9C536.5 749.9 536.0 749.6 536.0 747.3C536.0 744.9 536.2 744.8 540.0 745.3C542.3 745.6 544.0 745.4 544.0 744.8C544.0 743.5 546.6 741.0 548.1 741.0C549.8 741.0 554.2 736.1 553.5 734.9C553.1 734.4 552.0 734.0 550.9 734.0C549.7 734.0 549.0 733.3 549.0 732.1C549.0 730.8 548.2 730.0 546.8 729.8C545.3 729.6 544.4 728.7 544.2 727.2C543.9 725.0 539.0 723.8 539.0 726.0C539.0 726.5 538.1 727.0 537.0 727.0C535.5 727.0 535.0 726.3 535.0 724.5C535.0 723.1 535.5 722.0 536.0 722.0C536.5 722.0 537.0 721.1 537.0 719.9C537.0 718.3 536.6 718.0 534.8 718.6C530.2 719.9 526.2 721.8 525.6 722.9C525.2 723.5 523.3 724.0 521.4 724.0C518.5 724.0 517.6 724.6 515.9 727.5C514.7 729.5 513.0 731.0 511.9 731.0C510.9 731.0 510.0 731.5 510.0 732.0C510.0 732.5 510.4 733.0 510.8 733.0C511.9 733.0 514.5 740.8 513.7 741.6C513.4 741.9 511.9 741.8 510.3 741.3C507.9 740.4 507.5 739.8 507.6 736.6C507.7 734.6 507.3 733.0 506.9 733.0C505.7 733.0 505.7 724.3 506.8 723.8C508.0 723.4 509.3 718.0 508.3 718.0C505.6 718.1 503.7 726.2 504.3 735.0C504.9 744.2 504.4 745.5 501.3 742.5C500.3 741.5 499.9 739.8 500.3 737.7C500.9 733.7 499.2 730.0 496.8 730.0C495.8 730.0 495.0 729.5 495.0 728.9C495.0 727.0 492.2 725.0 490.5 725.6C489.5 726.0 488.4 725.7 488.0 724.9C487.0 723.3 483.1 727.5 483.0 730.2C483.0 731.7 482.0 732.0 476.9 732.0C471.6 732.0 470.9 732.2 471.4 733.6C472.3 735.9 471.2 739.0 469.4 739.0C468.6 739.0 468.0 740.0 468.0 741.5C468.0 743.3 467.5 744.0 466.0 744.0C464.9 744.0 464.0 744.7 464.0 745.5C464.0 746.3 463.1 747.0 462.0 747.0C460.9 747.0 460.0 747.4 460.0 747.9C460.0 749.1 465.4 750.1 465.8 748.9C466.9 746.1 471.4 750.1 470.5 753.0C470.0 754.6 470.3 755.0 472.4 755.0C476.9 755.0 475.9 759.3 471.0 761.5C468.8 762.5 467.0 764.0 467.0 764.9C467.0 765.8 466.1 767.6 465.0 769.0C462.4 772.4 462.5 772.7 466.5 773.4C468.5 773.8 470.0 774.7 470.0 775.5C470.0 777.9 468.8 780.0 467.4 780.0C466.6 780.0 466.0 780.5 466.0 781.0C466.0 781.5 466.6 782.0 467.4 782.0C468.3 782.0 468.9 784.0 469.3 788.6C470.0 795.6 470.6 797.2 471.8 795.3C472.2 794.6 474.8 793.6 477.5 792.9C480.3 792.3 483.2 791.4 484.0 790.9C484.8 790.4 486.5 789.6 487.8 789.0C489.0 788.5 490.0 787.2 490.0 786.0C490.0 784.9 490.6 784.0 491.4 784.0C493.6 784.0 494.2 787.5 492.7 791.2C490.4 796.8 492.3 805.1 495.3 802.1C497.3 800.1 498.6 801.0 499.6 805.2C500.2 808.1 501.1 809.6 502.3 809.8C504.5 810.2 506.7 812.3 509.3 816.3C511.2 819.2 514.0 819.9 514.0 817.5ZM492.0 779.8C492.1 777.1 494.2 774.0 495.9 774.0C497.1 774.0 496.6 779.0 495.3 781.2C494.3 782.9 492.0 781.9 492.0 779.8ZM477.0 757.2C477.0 755.4 478.8 754.0 481.2 754.0C481.7 754.0 482.0 755.0 481.8 756.2C481.4 759.2 477.0 760.1 477.0 757.2Z',
 plinth:'M152 1182H876M152 1182L148 1290M876 1182L882 1290M148 1290H882'
};
var svg='<svg viewBox="0 0 1024 1536" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"><defs><filter id="ib"><feGaussianBlur stdDeviation="2.5"/></filter></defs>'+
 '<path class="ln" pathLength="1" data-p="plinth" d="'+P.plinth+'" stroke-width=".9" opacity=".55"/>'+
 '<path class="ln" pathLength="1" data-p="bot" d="'+P.bot+'" stroke-width="1.2"/><path class="ln" pathLength="1" data-p="cap" d="'+P.cap+'" stroke-width="1"/>'+
 '<path class="ln" pathLength="1" data-p="lab" d="'+P.lab+'" stroke-width="1.1"/><path class="ln" pathLength="1" data-p="lab2" d="'+P.lab2+'" stroke-width=".6"/>'+
 '<path class="ln" pathLength="1" data-p="leaf" d="'+P.leaf+'" stroke-width=".8"/>'+
 '<text class="tx" x="513" y="881" text-anchor="middle" font-family="Cinzel,Bodoni Moda,serif" font-size="33" letter-spacing="2">RISERVA</text>'+
 '<text class="tx" x="513" y="941" text-anchor="middle" font-family="Cinzel,Bodoni Moda,serif" font-size="16" letter-spacing="1">2021</text>'+
 '<g class="tip" opacity="0"><circle r="11" fill="'+INK+'" opacity=".12" filter="url(#ib)"/><circle r="2.6" fill="'+INK+'"/></g></svg>';

var o=document.createElement('div');o.id='intro';o.setAttribute('aria-hidden','true');
o.innerHTML='<div class="bgb"></div><div class="box"><div class="ph"></div><div class="edge"></div></div><div class="paper"></div>'+svg+
 '<span class="mark">UltraPixel · Atelier</span><button class="skip" type="button">'+TX.k+'</button><div class="c">'+TX.c+'</div><div class="a">'+TX.a+'</div>';
document.body.appendChild(o);de.classList.remove('pre');
var q=function(s){return o.querySelector(s)};

var done=false,timers=[],raf=0;
function at(ms,f){timers.push(setTimeout(function(){if(!done)f()},ms))}
function chiudi(){if(done)return;done=true;timers.forEach(clearTimeout);cancelAnimationFrame(raf);o.classList.add('out');setTimeout(function(){o.remove();fine()},1250)}
o.addEventListener('click',chiudi);document.addEventListener('keydown',function k(){document.removeEventListener('keydown',k);chiudi()});
if(RM){o.classList.add('lit');q('.c').classList.add('on2');q('.a').classList.add('on2');setTimeout(chiudi,3000);return}

/* la penna: una sequenza di tratti, la punta segue ciascuno */
var tip=q('.tip'),SEQ=[['bot',2300],['cap',260],['lab',1400],['lab2',700],['leaf',1300],['plinth',900]],queue=[];
function eas(t){return t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2}
function traccia(i){if(done||i>=SEQ.length){tip.setAttribute('opacity',0);return}
  var el=q('[data-p="'+SEQ[i][0]+'"]'),L=el.getTotalLength(),dur=SEQ[i][1],t0=0;el.style.strokeDashoffset=1;
  function f(now){if(done)return;if(!t0)t0=now;var k=Math.min(1,(now-t0)/dur),e=eas(k);el.style.strokeDashoffset=1-e;
    var p=el.getPointAtLength(L*e);tip.setAttribute('transform','translate('+p.x+' '+p.y+')');tip.setAttribute('opacity',1);
    if(k<1)raf=requestAnimationFrame(f);else{if(SEQ[i][0]==='leaf')scrivi();traccia(i+1)}}
  raf=requestAnimationFrame(f)}
function scrivi(){[].forEach.call(o.querySelectorAll('.tx'),function(t,j){t.style.transition='stroke-dashoffset '+(j?1:1.6)+'s ease-in-out '+(j?.9:0)+'s, fill 1s ease 1.4s';
  t.style.strokeDashoffset=0;setTimeout(function(){t.style.fill=INK},1800+j*600)})}
at(500,function(){traccia(0)});
at(7600,function(){o.classList.add('lit')});            // si accendono le luci: il disegno diventa la foto
at(9300,function(){q('.c').classList.add('on2')});
at(9900,function(){q('.a').classList.add('on2')});
at(12600,chiudi);
})();
