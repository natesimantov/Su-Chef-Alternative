/* Su Chef — Flask frontend (Modern Archive). Left-sidebar app shell with
   Claude-style sessions, chat, Recipe Lab, Saved, and About. One brain (Flask
   API), one page. */

const state = {
  messages: [],
  units: localStorage.getItem('units') || 'metric',
  theme: ['archive', 'nocturnal'].includes(localStorage.getItem('theme')) ? localStorage.getItem('theme') : 'archive',
  audioOn: localStorage.getItem('audioOn') === 'on',
  busy: false,
};
const $ = (id) => document.getElementById(id);
const thread = $('thread'), empty = $('empty'), qInput = $('q');
let currentAudio = null;

/* ---------- sessions (localStorage) ---------- */
function getLS(k) { try { return JSON.parse(localStorage.getItem(k) || '[]'); } catch (e) { return []; } }
function setLS(k, v) { localStorage.setItem(k, JSON.stringify(v)); }
function mkSession() { return { id: 'S' + Date.now() + Math.random().toString(36).slice(2, 6), title: '', messages: [], ts: Date.now() }; }

let sessions = getLS('su_sessions');
if (!Array.isArray(sessions)) sessions = [];
sessions = sessions.filter(s => s && Array.isArray(s.messages) && s.messages.length);  // keep only real chats
// Always land on a fresh home screen; past chats stay in the sidebar (Claude-style).
const _firstSession = mkSession();
sessions.unshift(_firstSession);
let currentId = _firstSession.id;
state.messages = currentSession().messages;

function currentSession() { return sessions.find(s => s.id === currentId) || sessions[0]; }
function persist() { setLS('su_sessions', sessions.slice(0, 25)); localStorage.setItem('su_current', currentId); }
function syncCurrent() {
  const s = currentSession();
  const firstUser = state.messages.find(m => m.role === 'user');
  s.title = firstUser ? firstUser.content : '';
  s.ts = Date.now();
  persist(); renderSessions();
}
function newSession() {
  closeDrawer();
  const cur = currentSession();
  if (!cur.messages.length) { showView('chat'); qInput.focus(); return; }  // reuse empty
  syncCurrent();
  const s = mkSession(); sessions.unshift(s); currentId = s.id;
  state.messages = s.messages;
  persist(); render(); renderSessions(); showView('chat'); qInput.focus();
}
function loadSession(id) {
  closeDrawer();
  syncCurrent(); currentId = id;
  state.messages = currentSession().messages;
  persist(); render(); renderSessions(); showView('chat');
}
function deleteSession(id) {
  sessions = sessions.filter(s => s.id !== id);
  if (!sessions.length) sessions = [mkSession()];
  if (id === currentId) { currentId = sessions[0].id; state.messages = currentSession().messages; render(); }
  persist(); renderSessions();
}
function sessionTitle(s) { return s.customTitle || s.title || 'New topic'; }
function renameSession(id, name) {
  const s = sessions.find(x => x.id === id); if (!s) return;
  s.customTitle = (name || '').trim(); persist(); renderSessions();
}
function startRename(row, titleEl, s) {
  const inp = document.createElement('input'); inp.className = 'srename'; inp.value = sessionTitle(s);
  row.replaceChild(inp, titleEl); inp.focus(); inp.select();
  inp.onclick = (e) => e.stopPropagation();
  inp.onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); inp.blur(); } else if (e.key === 'Escape') { inp.dataset.cancel = '1'; renderSessions(); } };
  inp.onblur = () => { if (inp.dataset.cancel) return; renameSession(s.id, inp.value); };
}
function renderSessions() {
  const list = $('sessions-list'); if (!list) return;
  const ordered = [...sessions].sort((a, b) => b.ts - a.ts);
  list.innerHTML = '';
  ordered.forEach(s => {
    const row = el('div', 'session' + (s.id === currentId ? ' active' : ''));
    const t = el('span', 'stitle', sessionTitle(s).slice(0, 44));
    row.appendChild(t);
    const edit = el('button', 'sedit'); edit.innerHTML = '<span class="material-symbols-outlined">edit</span>'; edit.title = 'Rename';
    edit.onclick = (e) => { e.stopPropagation(); startRename(row, t, s); };
    const del = el('button', 'sdel'); del.innerHTML = '<span class="material-symbols-outlined">close</span>'; del.title = 'Delete';
    del.onclick = (e) => { e.stopPropagation(); deleteSession(s.id); };
    row.appendChild(edit); row.appendChild(del);
    row.onclick = () => loadSession(s.id);
    list.appendChild(row);
  });
}

/* ---------- view switching ---------- */
function showView(v) {
  document.querySelectorAll('.view').forEach(s => s.classList.toggle('active', s.id === 'v-' + v));
  document.querySelectorAll('[data-view]').forEach(a => a.classList.toggle('active', a.dataset.view === v));
  if (v === 'saved') renderSaved();
  if (v === 'about') loadAbout();
  if (v === 'lab') loadLab();
}
document.querySelectorAll('[data-view]').forEach(a =>
  a.addEventListener('click', () => {
    closeDrawer();
    if ($('modal')) $('modal').classList.add('hidden');
    showView(a.dataset.view);
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (a.dataset.view === 'chat' && qInput) qInput.focus();
  }));
if ($('newSide')) $('newSide').onclick = newSession;
if ($('newTop')) $('newTop').onclick = newSession;

/* hamburger nav menu (desktop popover) */
const menuBtn = $('menuBtn'), navMenu = $('navMenu');
if (menuBtn && navMenu) {
  menuBtn.onclick = (e) => { e.stopPropagation(); navMenu.classList.toggle('open'); };
  navMenu.querySelectorAll('[data-view]').forEach(a => a.addEventListener('click', () => navMenu.classList.remove('open')));
  document.addEventListener('click', (e) => { if (!navMenu.contains(e.target) && !menuBtn.contains(e.target)) navMenu.classList.remove('open'); });
}

