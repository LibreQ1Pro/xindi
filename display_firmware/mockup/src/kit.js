// ---- the pieces of the design: every function returns HTML positioned on the 272 x 480 screen -----------------------
const LANGS = ['zh','ru','en','ja','fr','de','it','es','ko','pt','ar','tr','he'];
const LANG_NAMES = ['中文简体','Русский','English','日本語','Français','Deutsch','Italiano','Español','한국어','Português','العربية','Türkçe','עברית'];
let lang = 2;
let CUR = '';            // the screen that is being built (the key of its texts)

const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
function anyText(key){ for(const p in TEXTS){ const e=TEXTS[p][key]; if(e && (e[lang]||e[2])) return e; } return null; }
function T(key, page, fb){
  const p = page || CUR;
  let e = (TEXTS[p] || {})[key];
  if(!e || !(e[lang]||e[2])) e = anyText(key) || e;
  let v = e && (e[lang] || e[2]);
  if (v == null || v === '') v = (fb != null ? fb : key);
  return esc(v).replace(/\n/g,'<br>');
}
function raw(key, page){ const e=(TEXTS[page||CUR]||{})[key]; return e && (e[lang]||e[2]) || ''; }
const isRtl = () => lang === 10 || lang === 12;
const ICONS_CACHE = {};
function ico(name, size, color, sw){
  const s = ICONS[name] || ICONS['image'];
  const w = sw || 2;
  return `<span class="ico" style="width:${size}px;height:${size}px;color:${color||'currentColor'}">${s.replace('stroke-width="2"','stroke-width="'+w+'"')}</span>`;
}
const st = (x,y,w,h,extra) => `left:${x}px;top:${y}px;width:${w}px;height:${h}px;${extra||''}`;
function nm(name){ return name ? ` data-w="${CUR}.${name}"` : ''; }
function box(x,y,w,h,cls,inner,name,extra){ return `<div class="${cls||''}"${nm(name)} title="${name?CUR+'.'+name+'  '+x+','+y+'  '+w+'×'+h:''}" style="${st(x,y,w,h,extra)}">${inner||''}</div>`; }
function rect(x,y,w,h,color,r,extra){ return `<div style="${st(x,y,w,h)}background:${color};border-radius:${r||0}px;${extra||''}"></div>`; }
// text: o = {c:center, r:right, s/m/l/xl/d: size class, mute, acc, red, top, bottom}
function txt(x,y,w,h,content,o,name){
  o = o || {};
  const cls = ['t', o.a==='c'?'c':'', o.a==='r'?'r':'', o.sz||'m', o.mute?'mute':'', o.acc?'acc':'', o.red?'red':'', o.v==='top'?'top':'', o.v==='bottom'?'bottom':'', isRtl()&&!o.num?'rtl':''].join(' ');
  return `<div class="${cls}"${nm(name)} title="${name?CUR+'.'+name+'  '+x+','+y+'  '+w+'×'+h:''}" style="${st(x,y,w,h,o.css)}"><span>${content}</span></div>`;
}

