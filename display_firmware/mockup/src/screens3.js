// ---- screens: settings, network, keyboard --------------------------------------------------------------------------
S('settings','Settings and network','Settings',()=>{
  CUR='common_set';
  let s = tabs('l','r','r',['tab_calib','tab_settings']);
  [['lang_lbl','lang_btn'],['network_lbl','network_btn'],['sysinfo_lbl','sysinfo_btn'],['sleep_lbl','sleep_btn']].forEach((r,i)=>{ s += row(12,60+60*i,248,52,T(r[0]),{chev:1},r[1]); });
  s += row(12,300,248,52,T('reset_lbl').replace('<br>',' '),{},'reset_btn').replace('class="t ','class="t red ');
  s += nav('settings');
  return screen('common_set', s);
}, 'The last row is "Restore Factory Settings"; while the setup guide is switched on the host shows "Setup Guide" there instead.');

S('language','Settings and network','Language',()=>{
  CUR='language';
  let s = header(T('title'));
  const names=['lang_cn','lang_ru','lang_en','lang_jp','lang_fr','lang_de','lang_it','lang_es'];
  names.forEach((n,i)=>{
    const x=12+128*(i%2), y=60+68*Math.floor(i/2), sel=(n==='lang_en');
    s += `<div${nm(n)} style="${st(x,y,120,60)}background:${sel?'var(--btn-hi)':'var(--btn)'};border-radius:12px"></div>`+
         `<div class="radio${sel?' on':''}" style="left:${x+12}px;top:${y+19}px"></div>` + txt(x+42,y,74,60,T(n+'_name'),{num:1,css:'font-size:16px'},n+'_name');
  });
  s += btn(12,340,120,44,'',{icon:'chevron-up',is:24,v:'dim'},'prev_page')+btn(140,340,120,44,'',{icon:'chevron-down',is:24},'next_page');
  s += nav('settings');
  return screen('language', s);
});
S('language2','Settings and network','Language, page 2',()=>{
  CUR='language2';
  let s = header(T('title','language'));
  const names=['lang_kr','lang_pt','lang_ar','lang_tr','lang_he'];
  names.forEach((n,i)=>{
    const x=12+128*(i%2), y=60+68*Math.floor(i/2), sel=false;
    s += `<div${nm(n)} style="${st(x,y,120,60)}background:var(--btn);border-radius:12px"></div><div class="radio" style="left:${x+12}px;top:${y+19}px"></div>` + txt(x+42,y,74,60,T(n+'_name','language2'),{num:1},n+'_name');
  });
  s += btn(12,340,120,44,'',{icon:'chevron-up',is:24},'prev_page')+btn(140,340,120,44,'',{icon:'chevron-down',is:24,v:'dim'},'next_page');
  s += nav('settings');
  return screen('language2', s);
});

S('screen','Settings and network','Screen (sleep, brightness)',()=>{
  CUR='sleep_mode';
  let s = header(T('title'));
  [['opt_5min_lbl',true],['opt_15min_lbl',false],['opt_30min_lbl',false],['opt_never_lbl',false]].forEach((o,i)=>{ s += row(12,60+56*i,248,48,T(o[0]),{radio:o[1],sel:o[1]},o[0].replace('_lbl','')); });
  s += txt(12,296,200,28,T('brightness_lbl'),{sz:'m'},'brightness_lbl') + txt(200,296,60,28,'80 %',{a:'r',mute:1,num:1});
  s += `<div style="${st(12,340,248,10)}background:#2c2c33;border-radius:5px"></div><div style="${st(12,340,198,10)}background:var(--accent);border-radius:5px"></div><div style="${st(198,330,28,28)}background:#fff;border-radius:14px"></div>`;
  s += `<div style="${st(12,364,20,20)}color:var(--text3)">${ico('sun-dim',18)}</div>`;
  s += nav('settings');
  return screen('sleep_mode', s);
});

