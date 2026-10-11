// ---- screens: filament, fans, move, calibration ---------------------------------------------------------------------
function seg(x,y,w,h,labels,active,names){
  const n = labels.length, cw = (w-6)/n;
  return `<div class="tabs" style="${st(x,y,w,h)}">` + labels.map((l,i)=>`<div class="tab${i===active?' on':''}"${nm(names&&names[i])} style="${st(3+cw*i,3,cw,h-6)};font-size:15px">${l}</div>`).join('') + '</div>';
}
function heatEdit(x,y,w,glyph,cur,tar,on,name){     // toggle + current / target
  return btn(x,y,50,50,'',{icon:'',css:'background:'+(on?'var(--danger-bg)':'var(--btn)')},name+'_toggle') +
    `<div style="${st(x+12,y+12,26,26)}color:${on?HOT:'var(--text2)'}">${hico(glyph,26)}</div>` +
    box(x+58,y,w-58,50,'card hi','',name+'_row') +
    txt(x+70,y,w-74,50,`<b style="font-size:22px;font-weight:600;color:${on?HOT:'var(--text)'}">${cur}</b><span style="font-size:16px;color:var(--text3)"> / ${tar}</span><span style="font-size:13px;color:var(--text2)"> °C</span>`,{num:1},name+'_temp');
}
S('filament','Filament and movement','Filament',()=>{
  CUR='filament';
  let s = tabs('l','r','l',['tab_load','tab_manual']);
  s += heatEdit(12,56,198,'nozzle',220,220,true,'nozzle')+heatEdit(12,114,198,'bed',60,60,true,'bed')+heatEdit(12,172,198,'chamber',35,0,false,'chamber');
  s += btn(218,56,42,166,'',{icon:'fan',is:24},'fan_btn');
  s += tb(12,230,120,46,'load_btn',{},'load_btn')+tb(140,230,120,46,'replace_btn',{wrap:1},'replace_btn');
  s += seg(12,284,248,40,['10 mm','50 mm','100 mm'],1,['step_10','step_50','step_100']);
  s += btn(12,332,120,64,'',{icon:'arrow-up',is:28},'extr_up')+btn(140,332,120,64,'',{icon:'arrow-down',is:28},'extr_down');
  s += nav('adjust');
  return screen('filament', s);
}, 'The icon at the left of a heater is its switch (red = heating). The tall button opens the fans.');

S('fans','Filament and movement','Fans',()=>{
  CUR='fila_set_fan';
  let s = header('') ;
  [[56,'fan1_name',0,false],[172,'fan2_name',60,true],[288,'fan3_name',100,true]].forEach((f,i)=>{
    const [y,key,val,on]=f; const n=i+1;
    s += card(12,y,248,108,'');
    s += tt(24,y+4,224,38,key,{css:'font-size:15px;line-height:1.15;font-weight:500'},key);
    const tx=36, tw=200, kx=tx+tw*val/100;
    s += box(tx,y+52,tw,10,'bar','<i style="width:'+val+'%"></i>','fan'+n+'_slider');
    [20,40,60,80,100].forEach(v=>{ s += rect(tx+tw*v/100-1,y+66,2,6,'#4a4a54',1); });
    s += `<div style="${st(kx-14,y+43,28,28)}background:#fff;border-radius:14px"></div>`;
    s += box(24,y+78,60,26,'', toggle(0,0,on),'fan'+n+'_toggle');
    s += txt(140,y+74,108,30,`<b style="font-size:22px">${val}</b><span style="font-size:14px;color:var(--text2)"> %</span>`,{a:'r',num:1},'fan'+n+'_val');
  });
  s += nav('adjust');
  return screen('fila_set_fan', s);
});

