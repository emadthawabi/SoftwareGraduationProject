'use strict';
/* ===== helpers ===== */
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>'₪'+Number(n||0).toLocaleString('en-US');
const today=()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')};
const daysTo=d=>Math.round((new Date(d+'T00:00:00')-new Date(today()+'T00:00:00'))/864e5);
const rel=d=>{if(!d)return'';const n=daysTo(d);return n===0?'اليوم':n===1?'غداً':n===-1?'أمس':n>0?`بعد ${n} يوم`:`منذ ${-n} يوم`};
const dt=d=>d?`<bdi class="num">${esc(d)}</bdi>`:'—';
const dueTag=(due,done)=>{if(!due)return'<span class="muted">بلا موعد</span>';if(done)return dt(due);const n=daysTo(due);return `<span class="badge ${n<0?'bad':n<=3?'warn':''}">${dt(due)} · ${rel(due)}</span>`};
const isLate=(due,done)=>!done&&due&&daysTo(due)<0;
let _id=5000;const nid=()=>++_id;
const byId=(arr,id)=>arr.find(x=>x.id===Number(id));
const removeId=(arr,id)=>{const i=arr.findIndex(x=>x.id===Number(id));if(i>=0)arr.splice(i,1)};
const C=id=>byId(db.cases,id),CL=id=>byId(db.clients,id);
const clientName=id=>CL(id)?.name||'—';
const sum=(a,f)=>a.reduce((s,x)=>s+(f?f(x):x),0);
const badge=(t,k='')=>`<span class="badge ${k}">${esc(t)}</span>`;
const ICONS={home:'M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z',briefcase:'M3 7h18v13H3z M9 7V4h6v3 M3 13h18',users:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75',calendar:'M3 5h18v16H3z M3 10h18 M8 3v4 M16 3v4',receipt:'M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2z M9 8h6 M9 12h6',gavel:'M9 11l3 3L22 4 M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11',folder:'M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z',wallet:'M3 7h18v12H3z M3 7l2-3h14l2 3 M16 13h2',pen:'M12 20h9 M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z',link:'M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7 M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7',plus:'M12 5v14 M5 12h14',search:'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16 M21 21l-4.3-4.3',trash:'M3 6h18 M8 6V4h8v2 M6 6l1 14h10l1-14',x:'M6 6l12 12 M18 6L6 18',chevron:'M15 18l-6-6 6-6',menu:'M3 6h18 M3 12h18 M3 18h18',upload:'M12 16V4 M7 9l5-5 5 5 M4 20h16',clip:'M21 12.5l-8.5 8.5a5 5 0 0 1-7-7L14 5.5a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L15 8',check:'M5 12l5 5L20 7',alert:'M12 9v4 M12 17h.01 M10.3 3.9L2 18a2 2 0 0 0 1.7 3h16.6A2 2 0 0 0 22 18L13.7 3.9a2 2 0 0 0-3.4 0z',building:'M4 21V5l8-2 8 2v16 M9 21v-4h6v4 M8 9h2 M14 9h2 M8 13h2 M14 13h2',map:'M9 3L3 5v16l6-2 6 2 6-2V3l-6 2z M9 3v16 M15 5v16',scale:'M12 3v18 M5 7h14 M5 7l-3 7a3 3 0 0 0 6 0z M19 7l-3 7a3 3 0 0 0 6 0z M8 21h8',clock:'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20 M12 6v6l4 2',edit:'M12 20h9 M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z',inbox:'M22 12h-6l-2 3h-4l-2-3H2 M5.5 5h13l3.5 7v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-7z'};
const icon=(n,s)=>`<svg class="i" viewBox="0 0 24 24" ${s?`style="width:${s}px;height:${s}px"`:''}><path d="${ICONS[n]||''}"/></svg>`;
const fmtSize=n=>n>1048576?(n/1048576).toFixed(1)+' MB':Math.max(1,Math.round(n/1024))+' KB';
/* ===== ui state & routing ===== */
const ui={tab:{},f:{cases:{q:'',status:'',stage:'',lawyer:''},clients:{q:''},sessions:{when:'upcoming'},invoices:{status:''},exec:{status:''},office:{q:'',kind:'',lawyer:'',status:'open'},expenses:{tab:'office'}},nav:false};
const PAGES={},LIST={},ACT={},FORM={},CHG={},INP={},TABS_DEFAULT={case:'overview',exec:'procedures',office:'overview',client:'cases'};
function route(){const h=(location.hash||'').replace(/^#/,'')||'dashboard';const [r,id]=h.split('-');return {r:PAGES[r]?r:'dashboard',id:id?Number(id):null}}
function go(h){if(location.hash==='#'+h)renderPage();else location.hash=h}
let _lastKey='',pendingTab=null;
function renderPage(){const {r,id}=route();const key=r+'-'+id;if(key!==_lastKey){ui.tab[r]=(pendingTab&&pendingTab.r===r)?pendingTab.v:(TABS_DEFAULT[r]||'');pendingTab=null;_lastKey=key}
 const y=window.scrollY;$('#page').innerHTML=PAGES[r](id);syncNav(r);if(window.__keepScroll!==false)window.scrollTo(0,y)}
/* ===== shared UI pieces ===== */
const head=({crumbs=[],title,sub='',actions=''})=>`<div class="pagehead"><div>${crumbs.length?`<div class="crumbs">${crumbs.map(c=>c.go?`<a data-go="${c.go}">${esc(c.t)}</a>`:`<span>${esc(c.t)}</span>`).join(' <span class="faint">/</span> ')}</div>`:''}<h1>${title}</h1>${sub?`<div class="sub">${sub}</div>`:''}</div><div class="actions">${actions}</div></div>`;
const card=(title,body,{actions='',pad=true}={})=>`<section class="card">${title?`<div class="ch"><h3>${title}</h3><div class="row gap-s">${actions}</div></div>`:''}${pad?`<div class="cb">${body}</div>`:body}</section>`;
const stat=({l,v,s='',cls='',go:g=''})=>`<${g?'button':'div'} class="stat ${cls}" ${g?`data-go="${g}"`:''}><div class="l">${l}</div><div class="v">${v}</div>${s?`<div class="s">${s}</div>`:''}</${g?'button':'div'}>`;
const empty=(t,ic='inbox')=>`<div class="empty">${icon(ic)}<div>${t}</div></div>`;
const tabsBar=(k,items,cur)=>`<div class="tabs">${items.map(([v,l,c])=>`<button class="tab ${cur===v?'active':''}" data-act="tab" data-k="${k}" data-v="${v}">${l}${c!=null?`<span class="count">${c}</span>`:''}</button>`).join('')}</div>`;
const seg=(act,items,cur,extra='')=>`<div class="seg">${items.map(([v,l])=>`<button class="${cur===v?'active':''}" data-act="${act}" data-v="${v}" ${extra}>${l}</button>`).join('')}</div>`;
const table=(cols,rows,{go:g,emptyText='لا توجد بيانات'}={})=>rows.length?`<div class="tablewrap"><table class="t"><thead><tr>${cols.map(c=>`<th class="${c.cls||''}">${c.h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr ${g?`data-go="${g(r)}"`:''}>${cols.map(c=>`<td class="${c.cls||''}">${c.f(r)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:empty(emptyText);
const rowBtns=(editAct,delAct,id,extra='')=>`<div class="rowact">${extra}${editAct?`<button class="btn ghost icon" title="تعديل" data-act="${editAct}" data-id="${id}">${icon('edit',16)}</button>`:''}${delAct?`<button class="btn ghost icon" title="حذف" data-act="${delAct}" data-id="${id}">${icon('trash',16)}</button>`:''}</div>`;
const progress=p=>`<div class="progress"><i style="width:${Math.max(0,Math.min(100,p))}%"></i></div>`;
const dl=items=>`<dl class="dl">${items.map(([l,v,full])=>`<div class="${full?'full':''}"><dt>${l}</dt><dd>${v===''||v==null?'<span class="faint">—</span>':v}</dd></div>`).join('')}</dl>`;
/* form fields */
function fld(f,v={}){const val=v[f.k]??f.def??'';let ctl;const req=f.req?'required':'';
 if(f.type==='select'){const o=typeof f.opts==='function'?f.opts():f.opts;ctl=`<select name="${f.k}" ${req}>${o.map(([a,b])=>`<option value="${esc(a)}" ${String(a)===String(val)?'selected':''}>${esc(b)}</option>`).join('')}</select>`}
 else if(f.type==='textarea')ctl=`<textarea name="${f.k}" placeholder="${esc(f.ph||'')}">${esc(val)}</textarea>`;
 else ctl=`<input name="${f.k}" type="${f.type||'text'}" value="${esc(val)}" placeholder="${esc(f.ph||'')}" ${req} ${f.type==='number'?'min="0" step="any"':''}>`;
 return `<label class="fld ${f.full?'full':''} ${f.wide?'wide':''}"><span>${f.l}${f.req?' *':''}</span>${ctl}</label>`}
const inl=(form,fields,attrs='',btn='إضافة')=>`<form class="inline-form" data-form="${form}" ${attrs}>${fields.map(f=>fld(f)).join('')}<button class="btn primary">${icon('plus',16)} ${btn}</button></form>`;
/* overlay: drawer / dialog / toast */
function openDrawer(title,form,fields,vals,attrs=''){$('#overlay').innerHTML=`<div class="scrim" data-act="closeOverlay"></div><aside class="drawer"><div class="dh"><h2>${esc(title)}</h2><button class="btn ghost icon" data-act="closeOverlay">${icon('x')}</button></div><form data-form="${form}" ${attrs}><div class="dbody"><div class="form-grid">${fields.map(f=>fld(f,vals)).join('')}</div></div><div class="dfoot"><button class="btn primary">حفظ</button><button type="button" class="btn" data-act="closeOverlay">إلغاء</button></div></form></aside>`;$('#overlay').classList.add('show');setTimeout(()=>$('#overlay input:not([type=hidden]),#overlay select')?.focus(),50)}
function openDialog(html){$('#overlay').innerHTML=`<div class="scrim" data-act="closeOverlay"></div><div class="dialog">${html}</div>`;$('#overlay').classList.add('show')}
function confirmDlg(msg,fn){window.__confirm=fn;openDialog(`<h2>تأكيد الحذف</h2><p class="muted">${esc(msg)}</p><div class="dfoot"><button class="btn danger" data-act="confirmYes">حذف</button><button class="btn" data-act="closeOverlay">إلغاء</button></div>`)}
function closeOverlay(){$('#overlay').classList.remove('show');$('#overlay').innerHTML=''}
function toast(m){const t=document.createElement('div');t.className='toast';t.textContent=m;$('#toasts').appendChild(t);setTimeout(()=>t.remove(),2600)}
function preview(f){openDialog(`<h2>${esc(f.name)}</h2>${f.type?.startsWith('image/')?`<img src="${f.url}" alt="">`:'<div class="callout info">تم إرفاق الملف، ولا تتوفر معاينة لهذا النوع داخل الصفحة. في النظام الفعلي يمكن فتحه وتنزيله.</div>'}<div class="dfoot"><button class="btn" data-act="closeOverlay">إغلاق</button></div>`)}
const mkFile=f=>{const o={id:nid(),name:f.name,size:f.size,type:f.type||'',url:URL.createObjectURL(f),date:today()};window.__files=window.__files||{};window.__files[o.id]=o;return o};
const fileChip=(f,delAct,attrs)=>`<span class="chip">${f.type?.startsWith('image/')?`<img class="thumb" style="width:22px;height:22px" src="${f.url}" alt="">`:icon('clip',14)}<a data-act="viewFile" data-fid="${f.id}" ${attrs}>${esc(f.name)}</a><span class="faint">${fmtSize(f.size)}</span><button title="حذف" data-act="${delAct}" data-fid="${f.id}" ${attrs}>×</button></span>`;
function refresh(){renderPage()}
function refreshList(){const {r}=route();const el=$('#list');if(el&&LIST[r])el.innerHTML=LIST[r]()}
/* delegated events */
document.addEventListener('click',e=>{
 const a=e.target.closest('[data-act]');
 if(a){const fn=ACT[a.dataset.act];if(fn){if(a.tagName!=='INPUT')e.preventDefault();e.stopPropagation();fn(a.dataset,a,e)}return}
 const g=e.target.closest('[data-go]');if(g){closeMenus();if(g.dataset.tab){const r0=g.dataset.go.split('-')[0];pendingTab={r:r0,v:g.dataset.tab};ui.tab[r0]=g.dataset.tab}go(g.dataset.go);return}
 if(!e.target.closest('.menu'))closeMenus();if(!e.target.closest('.gsearch'))$('#gresults')&&($('#gresults').hidden=true)});
document.addEventListener('submit',e=>{const f=e.target.closest('form[data-form]');if(!f)return;e.preventDefault();const fn=FORM[f.dataset.form];if(fn){fn(Object.fromEntries(new FormData(f).entries()),f.dataset,f)}});
document.addEventListener('change',e=>{const a=e.target.closest('[data-change]');if(a&&CHG[a.dataset.change])CHG[a.dataset.change](a.dataset,a,e)});
document.addEventListener('input',e=>{const a=e.target.closest('[data-input]');if(a&&INP[a.dataset.input])INP[a.dataset.input](a.dataset,a,e)});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeOverlay()});
ACT.closeOverlay=closeOverlay;ACT.confirmYes=()=>{const f=window.__confirm;closeOverlay();f&&f()};
ACT.tab=d=>{ui.tab[d.k]=d.v;refresh()};
ACT.back=()=>history.back();
ACT.viewFile=(d,el)=>{const f=window.__files?.[d.fid];if(f)preview(f)};
const regFiles=a=>{window.__files=window.__files||{};a.forEach(f=>window.__files[f.id]=f)};
const closeMenus=()=>$$('.menu-pop').forEach(m=>m.hidden=true);
