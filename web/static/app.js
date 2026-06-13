/* Su Chef — Flask frontend (Modern Archive). Left-sidebar app shell + the
   conversation/recipe/insights/prefs views. One brain (Flask API), one page. */

const state = {
  messages: [],
  units: localStorage.getItem('units') || 'metric',
  theme: ['archive', 'nocturnal'].includes(localStorage.getItem('theme')) ? localStorage.getItem('theme') : 'archive',
  audioOn: localStorage.getItem('audioOn') !== 'off',
  busy: false,
};
const $ = (id) => document.getElementById(id);
const thread = $('thread'), empty = $('empty'), qInput = $('q');

/* ---------- view switching ---------- */
function showView(v) {
  document.querySelectorAll('.view').forEach(s => s.classList.toggle('active', s.id === 'v-' + v));
  document.querySelectorAll('[data-view]').forEach(a => a.classList.toggle('active', a.dataset.view === v));
  if (v === 'recipebox') renderBox();
  if (v === 'insights') loadInsights();
}
document.querySelectorAll('[data-view]').forEach(a =>
  a.addEventListener('click', () => { showView(a.dataset.view); if (a.dataset.home) qInput.focus(); }));

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
  if (!on) window.speechSynthesis.cancel();
}
setAudio(state.audioOn);
if ($('audioToggle')) $('audioToggle').onclick = () => setAudio(!state.audioOn);
if ($('newBtn')) $('newBtn').onclick = () => { state.messages = []; render(); window.speechSynthesis.cancel(); showView('chat'); qInput.focus(); };

/* voice persona list */
function fillVoices() {
  const sel = $('voice'); if (!sel) return;
  const voices = window.speechSynthesis.getVoices();
  const want = [['James — default','en'],['British','en-gb'],['American','en-us'],['Irish','en-ie'],['Australian','en-au'],['Indian','en-in']];
  sel.innerHTML = '';
  want.forEach(([label, lang]) => {
    const ok = lang === 'en' || voices.some(v => v.lang.toLowerCase().startsWith(lang));
    const o = document.createElement('option'); o.value = lang; o.textContent = label + (ok ? '' : ' · needs Edge'); o.disabled = !ok;
    sel.appendChild(o);
  });
}
fillVoices(); window.speechSynthesis.onvoiceschanged = fillVoices;
function speak(text) {
  if (!state.audioOn || !text) return;
  const u = new SpeechSynthesisUtterance(convertTemps(text, state.units));
  const lang = ($('voice') || {}).value || 'en', voices = window.speechSynthesis.getVoices();
  const v = voices.find(x => x.lang.toLowerCase().startsWith(lang)) || voices.find(x => /^en/i.test(x.lang));
  if (v) u.voice = v;
  window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
}