S('move','Filament and movement','Move',()=>{
  CUR='move';
  let s = tabs('l','r','r',['tab_load','tab_manual']);
  s += card(12,56,248,44,'');
  ['X','Y','Z'].forEach((a,i)=>{ s += txt(24+80*i,56,16,44,'<span style="color:var(--text2);font-weight:600">'+a+'</span>',{num:1}) + txt(42+80*i,56,52,44,'0.00',{num:1},a.toLowerCase()+'_pos'); });
  s += seg(12,108,248,40,['0.1 mm','1 mm','10 mm'],1,['dist_01','dist_1','dist_10']);
  // control: a pad 188 x 188 with 52-pixel keys 8 apart and 8 from the edge, the Z keys at its right (8 away)
  s += `<div style="${st(12,156,188,188)}background:var(--panel);border-radius:94px"></div>`;
  s += btn(80,164,52,52,'',{icon:'chevron-up',is:28},'y_up')+btn(20,224,52,52,'',{icon:'chevron-left',is:28},'x_down')+btn(140,224,52,52,'',{icon:'chevron-right',is:28},'x_up')+btn(80,284,52,52,'',{icon:'chevron-down',is:28},'y_down');
  s += btn(80,224,52,52,'',{icon:'house',is:24,css:'border-radius:26px;background:var(--btn-hi)'},'home_btn');
  s += btn(208,156,52,90,'',{icon:'chevrons-up',is:28},'z_up')+btn(208,254,52,90,'',{icon:'chevrons-down',is:28},'z_down');
  s += btn(12,352,248,44,'',{icon:'power',is:22,v:'dim'},'motors_off');
  s += nav('adjust');
  return screen('move', s);
});

S('keypad','Filament and movement','Number keyboard',()=>{
  CUR='filament_kb';
  let s = header(T('title@sys1=0','filament_kb'));
  s += card(12,56,248,72,'background:#111114');
  s += txt(24,60,160,44,'<span style="font-size:32px;font-weight:600">220</span><span style="font-size:18px;color:var(--text2)"> °C</span>',{a:'r',num:1},'input_show');
  s += txt(24,102,224,22,'MAX : 350',{sz:'s',mute:1,num:1},null);
  ['1','2','3','4','5','6','7','8','9','del','0','ok'].forEach((k,i)=>{
    const c=i%3,r=Math.floor(i/3); const fn=(k==='del'||k==='ok');
    s += `<div class="key${fn&&k==='del'?' fn':''}"${nm('key_'+k)} style="${st([12,97,183][c],136+66*r,[77,78,77][c],58)};font-size:26px${k==='ok'?';background:var(--accent)':''}">${k==='del'?ico('delete',24):k==='ok'?ico('check',28,'#fff',2.5):k}</div>`;
  });
  s += nav('adjust');
  return screen('filament_kb', s);
});

// -- calibration
S('level','Calibration','Calibration menu',()=>{
  CUR='level_mode';
  let s = tabs('l','r','l',['tab_calib','tab_settings']);
  s += `<div style="${st(12,58,248,148)}border:1.5px dashed #4a4a54;border-radius:14px"></div>`;
  s += tt(24,62,224,140,'msg',{a:'c',mute:1},'msg');
  s += row(12,214,248,50,T('auto_level'),{chev:1},'auto_level')+row(12,272,248,50,T('shaping'),{chev:1},'shaping')+row(12,330,248,50,T('bed_calib'),{chev:1},'bed_calib');
  s += nav('settings');
  return screen('level_mode', s);
});

