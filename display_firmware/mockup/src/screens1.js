// ---- screens: Home, files, print ------------------------------------------------------------------------------------
const SCREENS = [];
function S(id, group, title, build, note){ SCREENS.push({id, group, title, build, note}); }
const HOT = '#ff7a59';

function heaterTile(x,y,w,h,glyph,temp,on,name,target){
  return box(x,y,w,h,'card hi','',name) +
    `<div style="${st(x+14,y+(h-26)/2,26,26)}color:${on?HOT:'var(--text2)'}">${hico(glyph,26)}</div>` +
    txt(x+48,y,w-56,h,`<b style="font-size:28px;font-weight:600;color:${on?HOT:'var(--text)'}">${temp}</b><span style="font-size:14px;color:var(--text2)"> °C${target?' <span style="color:var(--text3)">/ '+target+'</span>':''}</span>`,{num:1},null);
}
function iconTile(x,y,w,h,glyph,on,name,o){
  o = o || {};
  const bg = o.v==='danger' ? 'background:var(--danger-bg)' : on ? 'background:var(--accent)' : '';
  return box(x,y,w,h,'btn',ico(glyph,24,o.v==='danger'?'#ff8d91':on?'#fff':'var(--text2)',2),name,bg);
}

S('home','Home and files','Home',()=>{
  CUR='main';
  let s = '';
  s += `<div style="${st(204,10,22,22)}color:var(--text2)">${ico('usb',20)}</div><div style="${st(232,10,22,22)}color:var(--text2)">${ico('wifi',20)}</div>`;
  s += box(12,38,248,202,'card hi','','last_file_btn');
  s += thumb(66,48,140,140,'last_file_pic');
  s += `<div style="${st(26,48,26,26)}background:#1b1b20;border-radius:13px;opacity:.9"></div><div style="${st(30,52,18,18)}color:#ddd">${ico('clock',18)}</div>`;
  s += txt(24,194,224,40,'Benchy_PLA_0.2mm.gcode',{a:'c',sz:'m',css:'line-height:1.2'},'last_file_name');
  s += heaterTile(12,248,166,52,'nozzle','220',true,'nozzle_btn');
  s += heaterTile(12,306,166,52,'bed','60',true,'bed_btn');
  s += heaterTile(12,364,166,52,'chamber','35',false,'chamber_btn');
  s += iconTile(186,248,74,52,'lightbulb',true,'light_btn');
  s += iconTile(186,306,74,52,'volume-2',false,'beep_btn');
  s += iconTile(186,364,74,52,'octagon-x',false,'stop_btn',{v:'danger'});
  s += nav('main');
  return screen('main', s);
}, 'Heaters are cards, the three switches are tiles: blue means on. Red value = the heater is on.');

S('files','Home and files','File list',()=>{
  CUR='filelist';
  let s = tabs('l','r','l',['local_tab','usb_tab']);
  const entries = [[12,56,'file','Benchy_PLA.gcode',true],[140,56,'dir','models',false],[12,214,'file','calibration_cube.gcode',false],[140,214,'file','part_with_a_very_long_name.gcode',false]];
  entries.forEach((e,i)=>{
    const [x,y,kind,name,last] = e;
    s += box(x,y,120,150,'card hi','','file'+(i+1));
    if(kind==='dir') s += `<div style="${st(x+22,y+14,76,76)}color:#8d8d9b">${ico('folder',64,null,1.5)}</div>`;
    else s += thumb(x+4,y+4,112,112,'file'+(i+1)+'_pic');
    if(last && kind==='file') s += `<div style="${st(x+10,y+10,24,24)}background:#1b1b20;border-radius:12px"></div><div style="${st(x+13,y+13,18,18)}color:#ddd">${ico('clock',18)}</div>`;
    s += txt(x+6,y+116,108,32,name,{a:'c',sz:'s',css:'color:var(--text);line-height:1.15;font-size:13px'},'file'+(i+1)+'_name');
  });
  s += btn(12,372,76,40,'',{icon:'chevron-left',is:24,v:'dim'},'prev')+btn(98,372,76,40,'',{icon:'chevron-right',is:24},'next')+btn(184,372,76,40,'',{icon:'undo-2',is:22},'up_dir');
  s += nav('files');
  return screen('filelist', s);
});

