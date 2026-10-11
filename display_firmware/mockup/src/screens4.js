// ---- screens: pop-ups, guide, boot ---------------------------------------------------------------------------------
function popup(page, kind, msgs, btns, o){
  o = o || {};
  CUR = page;
  const col = {info:'var(--accent)',warn:'var(--warn)',error:'var(--danger)',ok:'var(--ok)',ask:'var(--accent)'}[kind];
  const g = {info:'info',warn:'triangle-alert',error:'octagon-x',ok:'circle-check',ask:'info'}[kind];
  let s = rect(0,0,272,480,'#0c0c0e');
  s += `<div class="popup" style="${st(12,84,248,324)}"></div>`;
  s += `<div style="${st(112,100,48,48)}border-radius:24px;background:color-mix(in srgb, ${col} 18%, transparent);color:${col};display:flex;align-items:center;justify-content:center">${ico(g,26)}</div>`;
  if (msgs.length === 1) s += tt(28,158,216,160,msgs[0],{a:'c',v:'top',css:'font-size:15px'},msgs[0]);
  else { s += tt(28,158,216,90,msgs[0],{a:'c',v:'top',css:'font-size:15px'},msgs[0]); s += tt(28,248,216,60,msgs[1],{a:'c',v:'top',sz:'l'},msgs[1]); }
  if (btns.length === 1) s += tb(28,336,216,48,btns[0][0],{v:btns[0][1]||'primary'},btns[0][0]);
  else s += tb(28,336,104,48,btns[0][0],{v:btns[0][1]||'primary',wrap:1,css:'font-size:15px'},btns[0][0]) + tb(140,336,104,48,btns[1][0],{v:btns[1][1]||'',wrap:1,css:'font-size:15px'},btns[1][0]);
  return screen(page, s);
}
const POPS = [
  ['open_pop','ask',['msg'],[['ok','primary'],['cancel','']],'Setup guide: skip?'],
  ['print_finish','ok',['msg','time_txt'],[['ok','primary']],'Print complete'],
  ['print_stop','ask',['msg'],[['ok','danger'],['cancel','']],'Stop printing?'],
  ['stop_confirm','ask',['msg'],[['ok','danger'],['cancel','']],'Stop: are you sure?'],
  ['resume_print','ask',['msg'],[['ok','primary'],['cancel','']],'Resume the last print?'],
  ['print_no_fil','warn',['msg'],[['ok','primary']],'No filament'],
  ['print_no_fil2','warn',['msg'],[['ok','primary']],'Filament tangle'],
  ['print_lowtemp','warn',['msg'],[['ok','primary']],'Nozzle too cold'],
  ['preview_pop_1','warn',['msg'],[['ok','primary'],['no_more','']],'Closed chamber warning'],
  ['preview_pop_2','warn',['msg'],[['ok','primary'],['no_more','']],'Doors and cover'],
  ['move_pop_1','warn',['msg'],[['ok','primary']],'Out of range'],
  ['move_pop_2','ask',['msg'],[['ok','primary'],['cancel','']],'Home the axes?'],
  ['filament_pop_1','warn',['msg'],[['ok','primary']],'Nozzle temperature too low'],
  ['unload_finish','ok',['msg'],[['ok','primary']],'Unloading done'],
  ['auto_warning','warn',['msg'],[['ok','primary']],'Set the temperature'],
  ['cal_warning','warn',['msg'],[['next_btn','primary'],['back_btn','']],'Before calibrating'],
  ['level_error','error',['msg'],[['ok','primary']],'Leveling error'],
  ['detect_error','error',['msg'],[['ok','primary']],'Error'],
  ['gcode_error','error',['msg'],[['ok','primary']],'G-code error'],
  ['memory_warning','warn',['msg'],[['ok','primary']],'Memory is full'],
  ['restore_config','ask',['msg'],[['ok','danger'],['cancel','']],'Restore factory settings?'],
  ['update_success','ok',['msg'],[['ok','primary']],'Update complete'],
  ['print_log_s','ok',['msg'],[['ok','primary']],'Logs exported'],
  ['print_log_f','error',['msg'],[['ok','primary']],'Export failed'],
  ['wifi_success','ok',['msg'],[['ok','primary']],'Connected'],
  ['wifi_fail','error',['msg'],[['ok','primary']],'Connection failed'],
];
POPS.forEach(p=>S(p[0],'Pop-ups',p[4],()=>popup(p[0],p[1],p[2],p[3])));
['print_stopping','re_printing','syntony_move','bed_moving'].forEach(id=>S(id,'Pop-ups',{print_stopping:'Stopping',re_printing:'Resuming',syntony_move:'Input shaping',bed_moving:'Moving the bed'}[id],()=>{CUR=id;return screen(id,busy('msg'));}));