/* mobile sidebar drawer */
const sidebarEl = document.querySelector('.sidebar'), scrimEl = $('scrim');
function openDrawer() { if (sidebarEl) sidebarEl.classList.add('open'); if (scrimEl) scrimEl.classList.remove('hidden'); }
function closeDrawer() { if (sidebarEl) sidebarEl.classList.remove('open'); if (scrimEl) scrimEl.classList.add('hidden'); }
if ($('mTopMenu')) $('mTopMenu').onclick = openDrawer;
if (scrimEl) scrimEl.onclick = closeDrawer;

/* ---------- theme / units / audio (Preferences) ---------- */
function applyTheme(t) { document.documentElement.setAttribute('data-theme', t); state.theme = t; localStorage.setItem('theme', t); }
applyTheme(state.theme); if ($('theme')) { $('theme').value = state.theme; $('theme').onchange = e => applyTheme(e.target.value); }

function setUnits(u) {
  state.units = u; localStorage.setItem('units', u);
  document.querySelectorAll('#units button').forEach(b => b.classList.toggle('active', b.dataset.u === u));
  if (state.messages.length) render();
}
setUnits(state.units);
document.querySelectorAll('#units button').forEach(b => b.onclick = () => setUnits(b.dataset.u));

function setAudio(on) {
  state.audioOn = on; localStorage.setItem('audioOn', on ? 'on' : 'off');
  const t = $('audioToggle'); if (!t) return;
  t.classList.toggle('on', on);
  t.innerHTML = `<span class="material-symbols-outlined">${on ? 'volume_up' : 'volume_off'}</span>${on ? 'Audio on' : 'Audio off'}`;
  if (!on) stopSpeak();
}
setAudio(state.audioOn);
if ($('audioToggle')) $('audioToggle').onclick = () => setAudio(!state.audioOn);

/* voice list — real English accents (free edge-tts) */
function fillVoices() {
  const sel = $('voice'); if (!sel || sel.options.length) return;
  [['Aria · American', 'american-f'], ['Guy · American', 'american-m'],
   ['Sonia · British', 'british-f'], ['Ryan · British', 'british-m'],
   ['Emily · Irish', 'irish-f'], ['Connor · Irish', 'irish-m'],
   ['Natasha · Australian', 'australian-f'], ['William · Australian', 'australian-m'],
   ['Neerja · Indian', 'indian-f'], ['Prabhat · Indian', 'indian-m']]
    .forEach(([label, lang]) => sel.appendChild(new Option(label, lang)));
  const saved = localStorage.getItem('voice'); if (saved) sel.value = saved;
  sel.onchange = () => localStorage.setItem('voice', sel.value);
}
fillVoices();

/* voice playback speed */
state.speed = parseFloat(localStorage.getItem('voiceSpeed')) || 1;
function rateStr() { const pct = Math.round((state.speed - 1) * 100); return (pct >= 0 ? '+' : '-') + Math.abs(pct) + '%'; }
(function initSpeed() {
  const sl = $('voiceSpeed'), val = $('speedVal'); if (!sl) return;
  const fmt = v => parseFloat(v.toFixed(2)) + 'x';
  sl.value = state.speed; if (val) val.textContent = fmt(state.speed);
  sl.oninput = () => { state.speed = parseFloat(sl.value); localStorage.setItem('voiceSpeed', state.speed); if (val) val.textContent = fmt(state.speed); };
})();
if ($('voiceTest')) $('voiceTest').onclick = () =>
  playTTS("Hi, I'm Su Chef. Let's cook something delicious together.", ($('voice') || {}).value || 'american-f');

function stopSpeak() {
  if (currentAudio) { try { currentAudio.pause(); } catch (e) {} currentAudio = null; }
  try { window.speechSynthesis.cancel(); } catch (e) {}
}
let ttsToken = 0;
async function playTTS(text, lang) {
  stopSpeak();
  const my = ++ttsToken;  // supersede any in-flight request (debounce rapid clicks)
  const clean = convertTemps(text, state.units);
  try {
    const res = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: clean, lang, rate: rateStr() }) });
    if (my !== ttsToken) return;
    if (!res.ok) throw new Error('tts');
    const blob = await res.blob();
    if (my !== ttsToken) return;
    const a = new Audio(URL.createObjectURL(blob));
    currentAudio = a;
    a.play().catch(() => fallbackSpeak(clean, lang));
  } catch (e) { if (my === ttsToken) fallbackSpeak(clean, lang); }
}
async function speak(text) {
  if (!state.audioOn || !text) return;
  playTTS(text, ($('voice') || {}).value || 'american-f');
}
function fallbackSpeak(text, lang) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    const v = voices.find(x => x.lang.toLowerCase().startsWith(lang)) || voices.find(x => /^en/i.test(x.lang));
    if (v) u.voice = v;
    u.rate = state.speed || 1;
    window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
  } catch (e) {}
}

/* ---------- ask flow ---------- */
async function ask(text) {
  text = (text || '').trim(); if (!text || state.busy) return;
  state.busy = true; qInput.value = ''; showView('chat');
  state.messages.push({ role: 'user', content: text });
  state.messages.push({ role: 'assistant', content: '', pending: true });
  render(); syncCurrent();
  try {
    const res = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: state.messages.filter(m => !m.pending).map(m => ({ role: m.role, content: m.content })), units: state.units }) });
    const data = await res.json();
    const a = state.messages[state.messages.length - 1];
    a.pending = false; a.content = data.answer || data.error || '(no answer)';
    a.context = data.context || ''; a.follow_ups = (data.follow_ups || []).slice(0, 3);
    a.recipe_suggestion = data.recipe_suggestion || ''; a.recipe = data.recipe || null;
    render(); syncCurrent(); speak(a.content);
  } catch (e) {
    const a = state.messages[state.messages.length - 1]; a.pending = false; a.content = 'Connection hiccup, try again.'; render(); syncCurrent();
  }
  state.busy = false;
}
const SUGGESTIONS = [
  'e.g. "out of buttermilk, what now?"',
  'e.g. "which pan for searing salmon?"',
  'e.g. "my caramel crystallized, help"',
  'e.g. "how do I fix a broken sauce?"',
  'e.g. "steak medium-rare temp?"',
  'e.g. "substitute for an egg in baking?"',
  'e.g. "why is my rice mushy?"',
  'e.g. "make me a cozy weeknight pasta"',
  'e.g. "how long to rest a roast?"',
  'e.g. "season a cast iron pan?"',
];
function updatePlaceholder() {
  qInput.placeholder = state.messages.length ? 'Ask a follow-up question...'
    : SUGGESTIONS[Math.floor(Math.random() * SUGGESTIONS.length)];
}
if (qInput) qInput.addEventListener('focus', () => { if (!state.messages.length && !qInput.value) updatePlaceholder(); });

