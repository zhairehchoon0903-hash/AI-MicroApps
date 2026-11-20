(() => {
  const KEY = 'openmontage-film-studio-v1';
  const $ = (id) => document.getElementById(id);
  const starter = {projects:[], selected:null};
  let state = load();
  function load(){try{return {...starter,...JSON.parse(localStorage.getItem(KEY)||'{}')}}catch{return {...starter}}}
  function persist(){localStorage.setItem(KEY,JSON.stringify(state));$('saveState').textContent='● Saved on this device';}
  function esc(s=''){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function current(){return state.projects.find(p=>p.id===state.selected)||state.projects[0]||null}
  function projectCard(p){return `<article class="project-card" data-open="${p.id}"><div class="project-top"><span class="tag">${esc(p.genre)}</span><span style="color:#8d9aab;font-size:10px">IN DEVELOPMENT</span></div><h3>${esc(p.name)}</h3><p>${esc(p.logline||'Your story is waiting to take shape.')}</p><div class="project-meta">${p.scenes.length} scenes · Updated ${new Date(p.updated).toLocaleDateString()}</div></article>`}
  function empty(){return '<div class="empty">No films here yet. Start with the story you cannot stop thinking about.</div>'}
  function render(){
    const total=state.projects.reduce((n,p)=>n+p.scenes.length,0);
    $('statProjects').textContent=state.projects.length;$('statScenes').textContent=total;$('statActive').textContent=state.projects.length;
    $('recentProjects').innerHTML=state.projects.length?state.projects.slice(0,3).map(projectCard).join(''):empty();
    $('allProjects').innerHTML=state.projects.length?state.projects.map(projectCard).join(''):empty();
    const p=current();const options=state.projects.map(x=>`<option value="${x.id}" ${p&&x.id===p.id?'selected':''}>${esc(x.name)}</option>`).join('');
    $('projectSelect').innerHTML=options||'<option value="">Create a film first</option>';
    $('sceneProjectSelect').innerHTML=options||'<option value="">Create a film first</option>';
    if(p){$('scriptTitle').value=p.scriptTitle||'';$('scriptText').value=p.script||'';}
    else{$('scriptTitle').value='';$('scriptText').value='';}
    renderScenes();
  }
  function renderScenes(){const p=state.projects.find(x=>x.id===$('sceneProjectSelect').value)||current();$('sceneList').innerHTML=p&&p.scenes.length?p.scenes.map((s,i)=>`<article class="scene-card"><div class="scene-number">${String(i+1).padStart(2,'0')}</div><div><h3>${esc(s.title)}</h3><p>${esc(s.description||'No scene notes yet.')}</p></div><button data-delete-scene="${s.id}" title="Delete scene" aria-label="Delete scene">✕</button></article>`).join(''):empty();}
  function openView(name){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id==='view-'+name));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.view===name));$('crumbCurrent').textContent=name.toUpperCase();$('sidebar').classList.remove('open');}
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>openView(b.dataset.view)));
  document.querySelectorAll('[data-goto]').forEach(b=>b.addEventListener('click',()=>openView(b.dataset.goto)));
  $('menuBtn').addEventListener('click',()=>$('sidebar').classList.toggle('open'));
  function newProject(){ $('projectForm').reset();$('projectDialog').showModal(); }
  $('newProject').addEventListener('click',newProject);$('newProjectTop').addEventListener('click',newProject);
  $('projectForm').addEventListener('submit',e=>{if(e.submitter&&e.submitter.id==='createProject'){e.preventDefault();const name=$('projectName').value.trim();if(!name)return;const p={id:crypto.randomUUID(),name,genre:$('projectGenre').value,logline:$('projectLogline').value.trim(),scriptTitle:'',script:'',scenes:[],updated:Date.now()};state.projects.unshift(p);state.selected=p.id;persist();$('projectDialog').close();render();openView('projects');}});
  document.addEventListener('click',e=>{const card=e.target.closest('[data-open]');if(card){state.selected=card.dataset.open;persist();render();openView('writer');}});
  $('projectSelect').addEventListener('change',e=>{state.selected=e.target.value;render();});
  $('sceneProjectSelect').addEventListener('change',renderScenes);
  $('saveScript').addEventListener('click',()=>{const p=current();if(!p)return; p.scriptTitle=$('scriptTitle').value;p.script=$('scriptText').value;p.updated=Date.now();persist();$('scriptStatus').textContent='Saved just now.';});
  $('addScene').addEventListener('click',()=>{const p=state.projects.find(x=>x.id===$('sceneProjectSelect').value)||current();if(!p){alert('Create a film project first.');return;}const title=prompt('Scene title (for example: The First Omen)');if(!title||!title.trim())return;const description=prompt('What happens in this scene?')||'';p.scenes.push({id:crypto.randomUUID(),title:title.trim(),description});p.updated=Date.now();state.selected=p.id;persist();render();});
  $('sceneList').addEventListener('click',e=>{const b=e.target.closest('[data-delete-scene]');if(!b)return;const p=state.projects.find(x=>x.id===$('sceneProjectSelect').value)||current();if(!p)return;p.scenes=p.scenes.filter(s=>s.id!==b.dataset.deleteScene);p.updated=Date.now();persist();renderScenes();$('statScenes').textContent=state.projects.reduce((n,x)=>n+x.scenes.length,0);});
  if('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('./sw.js').catch(()=>{});
  render();
})();