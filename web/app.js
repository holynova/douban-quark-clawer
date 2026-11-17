'use strict';
const $ = s => document.querySelector(s);
const labels = {pending:'等待搜索',found:'已收集',empty:'未找到',error:'搜索失败',blocked:'等待验证'};
let state = {items:[],job:{active:false}}, filter = 'all', mode = 'douban', detailId = null, toastTimer, lastRender = '';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(text) { $('#toast').textContent = text; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 4000); }
async function api(path, data) {
  const response = await fetch('/api/' + path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || '操作未完成');
  return result;
}
function isAttention(i) { return ['empty','error','blocked'].includes(i.status); }
function render() {
  const {items,job} = state;
  const counts = {all:items.length,found:items.filter(i=>i.status==='found').length,pending:items.filter(i=>i.status==='pending').length,attention:items.filter(isAttention).length};
  for (const [key,value] of Object.entries(counts)) {
    $('#count-'+key).textContent=value;
    $(`[data-filter="${key}"] span`).textContent=value;
    $(`[data-filter="${key}"]`).setAttribute('aria-pressed',String(filter===key));
  }
  $('#list-heading').textContent = {all:'全部影片',found:'已收集链接',pending:'等待搜索',attention:'需要留意'}[filter];
  const query = $('#query').value.toLowerCase().trim();
  const visible = items.filter(i=>(filter==='all'||(filter==='attention'?isAttention(i):i.status===filter)) && (i.title+' '+i.note).toLowerCase().includes(query));
  $('#visible-count').textContent=visible.length+' 部';
  $('#empty').hidden=items.length>0;
  $('#no-results').hidden=!items.length||visible.length>0;
  $('#run').hidden=job.active;
  $('#pause').hidden=!job.active;
  $('#run').disabled=!items.some(i=>['pending','error','blocked'].includes(i.status));
  $('#run').textContent=items.some(i=>i.status==='blocked')?'继续搜索 ↗':'开始搜索 ↗';
  $('#retry').disabled=job.active||!items.some(isAttention);
  $('#task-dot').classList.toggle('active',job.active);
  $('#task-title').textContent=job.active?(job.kind==='import'?'正在导入豆瓣片单':`正在搜索 · ${job.done} / ${job.total}`):(items.length?'片单已保存，随时继续':'准备好下一部电影');
  $('#task-message').textContent=job.message==='准备就绪'?(items.length?'每完成一部自动保存；遇到验证时暂停等待。':'导入豆瓣片单，或粘贴你喜欢的片名。'):job.message;
  $('#progress').hidden=!job.active||!job.total;
  $('#progress').max=job.total||1; $('#progress').value=job.done||0;
  const rendered=JSON.stringify([visible,job.active]);
  if(rendered===lastRender)return;
  lastRender=rendered;
  $('#movie-list').innerHTML=visible.map(i=>{
    const index=items.indexOf(i)+1;
    const search='https://www.google.com/search?q='+encodeURIComponent('"'+i.title+'" 夸克');
    return `<article class="movie"><div class="movie-number" aria-hidden="true">${String(index).padStart(2,'0')}<small>影片</small></div><div><h3>${esc(i.title)}</h3><div class="movie-meta"><span class="badge ${i.status}">${labels[i.status]}</span>${i.year?`<span>${esc(i.year)}</span>`:''}${i.douban_url?`<a href="${esc(i.douban_url)}" target="_blank" rel="noopener noreferrer">豆瓣 ↗</a>`:''}${i.quark_links.length?`<span>${i.quark_links.length} 条候选链接</span>`:''}</div>${i.error?`<p class="movie-error">${esc(i.error)}</p>`:''}${i.note?`<p class="movie-note">${esc(i.note)}</p>`:''}<div class="movie-links">${i.quark_links.map((l,n)=>`<a href="${esc(l)}" target="_blank" rel="noopener noreferrer">夸克链接 ${n+1} ↗</a>`).join('')}</div></div><div class="movie-actions">${i.quark_links.length?`<button data-copy="${i.id}">复制链接</button>`:`<a href="${esc(search)}" target="_blank" rel="noopener noreferrer">手动搜索 ↗</a>`}<button data-edit="${i.id}" ${job.active?'disabled':''}>整理</button></div></article>`;
  }).join('');
}
async function refresh(){
  try {state=await api('state');render();$('#offline').hidden=true;$('#open-import').disabled=false;$('#connection').textContent='● 本地服务已连接 · 自动保存';}
  catch(error){$('#offline').hidden=false;['run','retry','pause','open-import'].forEach(id=>$('#'+id).disabled=true);$('#connection').textContent='连接中断 · 请确认 python server.py 正在运行';}
}
function openImport(){ $('#import-error').textContent='';$('#import-dialog').showModal(); }
$('#open-import').onclick=openImport;$('#empty-import').onclick=openImport;
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$('#'+b.dataset.close).close());
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{
  mode=b.dataset.mode;
  document.querySelectorAll('[data-mode]').forEach(t=>t.setAttribute('aria-pressed',String(t===b)));
  document.querySelectorAll('[data-pane]').forEach(p=>{p.hidden=p.dataset.pane!==mode;p.querySelectorAll('input,textarea,select').forEach(c=>c.disabled=p.hidden);});
  $('#import-error').textContent='';
});
$('#import-form').onsubmit=async event=>{
  event.preventDefault();$('#import-error').textContent='';$('#import-submit').disabled=true;
  try{
    let result;
    if(mode==='douban')result=await api('job',{kind:'import',url:$('#douban-url').value.trim(),limit:Number($('#limit').value)});
    else {
      let items;
      if(mode==='text')items=$('#titles').value.split('\n').map(t=>t.trim()).filter(Boolean);
      else {
        const file=$('#json-file').files[0];
        if(!file)throw Error('请先选择 JSON 文件。');
        if(file.size>2000000)throw Error('文件需小于 2 MB。');
        try{items=JSON.parse(await file.text());}catch{throw Error('JSON 文件格式不正确，请检查文件内容。');}
      }
      result=await api('import',{items});
    }
    $('#import-dialog').close();toast(mode==='douban'?'正在读取豆瓣片单…':result.message);await refresh();
  }catch(e){$('#import-error').textContent=e.message;}finally{$('#import-submit').disabled=false;}
};
$('#demo').onclick=async()=>{
  try{await api('import',{items:[{title:'重庆森林',year:'1994',note:'示例片单 · 给某个下雨的晚上'},{title:'海上钢琴师',year:'1998',note:'示例片单 · 音乐响起的时候'},{title:'完美的日子',year:'2023',note:'示例片单 · 在日常里找到光'}]});await refresh();toast('已加入 3 部示例影片，未执行搜索');}catch(e){toast(e.message);}
};
$('#query').oninput=render;
$('#filters').onclick=e=>{const b=e.target.closest('[data-filter]');if(b){filter=b.dataset.filter;render();}};
$('#reset-filter').onclick=()=>{filter='all';$('#query').value='';render();};
async function run(kind){try{await api('job',{kind});await refresh();}catch(e){toast(e.message);}}
$('#run').onclick=()=>run('search');$('#retry').onclick=()=>run('retry');
$('#pause').onclick=async()=>{try{await api('pause',{});await refresh();}catch(e){toast(e.message);}};
$('#movie-list').onclick=async e=>{
  const edit=e.target.closest('[data-edit]'),copy=e.target.closest('[data-copy]');
  if(edit){const i=state.items.find(i=>i.id===edit.dataset.edit);detailId=i.id;$('#detail-title').textContent=i.title;$('#detail-links').value=i.quark_links.join('\n');$('#detail-note').value=i.note;$('#detail-error').textContent='';$('#detail-dialog').showModal();}
  if(copy){try{await navigator.clipboard.writeText(state.items.find(i=>i.id===copy.dataset.copy).quark_links.join('\n'));toast('链接已复制');}catch{toast('无法访问剪贴板，请在「整理」中手动复制链接。');}}
};
$('#detail-form').onsubmit=async e=>{
  e.preventDefault();
  try{await api('item',{id:detailId,quark_links:$('#detail-links').value.split('\n').map(s=>s.trim()).filter(Boolean),note:$('#detail-note').value});$('#detail-dialog').close();await refresh();toast('影片信息已保存');}catch(error){$('#detail-error').textContent=error.message;}
};
(async function poll(){await refresh();setTimeout(poll,1500);})();

$('#delete-item').onclick=async()=>{
  if(!confirm('将这部影片移出片单？本地保存的链接和备注也会移除。'))return;
  try{await api('delete',{id:detailId});$('#detail-dialog').close();await refresh();toast('已移出片单');}catch(e){$('#detail-error').textContent=e.message;}
};
