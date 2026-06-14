/* Su Chef — Flask frontend (Modern Archive). Left-sidebar app shell with
   Claude-style sessions, chat, Recipe Lab, Saved, and About. One brain (Flask
   API), one page. */

const state = {
  messages: [],
  units: localStorage.getItem('units') || 'metric',
  theme: ['archive', 'nocturnal'].includes(localStorage.getItem('theme')) ? localStorage.getItem('theme') : 'archive',
  audioOn: localStorage.getItem('audioOn') !== 'off',
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
let currentId = localStorage.getItem('su_current');
if (!Array.isArray(sessions) || !sessions.length) { const s = mkSession(); sessions = [s]; currentId = s.id; }
if (!sessions.find(s => s.id === currentId)) currentId = sessions[0].id;
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
  const cur = currentSession();
  if (!cur.messages.length) { showView('chat'); qInput.focus(); return; }  // reuse empty
  syncCurrent();
  const s = mkSession(); sessions.unshift(s); currentId = s.id;
  state.messages = s.messages;
  persist(); render(); renderSessions(); showView('chat'); qInput.focus();
}
function loadSession(id) {
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
function renderSessions() {
  const list = $('sessions-list'); if (!list) return;
  const ordered = [...sessions].sort((a, b) => b.ts - a.ts);
  list.innerHTML = '';
  ordered.forEach(s => {
    const title = (s.title || 'New chat').slice(0, 44);
    const row = el('div', 'session' + (s.id === currentId ? ' active' : ''));
    const t = el('span', 'stitle', title); row.appendChild(t);
    const del = el('button', 'sdel'); del.innerHTML = '<span class="material-symbols-outlined">close</span>';
    del.title = 'Delete session';
    del.onclick = (e) => { e.stopPropagation(); deleteSession(s.id); };
    row.appendChild(del);
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
  a.addEventListener('click', () => { showView(a.dataset.view); if (a.dataset.view === 'chat') qInput.focus(); }));
$('newSide').onclick = newSession;
if ($('newTop')) $('newTop').onclick = newSession;

/* hamburger nav menu (desktop) */
const menuBtn = $('menuBtn'), navMenu = $('navMenu');
if (menuBtn && navMenu) {
  menuBtn.onclick = (e) => { e.stopPropagation(); navMenu.classList.toggle('open'); };
  navMenu.querySelectorAll('[data-view]').forEach(a => a.addEventListener('click', () => navMenu.classList.remove('open')));
  document.addEventListener('click', (e) => { if (!navMenu.contains(e.target) && !menuBtn.contains(e.target)) navMenu.classList.remove('open'); });
}

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

/* voice persona list */
function fillVoices() {
  const sel = $('voice'); if (!sel || sel.options.length) return;
  [['Aria', 'en-us'], ['Sonia', 'en-gb'], ['Emily', 'en-ie'],
   ['Natasha', 'en-au'], ['Neerja', 'en-in']]
    .forEach(([label, lang]) => sel.appendChild(new Option(label, lang)));
}
fillVoices();

function stopSpeak() {
  if (currentAudio) { try { currentAudio.pause(); } catch (e) {} currentAudio = null; }
  try { window.speechSynthesis.cancel(); } catch (e) {}
}
async function speak(text) {
  if (!state.audioOn || !text) return;
  stopSpeak();
  const lang = ($('voice') || {}).value || 'en';
  const clean = convertTemps(text, state.units);
  try {
    const res = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: clean, lang }) });
    if (!res.ok) throw new Error('tts');
    const a = new Audio(URL.createObjectURL(await res.blob()));
    currentAudio = a;
    a.play().catch(() => fallbackSpeak(clean, lang));
  } catch (e) { fallbackSpeak(clean, lang); }
}
function fallbackSpeak(text, lang) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    const v = voices.find(x => x.lang.toLowerCase().startsWith(lang)) || voices.find(x => /^en/i.test(x.lang));
    if (v) u.voice = v;
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
    const a = state.messages[state.messages.length - 1]; a.pending = false; a.content = 'Connection hiccup — try again.'; render(); syncCurrent();
  }
  state.busy = false;
}
function updatePlaceholder() {
  qInput.placeholder = state.messages.length ? 'Ask a follow-up question…' : 'e.g. "out of buttermilk — what now?"';
}

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
    else { main = el('div', a.pending ? 'answer thinking' : 'answer'); main.textContent = a.pending ? 'Su Chef is thinking…' : cv(a.content || ''); }
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