/* ---------- render thread (newest-first) ---------- */
function render() {
  empty.classList.toggle('hidden', state.messages.length > 0);
  updatePlaceholder();
  const turns = [];
  for (let i = 0; i < state.messages.length; i += 2) turns.push({ q: state.messages[i], a: state.messages[i + 1], idx: i });
  thread.innerHTML = '';
  turns.reverse().forEach((turn, top) => {
    const latest = top === 0, a = turn.a || {};
    const div = el('div', 'turn ' + (latest ? 'latest' : 'old'));
    div.appendChild(el('p', 'q', `“${turn.q.content}”`));
    if (a.context) div.appendChild(el('p', 'ctx', a.context));
    const row = el('div', 'row');
    let main;
    if (!a.pending && a.recipe) main = renderRecipe(a.recipe);
    else if (a.pending) { main = el('div', 'answer'); main.appendChild(thinkingEl('Su Chef is thinking...')); }
    else { main = el('div', 'answer'); main.textContent = cv(a.content || ''); }
    row.appendChild(main);
    if (!a.pending) {
      const tools = el('div', 'answer-tools');
      tools.appendChild(tbtn('volume_up', () => speak(a.content)));
      const pin = tbtn('push_pin', (b) => { togglePin(turn); b.classList.toggle('pinned', isPinned(turn.q.content)); });
      if (isPinned(turn.q.content)) pin.classList.add('pinned');
      tools.appendChild(pin); row.appendChild(tools);
    }
    div.appendChild(row);
    if (latest && !a.pending) {
      const chips = el('div', 'chips');
      (a.follow_ups || []).slice(0, a.recipe_suggestion ? 2 : 3).forEach(f => chips.appendChild(chip(f, false)));
      if (a.recipe_suggestion) chips.appendChild(chip(a.recipe_suggestion, true));
      if (chips.children.length) div.appendChild(chips);
    }
    thread.appendChild(div);
  });
}
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function tbtn(icon, fn) { const b = el('button', 'tbtn'); b.innerHTML = `<span class="material-symbols-outlined">${icon}</span>`; b.onclick = () => fn(b); return b; }
function chip(text, isRecipe) { const b = el('button', 'chip' + (isRecipe ? ' recipe' : '')); b.textContent = (isRecipe ? '🍳 ' : '') + text; b.onclick = () => ask(text); return b; }
function thinkingEl(label) {
  const w = el('div', 'thinking');
  const spec = el('div', 'thinking-spectrum');
  for (let i = 0; i < 6; i++) { const b = el('span', 'tspec-bar'); b.style.animationDelay = (i * 0.11) + 's'; spec.appendChild(b); }
  w.appendChild(spec); w.appendChild(el('span', 'tlabel', label || 'Su Chef is thinking...'));
  return w;
}

/* ---------- recipe widget (two-column editorial + nutrition) ---------- */
function renderRecipe(r) {
  const card = el('div', 'recipe');
  if (r.image_url) {  // chef/measured recipes: real sourced photo (never AI)
    const ph = el('div', 'recipe-photo');
    const img = document.createElement('img'); img.src = r.image_url; img.alt = r.title || ''; img.loading = 'lazy';
    img.onerror = () => ph.remove();
    ph.appendChild(img); card.appendChild(ph);
  }
  const head = el('div', 'recipe-head');
  head.appendChild(el('h3', '', r.title || 'Recipe'));
  const actions = el('div', 'recipe-actions');
  actions.appendChild(shareRecipeBtn(r));
  actions.appendChild(addRecipeBtn(r));
  head.appendChild(actions);
  card.appendChild(head);
  if (r.intro) card.appendChild(el('p', 'intro', cv(r.intro)));
  const meta = el('div', 'meta');
  if (r.servings) meta.appendChild(servingsStepper(r, card));
  if (r.total_time_min) meta.appendChild(el('span', 'pill', `${r.total_time_min} min`));
  if (r.course) meta.appendChild(el('span', 'pill', r.course));
  if (r.diet_tags) r.diet_tags.split(',').map(s => s.trim()).filter(Boolean).forEach(t => meta.appendChild(el('span', 'pill diet', t)));
  if (r.nutrition && r.nutrition.calories) meta.appendChild(el('span', 'pill', `${Math.round(r.nutrition.calories)} kcal`));
  const _er = r.expert_review || {}, _ds = _er.diet_safety || {};
  (_ds.diet_flags || []).forEach(f => meta.appendChild(el('span', 'pill ok', f + ' ✓')));
  (_ds.allergens || []).forEach(a => meta.appendChild(el('span', 'pill warn', '⚠ ' + a)));
  if (meta.children.length) card.appendChild(meta);
  const cols = el('div', 'cols');
  const left = el('div', '');
  left.appendChild(el('h4', 'sec', 'Ingredients'));
  const ing = el('ul', 'ing'); (r.ingredients || []).forEach(i => ing.appendChild(el('li', '', cv(i)))); left.appendChild(ing);
  if (r.utensils && r.utensils.length) { left.appendChild(el('h4', 'sec', 'Utensils')); const u = el('ul', 'util'); r.utensils.forEach(x => u.appendChild(el('li', '', x))); left.appendChild(u); }
  if (r.nutrition) left.appendChild(renderNutrition(r.nutrition, r.measured));
  if (r.nutrition_model && !r.measured) left.appendChild(el('div', 'crosscheck', `Our trained model predicts: ~${Math.round(r.nutrition_model.calories)} kcal, ${Math.round(r.nutrition_model.protein_g)}g protein, ${Math.round(r.nutrition_model.carbs_g)}g carbs, ${Math.round(r.nutrition_model.fat_g)}g fat`));
  left.appendChild(renderExpertsTool(r));  // "Consult the experts" tool, bottom-left
  cols.appendChild(left);
  if ((r.steps && r.steps.length) || r.tip) {
    const right = el('div', '');
    if (r.steps && r.steps.length) { right.appendChild(el('h4', 'sec', 'Steps')); const steps = el('ol', 'steps'); r.steps.forEach(s => steps.appendChild(el('li', '', cv(s)))); right.appendChild(steps); }
    if (r.tip) right.appendChild(el('div', 'tip', '💡 ' + cv(r.tip)));
    cols.appendChild(right);
  } else { cols.classList.add('single'); }
  card.appendChild(cols);
  attachAskAbout(card);
  return card;
}