// A value with units on the screen: a text widget draws one font only, so "35 %" is two widgets (number, unit), each as wide as its
// text (the host knows the widths from the font and sets x), and their baselines lie on one line (y is computed from the font
// metrics: the baseline of a centred line is y + h/2 + 0.388*size for the preview font; measure the real .zi font and put its numbers here).
const _cv = document.createElement('canvas').getContext('2d');
function measure(t,size,weight){ _cv.font = `${weight||400} ${size}px 'Noto Sans'`; return Math.ceil(_cv.measureText(t).width); }
// parts: [{t, s:size, w:weight, c:colour}], the first is the main one. y,h: the box of the main part. align l/c/r inside x..x+w
function vals(x,y,w,h,parts,align,name,gap){
  gap = gap == null ? 3 : gap;
  const ws = parts.map(p => measure(p.t,p.s,p.w)+1);
  const total = ws.reduce((a,b)=>a+b,0) + gap*(parts.length-1);
  let cx = align==='r' ? x+w-total : align==='c' ? x+Math.round((w-total)/2) : x;
  const base = y + h/2 + 0.388*parts[0].s;
  return parts.map((p,i)=>{
    const ph = Math.ceil(p.s*1.4/2)*2, py = Math.round(base - ph/2 - 0.388*p.s);
    const out = `<div class="t vp"${i===0?nm(name):''} title="${name?CUR+'.'+name+(i?'_u'+i:'')+'  '+cx+','+py+'  '+ws[i]+'×'+ph:''}" style="${st(cx,py,ws[i],ph)};font-size:${p.s}px;font-weight:${p.w||400};color:${p.c||'var(--text)'}"><span style="white-space:nowrap">${p.t}</span></div>`;
    cx += ws[i] + gap; return out;
  }).join('');
}
const tt = (x,y,w,h,key,o,name) => txt(x,y,w,h,T(key),o,name||key);   // a text widget of the page
// buttons
function btn(x,y,w,h,label,o,name){
  o = o || {};
  const cls = ['btn', o.v||'', o.press?'press':'', o.wrap?'wrap':''].join(' ');
  const inner = (o.icon?ico(o.icon,o.is||22,o.ic):'') + (label?`<span${isRtl()?' class="rtl"':''} style="padding:0 6px">${label}</span>`:'');
  return `<div class="${cls}"${nm(name)} title="${name?CUR+'.'+name+'  '+x+','+y+'  '+w+'×'+h:''}" style="${st(x,y,w,h,o.css)}">${inner}</div>`;
}
const tb = (x,y,w,h,key,o,name) => btn(x,y,w,h,T(key),o,name||key);
function row(x,y,w,h,label,o,name){          // a list row: label on the left, something on the right
  o = o || {};
  let right = '';
  if (o.chev) right = `<div style="${st(w-34,(h-22)/2,22,22)}color:var(--text3)">${ico('chevron-right',22)}</div>`;
  if (o.sw!=null) right = `<div class="sw${o.sw?' on':''}" style="left:${w-56}px;top:${(h-26)/2}px"></div>`;
  if (o.check) right = `<div style="${st(w-38,(h-24)/2,24,24)}color:var(--accent)">${ico('check',24,null,2.5)}</div>`;
  if (o.lock) right = `<div style="${st(w-36,(h-20)/2,20,20)}color:var(--text2)">${ico('lock',20)}</div>`;
  if (o.radio!=null) right = `<div class="radio${o.radio?' on':''}" style="left:14px;top:${(h-22)/2}px"></div>`;
  const left = o.radio!=null ? 46 : 16;
  const lab = txt(left,0,w-left-(o.radio!=null?12:46),h,label,{num:o.num},null);
  const bg = `<div style="${st(0,0,w,h)}background:${o.sel?'var(--btn-hi)':'var(--btn)'};border-radius:12px;${o.press?'opacity:.8':''}"></div>`;
  return `<div${nm(name)} title="${name?CUR+'.'+name+'  '+x+','+y+'  '+w+'×'+h:''}" style="${st(x,y,w,h)}">${bg}${lab}${right}</div>`;
}
const toggle = (x,y,on) => `<div class="sw${on?' on':''}" style="left:${x}px;top:${y}px"></div>`;
function progress(x,y,w,h,pct,name){ return box(x,y,w,h,'bar',`<i style="width:${pct}%"></i>`,name); }
function thumb(x,y,w,h,name,glyph){ return box(x,y,w,h,'thumb',ico(glyph||'image',Math.min(w,h)*0.38,null,1.6),name); }
// chrome
const NAVS = [['house','main'],['sliders-horizontal','adjust'],['folder-open','files'],['settings','settings']];
function nav(active){
  let s='';
  NAVS.forEach((n,i)=>{ s+=`<div class="it${n[1]===active?' on':''}"${nm('nav_'+n[1])} style="left:${68*i}px"><div class="pill">${ico(n[0],22,null,2)}</div></div>`; });
  return `<div class="nav" style="${st(0,424,272,56)}">${s}</div>`;
}
function header(title, o){
  o = o || {};
  const back = btn(4,4,40,40,'',{icon:'chevron-left',is:26,css:'background:transparent'},'back_btn');
  const right = o.right || '';
  return back + txt(48,0,o.tw||200,48,title,{sz:'l',css:'font-weight:600;font-size:19px'},'title') + right + rect(0,48,272,1,'var(--line)');
}
function tabs(l,r,active,names){
  const n = names || ['tab_calib','tab_settings'];
  return `<div class="tabs" style="${st(12,8,248,40)}">`+
    `<div class="tab${active==='l'?' on':''}"${nm(n[0])} style="${st(3,3,121,34)}">${T(n[0])}</div>`+
    `<div class="tab${active==='r'?' on':''}"${nm(n[1])} style="${st(124,3,121,34)}">${T(n[1])}</div></div>`;
}
const card = (x,y,w,h,extra) => `<div class="card" style="${st(x,y,w,h,extra)}"></div>`;
function screen(page, body, o){
  o = o || {};
  CUR = page;
  return `<div class="scr" data-page="${page}">${body}<div class="grid-ov"></div><div class="guide" style="${st(12,0,248,480)}"></div></div>`;
}
// heater icons (Lucide has no nozzle / bed / chamber): drawn here
const HEAT = {
  nozzle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v6l-3 3v3l-3 4-3-4v-3L6 9z"/></svg>',
  bed: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18h18"/><path d="M7 14c-1.5-1.5 1.5-2.500 0-4M12 14c-1.5-1.5 1.500-2.500 0-4M17 14c-1.500-1.500 1.500-2.500 0-4"/><path d="M3 21h18"/></svg>',
  chamber: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M12 7v7"/><circle cx="12" cy="16.5" r="2"/></svg>'
};
function hico(name,size,color){ return `<span class="ico" style="width:${size}px;height:${size}px;color:${color||'currentColor'}">${HEAT[name]}</span>`; }