/* ---------- recipe widget (two-column editorial + nutrition) ---------- */
function renderRecipe(r) {
  const card = el('div', 'recipe');
  const head = el('div', 'recipe-head');
  head.appendChild(el('h3', '', r.title || 'Recipe'));
  head.appendChild(addRecipeBtn(r));
  card.appendChild(head);
  if (r.intro) card.appendChild(el('p', 'intro', cv(r.intro)));
  const meta = el('div', 'meta');
  if (r.servings) meta.appendChild(el('span', 'pill', `${r.servings} servings`));
  if (r.total_time_min) meta.appendChild(el('span', 'pill', `${r.total_time_min} min`));
  if (r.course) meta.appendChild(el('span', 'pill', r.course));
  if (r.diet_tags) r.diet_tags.split(',').map(s => s.trim()).filter(Boolean).forEach(t => meta.appendChild(el('span', 'pill diet', t)));
  if (meta.children.length) card.appendChild(meta);
  const cols = el('div', 'cols');
  const left = el('div', '');
  left.appendChild(el('h4', 'sec', 'Ingredients'));
  const ing = el('ul', 'ing'); (r.ingredients || []).forEach(i => ing.appendChild(el('li', '', cv(i)))); left.appendChild(ing);
  if (r.utensils && r.utensils.length) { left.appendChild(el('h4', 'sec', 'Utensils')); const u = el('ul', 'util'); r.utensils.forEach(x => u.appendChild(el('li', '', x))); left.appendChild(u); }
  if (r.nutrition) left.appendChild(renderNutrition(r.nutrition, r.measured));
  if (r.nutrition_model && !r.measured) left.appendChild(el('div', 'crosscheck', `Model cross-check: ~${Math.round(r.nutrition_model.calories)} kcal, ${Math.round(r.nutrition_model.protein_g)}g protein, ${Math.round(r.nutrition_model.carbs_g)}g carbs, ${Math.round(r.nutrition_model.fat_g)}g fat`));
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
$('modal-close').onclick = () => $('modal').classList.add('hidden');
$('modal').onclick = (e) => { if (e.target === $('modal')) $('modal').classList.add('hidden'); };

/* ---------- Recipe Lab ---------- */
let labLoaded = false;
async function loadLab() {
  if (labLoaded) return; labLoaded = true;
  try {
    const d = await (await fetch('/api/insights')).json();
    const cs = $('lab-course'); cs.appendChild(new Option('Any', 'Any'));
    (d.courses || []).forEach(c => cs.appendChild(new Option(c, c)));
    const ec = $('est-course'); if (ec) (d.courses || []).forEach(c => ec.appendChild(new Option(c, c)));
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
  const ings = $('est-ingredients').value.split('\n').map(s => s.trim()).filter(Boolean);
  if (!ings.length) { $('est-result').textContent = 'Add a few ingredients first.'; return; }
  const body = { ingredients: ings, num_ingredients: ings.length, servings: +$('est-servings').value || 2, course: $('est-course').value };
  $('est-result').textContent = 'Estimating…';
  try {
    const d = await (await fetch('/api/estimate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
    $('est-result').innerHTML = '';
    if (d.nutrition) $('est-result').appendChild(renderNutrition(d.nutrition, false));
    else $('est-result').textContent = d.error || 'Estimate unavailable';
  } catch (e) { $('est-result').textContent = 'Estimate failed. Try again.'; }
}
function labTargets() {
  const num = (id) => { const v = parseFloat($(id).value); return Number.isFinite(v) && v > 0 ? Math.round(v) : undefined; };
  const t = {}; const cal = num('t-cal'), p = num('t-protein'), c = num('t-carbs'), f = num('t-fat');
  if (cal) t.calories = cal; if (p) t.protein_g = p; if (c) t.carbs_g = c; if (f) t.fat_g = f;
  return t;
}
function labDiets() { return [...document.querySelectorAll('#lab-diets .dchip.on')].map(b => b.dataset.diet); }
async function labRun(mode) {
  const status = $('lab-status'), out = $('lab-results');
  const body = { targets: labTargets(), diets: labDiets(), course: $('lab-course').value, query: $('lab-query').value.trim(), units: state.units };
  out.innerHTML = ''; status.textContent = mode === 'find' ? 'Finding chef recipes…' : 'Cooking up a custom recipe…';
  try {
    if (mode === 'find') {
      const d = await (await fetch('/api/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
      const hits = d.results || [];
      status.textContent = hits.length ? `${hits.length} chef recipes matching your targets` : 'No matches — try widening your targets or diets.';
      hits.forEach(h => out.appendChild(renderRecipe({ ...h, measured: true })));
    } else {
      const d = await (await fetch('/api/build', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
      if (d.error || !d.recipe) { status.textContent = d.answer || 'Could not generate a recipe.'; return; }
      status.textContent = 'Generated for you';
      if (d.fit) out.appendChild(renderFit(d.fit));
      out.appendChild(renderRecipe(d.recipe));
    }
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
let aboutLoaded = false;
async function loadAbout() {
  if (aboutLoaded) return; aboutLoaded = true;
  try {
    const d = await (await fetch('/api/insights')).json();
    $('about-modelcard').textContent = d.model_card || '';
  } catch (e) {}
  const frame = $('eda-frame'), det = frame && frame.closest('details');
  if (det) det.addEventListener('toggle', () => { if (det.open && !frame.src && frame.dataset.src) frame.src = frame.dataset.src; });
}

/* ---------- voice input (record -> /api/transcribe -> ask) ---------- */
const micBtn = $('mic');
let recording = false, mediaRecorder, audioCtx, analyser, rafId, micStream, chunks = [];
let startedAt = 0, lastVoiceAt = 0, hasSpoken = false;
const SILENCE_MS = 2000, MAX_MS = 15000, NO_SPEECH_MS = 7000, SPEAK_RMS = 9, SILENCE_RMS = 6;
micBtn.onclick = async () => {
  if (recording) { stopRec(); return; }
  if (!navigator.mediaDevices || !window.MediaRecorder) { qInput.placeholder = 'Voice not supported — type instead'; return; }
  try { micStream = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch (e) { qInput.placeholder = 'Mic blocked — type instead'; return; }
  chunks = []; mediaRecorder = new MediaRecorder(micStream);
  mediaRecorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
  mediaRecorder.onstop = finishRec; mediaRecorder.start();
  audioCtx = new (window.AudioContext || window.webkitAudioContext)(); analyser = audioCtx.createAnalyser(); analyser.fftSize = 256;
  audioCtx.createMediaStreamSource(micStream).connect(analyser);
  startedAt = lastVoiceAt = Date.now(); hasSpoken = false; recording = true; micBtn.classList.add('listening'); monitor();
};
function rmsLevel() { const b = new Uint8Array(analyser.fftSize); analyser.getByteTimeDomainData(b); let s = 0; for (let i = 0; i < b.length; i++) { const d = b[i] - 128; s += d * d; } return Math.sqrt(s / b.length); }
function monitor() { const now = Date.now(), lvl = rmsLevel(); if (lvl > SPEAK_RMS) { hasSpoken = true; lastVoiceAt = now; } if (now - startedAt > MAX_MS) return stopRec(); if (!hasSpoken && now - startedAt > NO_SPEECH_MS) return stopRec(); if (hasSpoken && lvl < SILENCE_RMS && now - lastVoiceAt > SILENCE_MS) return stopRec(); rafId = requestAnimationFrame(monitor); }
function stopRec() { if (!recording) return; recording = false; cancelAnimationFrame(rafId); micBtn.classList.remove('listening'); try { mediaRecorder.stop(); } catch (e) {} }
async function finishRec() {
  if (micStream) micStream.getTracks().forEach(t => t.stop()); if (audioCtx) audioCtx.close().catch(() => {});
  if (!hasSpoken || !chunks.length) return;
  const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' }); const fd = new FormData(); fd.append('audio', blob, 'rec.webm');
  const ph = qInput.placeholder; qInput.placeholder = 'Transcribing…';
  try { const d = await (await fetch('/api/transcribe', { method: 'POST', body: fd })).json(); qInput.placeholder = ph; if (d.text) ask(d.text); } catch (e) { qInput.placeholder = ph; }
}

/* ---------- input wiring + boot ---------- */
$('send').onclick = () => ask(qInput.value);
qInput.addEventListener('keydown', e => { if (e.key === 'Enter') ask(qInput.value); });
renderSessions();
render();
qInput.focus();