/* ---------- "Consult the experts" tool (per-agent dropdowns, on demand) ---------- */
const EXPERT_AGENTS = [
  { key: 'nutrition', icon: 'nutrition', color: '#c8862b', label: 'Nutritionist' },
  { key: 'diet', icon: 'health_and_safety', color: '#2a6f7f', label: 'Dietitian & Safety' },
  { key: 'equipment', icon: 'blender', color: '#6a4a8a', label: 'Equipment' },
  { key: 'subs', icon: 'swap_horiz', color: '#b4501f', label: 'Substitutions' },
];
const _expertFetches = new WeakMap();  // recipe object -> in-flight promise (fetch once)
function ensureExperts(r) {
  if (r.expert_review) return Promise.resolve(r.expert_review);
  let p = _expertFetches.get(r);
  if (!p) {
    p = fetch('/api/expert-review', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: r.title, ingredients: r.ingredients || [], steps: r.steps || [], nutrition: r.nutrition || null, units: state.units }) })
      .then(res => res.json())
      .then(d => { if (d && d.expert_review) { r.expert_review = d.expert_review; return d.expert_review; } throw new Error((d && d.error) || 'no_review'); });
    _expertFetches.set(r, p);
  }
  return p;
}
function renderExpertsTool(r) {
  const tool = el('div', 'experts-tool');
  const head = el('div', 'experts-head');
  head.innerHTML = '<span class="material-symbols-outlined">groups</span>Consult the experts';
  tool.appendChild(head);
  const list = el('div', 'experts-list'); tool.appendChild(list);
  const bodies = {};
  EXPERT_AGENTS.forEach(a => {
    const d = document.createElement('details'); d.className = 'expert-agent';
    const sum = document.createElement('summary'); sum.className = 'expert-agent-sum';
    const ic = el('span', 'expert-agent-icon material-symbols-outlined', a.icon); ic.style.background = a.color;
    sum.appendChild(ic);
    sum.appendChild(el('span', 'expert-agent-label', a.label));
    sum.appendChild(el('span', 'chev material-symbols-outlined', 'expand_more'));
    d.appendChild(sum);
    const body = el('div', 'expert-agent-body'); d.appendChild(body); bodies[a.key] = body;
    if (!r.expert_review) body.appendChild(el('div', 'expert-hint', 'Tap to consult.'));
    d.addEventListener('toggle', () => {
      if (!d.open || r.expert_review) return;
      Object.values(bodies).forEach(b => { b.innerHTML = ''; });
      body.appendChild(thinkingEl('Consulting...'));
      ensureExperts(r).then(() => fillExperts(r, bodies))
        .catch(() => { Object.values(bodies).forEach(b => { b.innerHTML = ''; b.appendChild(el('div', 'expert-hint', 'Could not reach the experts. Try again.')); }); });
    });
    list.appendChild(d);
  });
  if (r.expert_review) fillExperts(r, bodies);
  return tool;
}
function fillExperts(r, bodies) {
  const er = r.expert_review; if (!er) return;
  const chipRow = (items, cls) => { const w = el('div', 'er-chips'); items.forEach(t => w.appendChild(el('span', 'er-chip' + (cls ? ' ' + cls : ''), t))); return w; };
  const set = (body, fn) => { if (!body) return; body.innerHTML = ''; fn(body); };
  set(bodies.nutrition, b => b.appendChild(el('div', 'er-line', cv(er.nutrition_note || 'No notes on the macros.'))));
  const ds = er.diet_safety || {};
  set(bodies.diet, b => {
    if (ds.diet_flags && ds.diet_flags.length) b.appendChild(chipRow(ds.diet_flags, 'ok'));
    if (ds.allergens && ds.allergens.length) b.appendChild(chipRow(ds.allergens.map(a => '⚠ ' + a), 'warn'));
    else b.appendChild(el('div', 'er-line', 'No common allergens flagged.'));
    if (ds.safety_note) b.appendChild(el('div', 'er-line', cv(ds.safety_note)));
  });
  const eq = er.equipment || {};
  set(bodies.equipment, b => {
    if (eq.tools && eq.tools.length) b.appendChild(chipRow(eq.tools, ''));
    else b.appendChild(el('div', 'er-line', 'No special equipment needed.'));
    if (eq.note) b.appendChild(el('div', 'er-line', cv(eq.note)));
  });
  set(bodies.subs, b => {
    if (eq.substitutions && eq.substitutions.length) {
      const ul = el('ul', 'er-swaps'); eq.substitutions.forEach(s => ul.appendChild(el('li', '', cv(String(s).replace(/->/g, '→'))))); b.appendChild(ul);
    } else b.appendChild(el('div', 'er-line', 'No swaps suggested.'));
  });
}