// -- guide
function guide(page, title, body){ CUR=page; return screen(page, txt(16,8,240,32,title,{sz:'l'},'title') + body); }
function nextRound(x,y){ return btn(x,y,64,64,'',{icon:'chevron-right',is:30,v:'primary',css:'border-radius:32px'},'next'); }
S('open_language','Setup guide','Language (first start)',()=>{
  CUR='open_language';
  let s = txt(16,8,240,32,T('title'),{sz:'l'},'title');
  ['lang_cn','lang_ru','lang_en','lang_jp','lang_fr','lang_de','lang_it','lang_es'].forEach((n,i)=>{
    const x=12+128*(i%2), y=52+68*Math.floor(i/2), sel=n==='lang_en';
    s += `<div style="${st(x,y,120,60)}background:${sel?'var(--btn-hi)':'var(--btn)'};border-radius:12px"></div><div class="radio${sel?' on':''}" style="left:${x+12}px;top:${y+19}px"></div>`+txt(x+42,y,74,60,T(n+'_name'),{num:1},n+'_name');
  });
  s += btn(12,330,120,44,'',{icon:'chevron-up',is:24,v:'dim'},'prev_page')+btn(140,330,120,44,'',{icon:'chevron-down',is:24},'next_page');
  s += tb(12,424,120,46,'skip',{},'skip')+tb(140,424,120,46,'next',{v:'primary'},'next');
  return screen('open_language', s);
});
S('open_video_1','Setup guide','Unboxing',()=>{CUR='open_video_1';return guide('open_video_1',T('title'),box(12,48,248,190,'anim','animation 248 × 190')+tt(16,252,240,70,'msg',{a:'c'},'msg')+nextRound(196,404));});
S('open_warning','Setup guide','Unboxing: warning',()=>{CUR='open_warning';return guide('open_warning',T('title'),`<div style="${st(112,70,48,48)}border-radius:24px;background:rgba(245,165,36,.18);color:var(--warn);display:flex;align-items:center;justify-content:center">${ico('triangle-alert',26)}</div>`+tt(20,132,232,240,'msg',{a:'c',v:'top'},'msg')+btn(12,418,248,48,'',{icon:'chevron-right',is:28,v:'primary'},'next'));});
S('filamentVideo1','Setup guide','Load filament: insert',()=>{CUR='filamentVideo1';return guide('filamentVideo1',T('title'),box(12,48,248,190,'anim','animation 248 × 190')+tt(16,250,240,110,'msg',{a:'c'},'msg')+nextRound(196,404));});
S('filamentVideo2','Setup guide','Load filament: heat',()=>{
  CUR='filamentVideo2';
  let s = txt(16,8,240,32,T('title'),{sz:'l'},'title');
  s += heatEdit(12,52,248,'nozzle','220','220',true,'heat');
  s += btn(12,110,120,46,'',{icon:'minus',is:26},'temp_down')+btn(140,110,120,46,'',{icon:'plus',is:26},'temp_up');
  s += tt(16,176,240,90,'msg_heat',{a:'c',mute:1},'msg_heat') + tt(16,272,170,100,'msg_wait',{v:'top',css:'color:var(--warn);font-size:15px'},'msg_wait') + nextRound(196,404);
  return screen('filamentVideo2', s);
});
S('filamentVideo3','Setup guide','Load filament: extrude',()=>{
  CUR='filamentVideo3';
  let s = txt(16,8,240,32,T('title'),{sz:'l'},'title') + box(12,48,248,190,'anim','animation 248 × 190');
  s += btn(86,246,100,44,'',{icon:'arrow-down',is:24},'extrude') + tt(16,300,240,110,'msg',{a:'c',mute:1},'msg') + btn(12,418,248,48,'',{icon:'chevron-right',is:28,v:'primary'},'next');
  return screen('filamentVideo3', s);
});
S('open_finish','Setup guide','Guide finished',()=>{
  CUR='open_finish';
  let s = `<div style="${st(96,60,80,80)}border-radius:40px;background:rgba(48,164,108,.18);color:var(--ok);display:flex;align-items:center;justify-content:center">${ico('circle-check',44)}</div>`;
  s += tt(16,160,240,100,'msg',{a:'c',sz:'l'},'msg') + tt(16,262,240,120,'msg_level',{a:'c',mute:1},'msg_level') + tb(12,418,248,48,'finish',{v:'primary'},'finish');
  return screen('open_finish', s);
});
function stepsScreen(page, ys, active, buttons){
  CUR=page;
  let s = '';
  const keys=['step1_txt','step2_txt','step3_txt','step4_txt'].filter(k=>(TEXTS[page]||{})[k]);
  keys.forEach((k,i)=>{
    const done=i<active,on=i===active;
    s += `<div class="step${done?' done':on?' on':''}" style="${st(14,ys[i]+2,26,26)}">${done?ico('check',16,'#fff',3):i+1}</div>`;
    if(i<keys.length-1) s += `<div class="vline" style="${st(26,ys[i]+34,2,ys[i+1]-ys[i]-38)}"></div>`;
    s += tt(52,ys[i],208,34,k,{v:'top',mute:!on,css:on?'font-weight:600':''},k);
  });
  return s + buttons;
}
S('filament_pop_2','Setup guide','Unload filament (steps)',()=>{
  let s = stepsScreen('filament_pop_2',[16,252,312,372],1,'');
  s += tt(52,50,208,24,'hint',{v:'top',mute:1,sz:'s'},'hint') + box(52,76,208,150,'anim','animation') + txt(52,282,208,26,'(250/250 °C)',{sz:'s',mute:1,num:1},'temp_txt');
  s += tb(12,418,120,48,'back_btn',{},'back_btn')+tb(140,418,120,48,'next_btn',{v:'primary'},'next_btn');
  return screen('filament_pop_2', s);
});
S('filament_pop_3','Setup guide','Load filament (steps)',()=>{
  let s = stepsScreen('filament_pop_3',[16,252,312,372],2,'');
  s += tt(52,50,208,24,'hint',{v:'top',mute:1,sz:'s'},'hint') + box(52,76,208,150,'anim','animation');
  s += tb(12,418,120,48,'back_btn',{},'back_btn')+tb(140,418,120,48,'done_btn',{v:'primary'},'done_btn');
  return screen('filament_pop_3', s);
});
S('unload_mode','Setup guide','Unload: choose',()=>{
  CUR='unload_mode';
  let s = tt(16,12,240,100,'msg',{a:'c'},'msg');
  s += tb(12,124,248,52,'manual_btn',{},'manual_btn') + tt(16,182,240,60,'hint',{a:'c',mute:1,sz:'s'},'hint');
  s += tb(12,254,248,52,'auto_btn',{},'auto_btn') + tt(16,314,240,100,'warn',{a:'c',css:'color:var(--warn);font-size:14px'},'warn');
  s += tb(12,424,248,46,'back_btn',{},'back_btn');
  return screen('unload_mode', s);
});
S('auto_unload','Setup guide','Automatic unload',()=>{
  let s = stepsScreen('auto_unload',[16,140,262],1,'');
  s += txt(52,50,208,24,'(220/220 °C)',{sz:'s',mute:1,num:1},'temp_txt');
  s += tb(12,368,248,46,'load_btn',{},'load_btn') + tb(12,422,248,46,'ok',{v:'primary'},'ok');
  return screen('auto_unload', s);
});
S('pre_heat','Setup guide','Preheat: choose temperature',()=>{
  CUR='pre_heat';
  let s = rect(0,0,272,480,'#0c0c0e') + `<div class="popup" style="${st(12,84,248,324)}"></div>`;
  s += tt(28,100,216,80,'msg',{a:'c',v:'top',css:'font-size:15px'},'msg');
  ['220','250','300'].forEach((v,i)=>{ const sel=i===0; s += `<div${nm('temp_opt'+(i+1))} style="${st(28+76*i,200,68,74)};background:${sel?'var(--btn-hi)':'var(--btn)'};border-radius:12px"></div><div class="radio${sel?' on':''}" style="left:${28+76*i+23}px;top:210px"></div>`+txt(28+76*i,238,68,30,v+' °C',{a:'c',num:1}); });
  s += tb(28,336,104,48,'back_btn',{},'back_btn')+tb(140,336,104,48,'next_btn',{v:'primary'},'next_btn');
  return screen('pre_heat', s);
});
// -- boot
S('logo','Boot','Boot logo',()=>{
  CUR='logo';
  return screen('logo', `<div style="${st(36,120,200,120)}border-radius:20px;background:#1f1f25;display:flex;align-items:center;justify-content:center;color:#6c6c78;font-size:12px;letter-spacing:.08em">QIDI TECH LOGO</div>`+txt(16,330,240,50,T('boot_msg'),{a:'c',mute:1},'boot_msg'));
});
S('restart','Boot','Restart needed',()=>{
  CUR='restart';
  return screen('restart', `<div style="${st(112,100,48,48)}color:var(--danger)">${ico('triangle-alert',44)}</div>`+txt(16,168,240,70,T('title'),{a:'c',sz:'l'},'title')+txt(24,250,224,120,T('hint'),{a:'c',mute:1},'hint'));
});
S('shutdown','Boot','Shutting down',()=>{
  CUR='shutdown';
  return screen('shutdown', `<div style="${st(116,170,40,40)};color:var(--text2)">${ico('power-off',40)}</div>`+txt(16,230,240,50,T('msg'),{a:'c'},'msg'));
});

S('open_video_2','Setup guide','Unboxing 2',()=>{CUR='open_video_2';return guide('open_video_2',T('title'),box(12,48,248,190,'anim','animation 248 × 190')+tt(16,252,240,70,'msg',{a:'c'},'msg')+nextRound(196,404));});
S('filamentVideo0','Setup guide','Filament holder',()=>{CUR='filamentVideo0';return guide('filamentVideo0',T('title'),box(12,48,248,190,'anim','animation 248 × 190')+tt(16,250,240,110,'msg',{a:'c'},'msg')+nextRound(196,404));});
S('open_moving','Setup guide','Please wait',()=>{CUR='open_moving';return guide('open_moving',T('title'),`<div style="${st(116,150,40,40)};border:3px solid #34343c;border-top-color:var(--accent);border-radius:50%"></div>`+tt(20,214,232,200,'msg',{a:'c',v:'top'},'msg'));});
