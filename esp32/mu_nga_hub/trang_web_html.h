// trang_web_html.h — trang theo dõi mũ, do ESP32 phục vụ ở http://<IP ESP32>/ (mu_nga_hub.ino).
// Tự chứa (không CDN): xem được trên hotspot điện thoại không có Internet. Trang hỏi /data mỗi 300 ms.
#pragma once

static const char TRANG_WEB[] PROGMEM = R"HTML(<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mũ phát hiện té ngã</title>
<style>
:root{--bg:#f4f5f7;--card:#fff;--ink:#1d2330;--mute:#6b7280;--line:#e3e6ea;--ok:#16a34a;--warn:#d97706;--bad:#dc2626;--info:#2563eb}
@media (prefers-color-scheme:dark){:root{--bg:#111418;--card:#1b2027;--ink:#e8eaee;--mute:#9aa3ad;--line:#2b323b}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
main{max-width:980px;margin:0 auto;padding:16px}
h1{font-size:18px;margin:0 0 12px}.muted{color:var(--mute)}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
#st{font-size:30px;font-weight:700;letter-spacing:.5px;padding:18px;border-radius:12px;text-align:center;color:#fff;background:var(--ok);transition:background .2s}
#st.SUSPECT{background:var(--warn)}#st.PRE_ALARM{background:var(--bad);animation:nhay 1s infinite}#st.ALARM{background:var(--bad)}
#st.STANDBY,#st.COOLDOWN{background:#64748b}#st.MAT{background:#475569}
@keyframes nhay{50%{opacity:.55}}
.big{font-size:26px;font-weight:700}.row{display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:1px dashed var(--line)}
.row:last-child{border:0}canvas{width:100%;height:190px;display:block}
button{font:inherit;padding:10px 14px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button.do{background:var(--bad);color:#fff;border:0}button:disabled{opacity:.35;cursor:default}
#ev{font:12px/1.5 ui-monospace,Consolas,monospace;max-height:240px;overflow:auto;white-space:pre-wrap;margin:0}
#tt{font-size:26px;font-weight:700;display:flex;align-items:center;gap:10px}#tt i{width:14px;height:14px;border-radius:50%;flex:none}
#pt{font-size:13px;margin:0;padding:0;list-style:none;max-height:240px;overflow:auto}#pt li{display:flex;gap:8px;align-items:center;padding:2px 0}
#pt i{width:10px;height:10px;border-radius:2px;flex:none}
.lg{display:flex;gap:14px;font-size:12px}.lg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
</style></head><body><main>
<h1>Mũ bảo hộ phát hiện té ngã <span class="muted" id="ket">· đang kết nối…</span></h1>
<div id="st">…</div>
<div class="grid" style="margin-top:12px">
 <div class="card"><div class="muted">Tư thế hiện tại</div><div id="tt"><i></i><span>–</span></div><div class="muted" id="ttd">Không phải té ngã: chỉ để theo dõi</div></div>
 <div class="card"><div class="muted">Kết quả CNN mới nhất (FPGA)</div><div class="big" id="cls">–</div><div class="muted" id="scr"></div></div>
 <div class="card"><div class="muted">Tự kiểm FPGA lúc khởi động</div><div class="big" id="tk">–</div><div class="muted" id="tkd"></div></div>
 <div class="card"><div class="muted">Hành động</div><p style="margin:8px 0;display:flex;gap:8px;flex-wrap:wrap">
  <button class="do" id="bh" onclick="lenh('/huy')">Hủy cảnh báo</button><button id="bb" onclick="lenh('/bat')">Bật lại hệ thống</button></p>
  <div class="muted" style="font-size:12px" id="tb">Hủy chỉ dùng khi CẢNH BÁO / BÁO ĐỘNG. Bật lại khi hệ thống TẮT.</div></div>
</div>
<div class="card" style="margin-top:12px"><div class="row"><b>Gia tốc |a| (g), 30 s gần nhất</b>
 <span class="lg"><span><i style="background:var(--info)"></i>|a|</span><span><i style="background:var(--bad)"></i>cửa sổ FALL</span><span>dải dưới: tư thế</span></span></div>
 <canvas id="cv"></canvas></div>
<div class="grid" style="margin-top:12px">
 <div class="card"><b>Thống kê</b><div id="tke"></div></div>
 <div class="card"><b>Lịch sử tư thế</b><ul id="pt"></ul></div>
 <div class="card"><b>Sự kiện</b><pre id="ev"></pre></div>
</div>
<p class="muted" style="font-size:12px">MPU6050 → SN32F407 → UART → ESP32 → SPI → FPGA Kiwi (1D-CNN INT8) → Safety FSM. Cập nhật 3 lần/giây.</p>
</main><script>
const TEN={MONITOR:'ĐANG THEO DÕI',SUSPECT:'NGHI NGÃ',PRE_ALARM:'CẢNH BÁO – nhấn hủy nếu ổn',ALARM:'BÁO ĐỘNG',COOLDOWN:'TẠM NGHỈ',STANDBY:'TẮT',MAT:'MẤT KẾT NỐI'};
const LOP={0:'NORMAL – bình thường',1:'lớp 1',2:'lớp 2',3:'FALL – ngã'};
const TT={DUNG:['Đứng thẳng','#16a34a'],DI_LAI:['Đang di chuyển','#0d9488'],NGOI:['Ngồi','#2563eb'],
 NAM_NGUA:['Nằm ngửa (nằm thẳng)','#7c3aed'],NAM_SAP:['Nằm sấp','#a21caf'],NGHIENG_TRAI:['Nằm nghiêng trái','#c026d3'],
 NGHIENG_PHAI:['Nằm nghiêng phải','#db2777'],CUI:['Cúi người','#ca8a04']};
const tt=k=>TT[k]||[k,'#64748b'];
let loi=0;
async function lay(){try{const r=await fetch('/data',{cache:'no-store'});const d=await r.json();loi=0;ve(d)}catch(e){if(++loi>3)dat('MAT')}}
function dat(s){const e=document.getElementById('st');e.className=s;e.textContent=TEN[s]||s}
function ve(d){
 document.getElementById('ket').textContent='· t = '+(d.t/1000).toFixed(1)+' s';
 dat(d.st);
 const c=document.getElementById('cls');
 if(d.rc===0){c.textContent=LOP[d.cls]||d.cls;c.style.color=d.cls==3?'var(--bad)':'var(--ok)';document.getElementById('scr').textContent='điểm '+d.score+' · cửa sổ '+d.seq}
 else if(d.rc>0){c.textContent='lỗi SPI rc='+d.rc;c.style.color='var(--warn)'}
 const t=document.getElementById('tk');t.textContent=d.tk?'PASS':'FAIL';t.style.color=d.tk?'var(--ok)':'var(--bad)';
 document.getElementById('tkd').textContent='SPI '+d.s.spi_khz+' kHz';
 const s=d.s,R=(a,b)=>'<div class="row"><span>'+a+'</span><b>'+b+'</b></div>';
 document.getElementById('tke').innerHTML=R('Mẫu nhận',s.mau)+R('Mẫu mất',s.mat)+R('Khung hỏng',s.hong)+R('Cửa sổ gửi FPGA',s.gui)+R('FPGA trả OK',s.ok)+R('Timeout',s.to)+R('Lỗi khác',s.loi);
 const [tn,tc]=tt(d.tt),te=document.getElementById('tt');te.children[0].style.background=tc;te.children[1].textContent=tn;
 const last=d.pt.length?d.pt[d.pt.length-1][0]:0;
 document.getElementById('ttd').textContent=(last?'từ '+((d.t-last)/1000).toFixed(0)+' s trước · ':'')+'không phải té ngã, chỉ để theo dõi';
 document.getElementById('pt').innerHTML=d.pt.slice().reverse().map(p=>'<li><i style="background:'+tt(p[1])[1]+'"></i><span class="muted">'+(p[0]/1000).toFixed(0)+' s</span>'+tt(p[1])[0]+'</li>').join('')||'<li class="muted">chưa đổi tư thế (bắt đầu: đứng thẳng)</li>';
 const ev=document.getElementById('ev');ev.textContent=d.ev.slice().reverse().join('\n');
 document.getElementById('bh').disabled=!(d.st=='PRE_ALARM'||d.st=='ALARM');
 document.getElementById('bb').disabled=d.st!='STANDBY';
 bieu(d);
}
function bieu(d){
 const cv=document.getElementById('cv'),r=devicePixelRatio||1,W=cv.clientWidth,Hh=cv.clientHeight;cv.width=W*r;cv.height=Hh*r;
 const g=cv.getContext('2d');g.scale(r,r);g.clearRect(0,0,W,Hh);
 const css=getComputedStyle(document.documentElement),ink=css.getPropertyValue('--mute'),ln=css.getPropertyValue('--line');
 const t1=d.t,t0=t1-30000,X=t=>(t-t0)/30000*W,maxg=Math.max(3,...d.acc.map(p=>p[1]/100)),Y=v=>Hh-6-(v/maxg)*(Hh-18);
 g.strokeStyle=ln;g.fillStyle=ink;g.font='11px system-ui';g.lineWidth=1;
 for(let v=0;v<=maxg;v++){g.beginPath();g.moveTo(0,Y(v));g.lineTo(W,Y(v));g.stroke();g.fillText(v+' g',4,Y(v)-2)}
 g.fillStyle=css.getPropertyValue('--bad');
 for(const p of d.res){if(p[1]==3&&p[0]>=t0){g.globalAlpha=.25;g.fillRect(X(p[0]-2560),0,X(p[0])-X(p[0]-2560),Hh);g.globalAlpha=1}}
 if(!d.acc.length||d.acc[d.acc.length-1][0]<t1-2000){g.fillStyle=css.getPropertyValue('--warn');g.font='14px system-ui';g.fillText('Không có mẫu mới từ cảm biến (kiểm dây MPU6050)',40,Hh/2)}
 for(let k=(d.pt.length>=24?1:0);k<=d.pt.length;k++){const a=k?d.pt[k-1][0]:t0-1,b=k<d.pt.length?d.pt[k][0]:t1;if(b<t0)continue;
  g.fillStyle=tt(k?d.pt[k-1][1]:'DUNG')[1];g.fillRect(X(Math.max(a,t0)),Hh-5,X(b)-X(Math.max(a,t0)),5)}
 g.strokeStyle=css.getPropertyValue('--info');g.lineWidth=2;g.beginPath();let f=1;
 for(const p of d.acc){if(p[0]<t0)continue;const x=X(p[0]),y=Y(p[1]/100);f?g.moveTo(x,y):g.lineTo(x,y);f=0}g.stroke();
}
async function lenh(u){try{const r=await fetch(u,{method:'POST'});document.getElementById('tb').textContent=await r.text()}catch(e){}}
setInterval(lay,300);lay();
</script></body></html>)HTML";