/* ---------- servings stepper (smart AI rescale, debounced to one call) ---------- */
function servingsStepper(r, card) {
  if (!(r.ingredients && r.ingredients.length)) return el('span', 'pill', `${r.servings} servings`);
  const wrap = el('div', 'servings-step');
  const dec = el('button', 'sv-btn'); dec.type = 'button'; dec.innerHTML = '<span class="material-symbols-outlined">remove</span>';
  const lab = el('span', 'sv-num'); const inc = el('button', 'sv-btn'); inc.type = 'button'; inc.innerHTML = '<span class="material-symbols-outlined">add</span>';
  wrap.appendChild(dec); wrap.appendChild(lab); wrap.appendChild(inc);
  const base = r.servings; let target = r.servings, timer = null;
  const draw = () => { lab.textContent = `${target} serving${target === 1 ? '' : 's'}`; dec.disabled = target <= 1; inc.disabled = target >= 99; };
  const schedule = () => {
    draw();
    if (timer) clearTimeout(timer);
    if (target === base) return;  // back to where we started; nothing to do
    timer = setTimeout(() => doRescale(r, target, card, wrap), 800);  // one call after clicks settle
  };
  dec.onclick = () => { if (target > 1) { target--; schedule(); } };
  inc.onclick = () => { if (target < 99) { target++; schedule(); } };
  draw();
  return wrap;
}
async function doRescale(r, servings, card, wrap) {
  wrap.classList.add('loading');
  const lab = wrap.querySelector('.sv-num'); const prev = lab.textContent; lab.textContent = 'Rescaling...';
  try {
    const d = await (await fetch('/api/rescale', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipe: { title: r.title, servings: r.servings, ingredients: r.ingredients, steps: r.steps }, servings, units: state.units }) })).json();
    if (d.error || !d.ingredients) { lab.textContent = prev; wrap.classList.remove('loading'); toast('Could not rescale. Try again.'); return; }
    r.servings = d.servings || servings; r.ingredients = d.ingredients;
    if (d.steps && d.steps.length) r.steps = d.steps;
    try { persist(); } catch (e) {}
    card.replaceWith(renderRecipe(r));
  } catch (e) { lab.textContent = prev; wrap.classList.remove('loading'); toast('Could not rescale. Try again.'); }
}

/* ---------- share a recipe as a self-contained link (recipe encoded in URL) ---------- */
function shareRecipeBtn(r) {
  const b = el('button', 'sharerec');
  b.innerHTML = '<span class="material-symbols-outlined">ios_share</span>Share';
  b.onclick = (e) => { e.stopPropagation(); shareRecipe(r); };
  return b;
}
function encodeRecipe(obj) {
  const bytes = new TextEncoder().encode(JSON.stringify(obj));
  let bin = ''; bytes.forEach(c => bin += String.fromCharCode(c));
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function decodeRecipe(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '=';
  const bin = atob(s); const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return JSON.parse(new TextDecoder().decode(bytes));
}
async function shareRecipe(r) {
  const slim = {};
  ['title', 'intro', 'servings', 'total_time_min', 'ingredients', 'steps', 'utensils', 'tip', 'nutrition', 'course', 'diet_tags', 'image_url', 'measured']
    .forEach(k => { if (r[k] != null) slim[k] = r[k]; });
  const url = location.origin + location.pathname + '#r=' + encodeRecipe(slim);
  try { await navigator.clipboard.writeText(url); toast('Recipe link copied'); }
  catch (e) { window.prompt('Copy this recipe link:', url); }
}
function handleShareHash() {
  if (!location.hash.startsWith('#r=')) return;
  try { const r = decodeRecipe(location.hash.slice(3)); if (r && r.title) openRecipeModal(r); } catch (e) {}
  try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {}
}
function toast(msg) {
  let t = $('toast'); if (!t) { t = el('div', 'toast'); t.id = 'toast'; document.body.appendChild(t); }
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), 2600);
}
function renderNutrition(n, measured) {
  const wrap = el('div', 'nutri');
  wrap.appendChild(el('h4', 'sec', 'Nutrition · ' + (measured ? 'measured' : 'estimated')));
  const macros = el('div', 'macros');
  [['Calories', n.calories, ''], ['Protein', n.protein_g, 'g'], ['Carbs', n.carbs_g, 'g'], ['Fat', n.fat_g, 'g']].forEach(([lab, val, unit]) => {
    const s = el('div', 'stat'); s.appendChild(el('b', '', (val != null ? Math.round(val) : '—') + unit)); s.appendChild(el('span', '', lab)); macros.appendChild(s);
  });
  wrap.appendChild(macros);
  const sec = [n.fiber_g != null ? `Fiber ${Math.round(n.fiber_g)}g` : '', n.sugar_g != null ? `Sugar ${Math.round(n.sugar_g)}g` : '', n.sodium_mg != null ? `Sodium ${Math.round(n.sodium_mg)}mg` : ''].filter(Boolean).join(' · ');
  wrap.appendChild(el('div', 'second', (sec ? sec + '  · ' : '') + 'per serving'));
  return wrap;
}
function addRecipeBtn(r) {
  const b = el('button', 'addrec');
  const upd = () => { const on = isRecipeSaved(r); b.classList.toggle('on', on); b.innerHTML = `<span class="material-symbols-outlined">${on ? 'bookmark_added' : 'bookmark_add'}</span>${on ? 'Saved' : 'Add to recipes'}`; };
  b.onclick = (e) => { e.stopPropagation(); toggleRecipe(r); upd(); };
  upd(); return b;
}

