(function(){
const $=id=>document.getElementById(id), NS="http://www.w3.org/2000/svg";
const el=(p,n,a)=>{const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e};
const cl=x=>Math.max(0,Math.min(1,x)), seg=(t,a,b)=>cl((t-a)/(b-a)), ease=x=>x*x*(3-2*x), mix=(a,b,k)=>a+(b-a)*k;

const inks=["#00A0DC","#D6006F","#F5D800","#2a2a2e","#F26B21","#2E9E5B","#5B3FA8","#ffffff"], names=["C","M","Y","K","5","6","7","8"];
names.forEach((n,i)=>{const b=document.createElement("b");b.textContent=n;b.style.background=inks[i];if(i==2||i==7)b.style.color="#101418";$("chips").appendChild(b)});
const chips=[...$("chips").children], panels=[...document.querySelectorAll(".panel")], qcs=[...document.querySelectorAll(".qc")];
const sheet=$("sheet"),Lp=$("Lpaper"),Lpr=$("Lprint"),Lg=$("Lgold"),Ls=$("Lscreen"),Lf=$("Lfinal"),glint=$("glint");
const seps=[...Lpr.querySelectorAll('.sp')], stns=inks.map(c=>{const e=document.createElement('div');e.className='stn';e.style.background=c;$('stations').appendChild(e);return e});
const zs=[sheet,Lpr,Lg,Ls,Lf], mats=JSON.parse($("hint").dataset.mats);

let lx=.35, ly=.4, queued=false;
function frame(){
  queued=false;
  const film=$("film"), vw=innerWidth, vh=$("stage").clientHeight, r=film.getBoundingClientRect();
  const t=cl(-r.top/(r.height-vh))*9, wide=vw>=900;
  $("bar").style.width=(t/9*100)+"%"; $("hint").style.opacity=t<.25?1:0;
  const c=Math.round(t); panels.forEach(p=>p.classList.toggle("on",+p.dataset.c===c));

  /* camera */
  const zin=ease(seg(t,.1,.95)), zout=ease(seg(t,7.6,8.5)), end=t>4, z=zin*(1-zout);
  const s0=Math.min(vh*(wide?.84:vw<380?.38:.44)/1026,vw*.6/387), s1=Math.min(vh*(wide?.68:.46)/375.5,vw*(wide?.4:.7)/300), sh=Math.min(vh*(wide?.6:.34)/375.5,vw*(wide?.34:.62)/300);
  /* the label opens alone, suspended; the bottle only arrives with the result */
  const s=end?mix(s1,s0,zout):mix(sh,s1,zin), ax=wide?vw*.68:vw*.5, ay=wide?vh*.5:vh*(end?mix(.36,vw<380?.78:.74,zout):mix(.77,.36,zin));
  $("rig").style.transform=`translate(${ax-193.5}px,${ay-643+(end?130*s0*zout:0)}px) scale(${s})`;
  const off=1-seg(t,7.7,8.2);
  $("bottle").style.opacity=1-off; $("curve").style.opacity=1-off;

  /* state: finished label at start and end; built pass by pass in between */
  const build=t>=1.15&&t<6.25, strip=seg(t,.9,1.15);
  const pP=seg(t,1.6,2.35), st=i=>cl(pP*3.1-i*.3), pF=seg(t,2.65,3.3), pS=seg(t,3.6,4.3), pE=seg(t,4.9,5.3);
  sheet.style.opacity=build?1:(t<1.15?seg(t,1,1.15):0);
  Lp.style.opacity=build?0:1;
  Lf.style.opacity=build?pE:(t<1.15?1-strip:1);
  [Lpr,Lg,Ls].forEach(e=>e.style.opacity=build?1:0);
  Lpr.style.opacity=build&&pP>0?1:0; seps.forEach((e,i)=>e.style.clipPath=`inset(0 0 ${100-st(i)*100}% 0)`); Lg.style.clipPath=`inset(0 0 ${100-pF*100}% 0)`; Ls.style.clipPath=`inset(0 0 0 ${100-pS*100}%)`;
  const m=seg(t,1.05,1.6)*4, w=i=>Math.max(0,1-Math.abs(m-i));
  $("m0").style.opacity=m>=4?1:Math.max(w(0),w(4)); $("m1").style.opacity=w(1); $("m2").style.opacity=w(2); $("m3").style.opacity=w(3);
  $("mat").textContent=mats[Math.round(m)];
  chips.forEach((b,i)=>b.classList.toggle("on",st(i)>0||t>2.35));
  stns.forEach((e,i)=>{const q=st(i);e.style.opacity=build&&q>0&&q<1?1:0;e.style.transform=`translateY(${375.5*q}px)`});
  glint.style.opacity=build?(pF>=1?1:0):+Lf.style.opacity;
  glint.style.backgroundPosition=`${(110-((lx*90+t*55)%140)*1.1)}% 0`;

    const rb=$("ribbon"); rb.style.opacity=build&&pF>0&&pF<1?1:0; rb.style.transform=`translateY(${375.5*pF-37}px)`;
  const sq=$("sq"); sq.style.opacity=build&&pS>0&&pS<1?1:0; sq.style.transform=`translateX(${300*(1-pS)-8}px)`;

  /* side view: the passes pull apart, then the relief lands on top */
  const sv=ease(seg(t,4.4,4.8))*(1-ease(seg(t,5.4,5.8)));
  const hk=1-seg(t,.15,.7);
  $("label").style.transform=sv?`perspective(1300px) rotateY(${-56*sv}deg) rotateX(${7*sv}deg)`:hk>0?`perspective(1200px) rotateY(${(lx-.5)*18*hk}deg) rotateX(${-(ly-.5)*12*hk}deg)`:"none";
  const rl=$("relit"); rl.style.opacity=build?0:.9; rl.style.setProperty("--lx",(lx*100).toFixed(1)+"%"); rl.style.setProperty("--ly",(ly*100).toFixed(1)+"%");
  zs.forEach((e,i)=>e.style.transform=sv?`translateZ(${i*26*sv}px)`:"none"); glint.style.transform=sv?`translateZ(${4*26*sv+1}px)`:"none";
  $("shadow").style.opacity=.3*off*(1-sv);

  /* die */
  const pD=seg(t,5.75,6.25), fall=seg(t,6.25,6.65);
  $("diep").setAttribute("stroke-dashoffset",1-pD); $("die").style.opacity=(t>5.7&&t<6.7)?1-seg(t,6.45,6.7):0;
  const dim=seg(t,5.55,5.8)*(1-seg(t,6.3,6.55)), fl=dim?`brightness(${1-.42*dim}) saturate(${1-.5*dim})`:"none"; Lf.style.filter=fl; sheet.style.filter=fl; $("matrix").style.filter=fl; glint.style.visibility=dim>.05?"hidden":"visible";
  const mx=$("matrix"); mx.style.opacity=t>=6.25&&fall<1?1-fall:0; mx.style.transform=`translate(${18*fall}px,${150*fall}px) rotate(${9*fall}deg)`;

  /* scan */
  const pQ=seg(t,6.75,7.4), sc=$("scan"); sc.style.opacity=pQ>0&&pQ<1?1:0; sc.style.transform=`translateY(${375.5*pQ}px)`;
  qcs.forEach(q=>q.style.opacity=(pQ>+q.dataset.y&&t<7.65)?1:0);
}
function ask(){if(!queued){queued=true;requestAnimationFrame(frame)}}
addEventListener("scroll",ask,{passive:true}); addEventListener("resize",ask);
addEventListener("pointermove",e=>{lx=e.clientX/innerWidth;ly=e.clientY/innerHeight;ask()},{passive:true});
addEventListener("load",ask); frame();

})();