function wizardFrame(page, title){ CUR=page; return txt(16,8,240,32,title,{sz:'l'},'title'); }
function stepper(page, y, steps, active, names){
  let s='';
  steps.forEach((t,i)=>{
    const done=i<active, on=i===active;
    s += `<div class="step${done?' done':on?' on':''}" style="${st(14,y[i],26,26)}">${done?ico('check',16,'#fff',3):i+1}</div>`;
    if(i<steps.length-1) s += `<div class="vline" style="${st(26,y[i]+32,2,y[i+1]-y[i]-38)}"></div>`;
    s += txt(52,y[i]-12,208,50,t,{mute:!on,css:on?'':''},names&&names[i]);
  });
  return s;
}
S('auto_moving','Calibration','Auto leveling in progress',()=>{
  CUR='auto_moving';
  let s='';
  const ys=[36,150,264,378];
  s += stepper('auto_moving',ys,[T('step1_txt'),T('step2_txt'),T('step3_txt'),T('step4_txt')],1,['step1_txt','step2_txt','step3_txt','step4_txt']);
  s += card(12,438,248,30,'') + txt(24,438,224,30,T('bed_lbl')+' <b>(120/120)</b>',{sz:'s',num:1},'bed_temp');
  return screen('auto_moving', s);
});
S('auto_heaterbed','Calibration','Preheat the bed',()=>{
  CUR='auto_heaterbed';
  let s = header('');
  s += heatEdit(12,56,248,'bed',120,120,true,'heat');
  s += btn(12,114,120,46,'',{icon:'minus',is:26},'temp_down')+btn(140,114,120,46,'',{icon:'plus',is:26},'temp_up');
  s += tt(16,176,240,230,'msg',{a:'c',mute:1},'msg');
  s += btn(12,420,248,46,'',{icon:'chevron-right',is:28,v:'primary'},'next_btn');
  return screen('auto_heaterbed', s);
});
S('pre_bed_cal','Calibration','Adjust the reference point',()=>{
  CUR='pre_bed_cal';
  let s = box(12,12,248,70,'anim','platform illustration');
  ['0.01','0.05','0.1','0.5'].forEach((v,i)=>{ s += `<div class="btn${i===1?' primary':''}"${nm('step_'+v.replace('.',''))} style="${st(12+64*i,90,56,46)}">${v}</div>`; });
  s += btn(12,144,120,46,'',{icon:'chevron-up',is:26},'z_up')+btn(140,144,120,46,'',{icon:'chevron-down',is:26},'z_down');
  s += tt(12,198,248,46,'title',{a:'c',acc:1,sz:'l',css:'font-size:17px;line-height:1.15'},'title')+tt(16,252,240,160,'msg',{a:'c',mute:1},'msg');
  s += btn(12,420,248,46,'',{icon:'chevron-right',is:28,v:'primary'},'enter_btn');
  return screen('pre_bed_cal', s);
});
S('bed_calibrate','Calibration','Nut adjusting',()=>{
  CUR='bed_calibrate';
  let s = box(12,12,248,170,'anim','nut illustration');
  s += tt(12,194,248,32,'step_txt',{a:'c',acc:1,sz:'l'},'step_txt')+tt(16,230,240,180,'msg',{a:'c',mute:1},'msg');
  s += btn(12,420,248,46,'',{icon:'chevron-right',is:28,v:'primary'},'next_btn');
  return screen('bed_calibrate', s);
});
S('bed_finish','Calibration','Choose a nut',()=>{
  CUR='bed_finish';
  let s = box(12,12,248,150,'anim','platform with three nuts');
  s += btn(86,24,100,40,'Nut 3',{},'screw3')+btn(32,100,100,40,'Nut 1',{},'screw1')+btn(140,100,100,40,'Nut 2',{},'screw2');
  s += tt(16,176,240,230,'msg',{a:'c',mute:1},'msg');
  s += tb(12,420,248,46,'ok',{v:'primary'},'ok');
  return screen('bed_finish', s);
});
S('zoffset','Calibration','Z offset table',()=>{
  CUR='zoffset';
  let s = header('');
  const table=(y,cols,ofs)=>{ let h=''; const cw=Math.floor(248/cols);
    for(let r=0;r<6;r++) for(let c=0;c<cols;c++){ const head=r===0;
      h += `<div style="${st(12+cw*c,y+30*r,cw,30)}display:flex;align-items:center;justify-content:center;background:${head?'#2d2d35':r%2?'var(--panel)':'#1e1e22'};font-size:${head?13:14}px;color:${head?'var(--text2)':'var(--text)'};font-weight:${head?600:400};font-variant-numeric:tabular-nums;border-radius:${r===0&&c===0?'8px 0 0 0':r===0&&c===cols-1?'0 8px 0 0':r===5&&c===0?'0 0 0 8px':r===5&&c===cols-1?'0 0 8px 0':0}">${head?T('cell_'+(ofs+c)):'0.000'}</div>`; }
    return h; };
  s += table(60,3,25)+table(260,2,28);
  return screen('zoffset', s);
}, 'Two tables of the mesh: 3 + 2 columns, 5 rows. Header cells are the stock texts.');
S('auto_finish','Calibration','Calibration done',()=>{
  CUR='auto_finish';
  let s = `<div style="${st(96,110,80,80)}border-radius:40px;background:rgba(48,164,108,.18);color:var(--ok);display:flex;align-items:center;justify-content:center">${ico('circle-check',44,null,2)}</div>`;
  s += tt(16,210,240,120,'msg',{a:'c'},'msg') + tb(12,420,248,46,'ok',{v:'primary'},'ok');
  return screen('auto_finish', s);
});

S('syntony_finish','Calibration','Input shaping done',()=>{
  CUR='syntony_finish';
  let s = `<div style="${st(96,110,80,80)}border-radius:40px;background:rgba(48,164,108,.18);color:var(--ok);display:flex;align-items:center;justify-content:center">${ico('circle-check',44)}</div>`;
  s += tt(16,210,240,120,'msg',{a:'c'},'msg') + tb(12,420,248,46,'ok',{v:'primary'},'ok');
  return screen('syntony_finish', s);
});
