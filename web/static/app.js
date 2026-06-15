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
    const a = state.messages[state.messages.length - 1]; a.pending = false; a.content = 'Connection hiccup — try again.'; render(); syncCurrent();
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
  } else if (r.expert_review || r.nutrition_model) {  // generated: abstract header, no photo
    const ab = el('div', 'recipe-abstract'); ab.innerHTML = '<span class="material-symbols-outlined">restaurant</span>';
    card.appendChild(ab);
  }
  const head = el('div', 'recipe-head');
  head.appendChild(el('h3', '', r.title || 'Recipe'));
  const actions = el('div', 'recipe-actions');
  let panel = null;
  if (r.expert_review) {
    panel = renderExpertReview(r.expert_review); panel.classList.add('hidden');
    const erBtn = el('button', 'erbtn');
    erBtn.innerHTML = '<span class="material-symbols-outlined">groups</span>Expert review<span class="material-symbols-outlined chev">expand_more</span>';
    erBtn.onclick = (e) => { e.stopPropagation(); const open = !panel.classList.toggle('hidden'); erBtn.classList.toggle('on', open); };
    actions.appendChild(erBtn);
  }
  actions.appendChild(addRecipeBtn(r));
  head.appendChild(actions);
  card.appendChild(head);
  if (panel) card.appendChild(panel);
  if (r.intro) card.appendChild(el('p', 'intro', cv(r.intro)));
  const meta = el('div', 'meta');
  if (r.servings) meta.appendChild(el('span', 'pill', `${r.servings} servings`));
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
function renderExpertReview(er) {
  const panel = el('div', 'expert-review');
  const chipRow = (items, cls) => { const w = el('div', 'er-chips'); items.forEach(t => w.appendChild(el('span', 'er-chip' + (cls ? ' ' + cls : ''), t))); return w; };
  const addRow = (color, name, content) => {
    const row = el('div', 'expert-row');
    const dot = el('span', 'expert-dot'); dot.style.background = color; row.appendChild(dot);
    const txt = el('div', 'expert-txt'); txt.appendChild(el('b', '', name));
    if (content) txt.appendChild(content);
    row.appendChild(txt); panel.appendChild(row);
  };
  if (er.nutrition_note) addRow('#9e0027', 'Nutritionist', el('span', 'er-line', cv(er.nutrition_note)));
  const ds = er.diet_safety || {};
  const dw = el('div', '');
  if (ds.diet_flags && ds.diet_flags.length) dw.appendChild(chipRow(ds.diet_flags, 'ok'));
  if (ds.allergens && ds.allergens.length) dw.appendChild(chipRow(ds.allergens.map(a => '⚠ ' + a), 'warn'));
  else dw.appendChild(el('span', 'er-line', 'No common allergens flagged.'));
  if (ds.safety_note) dw.appendChild(el('span', 'er-line', cv(ds.safety_note)));
  if (dw.children.length) addRow('#2a6f7f', 'Dietitian & Safety', dw);
  const eq = er.equipment || {};
  const ew = el('div', '');
  if (eq.tools && eq.tools.length) ew.appendChild(chipRow(eq.tools, ''));
  if (eq.substitutions && eq.substitutions.length) {
    const ul = el('ul', 'er-swaps'); eq.substitutions.forEach(s => ul.appendChild(el('li', '', cv(String(s).replace(/->/g, '→'))))); ew.appendChild(ul);
  }
  if (eq.note) ew.appendChild(el('span', 'er-line', cv(eq.note)));
  if (ew.children.length) addRow('#b4501f', 'Equipment & Subs', ew);
  return panel;
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
    if (d.clarify) out.appendChild(el('div', 'calc-clarify', '💬 ' + d.clarify));
    if (d.nutrition_model) out.appendChild(el('div', 'crosscheck', `Model cross-check: ~${Math.round(d.nutrition_model.calories)} kcal, ${Math.round(d.nutrition_model.protein_g)}g protein, ${Math.round(d.nutrition_model.carbs_g)}g carbs, ${Math.round(d.nutrition_model.fat_g)}g fat`));
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
  status.appendChild(thinkingEl(mode === 'find' ? 'Finding chef recipes...' : 'Cooking up your recipe...'));
  try {
    if (mode === 'find') {
      const d = await (await fetch('/api/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
      const hits = d.results || [];
      status.textContent = hits.length ? `${hits.length} chef recipes matching your targets` : 'No matches. Try widening your targets or diets.';
      hits.forEach(h => out.appendChild(renderChefResult(h)));
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
function mdToHtml(md) {
  md = (md || '').replace(/\s*—\s*/g, ' - ');  // no em dashes in the UI
  const esc = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  let html = '', inList = false;
  const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
  (md || '').split('\n').forEach(raw => {
    const line = raw.trimEnd();
    if (/^###\s+/.test(line)) { closeList(); html += '<h4>' + inline(line.replace(/^###\s+/, '')) + '</h4>'; }
    else if (/^##\s+/.test(line)) { closeList(); html += '<h3>' + inline(line.replace(/^##\s+/, '')) + '</h3>'; }
    else if (/^#\s+/.test(line)) { closeList(); html += '<h2>' + inline(line.replace(/^#\s+/, '')) + '</h2>'; }
    else if (/^[-*]\s+/.test(line)) { if (!inList) { html += '<ul>'; inList = true; } html += '<li>' + inline(line.replace(/^[-*]\s+/, '')) + '</li>'; }
    else if (line === '') { closeList(); }
    else { closeList(); html += '<p>' + inline(line) + '</p>'; }
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

/* ---------- voice input (browser SpeechRecognition, no server needed) ---------- */
const micBtn = $('mic');
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
let recog = null, recognizing = false, micStream = null, micCtx = null, micRaf = 0, lastErr = '', micStart = 0;
function stopMicViz() {
  cancelAnimationFrame(micRaf);
  if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
  if (micCtx) { try { micCtx.close(); } catch (e) {} micCtx = null; }
  if (micBtn) micBtn.style.removeProperty('--vol');
}
async function startMicViz() {  // explicit permission + reactive level (real "listening" feedback)
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micCtx = new (window.AudioContext || window.webkitAudioContext)();
    const an = micCtx.createAnalyser(); an.fftSize = 256;
    micCtx.createMediaStreamSource(micStream).connect(an);
    const buf = new Uint8Array(an.fftSize);
    const tick = () => {
      an.getByteTimeDomainData(buf);
      let s = 0; for (let i = 0; i < buf.length; i++) { const d = buf[i] - 128; s += d * d; }
      micBtn.style.setProperty('--vol', Math.min(1, Math.sqrt(s / buf.length) / 30).toFixed(2));
      micRaf = requestAnimationFrame(tick);
    };
    tick(); return true;
  } catch (e) { return false; }
}
function endVoice() {
  recognizing = false; if (micBtn) micBtn.classList.remove('listening'); stopMicViz();
  const said = (qInput.value || '').trim();
  if (!said && lastErr && (Date.now() - micStart < 1500)) {
    qInput.placeholder = 'Voice input is blocked in this browser (e.g. Brave). Use Edge or Chrome.';
  } else if (said) { ask(said); }
  else updatePlaceholder();
}
if (micBtn && !SpeechRec) {
  micBtn.onclick = () => { qInput.placeholder = 'Voice input needs Chrome or Edge. Type instead.'; };
} else if (micBtn) {
  let finalText = '';
  const startRecog = async () => {
    lastErr = ''; finalText = ''; micStart = Date.now();
    if (!(await startMicViz())) { qInput.placeholder = 'Mic blocked. Allow microphone access, then tap again.'; return; }
    recog = new SpeechRec();
    recog.lang = 'en-US'; recog.interimResults = true; recog.continuous = true; recog.maxAlternatives = 1;
    recog.onstart = () => { recognizing = true; micBtn.classList.add('listening'); qInput.placeholder = 'Listening, speak now...'; };
    recog.onresult = (e) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalText += t; else interim += t;
      }
      qInput.value = (finalText + interim).trim();
      if (finalText.trim()) { try { recog.stop(); } catch (e) {} }  // full phrase -> finish + ask
    };
    recog.onerror = (e) => { lastErr = e.error || 'error'; };
    recog.onend = endVoice;
    try { recog.start(); } catch (e) { stopMicViz(); micBtn.classList.remove('listening'); recognizing = false; }
  };
  micBtn.onclick = () => {
    if (recognizing) { try { recog.stop(); } catch (e) {} return; }
    startRecog();
  };
}

/* ---------- input wiring + boot ---------- */
if ($('send')) $('send').onclick = () => ask(qInput.value);
if (qInput) qInput.addEventListener('keydown', e => { if (e.key === 'Enter') ask(qInput.value); });
renderSessions();
render();
if (qInput) qInput.focus();