S('preview','Home and files','File preview',()=>{
  CUR='preview';
  let s = thumb(12,12,152,152,'preview_pic');
  s += btn(172,12,88,72,'',{icon:'undo-2',is:30},'back_btn') + btn(172,92,88,72,'',{icon:'play',is:32,v:'primary'},'start_btn');
  s += card(12,176,248,96,'');
  const cell=(x,y,glyph,val,name)=>`<div style="${st(x,y+6,24,24)}color:var(--text2)">${ico(glyph,22)}</div>`+txt(x+34,y,92,36,val,{num:1},name);
  s += cell(26,184,'clock','03h05m','est_time')+cell(146,184,'ruler','7.9 m','fil_length')+cell(26,228,'spool','PLA','fil_type')+cell(146,228,'weight','24 g','fil_weight');
  s += row(12,284,248,46,T('level_lbl'),{sw:true},'level_btn') + row(12,336,248,46,T('timelapse_lbl'),{sw:false},'timelapse_btn');
  s += nav('files');
  return screen('preview', s);
});

// -- printing
function printTop(page, paused){
  CUR=page;
  let s = thumb(12,12,132,132,'thumb');
  s += btn(156,12,104,62,'',{icon:paused?'play':'pause',is:30},'pause_btn') + btn(156,82,104,62,'',{icon:'square',is:26,v:'danger'},'stop_btn');
  s += txt(12,150,248,26,'Benchy_PLA_0.2mm.gcode',{a:'c'},'file_name');
  s += txt(12,178,80,22,'0h10m',{sz:'s',num:1},'time_elapsed') + txt(96,174,80,28,'<b style="font-size:20px">35</b><span style="font-size:13px;color:var(--text2)"> %</span>',{a:'c',num:1},'progress_pct') + txt(180,178,80,22,'0h18m',{a:'r',sz:'s',num:1},'time_left');
  s += progress(12,206,248,8,35,'progress');
  return s;
}
function heatRow(x,y,w,glyph,cur,tar,on,name){
  return box(x,y,w,50,'card hi','',name) + `<div style="${st(x+12,y+12,26,26)}color:${on?HOT:'var(--text2)'}">${hico(glyph,26)}</div>` +
    txt(x+44,y,w-50,50,`<b style="font-size:24px;font-weight:600;color:${on?HOT:'var(--text)'}">${cur}</b><span style="font-size:16px;color:var(--text3)"> / ${tar}</span><span style="font-size:13px;color:var(--text2)"> °C</span>`,{num:1},null);
}
function fanTile(x,y,w,h,i,val,name){
  return box(x,y,w,h,'card hi','',name) + `<div style="${st(x+10,y+13,24,24)}color:var(--text2)">${ico('fan',22)}</div>` +
    `<div style="${st(x+30,y+30,14,14)}font-size:11px;color:var(--text3)">${i}</div>` +
    txt(x+34,y,w-40,h,`<b style="font-size:20px">${val}</b><span style="font-size:13px;color:var(--text2)"> %</span>`,{a:'r',num:1},name+'_val');
}
S('printing','Printing','Printing',()=>{
  let s = printTop('printing');
  s += heatRow(12,226,164,'nozzle',220,220,true,'nozzle_btn')+heatRow(12,282,164,'bed',60,60,true,'bed_btn')+heatRow(12,338,164,'chamber',35,0,false,'chamber_btn');
  s += fanTile(184,226,76,50,1,100,'fan1_btn')+fanTile(184,282,76,50,2,0,'fan2_btn')+fanTile(184,338,76,50,3,60,'fan3_btn');
  s += btn(12,402,124,52,'',{icon:'layers',is:24},'speed_btn')+btn(144,402,116,52,'',{icon:'octagon-x',is:24,v:'danger'},'flow_btn');
  return screen('printing', s);
}, 'Pause / stop are large tiles next to the thumbnail; the lower half is the heaters and fans; the two buttons at the bottom open page 2 and stop the machine.');

