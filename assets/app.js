const fmt = new Intl.NumberFormat('en-US');

async function loadJSON(path){
  const r = await fetch(path,{cache:'no-store'});
  if(!r.ok) throw new Error(`Could not load ${path}`);
  return r.json();
}

function escapeHTML(s=''){
  return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function studyCard(s, root=''){
  const label=s.design_label||'Other research';
  const cls=s.design_class||'e';
  return `<article class="paper">
    <div class="meta">${escapeHTML(s.year||'—')}<br>${escapeHTML((s.authors||[])[0]||'')}</div>
    <div><h3><a href="${root}/studies/${encodeURIComponent(s.pmid)}/">${escapeHTML(s.title)}</a></h3><div class="journal">${escapeHTML(s.journal||'')} ${s.doi?`· DOI ${escapeHTML(s.doi)}`:''}</div></div>
    <span class="badge ${cls}">${escapeHTML(label)}</span>
  </article>`;
}

async function hydrateHome(){
  try{
    const [stats,studies,trials] = await Promise.all([
      loadJSON('/data/stats.json'),loadJSON('/data/studies.json'),loadJSON('/data/trials.json')
    ]);
    document.querySelectorAll('[data-stat="studies"]').forEach(x=>x.textContent=fmt.format(stats.total_studies||0));
    document.querySelectorAll('[data-stat="trials"]').forEach(x=>x.textContent=fmt.format(stats.total_trials||0));
    document.querySelectorAll('[data-stat="topics"]').forEach(x=>x.textContent=fmt.format(stats.total_topics||0));
    document.querySelectorAll('[data-stat="updated"]').forEach(x=>x.textContent=stats.updated_label||'Pending first refresh');
    const feed=document.querySelector('#latest-feed');
    if(feed){
      const limit=location.pathname.startsWith('/latest')?80:8;
      feed.innerHTML=studies.length?studies.slice(0,limit).map(s=>studyCard(s)).join(''):'<div class="empty">Run the research update Action once to populate the live PubMed feed.</div>';
    }
    document.querySelectorAll('[data-topic-count]').forEach(el=>{
      const slug=el.dataset.topicCount; const t=(stats.topics||{})[slug];
      if(t) el.textContent=`${fmt.format(t.studies||0)} papers · ${fmt.format(t.trials||0)} trials`;
    });
    const recruiting=trials.filter(t=>['RECRUITING','NOT_YET_RECRUITING','ACTIVE_NOT_RECRUITING','ENROLLING_BY_INVITATION'].includes(t.status)).length;
    const r=document.querySelector('[data-stat="active-trials"]');if(r)r.textContent=fmt.format(recruiting);
  }catch(e){console.warn(e)}
}

async function initSearch(){
  const input=document.querySelector('#research-search');
  const results=document.querySelector('#search-results');
  if(!input||!results)return;
  let studies=[];
  try{studies=await loadJSON('/data/studies.json')}catch(e){return}
  function run(){
    const q=input.value.trim().toLowerCase();
    if(q.length<2){results.innerHTML='';return}
    const found=studies.filter(s=>[s.title,s.journal,(s.authors||[]).join(' '),(s.topics||[]).join(' '),(s.mesh||[]).join(' ')].join(' ').toLowerCase().includes(q)).slice(0,12);
    results.innerHTML=found.length?`<div class="paper-list">${found.map(s=>studyCard(s)).join('')}</div>`:'<div class="empty">No indexed records matched that search.</div>';
  }
  input.addEventListener('input',run);
  const form=input.closest('form');if(form)form.addEventListener('submit',e=>{e.preventDefault();run();});
}

document.addEventListener('DOMContentLoaded',()=>{hydrateHome();initSearch()});
