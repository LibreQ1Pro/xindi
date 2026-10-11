// ---- the page around the screens ------------------------------------------------------------------------------------
const GROUPS = [];
SCREENS.forEach(s=>{ if(!GROUPS.includes(s.group)) GROUPS.push(s.group); });
let zoom = 1, showGrid = false, showNames = false;

function tokensHTML(){
  const sw = (n,v,t)=>`<div class="sw-c"><div style="background:${v}"></div><span><b>${n}</b><br>${v}${t?'<br>'+t:''}</span></div>`;
  return `<h2 id="tokens">Design tokens</h2>
  <p style="color:#9a9aa6;max-width:900px;font-size:13px;line-height:1.5">The screen is 272 × 480, 16-bit colour: flat fills only (no gradients, no shadows: they band). One grid: <b>8 px</b>; page margin <b>12</b>, content width <b>248</b>, gap <b>8</b>; touch targets are at least <b>40</b> high (buttons 44, list rows 46–52); corner radius <b>14</b> for cards, <b>10</b> for buttons, <b>8</b> for keys. The navigation bar is 56 high (y 424), the header 48.</p>
  <div class="sw-row">
  ${sw('bg','#17171a','page')}${sw('panel','#222226','card')}${sw('card','#2a2a30','card, raised')}${sw('btn','#35353d','button')}${sw('btn-hi','#41414b','selected')}${sw('btn-press','#2a2a31','pressed')}
  ${sw('line','#3a3a43','dividers')}${sw('nav','#0f0f11','navigation bar')}${sw('accent','#3d7bff','primary, active')}${sw('accent-press','#2e60cf','primary pressed')}${sw('danger','#e5484d','stop, forget')}${sw('danger-bg','#4a2326','danger button')}${sw('heat','#ff7a59','heater is on')}${sw('ok','#30a46c','done')}${sw('warn','#f5a524','warning')}
  ${sw('text','#f4f4f7','text')}${sw('text2','#a6a6b3','secondary text')}${sw('text3','#70707d','disabled')}
  </div>
  <div class="type-sample"><div style="font-size:24px;font-weight:600">Title 24 / 600 — Nozzle Temp 220</div><div style="font-size:19px;font-weight:600">Header 19 / 600 — Wi-Fi Connection</div>
  <div style="font-size:16px;font-weight:500">Button, body 16 / 500 — Please select the nozzle temperature.</div><div style="font-size:13px;color:#a6a6b3">Caption 13 / 400 — MAX : 350</div>
  <div style="font-size:28px;font-weight:600;font-variant-numeric:tabular-nums">Digits 28 / 600 — 0123456789 °C %</div>
  <div style="font-size:16px;margin-top:6px">中文简体 日本語 한국어 العربية עברית Русский Türkçe</div></div>
  <p style="color:#9a9aa6;max-width:900px;font-size:13px">Fonts needed on the screen (to be rendered as .zi in USART HMI): a text font at 13, 16 (medium) and 19–24 (semibold) pixels that covers Latin, Cyrillic, Greek-less European accents, Chinese, Japanese, Korean, Arabic and Hebrew; and a digit font at 20 / 28 pixels (0-9, "." "-" "/" "%" "°" "℃"). The preview uses Noto Sans.</p>`;
}
function componentsHTML(){
  CUR='';
  const b=(x,y,w,h,l,o)=>btn(x,y,w,h,l,o);
  const comp = (title,html,w,h)=>`<div class="item"><div class="cap">${title}</div><div class="scr" style="width:${w}px;height:${h}px;background:var(--bg)">${html}</div></div>`;
  let h = `<h2 id="components">Components</h2><div class="grid">`;
  h += comp('Buttons: normal / pressed / primary / danger / dim', b(12,12,110,44,'OK')+b(130,12,110,44,'OK',{press:1})+b(12,64,110,44,'Start',{v:'primary'})+b(130,64,110,44,'Start',{v:'primary',press:1})+b(12,116,110,44,'Stop',{v:'danger'})+b(130,116,110,44,'Back',{v:'dim'})+b(12,168,110,44,'',{icon:'chevron-left',is:24})+b(130,168,110,44,'Wi-Fi',{icon:'wifi'}),252,226);
  h += comp('List rows', row(12,12,228,48,'Language',{chev:1})+row(12,68,228,48,'Setup Guide',{sw:true})+row(12,124,228,48,'5 minutes',{radio:true,sel:true})+row(12,180,228,48,'15 minutes',{radio:false})+row(12,236,228,48,'Home Wi-Fi',{check:true})+row(12,292,228,48,'Neighbour',{lock:true}),252,352);
  h += comp('Tabs, toggles, progress', `<div class="tabs" style="${st(12,12,228,40)}"><div class="tab on" style="${st(3,3,111,34)}">General</div><div class="tab" style="${st(114,3,111,34)}">Calibration</div></div>`+toggle(20,70,true)+toggle(80,70,false)+progress(12,116,228,8,35)+`<div class="radio on" style="left:20px;top:150px"></div><div class="radio" style="left:60px;top:150px"></div>`+btn(12,186,228,44,'Auto Bed Leveling',{}),252,250);
  h += comp('Keys', ['1','2','3','4','5','6'].map((k,i)=>`<div class="key" style="${st(12+78*(i%3),12+48*Math.floor(i/3),72,42)}">${k}</div>`).join('')+`<div class="key fn" style="${st(12,108,72,42)}">${ico('delete',20)}</div><div class="key" style="${st(90,108,72,42)}">0</div><div class="key" style="${st(168,108,72,42)};background:var(--accent)">${ico('check',22,'#fff',2.5)}</div>`,252,162);
  return h + '</div>';
}
function cardHTML(s, z){
  lang = lang; const html = s.build();
  return `<div class="item" id="s-${s.id}"><div class="cap"><b style="color:#ddd">${s.title}</b><code>${s.id}</code><a data-all="${s.id}">all languages</a></div>`+
    `<div class="zoomwrap" style="width:${272*z}px;height:${480*z}px"><div style="transform:scale(${z});transform-origin:0 0;width:272px;height:480px;position:relative">${html}</div></div>${s.note?`<div class="cap" style="max-width:${272*z}px;white-space:normal;color:#7d7d89">${s.note}</div>`:''}</div>`;
}
function render(){
  const main = document.getElementById('main');
  let h = tokensHTML() + componentsHTML();
  GROUPS.forEach((g,gi)=>{
    h += `<h2 id="g${gi}">${g}</h2><div class="grid">` + SCREENS.filter(s=>s.group===g).map(s=>cardHTML(s,zoom)).join('') + '</div>';
  });
  main.innerHTML = h;
  document.body.classList.toggle('showgrid', showGrid);
  document.body.classList.toggle('show-names', showNames);
  document.querySelectorAll('[data-all]').forEach(a=>a.onclick=()=>allLanguages(a.dataset.all));
}
function allLanguages(id){
  const s = SCREENS.find(x=>x.id===id); const saved = lang; let h='';
  for(let i=0;i<LANGS.length;i++){ lang=i; h+=`<div class="item"><div class="cap">${LANG_NAMES[i]} <code>${LANGS[i]}</code></div><div class="zoomwrap" style="width:${272*zoom}px;height:${480*zoom}px"><div style="transform:scale(${zoom});transform-origin:0 0;width:272px;height:480px;position:relative">${s.build()}</div></div></div>`; }
  lang = saved;
  const m = document.getElementById('modal');
  m.innerHTML = `<div class="box"><h3>${s.title} — all 13 languages <button id="close">Close</button></h3><div class="langgrid">${h}</div></div>`;
  m.classList.add('on'); document.getElementById('close').onclick=()=>m.classList.remove('on');
}
function init(){
  const side = document.getElementById('side');
  const opts = LANG_NAMES.map((n,i)=>`<option value="${i}"${i===2?' selected':''}>${n} (${LANGS[i]})</option>`).join('');
  side.innerHTML = `<h1>QIDI Q1 Pro screen — mockup</h1><p>272 × 480. Texts are the real ones of the project, in all 13 languages.</p>
   <label>Language</label><select id="lang">${opts}</select>
   <label>Size</label><div class="row"><button data-z="1" class="on">1×</button><button data-z="1.5">1.5×</button><button data-z="2">2×</button></div>
   <label>Overlays</label><div class="row"><button id="grid">8 px grid</button><button id="names">Widget names</button></div>
   <nav><b>Overview</b><a href="#tokens">Design tokens</a><a href="#components">Components</a>${GROUPS.map((g,i)=>`<b>${g}</b>`+SCREENS.filter(s=>s.group===g).map(s=>`<a href="#s-${s.id}">${s.title}</a>`).join('')).join('')}</nav>`;
  document.getElementById('lang').onchange = e=>{ lang=+e.target.value; render(); };
  side.querySelectorAll('[data-z]').forEach(b=>b.onclick=()=>{ zoom=+b.dataset.z; side.querySelectorAll('[data-z]').forEach(x=>x.classList.toggle('on',x===b)); render(); });
  document.getElementById('grid').onclick=e=>{ showGrid=!showGrid; e.target.classList.toggle('on',showGrid); render(); };
  document.getElementById('names').onclick=e=>{ showNames=!showNames; e.target.classList.toggle('on',showNames); render(); };
  const q = new URLSearchParams(location.search); if(q.has('lang')){ lang=+q.get('lang'); document.getElementById('lang').value=lang; }
  if(q.has('zoom')) zoom=+q.get('zoom');
  if(q.has('only')){      // for screenshots: just these screens (?only=a,b&all=1 for every language)
    side.style.display='none';
    const ids=q.get('only').split(',');
    let h='<div class="grid" style="padding:16px">';
    ids.forEach(id=>{ const sc=SCREENS.find(x=>x.id===id); if(!sc) return;
      if(q.has('all')){ const saved=lang; for(let i=0;i<LANGS.length;i++){ lang=i; h+=`<div class="item"><div class="cap">${LANG_NAMES[i]}</div>`+`<div class="zoomwrap" style="width:${272*zoom}px;height:${480*zoom}px"><div style="transform:scale(${zoom});transform-origin:0 0;width:272px;height:480px;position:relative">${sc.build()}</div></div></div>`; } lang=saved; }
      else h+=cardHTML(sc,zoom); });
    document.getElementById('main').innerHTML=h+'</div>'; document.getElementById('main').style.padding='0';
    document.body.classList.toggle('showgrid', q.has('grid')); document.body.classList.toggle('show-names', q.has('names'));
    return;
  }
  render();
}