S('printing2','Printing','Printing 2',()=>{
  let s = printTop('printing_2');
  const tool = (x,y,glyph,val,unit,name)=> box(x,y,76,92,'card hi','',name)+`<div style="${st(x+26,y+12,24,24)}color:var(--text2)">${ico(glyph,24)}</div>`+txt(x,y+46,76,40,`<b style="font-size:20px">${val}</b><span style="font-size:13px;color:var(--text2)"> ${unit}</span>`,{a:'c',num:1},name+'_val');
  s += tool(12,226,'arrow-up-down','-1.000','mm','zoffset_btn')+tool(98,226,'gauge','100','%','speed_btn')+tool(184,226,'droplet','100','%','flow_btn');
  s += box(12,326,76,92,'btn','<div style="position:static;display:flex;flex-direction:column;align-items:center;gap:10px">'+ico('lightbulb',26,'#ffd36b')+'<div style="position:relative;width:44px;height:26px" class="sw on"></div></div>','light_btn');
  s += btn(184,326,76,92,'',{icon:'undo-2',is:28},'back_btn');
  return screen('printing_2', s);
});

function sheet(page, title, y, body){
  CUR=page;
  return rect(0,y,272,480-y,'var(--bg)') + rect(0,y,272,1,'var(--line)');
}
S('print_kb','Printing','Number keyboard (print)',()=>{
  let s = printTop('keybdB');
  s += rect(0,224,272,256,'#1d1d21',0)+rect(0,224,272,1,'var(--line)');
  s += btn(8,230,40,40,'',{icon:'chevron-left',is:26,css:'background:transparent'},'back_btn') + txt(52,230,200,40,T('title@sys0=0'),{sz:'l'},'title');
  s += card(12,276,248,44,'background:#111114') + txt(20,276,232,44,'<span style="font-size:22px;font-weight:600">220</span>',{a:'r',num:1},'input_show');
  ['1','2','3','4','5','6','7','8','9','⌫','0','✓'].forEach((k,i)=>{
    const x=12+62*(i%4)*0, c=i%3, r=Math.floor(i/3);
    const kx = 12+84*c, ky=330+34*r*0+ 0;
    s += `<div class="key${(k==='⌫'||k==='✓')?' fn':''}"${nm('key_'+(k==='⌫'?'del':k==='✓'?'ok':k))} style="${st(12+84*c,328+36*r,80,32,k==='✓'?'background:var(--accent)':'')}">${k==='⌫'?ico('delete',20):k==='✓'?ico('check',22,'#fff',2.5):k}</div>`;
  });
  return screen('keybdB', s);
}, 'On the print page the keyboard takes the lower half (the status stays visible).');

S('babystep','Printing','Z offset while printing',()=>{
  let s = printTop('print_zoffset');
  s += rect(0,224,272,256,'#1d1d21')+rect(0,224,272,1,'var(--line)');
  s += btn(8,230,40,40,'',{icon:'chevron-left',is:26,css:'background:transparent'},'back_btn') + txt(52,230,200,40,T('title'),{sz:'l'},'title');
  const steps=['0.01','0.05','0.1','0.5'];
  steps.forEach((v,i)=>{ s += `<div class="btn${i===1?' primary':''}"${nm('step_'+v.replace('.',''))} style="${st(12+62*i,278,58,40)}">${v}</div>`; });
  s += btn(12,326,120,52,'',{icon:'chevron-up',is:26},'z_up')+btn(140,326,120,52,'',{icon:'chevron-down',is:26},'z_down');
  s += txt(12,390,120,40,'<span style="font-size:13px;color:var(--text2)">G-code Z</span><br><b>0.200</b>',{a:'c',num:1},'gcode_z')+txt(140,390,120,40,'<span style="font-size:13px;color:var(--text2)">Offset</span><br><b>-1.000</b>',{a:'c',num:1},'z_offset');
  return screen('print_zoffset', s);
});

S('print_filament','Printing','Filament while printing',()=>{
  let s = printTop('print_filament');
  s += rect(0,224,272,256,'#1d1d21')+rect(0,224,272,1,'var(--line)');
  s += txt(12,230,248,36,T('title'),{sz:'l'},'title');
  s += heatRow(12,270,248,'nozzle',220,220,true,'heat_btn');
  s += btn(12,328,120,44,'',{icon:'minus',is:26},'temp_down')+btn(140,328,120,44,'',{icon:'plus',is:26},'temp_up');
  s += btn(12,384,56,52,'',{icon:'arrow-up',is:24},'retract_btn')+btn(76,384,56,52,'',{icon:'arrow-down',is:24},'extrude_btn')+tb(140,384,120,52,'replace_btn',{wrap:1},'replace_btn');
  return screen('print_filament', s);
});