/* ---------- temperatures (live °F<->°C) ---------- */
function convertTemps(text, units) {
  if (!text) return text;
  const re = /(\d{2,3}(?:\.\d+)?)\s*(?:°\s*|degrees?\s*)(C|F|celsius|fahrenheit)\b/gi;
  return text.replace(re, (m, num, unit) => {
    const u = unit[0].toUpperCase(), n = parseFloat(num);
    if (units === 'metric' && u === 'F') return Math.round((n - 32) * 5 / 9) + '°C';
    if (units === 'us' && u === 'C') return Math.round(n * 9 / 5 + 32) + '°F';
    return Math.round(n) + '°' + u;
  });
}
const cv = (t) => convertTemps(t, state.units);

/* ---------- "Ask about this" (right-click / long-press in a recipe) ---------- */
function attachAskAbout(card) {
  const open = (x, y, s) => { if (s && s.trim()) showAskMenu(x, y, s.trim()); };
  card.addEventListener('contextmenu', e => { e.preventDefault(); const sel = window.getSelection().toString(); open(e.pageX, e.pageY, sel || (e.target.closest('li,h3,h4,p,span') || {}).textContent || ''); });
  let lp; card.addEventListener('touchstart', e => { const t = e.target.closest('li,h3,h4,p,span'); lp = setTimeout(() => { if (t) open(e.touches[0].pageX, e.touches[0].pageY, t.textContent); }, 550); }, { passive: true });
  card.addEventListener('touchend', () => clearTimeout(lp));
}
function showAskMenu(x, y, s) { closeAskUI(); const m = el('div', 'ctxmenu'); m.id = '__ctxmenu'; const i = el('button', 'ctxitem', '🔎 Ask about this'); m.appendChild(i); i.onclick = () => { closeAskUI(); showAskPopover(x, y, s); }; floatAt(m, x, y); document.body.appendChild(m); setTimeout(() => document.addEventListener('click', closeAskUI, { once: true }), 0); }
function showAskPopover(x, y, s) { const p = el('div', 'askpop'); p.id = '__askpop'; p.appendChild(el('div', 'askctx', `About: “${s.slice(0, 80)}”`)); const inp = document.createElement('input'); inp.placeholder = 'What do you want to know?'; p.appendChild(inp); const g = el('button', 'asksend', 'Ask'); p.appendChild(g); const go = () => { const q = inp.value.trim(); closeAskUI(); if (q) ask(`About "${s}": ${q}`); }; g.onclick = go; inp.addEventListener('keydown', e => { if (e.key === 'Enter') go(); }); floatAt(p, x, y); document.body.appendChild(p); inp.focus(); }
function floatAt(n, x, y) { n.style.position = 'absolute'; n.style.zIndex = 200; n.style.left = Math.min(x, window.innerWidth - 300) + 'px'; n.style.top = (y + 6) + 'px'; }
function closeAskUI() { ['__ctxmenu', '__askpop'].forEach(id => { const n = document.getElementById(id); if (n) n.remove(); }); }

