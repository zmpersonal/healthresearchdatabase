const fmt = new Intl.NumberFormat('en-US');
let HRD_STUDIES = [];
let HRD_STATS = null;
let FEED_FILTER = 'all';

async function loadJSON(path){
  const r = await fetch(path,{cache:'no-store'});
  if(!r.ok) throw new Error(`Could not load ${path}`);
  return r.json();
}
function escapeHTML(s=''){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function shortTopics(s){const a=s.topic_names||[];return a.slice(0,2).join(' · ') || 'Indexed research';}
function pulseCard(s){
  return `<article class="pulse-card" data-design="${escapeHTML(s.design_class||'e')}">
    <div class="pulse-meta"><span class="pulse-type">${escapeHTML(s.design_label||'Research record')}</span><span class="pulse-year">${escapeHTML(s.year||'—')}</span></div>
    <h3><a href="/studies/${encodeURIComponent(s.pmid)}/">${escapeHTML(s.title)}</a></h3>
    <div class="pulse-source">${escapeHTML(s.journal||'')} ${s.doi?`· DOI ${escapeHTML(s.doi)}`:''}</div>
    <div class="pulse-bottom"><span class="pulse-topics">${escapeHTML(shortTopics(s))}</span><span class="badge ${escapeHTML(s.design_class||'e')}">${escapeHTML((s.design_label||'Other research').replace('Systematic review / meta-analysis','Review / meta-analysis').replace('Randomized controlled trial','Randomized trial'))}</span></div>
  </article>`;
}
function studyCard(s){
  const first=(s.authors||[])[0]||'';
  return `<article class="paper"><div class="meta">${escapeHTML(s.year||'—')}<br>${escapeHTML(first)}</div><div><h3><a href="/studies/${encodeURIComponent(s.pmid)}/">${escapeHTML(s.title)}</a></h3><div class="journal">${escapeHTML(s.journal||'')} ${s.doi?`· DOI ${escapeHTML(s.doi)}`:''}</div></div><span class="badge ${escapeHTML(s.design_class||'e')}">${escapeHTML(s.design_label||'Other research')}</span></article>`;
}
function setStats(stats,trials=[]){
  const pending=!stats.generated_at && !(stats.total_studies||stats.total_trials);
  document.querySelectorAll('[data-stat="studies"]').forEach(x=>x.textContent=pending?'—':fmt.format(stats.total_studies||0));
  document.querySelectorAll('[data-stat="trials"]').forEach(x=>x.textContent=pending?'—':fmt.format(stats.total_trials||0));
  document.querySelectorAll('[data-stat="topics"]').forEach(x=>x.textContent=fmt.format(stats.total_topics||0));
  document.querySelectorAll('[data-stat="updated"]').forEach(x=>x.textContent=stats.updated_label||'Refresh pending');
  const recruiting=stats.active_trials ?? trials.filter(t=>['RECRUITING','NOT_YET_RECRUITING','ACTIVE_NOT_RECRUITING','ENROLLING_BY_INVITATION'].includes(t.status)).length;
  document.querySelectorAll('[data-stat="active-trials"]').forEach(x=>x.textContent=pending?'—':fmt.format(recruiting||0));
  document.querySelectorAll('[data-topic-count]').forEach(el=>{
    const t=(stats.topics||{})[el.dataset.topicCount];
    if(t) el.textContent=pending?'Research refresh pending':`${fmt.format(t.studies||0)} publications · ${fmt.format(t.trials||0)} trials`;
  });
}
function renderFeed(){
  const feed=document.querySelector('#latest-feed'); if(!feed) return;
  let items=HRD_STUDIES;
  if(FEED_FILTER!=='all') items=items.filter(s=>s.design_class===FEED_FILTER);
  items=items.slice(0,location.pathname.startsWith('/latest')?60:6);
  feed.innerHTML=items.length?items.map(pulseCard).join(''):'<div class="loading-card">No matching records are in the current index.</div>';
}
async function hydrateHome(){
  const needed=document.querySelector('[data-stat], [data-topic-count], #latest-feed, #research-search');
  if(!needed)return;
  try{
    const [stats,studies,trials]=await Promise.all([loadJSON('/data/stats.json'),loadJSON('/data/studies.json'),loadJSON('/data/trials.json')]);
    HRD_STATS=stats;HRD_STUDIES=studies;setStats(stats,trials);renderFeed();
  }catch(e){
    console.warn(e);
    const feed=document.querySelector('#latest-feed');if(feed)feed.innerHTML='<div class="loading-card">The live research feed is refreshing. The test and static research pages remain available.</div>';
  }
}
async function initSearch(){
  const input=document.querySelector('#research-search'),results=document.querySelector('#search-results');if(!input||!results)return;
  if(!HRD_STUDIES.length){try{HRD_STUDIES=await loadJSON('/data/studies.json')}catch(e){return}}
  function run(){
    const q=input.value.trim().toLowerCase();
    if(q.length<2){results.innerHTML='';return}
    const tokens=q.split(/\s+/).filter(Boolean);
    const found=HRD_STUDIES.filter(s=>{
      const hay=[s.title,s.journal,(s.authors||[]).join(' '),(s.topic_names||[]).join(' '),(s.mesh||[]).join(' '),(s.keywords||[]).join(' ')].join(' ').toLowerCase();
      return tokens.every(t=>hay.includes(t));
    }).slice(0,15);
    results.innerHTML=found.length?`<div class="paper-list">${found.map(studyCard).join('')}</div>`:'<div class="empty">No indexed records matched that search. Try a broader term.</div>';
    results.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  input.addEventListener('input',()=>{if(input.value.trim().length>=3)run();else results.innerHTML='';});
  input.closest('form')?.addEventListener('submit',e=>{e.preventDefault();run();});
  document.querySelectorAll('[data-search-example]').forEach(b=>b.addEventListener('click',()=>{input.value=b.dataset.searchExample;run();input.focus();}));
  const initial=new URLSearchParams(location.search).get('q');if(initial){input.value=initial;run();}
}
function initFeedFilters(){
  document.querySelectorAll('[data-feed-filter]').forEach(btn=>btn.addEventListener('click',()=>{
    FEED_FILTER=btn.dataset.feedFilter;document.querySelectorAll('[data-feed-filter]').forEach(x=>x.classList.toggle('active',x===btn));renderFeed();
  }));
}
function shareUrl(url,title,text){
  if(navigator.share) return navigator.share({title,text,url}).catch(()=>{});
  return navigator.clipboard?.writeText(url);
}
function initTopicShare(){
  document.querySelectorAll('[data-topic-share]').forEach(btn=>btn.addEventListener('click',()=>shareUrl(location.href,document.title,btn.dataset.shareText||document.title)));
}
window.HRD={loadJSON,escapeHTML,shareUrl};
document.addEventListener('DOMContentLoaded',async()=>{initFeedFilters();await hydrateHome();initSearch();initTopicShare();});
