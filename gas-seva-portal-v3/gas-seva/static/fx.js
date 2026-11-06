/* Gas Seva – presentation layer. No business logic lives here. */
const FX=(()=>{
const F={dir:0,fresh:true},g=window.gsap,RM=matchMedia("(prefers-reduced-motion:reduce)").matches;
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],sleep=ms=>new Promise(r=>setTimeout(r,ms));

/* ----- icons & logo ----- */
const P={
staff:'<circle cx="12" cy="8" r="3.6"/><path d="M5 20c0-4 3.5-6 7-6s7 2 7 6"/>',
admin:'<path d="M12 3l8 3v6c0 4.5-3.4 7.7-8 9-4.6-1.3-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
auditor:'<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5M8 10.5h5"/>',
dev:'<path d="M8 8l-5 4 5 4M16 8l5 4-5 4M13.5 5l-3 14"/>',
bookings:'<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M4 10h16M9 3v4M15 3v4"/>',
deliveries:'<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
unpaid:'<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
subsidy:'<circle cx="12" cy="12" r="8.5"/><path d="M9 8h6M9 11h6M10 8c3.5 0 3.5 4 0 4l4 4"/>',
cash:'<rect x="3" y="7" width="18" height="10" rx="2.5"/><circle cx="12" cy="12" r="2.4"/>',
upi:'<rect x="7" y="3" width="10" height="18" rx="2.5"/><path d="M11 18h2"/>',
empty:'<rect x="6" y="9" width="12" height="12" rx="5"/><path d="M10 9V5.5h4V9"/>'};
F.ic=k=>`<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[k]||""}</svg>`;
F.logo='<svg class="logo" viewBox="0 -14 80 134" aria-hidden="true"><path class="fl" d="M40 -14C47 -6 49 -1 45 3H35C31 -1 33 -6 40 -14Z"/><rect x="31" y="3" width="18" height="17" rx="4" fill="#9C2B3B"/><rect x="10" y="20" width="60" height="92" rx="26" fill="#FF9933" stroke="#9C2B3B" stroke-width="5"/><rect x="12.5" y="52" width="55" height="24" fill="#FFFBF1"/><circle cx="40" cy="64" r="7" fill="#138808"/></svg>';

/* ----- gate: content reveal waits until a curtain/loader opens ----- */
const hold=()=>{if(!F.pending){F.pending=1;F.gate=new Promise(r=>F.rel=r)}},rel=()=>{F.pending=0;F.rel()};
hold();

/* ----- tricolour curtain between "pages" (login / logout / first load) ----- */
F.route=async fn=>{
  hold();const cv=$("#cv"),anim=g&&!RM;
  if(anim){cv.classList.add("on");await g.fromTo("#cv i",{scaleX:0,transformOrigin:"0 50%"},{scaleX:1,duration:.45,stagger:.08,ease:"power3.inOut"})}
  F.fresh=true;
  try{await fn()}finally{rel()}
  if(anim){await g.to("#cv i",{scaleX:0,transformOrigin:"100% 50%",duration:.5,stagger:.08,ease:"power3.inOut"});cv.classList.remove("on")}
};

/* ----- loading page ----- */
F.load=async()=>{
  const ld=$("#ld");if(!ld)return;
  await sleep(Math.max(0,(sessionStorage.seen?600:1700)-performance.now()));
  sessionStorage.seen=1;ld.classList.add("full");await sleep(450);
  await F.route(()=>ld.remove());
};
setTimeout(()=>{if(!F.booted){F.booted=1;F.load()}},7000);

/* ----- ghost cross-fade for tab / language changes ----- */
F.ghost=()=>{
  if(!g||RM||F.pending)return;const m=$("#main");if(!m||!m.children.length)return;
  const r=m.getBoundingClientRect(),c=m.cloneNode(true);
  c.removeAttribute("id");c.querySelectorAll("[id]").forEach(e=>e.removeAttribute("id"));
  c.className="ghost";c.inert=true;c.setAttribute("aria-hidden","true");
  Object.assign(c.style,{top:r.top+scrollY+"px",left:r.left+"px",width:r.width+"px"});
  document.body.append(c);
  g.to(c,{opacity:0,x:-F.dir*50,y:-12,scale:.98,filter:"blur(4px)",duration:.35,ease:"power2.in",onComplete:()=>c.remove()});
};

/* ----- staggered reveal (direction-aware) ----- */
F.reveal=()=>{
  const d=F.dir||0,fr=F.fresh;F.dir=0;F.fresh=false;
  if(g&&!RM){
    const els=$$("#main .card,#main>.row,#view>.row,#view>button"),hd=fr?$$("header h1,header .row>*"):[];
    g.set([...els,...hd],{opacity:0});
    F.gate.then(()=>{
      g.fromTo(els,{y:30,x:d*40,scale:.96,opacity:0},{y:0,x:0,scale:1,opacity:1,duration:.65,stagger:{amount:.55},ease:"back.out(1.2)",clearProps:"transform,opacity"});
      g.fromTo(hd,{y:-20,opacity:0},{y:0,opacity:1,duration:.6,stagger:.07,ease:"power3.out",clearProps:"transform,opacity"});
      g.from("#view .bars i",{scaleY:0,transformOrigin:"50% 100%",duration:.8,stagger:{amount:.5},delay:.25,ease:"power3.out",clearProps:"transform"});
    });
  }
  if(!F.booted){F.booted=1;F.load()}
};

/* ----- tiny helpers ----- */
F.shake=sel=>{if(g&&!RM)g.fromTo(sel,{x:-12},{x:0,duration:.55,ease:"elastic.out(1.2,.25)",clearProps:"transform"})};
F.burst=el=>{
  if(!g||RM)return;const r=el.getBoundingClientRect();
  for(let i=0;i<14;i++){
    const p=document.createElement("i"),a=i/14*6.283+Math.random()*.5,d=44+Math.random()*56;
    p.className="bp";p.style.cssText=`left:${r.left+r.width/2}px;top:${r.top+r.height/2}px;background:${["#FF9933","#138808","#FFD9A0","#9C2B3B"][i%4]}`;
    document.body.append(p);
    g.to(p,{x:Math.cos(a)*d,y:Math.sin(a)*d,scale:0,opacity:0,duration:.7+Math.random()*.3,ease:"power2.out",onComplete:()=>p.remove()});
  }
};

/* ----- loading feedback: flag bar sweep + spinner on the pressed button ----- */
const of=window.fetch.bind(window);let n=0;
window.fetch=(...a)=>{
  const b=document.activeElement&&document.activeElement.matches&&document.activeElement.matches(".btn")?document.activeElement:null;
  n++;document.body.classList.add("busy");if(b)b.classList.add("busy");
  return of(...a).finally(()=>{if(!--n)document.body.classList.remove("busy");if(b)b.classList.remove("busy")});
};

/* ----- background: mandala + rising embers + cursor spotlight ----- */
const md=$("#bg .md");
if(md)md.innerHTML='<g fill="none" stroke="#9C2B3B" stroke-width=".8"><circle r="96"/><circle r="88"/><circle r="30"/><circle r="12"/>'+
  [...Array(16)].map((_,i)=>`<ellipse rx="10" ry="27" cy="-56" transform="rotate(${i*22.5})"/>`).join("")+
  [...Array(32)].map((_,i)=>`<circle r="2" cy="-92" transform="rotate(${i*11.25})"/>`).join("")+'</g>';
const em=$("#bg .em");
if(em&&!RM)for(let i=0;i<16;i++){
  const s=document.createElement("i"),z=6+Math.random()*14;
  s.style.cssText=`left:${Math.random()*100}%;width:${z}px;height:${z}px;--dx:${(Math.random()-.5)*160}px;animation-duration:${12+Math.random()*14}s;animation-delay:${-Math.random()*20}s`;
  em.append(s);
}

/* ----- ripple on press ----- */
document.addEventListener("pointerdown",e=>{
  const b=e.target.closest&&e.target.closest(".btn,.pill,.role");if(!b||RM)return;
  const r=b.getBoundingClientRect(),d=Math.max(r.width,r.height)*2.2,s=document.createElement("span");
  s.className="rp";Object.assign(s.style,{width:d+"px",height:d+"px",left:e.clientX-r.left-d/2+"px",top:e.clientY-r.top-d/2+"px"});
  b.append(s);setTimeout(()=>s.remove(),700);
});

/* ----- proximity-grow buttons (+ magnetic pull, + tilt on role cards) ----- */
let mx=-999,my=-999,run=0;const st=new WeakMap(),root=document.documentElement;
const tick=()=>{
  let moving=0;
  $$(".btn,.pill,.role,.fab").forEach(el=>{
    let s=st.get(el);if(!s)st.set(el,s={s:1,x:0,y:0,rx:0,ry:0});
    const r=el.getBoundingClientRect(),w=el.offsetWidth,h=el.offsetHeight,cx=r.left+r.width/2-s.x,cy=r.top+r.height/2-s.y;
    const role=el.classList.contains("role"),R=role?70:120,max=role?.05:el.classList.contains("fab")?.22:.17;
    const d=Math.hypot(Math.max(Math.abs(mx-cx)-w/2,0),Math.max(Math.abs(my-cy)-h/2,0)),k=Math.max(0,1-d/R),e=k*k*(3-2*k);
    const inside=role&&Math.abs(mx-cx)<w/2&&Math.abs(my-cy)<h/2;
    const T={s:1+max*e,x:Math.max(-7,Math.min(7,(mx-cx)*.1))*e,y:Math.max(-7,Math.min(7,(my-cy)*.1))*e,rx:inside?(cy-my)/h*10:0,ry:inside?(mx-cx)/w*10:0};
    let diff=0;for(const q in T){diff+=Math.abs(T[q]-s[q]);s[q]+=(T[q]-s[q])*.2}
    el.style.setProperty("--s",s.s.toFixed(3));el.style.setProperty("--tx",s.x.toFixed(2)+"px");el.style.setProperty("--ty",s.y.toFixed(2)+"px");
    el.style.setProperty("--rx",s.rx.toFixed(2)+"deg");el.style.setProperty("--ry",s.ry.toFixed(2)+"deg");
    el.style.zIndex=e>.05?2:"";if(diff>.004)moving=1;
  });
  run=moving?requestAnimationFrame(tick):0;
};
addEventListener("pointermove",e=>{
  root.style.setProperty("--mx",e.clientX+"px");root.style.setProperty("--my",e.clientY+"px");
  if(RM||e.pointerType!=="mouse")return;
  mx=e.clientX;my=e.clientY;if(!run)run=requestAnimationFrame(tick);
});
document.addEventListener("pointerleave",()=>{mx=my=-999;if(!run)run=requestAnimationFrame(tick)});
return F;})();
