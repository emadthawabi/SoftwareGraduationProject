'use strict';
/* ===== app shell: sidebar, topbar, global search, quick-add ===== */
const NAV=[
 {g:'',items:[['dashboard','لوحة التحكم','home']]},
 {g:'العمل القانوني',items:[['cases','القضايا','briefcase',()=>db.cases.filter(c=>c.status==='ongoing').length],['sessions','الجلسات','calendar',()=>db.sessions.filter(s=>{const n=daysTo(s.date);return n>=0&&n<=7}).length],['exec','القضايا التنفيذية','gavel',()=>db.exec.filter(x=>x.status==='ongoing').length],['office','ملفات المكتب','folder',()=>db.office.filter(x=>x.status==='open').length]]},
 {g:'العملاء والمالية',items:[['clients','العملاء','users',()=>db.clients.length],['invoices','الفواتير','receipt'],['expenses','المصاريف','wallet']]}];
const NAVMAP={case:'cases',client:'clients'};
function buildShell(){
 $('#app').innerHTML=`<aside class="sidebar" id="sidebar"><div class="brand"><div class="logo">${icon('scale',20)}</div><div>المكتب القانوني<small>نظام إدارة القضايا والعملاء</small></div></div><nav id="nav"></nav></aside>
 <div class="main"><header class="topbar"><button class="btn icon menu-btn" data-act="toggleNav">${icon('menu')}</button>
 <div class="gsearch">${icon('search')}<input id="gs" type="search" placeholder="بحث سريع: قضية، عميل، رقم دعوى، ملف..." autocomplete="off" data-input="gsearch"><div class="gresults" id="gresults" hidden></div></div>
 <div class="grow"></div><div class="menu"><button class="btn primary" data-act="toggleNew">${icon('plus',16)} جديد</button><div class="menu-pop" id="newmenu" hidden>
 ${[['newCase','قضية','briefcase'],['newSession','جلسة','calendar'],['newClient','عميل','users'],['newInvoice','فاتورة','receipt'],['newExec','ملف تنفيذي','gavel'],['newOffice','ملف مكتب','folder'],['newExpense','مصروف','wallet']].map(([a,l,i])=>`<button data-act="${a}">${icon(i,16)} ${l}</button>`).join('')}</div></div></header>
 <main id="page"></main></div>`;
}
function syncNav(r){const cur=NAVMAP[r]||r;$('#nav').innerHTML=NAV.map(g=>`${g.g?`<div class="navgroup">${g.g}</div>`:''}${g.items.map(([k,l,i,c])=>`<button class="navitem ${k===cur?'active':''}" data-go="${k}">${icon(i)}<span>${l}</span>${c?`<span class="count">${c()}</span>`:''}</button>`).join('')}`).join('');$('#sidebar').classList.remove('open');document.title=l_title(cur)+' · المكتب القانوني'}
const l_title=k=>NAV.flatMap(g=>g.items).find(i=>i[0]===k)?.[1]||'';
ACT.toggleNav=()=>$('#sidebar').classList.toggle('open');
ACT.toggleNew=()=>{const m=$('#newmenu');m.hidden=!m.hidden};
INP.gsearch=(d,el)=>{const q=el.value.trim().toLowerCase(),box=$('#gresults');if(!q){box.hidden=true;return}
 const m=(...a)=>a.some(x=>String(x??'').toLowerCase().includes(q));const res=[];
 db.cases.filter(c=>m(c.title,c.courtNo,c.officeNo,c.opponent,c.stageNo,clientName(c.clientId))).forEach(c=>res.push(['قضية',c.title,`${c.courtNo} · ${clientName(c.clientId)}`,'case-'+c.id]));
 db.clients.filter(c=>m(c.name,c.phone,c.email)).forEach(c=>res.push(['عميل',c.name,c.phone,'client-'+c.id]));
 db.exec.filter(x=>m(x.execNo,x.debtor,clientName(x.clientId))).forEach(x=>res.push(['تنفيذ',x.execNo,`${clientName(x.clientId)} ضد ${x.debtor}`,'exec-'+x.id]));
 db.office.filter(x=>m(x.title,x.ref,clientName(x.clientId))).forEach(x=>res.push([OFFICE_KINDS[x.kind],x.title,clientName(x.clientId),'office-'+x.id]));
 box.innerHTML=res.slice(0,10).map(r=>`<div class="ritem" data-go="${r[3]}"><span class="rtype">${r[0]}</span><div><div class="bold">${esc(r[1])}</div><div class="small muted">${esc(r[2])}</div></div></div>`).join('')||'<div class="empty">لا توجد نتائج</div>';box.hidden=false};
document.addEventListener('click',e=>{if(e.target.closest('#gresults [data-go]'))$('#gs').value=''});