S('klipper','Settings and network','Klipper status',()=>{
  CUR='sys_ok';
  let s = header(T('title'));
  s += card(12,60,248,150,'') + `<div style="${st(104,76,64,64)}border-radius:32px;background:rgba(48,164,108,.16);color:var(--ok);display:flex;align-items:center;justify-content:center">${ico('circle-check',34)}</div>`;
  s += tt(24,148,224,48,'msg',{a:'c'},'msg');
  s += btn(12,222,248,48,T('export_logs'),{},'export_logs');
  s += nav('settings');
  return screen('sys_ok', s);
});
S('klipper_err','Settings and network','Klipper error',()=>{
  CUR='reset';
  let s = header(T('title'));
  s += card(12,60,248,148,'') + `<div style="${st(24,72,28,28)}color:var(--danger)">${ico('triangle-alert',26)}</div>` + tt(60,70,190,130,'err_msg',{v:'top',mute:0,css:'font-size:15px'},'err_msg');
  s += btn(12,220,248,46,T('export_logs'),{},'export_logs')+btn(12,274,248,46,T('restart_klip'),{},'restart_klip')+btn(12,328,248,46,T('restart_fw'),{v:'danger'},'restart_fw');
  s += nav('settings');
  return screen('reset', s);
});

// network
const NT = k => T(k,'net');
S('network','Settings and network','Network',()=>{
  CUR='internet_page';
  let s = header(T('title'));
  s += card(12,60,248,52,'background:#111114') + txt(26,60,40,52,'IP',{mute:1,css:'font-weight:600'},null) + txt(66,60,180,52,'192.168.1.57',{css:'font-family:ui-monospace,monospace;font-size:17px',num:1},'ip_txt');
  s += `<div class="tabs" style="${st(12,122,248,44)}"><div class="tab on" style="${st(3,3,121,38)}">${ico('wifi',22)}</div><div class="tab" style="${st(124,3,121,38)}">${ico('ethernet-port',22)}</div></div>`;
  s += row(12,178,248,52,T('wifi_btn'),{chev:1},'wifi_btn') + row(12,238,248,52,T('info_lbl'),{chev:1},'info_btn');
  s += nav('settings');
  return screen('internet_page', s);
}, 'One way to the Wi-Fi list: the Wi-Fi row. Saved and Hidden networks are reached from the list (its two buttons), and Back from them returns to the list.');
function netList(page, top, withChips){
  const rows=[['Home-Network','check'],['Printer-AP','lock'],['Neighbour_5G','lock'],['Guest',null],['Cafe Free WiFi','lock']];
  let s='';
  rows.forEach((r,i)=>{ s += row(12,top+50*i,248,44,r[0],{check:r[1]==='check',lock:r[1]==='lock',num:1},'row'+(i+1)); });
  s += btn(12,top+262,120,40,'',{icon:'chevron-up',is:22,v:'dim'},'prev_btn')+btn(140,top+262,120,40,'',{icon:'chevron-down',is:22},'next_btn');
  return s;
}
S('wifi','Settings and network','Wi-Fi list',()=>{
  CUR='wifi_list';
  let s = header(T('title'));
  s += tb(12,58,86,40,'saved_btn',{},'saved_btn')+tb(104,58,86,40,'hidden_btn',{},'hidden_btn')+btn(220,58,40,40,'',{icon:'rotate-cw',is:20},'refresh_btn');
  s += netList('wifi_list',106);
  s += nav('settings');
  return screen('wifi_list', s);
});
S('saved','Settings and network','Saved networks',()=>{
  CUR='net_saved';
  let s = header(T('title'));
  s += netList('net_saved',60);
  s += nav('settings');
  return screen('net_saved', s);
});
S('net_detail','Settings and network','Network details',()=>{
  CUR='net_detail';
  let s = header(T('title'));
  s += card(12,60,248,84,'') + txt(26,66,220,34,'Home-Network',{sz:'l',num:1},'ssid_txt') + txt(26,100,220,34,NT('connected')+' · 192.168.1.57',{mute:1,sz:'s',num:1},'status_txt');
  s += btn(12,156,248,46,NT('disconnect'),{v:'primary'},'connect_btn')+tb(12,210,248,46,'passwd_btn',{},'passwd_btn');
  s += row(12,264,248,46,NT('autoconnect').replace(': ',''),{sw:true},'auto_btn')+tb(12,318,248,46,'forget_btn',{v:'danger'},'forget_btn');
  s += nav('settings');
  return screen('net_detail', s);
});
S('net_confirm','Settings and network','Forget network?',()=>{
  CUR='net_confirm';
  let s = header(T('title'));
  s += card(12,60,248,170,'') + `<div style="${st(112,76,48,48)}color:var(--danger)">${ico('triangle-alert',40)}</div>` + txt(28,130,216,90,NT('saved_password')+'<br><b>Home-Network</b><br>'+NT('will_be_deleted'),{a:'c',num:1},'msg');
  s += btn(12,244,120,46,NT('forget'),{v:'danger'},'forget_btn')+btn(140,244,120,46,NT('cancel'),{},'cancel');
  s += nav('settings');
  return screen('net_confirm', s);
});
S('net_info','Settings and network','Network info',()=>{
  CUR='net_info';
  let s = header(T('title'));
  s += card(12,60,248,128,'') + `<div style="${st(24,70,22,22)}color:var(--accent)">${ico('wifi',22)}</div>` + txt(54,68,100,26,'Wi-Fi',{sz:'l'},null) + txt(24,100,224,84,NT('connected')+'<br>Home-Network<br>192.168.1.57 · '+NT('gateway')+' 192.168.1.1',{sz:'s',mute:1,num:1},'wifi_txt');
  s += card(12,196,248,104,'') + `<div style="${st(24,206,22,22)}color:var(--text2)">${ico('ethernet-port',22)}</div>` + txt(54,204,100,26,'LAN',{sz:'l'},null) + txt(24,236,224,60,NT('disconnected'),{sz:'s',mute:1},'lan_txt');
  s += row(12,312,248,50,'Wi-Fi',{sw:true},'radio_btn');
  s += nav('settings');
  return screen('net_info', s);
});
S('wifi_kb','Keyboards','Text keyboard (Wi-Fi password)',()=>{
  CUR='wifi_kb';
  let s = header(T('title'));
  s += card(12,58,248,48,'background:#111114') + txt(24,58,224,48,'<span style="letter-spacing:3px;font-size:22px">••••••••</span>',{num:1},'input_show');
  const letters='abcdefghijklmnopqrstuvwxyz';
  for(let i=0;i<26;i++){ const c=i%4,r=Math.floor(i/4); s += `<div class="key"${nm('key_'+letters[i])} style="${st(12+52*c,114+48*r,46,42)};font-size:20px">${letters[i]}</div>`; }
  s += `<div class="key"${nm('key_space')} style="${st(116,402,98,42)}">${ico('chevrons-up',1)}<span style="position:static;width:30px;height:2px;background:var(--text2);border-radius:1px"></span></div>`;
  s += `<div class="key fn"${nm('key_del')} style="${st(220,114,40,90)}">${ico('delete',20)}</div>`;
  s += `<div class="key fn"${nm('key_shift')} style="${st(220,210,40,90)}">${ico('arrow-big-up',22)}</div>`;
  s += `<div class="key fn"${nm('key_sym')} style="${st(220,306,40,42)};font-size:12px">123</div>`;
  s += `<div class="key"${nm('key_ok')} style="${st(220,354,40,90)};background:var(--accent)">${ico('check',24,'#fff',2.5)}</div>`;
  return screen('wifi_kb', s);
});
S('wifi_connect','Settings and network','Connecting',()=>{
  CUR='wifi_connect';
  return screen('wifi_connect', busy('msg'));
});
function busy(key){
  return `<div style="${st(116,170,40,40)};border:3px solid #34343c;border-top-color:var(--accent);border-radius:50%"></div>` + tt(24,226,224,100,key,{a:'c',v:'top'},key);
}