/* ---------- pins + saved recipes (localStorage) ---------- */
function isPinned(q) { return getLS('su_pins').some(p => p.q === q); }
function togglePin(turn) {
  let pins = getLS('su_pins'); const q = turn.q.content;
  if (pins.some(p => p.q === q)) pins = pins.filter(p => p.q !== q);
  else pins.unshift({ q, title: (turn.a.recipe && turn.a.recipe.title) || q, answer: turn.a.content || '' });
  setLS('su_pins', pins.slice(0, 40));
}
function recipeKey(r) { return (r.title || '') + '|' + (r.servings || ''); }
function isRecipeSaved(r) { return getLS('su_recipes').some(x => recipeKey(x) === recipeKey(r)); }
function toggleRecipe(r) {
  let list = getLS('su_recipes'); const k = recipeKey(r);
  if (list.some(x => recipeKey(x) === k)) list = list.filter(x => recipeKey(x) !== k);
  else list.unshift(r);
  setLS('su_recipes', list.slice(0, 60));
  if ($('v-saved').classList.contains('active')) renderSaved();
}
function renderSaved() {
  const rl = $('recipes-list'), pl = $('pins-list');
  const recipes = getLS('su_recipes'), pins = getLS('su_pins');
  rl.innerHTML = recipes.length ? '' : '<p class="empty-note">Add a recipe with “Add to recipes” to keep it here.</p>';
  recipes.forEach(r => {
    const b = el('div', 'boxlink');
    const n = r.nutrition || {};
    const sub = n.calories != null ? `${Math.round(n.calories)} kcal · ${Math.round(n.protein_g || 0)}g protein/serving` : ((r.ingredients || []).length + ' ingredients');
    b.innerHTML = `<div class="t">${escapeHtml(r.title || 'Recipe')}</div><div class="m">${escapeHtml(sub)}</div>`;
    b.onclick = () => openRecipeModal(r);
    rl.appendChild(b);
  });
  pl.innerHTML = pins.length ? '' : '<p class="empty-note">Bookmark an answer with the pin to keep it here.</p>';
  pins.forEach(p => { const b = el('div', 'boxlink'); b.innerHTML = `<div class="t">${escapeHtml(p.title)}</div><div class="m">${escapeHtml((p.answer || '').slice(0, 90))}</div>`; b.onclick = () => ask(p.q); pl.appendChild(b); });
}
function escapeHtml(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

/* ---------- recipe modal ---------- */
function openRecipeModal(r) {
  const body = $('modal-body'); body.innerHTML = ''; body.appendChild(renderRecipe(r));
  $('modal').classList.remove('hidden');
}
if ($('modal-close')) $('modal-close').onclick = () => $('modal').classList.add('hidden');
if ($('modal')) $('modal').onclick = (e) => { if (e.target === $('modal')) $('modal').classList.add('hidden'); };

/* ---------- Recipe Lab ---------- */
let labLoaded = false;
async function loadLab() {
  if (labLoaded) return; labLoaded = true;
  try {
    const d = await (await fetch('/api/insights')).json();
    const cs = $('lab-course'); cs.appendChild(new Option('Any', 'Any'));
    (d.courses || []).forEach(c => cs.appendChild(new Option(c, c)));
    const chips = $('lab-diets');
    (d.diets || []).forEach(diet => {
      const b = el('button', 'dchip'); b.type = 'button'; b.textContent = diet; b.dataset.diet = diet;
      b.onclick = () => b.classList.toggle('on'); chips.appendChild(b);
    });
  } catch (e) {}
  $('lab-find').onclick = () => labRun('find');
  $('lab-generate').onclick = () => labRun('generate');
  $('est-go').onclick = estimateMeal;
}
async function estimateMeal() {
  const text = $('est-ingredients').value.trim();
  const out = $('est-result');
  if (!text) { out.textContent = 'Describe a meal first.'; return; }
  out.innerHTML = ''; out.appendChild(thinkingEl('Calculating nutrition...'));
  try {
    const d = await (await fetch('/api/calc-nutrition', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, units: state.units }) })).json();
    out.innerHTML = '';
    if (!d.nutrition) { out.textContent = d.error === 'no_key' ? 'Add an API key to calculate.' : 'Could not estimate. Try rephrasing.'; return; }
    out.appendChild(renderNutrition(d.nutrition, false));
    const note = [d.basis, d.assumptions].filter(Boolean).join(' · ');
    if (note) out.appendChild(el('div', 'calc-note', note));
    if (d.clarify) {
      const cw = el('div', 'calc-clarify');
      cw.appendChild(el('div', 'cc-q', '💬 ' + d.clarify));
      const rowq = el('div', 'cc-row');
      const inp = document.createElement('input'); inp.className = 'cc-input'; inp.placeholder = 'Add the detail and recalculate...';
      const go = el('button', 'cc-go'); go.type = 'button'; go.textContent = 'Recalculate';
      const submit = () => { const extra = inp.value.trim(); if (!extra) return; $('est-ingredients').value = text + ' (' + extra + ')'; estimateMeal(); };
      go.onclick = submit; inp.addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
      rowq.appendChild(inp); rowq.appendChild(go); cw.appendChild(rowq);
      out.appendChild(cw);
    }
    if (d.nutrition_model) out.appendChild(el('div', 'crosscheck', `Our trained model predicts: ~${Math.round(d.nutrition_model.calories)} kcal, ${Math.round(d.nutrition_model.protein_g)}g protein, ${Math.round(d.nutrition_model.carbs_g)}g carbs, ${Math.round(d.nutrition_model.fat_g)}g fat`));
  } catch (e) { out.textContent = 'Estimate failed. Try again.'; }
}
function labTargets() {
  const num = (id) => { const v = parseFloat($(id).value); return Number.isFinite(v) && v > 0 ? Math.round(v) : undefined; };
  const t = {}; const cal = num('t-cal'), p = num('t-protein'), c = num('t-carbs'), f = num('t-fat');
  if (cal) t.calories = cal; if (p) t.protein_g = p; if (c) t.carbs_g = c; if (f) t.fat_g = f;
  return t;
}
function labDiets() { return [...document.querySelectorAll('#lab-diets .dchip.on')].map(b => b.dataset.diet); }
function renderChefResult(h) {
  const d = document.createElement('details'); d.className = 'chef-result';
  const sum = document.createElement('summary'); sum.className = 'chef-sum';
  const thumb = el('div', 'chef-thumb');
  if (h.image_url) { const img = document.createElement('img'); img.src = h.image_url; img.alt = ''; img.loading = 'lazy'; img.onerror = () => thumb.classList.add('noimg'); thumb.appendChild(img); }
  else thumb.classList.add('noimg');
  sum.appendChild(thumb);
  const info = el('div', 'chef-info');
  info.appendChild(el('div', 'chef-title', h.title || 'Recipe'));
  const n = h.nutrition || {};
  const tags = [h.course, h.diet_tags].filter(Boolean).join(' · ');
  info.appendChild(el('div', 'chef-macros', `${Math.round(n.calories || 0)} kcal · ${Math.round(n.protein_g || 0)}g protein` + (tags ? ' · ' + tags : '')));
  sum.appendChild(info);
  sum.appendChild(el('span', 'chev material-symbols-outlined', 'expand_more'));
  d.appendChild(sum);
  const holder = el('div', 'chef-body'); d.appendChild(holder);
  let built = false;
  d.addEventListener('toggle', () => { if (d.open && !built) { built = true; holder.appendChild(renderRecipe({ ...h, measured: true })); } });
  return d;
}
async function labRun(mode) {
  const status = $('lab-status'), out = $('lab-results');
  const body = { targets: labTargets(), diets: labDiets(), course: $('lab-course').value, query: $('lab-query').value.trim(), units: state.units };
  out.innerHTML = ''; status.innerHTML = '';
  status.appendChild(thinkingEl(mode === 'find' ? 'Finding chef recipes...' : 'Dreaming up ideas...'));
  try {
    if (mode === 'find') {
      const d = await (await fetch('/api/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
      const hits = d.results || [];
      status.textContent = hits.length ? `${hits.length} chef recipes matching your targets` : 'No matches. Try widening your targets or diets.';
      hits.forEach(h => out.appendChild(renderChefResult(h)));
    } else {
      // Generate = propose pickable ideas first, then build the chosen one.
      const d = await (await fetch('/api/recipe-ideas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
      const ideas = d.ideas || [];
      if (d.error || !ideas.length) { status.textContent = d.error === 'no_key' ? 'Add an API key to generate.' : 'Could not come up with ideas. Try again.'; return; }
      status.textContent = 'Pick an idea and I will build the full recipe';
      out.appendChild(renderIdeas(ideas, body));
    }
  } catch (e) { status.textContent = 'Something went wrong. Try again.'; }
}
function renderIdeas(ideas, baseBody) {
  const wrap = el('div', 'ideas');
  ideas.forEach(idea => {
    const b = el('button', 'idea'); b.type = 'button';
    b.appendChild(el('div', 'idea-title', idea.title));
    if (idea.blurb) b.appendChild(el('div', 'idea-blurb', idea.blurb));
    b.onclick = () => buildIdea(idea, baseBody);
    wrap.appendChild(b);
  });
  return wrap;
}
async function buildIdea(idea, baseBody) {
  const status = $('lab-status'), out = $('lab-results');
  out.innerHTML = ''; status.innerHTML = ''; status.appendChild(thinkingEl(`Cooking up ${idea.title}...`));
  const body = { ...baseBody, query: (idea.title + (idea.blurb ? '. ' + idea.blurb : '')).trim() };
  try {
    const d = await (await fetch('/api/build', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
    if (d.error || !d.recipe) { status.textContent = d.answer || 'Could not generate a recipe.'; return; }
    status.textContent = 'Generated for you';
    if (d.fit) out.appendChild(renderFit(d.fit));
    out.appendChild(renderRecipe(d.recipe));
  } catch (e) { status.textContent = 'Something went wrong. Try again.'; }
}
function renderFit(fit) {
  const wrap = el('div', 'fit ' + (fit.on_target ? 'ok' : 'near'));
  wrap.appendChild(el('span', 'fit-head', fit.on_target ? '✓ On target' : '≈ Close to target'));
  fit.metrics.forEach(m => {
    const lab = { calories: 'kcal', protein_g: 'g protein', carbs_g: 'g carbs', fat_g: 'g fat' }[m.key] || m.key;
    wrap.appendChild(el('span', 'fit-m' + (m.ok ? ' ok' : ''), `${Math.round(m.value)} / ${m.target} ${lab}`));
  });
  return wrap;
}

/* ---------- About (estimator + model card) ---------- */
function mdToHtml(md) {
  md = (md || '').replace(/\s*—\s*/g, ' - ');  // no em dashes in the UI
  const esc = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Join soft-wrapped continuation lines so a wrapped bullet/paragraph stays one block.
  let items = [], cur = null;
  md.split('\n').forEach(raw => {
    const line = raw.trim();
    if (line === '') { cur = null; items.push({ t: 'blank' }); }
    else if (/^#{1,3}\s+/.test(line)) { cur = null; items.push({ t: 'h', n: line.match(/^#+/)[0].length, s: line.replace(/^#{1,3}\s+/, '') }); }
    else if (/^[-*]\s+/.test(line)) { cur = { t: 'li', s: line.replace(/^[-*]\s+/, '') }; items.push(cur); }
    else if (cur) { cur.s += ' ' + line; }
    else { cur = { t: 'p', s: line }; items.push(cur); }
  });
  let html = '', inList = false;
  const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
  items.forEach(it => {
    if (it.t === 'li') { if (!inList) { html += '<ul>'; inList = true; } html += '<li>' + inline(it.s) + '</li>'; return; }
    closeList();
    if (it.t === 'h') { const tag = it.n === 1 ? 'h2' : it.n === 2 ? 'h3' : 'h4'; html += '<' + tag + '>' + inline(it.s) + '</' + tag + '>'; }
    else if (it.t === 'p') { html += '<p>' + inline(it.s) + '</p>'; }
  });
  closeList();
  return html;
}
let aboutLoaded = false;
async function loadAbout() {
  if (aboutLoaded) return; aboutLoaded = true;
  try {
    const d = await (await fetch('/api/insights')).json();
    $('about-modelcard').innerHTML = mdToHtml(d.model_card || '');
  } catch (e) {}
  const frame = $('eda-frame'), det = frame && frame.closest('details');
  if (det) det.addEventListener('toggle', () => { if (det.open && !frame.src && frame.dataset.src) frame.src = frame.dataset.src; });
}

/* ---------- voice input (browser SpeechRecognition; it manages its own mic) ---------- */
const micBtn = $('mic');
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
let recog = null, recognizing = false;
if (micBtn && !SpeechRec) {
  micBtn.onclick = () => { qInput.placeholder = 'Voice input needs Chrome or Edge (Brave/Firefox block it). Type instead.'; };
} else if (micBtn) {
  let finalText = '', lastErr = '';
  const start = () => {
    finalText = ''; lastErr = '';
    recog = new SpeechRec();
    recog.lang = 'en-US'; recog.interimResults = true; recog.continuous = true; recog.maxAlternatives = 1;
    recog.onstart = () => { recognizing = true; micBtn.classList.add('listening'); qInput.placeholder = 'Listening, speak now...'; };
    recog.onresult = (e) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const tr = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalText += tr; else interim += tr;
      }
      qInput.value = (finalText + interim).trim();
      if (finalText.trim()) { try { recog.stop(); } catch (e) {} }  // got a full phrase -> finish + ask
    };
    recog.onerror = (e) => { lastErr = e.error || 'error'; };
    recog.onend = () => {
      recognizing = false; micBtn.classList.remove('listening');
      const said = (qInput.value || '').trim();
      if (said) { ask(said); return; }
      if (lastErr === 'not-allowed' || lastErr === 'service-not-allowed')
        qInput.placeholder = 'Mic blocked. Allow access, or use Edge/Chrome (Brave blocks voice).';
      else if (lastErr === 'no-speech') qInput.placeholder = "Didn't catch that. Tap the mic and speak.";
      else if (lastErr) qInput.placeholder = 'Voice unavailable here. Try Edge or Chrome.';
      else updatePlaceholder();
    };
    try { recog.start(); } catch (e) { recognizing = false; micBtn.classList.remove('listening'); }
  };
  micBtn.onclick = () => {
    if (recognizing) { try { recog.stop(); } catch (e) {} return; }
    start();
  };
}

/* ---------- input wiring + boot ---------- */
if ($('send')) $('send').onclick = () => ask(qInput.value);
if (qInput) qInput.addEventListener('keydown', e => { if (e.key === 'Enter') ask(qInput.value); });
renderSessions();
render();
handleShareHash();  // if opened via a shared recipe link, show that recipe
if (qInput) qInput.focus();