/* ---------- ask flow ---------- */
async function ask(text) {
  text = (text || '').trim(); if (!text || state.busy) return;
  state.busy = true; qInput.value = ''; showView('chat');
  pushRecent(text);
  state.messages.push({ role: 'user', content: text });
  state.messages.push({ role: 'assistant', content: '', pending: true });
  render();
  try {
    const res = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: state.messages.filter(m => !m.pending).map(m => ({ role: m.role, content: m.content })), units: state.units }) });
    const data = await res.json();
    const a = state.messages[state.messages.length - 1];
    a.pending = false; a.content = data.answer || data.error || '(no answer)';
    a.context = data.context || ''; a.follow_ups = (data.follow_ups || []).slice(0, 3);
    a.recipe_suggestion = data.recipe_suggestion || ''; a.recipe = data.recipe || null;
    render(); speak(a.content);
  } catch (e) {
    const a = state.messages[state.messages.length - 1]; a.pending = false; a.content = 'Connection hiccup — try again.'; render();
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
      const pinned = isPinned(turn.q.content);
      const pin = tbtn(pinned ? 'bookmark' : 'bookmark_border', (b) => { togglePin(turn); b.querySelector('span').textContent = isPinned(turn.q.content) ? 'bookmark' : 'bookmark_border'; });
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
  card.appendChild(el('h3', '', r.title || 'Recipe'));
  if (r.intro) card.appendChild(el('p', 'intro', cv(r.intro)));
  const meta = el('div', 'meta');
  if (r.servings) meta.appendChild(el('span', 'pill', `${r.servings} servings`));
  if (r.total_time_min) meta.appendChild(el('span', 'pill', `${r.total_time_min} min`));
  if (r.quick_prob != null) meta.appendChild(el('span', 'pill quick', (r.quick_prob >= 0.5 ? 'Quick' : 'Involved') + ` · ${Math.round(r.quick_prob*100)}%`));
  card.appendChild(meta);
  const cols = el('div', 'cols');
  const left = el('div', '');
  left.appendChild(el('h4', 'sec', 'Ingredients'));
  const ing = el('ul', 'ing'); (r.ingredients || []).forEach(i => ing.appendChild(el('li', '', cv(i)))); left.appendChild(ing);
  if (r.utensils && r.utensils.length) { left.appendChild(el('h4', 'sec', 'Utensils')); const u = el('ul', 'util'); r.utensils.forEach(x => u.appendChild(el('li', '', x))); left.appendChild(u); }
  if (r.nutrition) left.appendChild(renderNutrition(r.nutrition));
  cols.appendChild(left);
  const right = el('div', '');
  right.appendChild(el('h4', 'sec', 'Steps'));
  const steps = el('ol', 'steps'); (r.steps || []).forEach(s => steps.appendChild(el('li', '', cv(s)))); right.appendChild(steps);
  if (r.tip) right.appendChild(el('div', 'tip', '💡 ' + cv(r.tip)));
  cols.appendChild(right);
  card.appendChild(cols);
  attachAskAbout(card);
  return card;
}
function renderNutrition(n) {
  const wrap = el('div', 'nutri');
  wrap.appendChild(el('h4', 'sec', 'Nutrition · estimated'));
  const macros = el('div', 'macros');
  [['Calories', n.calories, ''], ['Protein', n.protein_g, 'g'], ['Carbs', n.carbs_g, 'g'], ['Fat', n.fat_g, 'g']].forEach(([lab, val, unit]) => {
    const s = el('div', 'stat'); s.appendChild(el('b', '', (val != null ? val : '—') + unit)); s.appendChild(el('span', '', lab)); macros.appendChild(s);
  });
  wrap.appendChild(macros);
  const sec = [n.fiber_g != null ? `Fiber ${n.fiber_g}g` : '', n.sugar_g != null ? `Sugar ${n.sugar_g}g` : '', n.sodium_mg != null ? `Sodium ${n.sodium_mg}mg` : ''].filter(Boolean).join(' · ');
  if (sec) wrap.appendChild(el('div', 'second', sec + '  · per serving'));
  return wrap;
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

/* ---------- Recipe Box (localStorage pins + recent) ---------- */
function getLS(k) { try { return JSON.parse(localStorage.getItem(k) || '[]'); } catch (e) { return []; } }
function setLS(k, v) { localStorage.setItem(k, JSON.stringify(v.slice(0, 30))); }
function pushRecent(q) { const r = getLS('su_recent').filter(x => x !== q); r.unshift(q); setLS('su_recent', r); }
function isPinned(q) { return getLS('su_pins').some(p => p.q === q); }
function togglePin(turn) {
  let pins = getLS('su_pins'); const q = turn.q.content;
  if (pins.some(p => p.q === q)) pins = pins.filter(p => p.q !== q);
  else pins.unshift({ q, title: (turn.a.recipe && turn.a.recipe.title) || q, answer: turn.a.content || '' });
  setLS('su_pins', pins);
}
function renderBox() {
  const pl = $('pins-list'), rl = $('recent-list');
  const pins = getLS('su_pins'), recent = getLS('su_recent');
  pl.innerHTML = pins.length ? '' : '<p class="empty-note">Bookmark an answer or recipe to keep it here.</p>';
  pins.forEach(p => { const b = el('div', 'boxlink'); b.innerHTML = `<div class="t">${escapeHtml(p.title)}</div><div class="m">${escapeHtml((p.answer || '').slice(0, 90))}</div>`; b.onclick = () => ask(p.q); pl.appendChild(b); });
  rl.innerHTML = recent.length ? '' : '<p class="empty-note">Your recent questions will show up here.</p>';
  recent.slice(0, 12).forEach(q => { const b = el('div', 'boxlink'); b.innerHTML = `<div class="t">${escapeHtml(q)}</div>`; b.onclick = () => ask(q); rl.appendChild(b); });
}
function escapeHtml(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

/* ---------- Insights (predict + model card) ---------- */
let insightsLoaded = false;
async function loadInsights() {
  if (insightsLoaded) return; insightsLoaded = true;
  try {
    const d = await (await fetch('/api/insights')).json();
    (d.courses || []).forEach(c => $('pcourse').appendChild(new Option(c)));
    (d.diets || []).forEach(c => $('pdiet').appendChild(new Option(c)));
    $('modelcard').textContent = d.model_card || '';
  } catch (e) {}
  $('predict').onclick = async () => {
    const body = { num_ingredients: +$('pi').value, num_steps: +$('ps').value, cuisine: 'Other', course: $('pcourse').value, diet: $('pdiet').value };
    const d = await (await fetch('/api/predict', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
    const r = $('predict-result');
    if (d.quick_prob != null) { const q = d.quick_prob >= 0.5; r.innerHTML = `<b style="color:var(--accent)">${q ? 'Likely quick (≤45 min)' : 'More involved (>45 min)'}</b> — ${Math.round(d.quick_prob * 100)}% likely quick.`; }
    else r.textContent = d.error || 'Prediction unavailable';
  };
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

/* ---------- input wiring ---------- */
$('send').onclick = () => ask(qInput.value);
qInput.addEventListener('keydown', e => { if (e.key === 'Enter') ask(qInput.value); });
qInput.focus();
