(() => {
  const $ = (id) => document.getElementById(id);
  const PROJECT_KEY = 'openmontage-film-studio-v1';
  let providers = [];
  let quotes = [];
  let selectedQuote = null;
  let tasks = [];
  let selectedProject = '';

  function headers(extra = {}) {
    const token = sessionStorage.getItem('filmStudioToken');
    return { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra };
  }
  async function api(path, options = {}) {
    const response = await fetch(path, { ...options, headers: headers(options.headers || {}) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail?.message || data.detail || data.message || `Server request failed (${response.status})`);
    return data;
  }
  function currentLocalProject() {
    try {
      const saved = JSON.parse(localStorage.getItem(PROJECT_KEY) || '{}');
      return (saved.projects || []).find((p) => p.id === saved.selected) || null;
    } catch { return null; }
  }
  function setStatus(id, message, kind = '') {
    const node = $(id); if (!node) return;
    node.textContent = message; node.className = `result-note ${kind}`;
  }
  function safe(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  async function loadProjects() {
    const select = $('videoProject');
    try {
      const data = await api('/api/projects');
      const list = data.projects || [];
      select.innerHTML = list.length ? list.map((p) => {
        const id = p.project_id || p.id;
        const title = p.title || p.name || id;
        return `<option value="${safe(id)}">${safe(title)}</option>`;
      }).join('') : '<option value="">No server projects — create one in Production Engine</option>';
      const local = currentLocalProject();
      const preferred = local?.backend ? local.id : '';
      if (preferred && list.some((p) => (p.project_id || p.id) === preferred)) select.value = preferred;
      selectedProject = select.value;
      await loadTasks();
      await loadShots();
    } catch (error) {
      select.innerHTML = '<option value="">Could not load server projects</option>';
      setStatus('videoLabStatus', `Server connection required: ${error.message}`, 'error');
    }
  }
  function renderProviders() {
    const ready = providers.filter((p) => p.configured);
    $('videoProviderCards').innerHTML = providers.map((p) => `<article class="video-provider-card ${p.configured ? 'ready' : 'not-ready'}"><div><b>${safe(p.name)}</b><span class="video-provider-state">${p.configured ? 'READY' : 'NOT CONFIGURED'}</span></div><small>${safe(p.model || '')}</small><p>${safe(p.note || '')}</p><small>API key: ${p.key_configured ? 'configured' : 'missing'} · Pricing: ${p.pricing_configured ? 'configured' : 'missing'}</small></article>`).join('') || '<div class="empty">No provider adapters registered.</div>';
    $('videoLabStatus').innerHTML = `<b>${ready.length} of ${providers.length} video engines ready</b><span>Credentials remain server-side. Checking readiness does not spend credits or start generation.</span>`;
  }
  async function loadProviders() {
    try { const data = await api('/api/video/providers'); providers = data.providers || []; renderProviders(); }
    catch (error) { $('videoLabStatus').textContent = `Could not inspect providers: ${error.message}`; }
  }
  async function loadShots() {
    const select = $('videoShotSelect');
    const projectId = $('videoProject').value;
    if (!projectId) { select.innerHTML = '<option value="">Choose a production project first</option>'; return; }
    try {
      const data = await api(`/api/projects/${encodeURIComponent(projectId)}`);
      const shots = data.studio?.shots || [];
      select.innerHTML = '<option value="">Choose a planned shot to prefill the prompt</option>' + shots.map((shot, i) => `<option value="${i}">${safe(shot.title || `Shot ${i + 1}`)}</option>`).join('');
      select.dataset.shots = JSON.stringify(shots);
    } catch (error) {
      select.innerHTML = `<option value="">Could not load shot plan: ${safe(error.message)}</option>`;
    }
  }
  function usePlannedShot() {
    const select = $('videoShotSelect');
    if (!select.value) return;
    let shots = []; try { shots = JSON.parse(select.dataset.shots || '[]'); } catch {}
    const shot = shots[Number(select.value)]; if (!shot) return;
    const parts = [
      `Shot: ${shot.title || 'Untitled shot'}.`,
      shot.scene ? `Scene: ${shot.scene}.` : '',
      shot.framing ? `Framing: ${shot.framing}.` : '',
      shot.movement ? `Camera movement: ${shot.movement}.` : '',
      shot.description ? `Visual direction: ${shot.description}.` : '',
      'Photorealistic cinematic character performance with natural body movement, believable facial expression and eye focus, physically plausible gestures, subtle hair and fabric motion, and coherent environmental movement. Preserve the approved character appearance and scene continuity.'
    ].filter(Boolean);
    $('videoPrompt').value = parts.join(' ').slice(0, 1000);
  }
  function handleFrameUpload(event) {
    const file = event.target.files?.[0]; if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) { setStatus('videoQuoteStatus', 'Choose a PNG, JPG, or WEBP image.', 'error'); event.target.value = ''; return; }
    if (file.size > 3.5 * 1024 * 1024) { setStatus('videoQuoteStatus', 'This image is too large. Choose a file under 3.5 MB.', 'error'); event.target.value = ''; return; }
    const reader = new FileReader();
    reader.onload = () => {
      $('videoStartImage').value = String(reader.result || '');
      $('videoFramePreview').hidden = false;
      $('videoFramePreview').innerHTML = `<img alt="Starting frame preview" src="${String(reader.result)}"><span>${safe(file.name)} · ${(file.size / 1024 / 1024).toFixed(2)} MB</span>`;
      setStatus('videoQuoteStatus', 'Starting frame loaded. Compare providers when your shot prompt is ready.', 'success');
    };
    reader.onerror = () => setStatus('videoQuoteStatus', 'Could not read the selected image.', 'error');
    reader.readAsDataURL(file);
  }
  function requestBody() {
    return {
      prompt: $('videoPrompt').value.trim(),
      start_image_url: $('videoStartImage').value.trim(),
      duration_seconds: Number($('videoDuration').value),
      aspect_ratio: $('videoRatio').value,
      resolution: $('videoResolution').value,
      audio: $('videoAudio').checked,
    };
  }
  function renderQuotes() {
    if (!quotes.length) { $('videoQuotes').innerHTML = '<div class="empty">No configured provider returned a quote. Configure an API key and current pricing on the server.</div>'; $('videoGenerateButton').disabled = true; return; }
    $('videoQuotes').innerHTML = quotes.map((q, i) => `<label class="video-quote ${selectedQuote?.provider_id === q.provider_id ? 'selected' : ''}"><input type="radio" name="videoProvider" value="${safe(q.provider_id)}" ${selectedQuote?.provider_id === q.provider_id ? 'checked' : ''}><span><b>${safe(q.provider_name)}</b><small>${safe(q.model)} · ${q.duration_seconds}s · ${safe(q.aspect_ratio)} · ${safe(q.resolution)}</small><small>${safe(q.pricing_basis)}</small></span><strong>$${Number(q.estimated_cost_usd).toFixed(2)}</strong></label>`).join('') + `<p class="hint">${safe(quotes[0].warning || '')}</p>`;
    $('videoQuotes').querySelectorAll('input[name="videoProvider"]').forEach((radio) => radio.addEventListener('change', () => {
      selectedQuote = quotes.find((q) => q.provider_id === radio.value) || null; renderQuotes();
    }));
    $('videoGenerateButton').disabled = !selectedQuote;
  }
  async function compareQuotes() {
    const projectId = $('videoProject').value;
    if (!projectId) return setStatus('videoQuoteStatus', 'Choose a server-side production project first.', 'error');
    const body = requestBody();
    if (!body.prompt || !body.start_image_url) return setStatus('videoQuoteStatus', 'Enter a motion prompt and a starting-frame image URL or data URI.', 'error');
    $('videoQuoteButton').disabled = true; setStatus('videoQuoteStatus', 'Comparing configured providers…');
    try {
      const data = await api(`/api/projects/${encodeURIComponent(projectId)}/video/quote`, { method: 'POST', body: JSON.stringify(body) });
      quotes = data.quotes || []; selectedQuote = quotes[0] || null; renderQuotes();
      setStatus('videoQuoteStatus', `${quotes.length} estimate(s) returned. No generation has started.`, quotes.length ? 'success' : '');
    } catch (error) { quotes = []; selectedQuote = null; renderQuotes(); setStatus('videoQuoteStatus', error.message, 'error'); }
    finally { $('videoQuoteButton').disabled = false; }
  }
  async function generate() {
    const projectId = $('videoProject').value;
    const ceiling = Number($('videoSpendLimit').value);
    if (!selectedQuote || !projectId) return;
    if (!Number.isFinite(ceiling) || ceiling < selectedQuote.estimated_cost_usd) return setStatus('videoGenerateStatus', 'Enter a maximum spend equal to or higher than the selected estimate.', 'error');
    const message = `You are approving ONE paid video generation.\nProvider: ${selectedQuote.provider_name}\nModel: ${selectedQuote.model}\nEstimated cost: $${selectedQuote.estimated_cost_usd.toFixed(2)}\nYour maximum: $${ceiling.toFixed(2)}\nDuration: ${selectedQuote.duration_seconds} seconds\nAspect ratio: ${selectedQuote.aspect_ratio}\n\nProvider prices can change. Continue only if you accept this estimated charge.`;
    if (!window.confirm(message)) return;
    $('videoGenerateButton').disabled = true; setStatus('videoGenerateStatus', 'Submitting one approved generation…');
    try {
      const body = { ...requestBody(), provider_id: selectedQuote.provider_id, approved_max_spend_usd: ceiling, confirm_generation: true };
      const data = await api(`/api/projects/${encodeURIComponent(projectId)}/video/generate`, { method: 'POST', body: JSON.stringify(body) });
      setStatus('videoGenerateStatus', `Submitted. Task ${data.task.task_id} · ${data.task.status}.`, 'success');
      await loadTasks();
    } catch (error) { setStatus('videoGenerateStatus', error.message, 'error'); }
    finally { $('videoGenerateButton').disabled = !selectedQuote; }
  }
  function renderTasks() {
    const node = $('videoTaskList');
    if (!tasks.length) { node.innerHTML = '<div class="empty">No generated shots recorded for this project yet.</div>'; return; }
    node.innerHTML = tasks.map((task) => `<article class="video-task-card"><div class="video-task-head"><b>${safe(task.provider_name)} · ${safe(task.model)}</b><span class="video-task-status">${safe(task.status)}</span></div><p>${safe(task.prompt)}</p><small>${safe(task.duration_seconds)}s · ${safe(task.aspect_ratio)} · ${safe(task.resolution)} · estimate $${Number(task.quote?.estimated_cost_usd || 0).toFixed(2)}</small>${task.output_url ? `<video controls playsinline preload="metadata" src="${safe(task.output_url)}"></video><a href="${safe(task.output_url)}" target="_blank" rel="noopener">Open generated video</a>` : ''}${task.error ? `<p class="error-text">${safe(task.error)}</p>` : ''}<button class="secondary" data-refresh-task="${safe(task.task_id)}" type="button">Refresh task</button></article>`).join('');
    node.querySelectorAll('[data-refresh-task]').forEach((button) => button.addEventListener('click', () => refreshTask(button.dataset.refreshTask)));
  }
  async function loadTasks() {
    const projectId = $('videoProject').value;
    if (!projectId) { tasks = []; renderTasks(); return; }
    try { const data = await api(`/api/projects/${encodeURIComponent(projectId)}/video/tasks`); tasks = data.tasks || []; renderTasks(); }
    catch (error) { $('videoTaskList').innerHTML = `<div class="empty">${safe(error.message)}</div>`; }
  }
  async function refreshTask(taskId) {
    const projectId = $('videoProject').value; if (!projectId) return;
    try { const data = await api(`/api/projects/${encodeURIComponent(projectId)}/video/tasks/${encodeURIComponent(taskId)}`); tasks = tasks.map((task) => task.task_id === taskId ? data.task : task); renderTasks(); }
    catch (error) { setStatus('videoGenerateStatus', error.message, 'error'); }
  }
  function init() {
    if (!$('view-video-lab')) return;
    document.querySelectorAll('[data-view="video-lab"]').forEach((button) => button.addEventListener('click', () => { loadProviders(); loadProjects(); }));
    $('videoQuoteButton').addEventListener('click', compareQuotes);
    $('videoGenerateButton').addEventListener('click', generate);
    $('refreshVideoTasks').addEventListener('click', loadTasks);
    $('videoShotSelect').addEventListener('change', usePlannedShot);
    $('videoStartFile').addEventListener('change', handleFrameUpload);
    $('videoProject').addEventListener('change', () => { selectedProject = $('videoProject').value; loadTasks(); loadShots(); quotes = []; selectedQuote = null; renderQuotes(); });
    loadProviders(); loadProjects();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
