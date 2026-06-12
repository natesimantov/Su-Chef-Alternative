/* Su Chef — Flask frontend logic (vanilla JS). */

const state = {
  messages: [],          // [{role, content, ...extras}]
  units: localStorage.getItem('units') || 'metric',
  theme: localStorage.getItem('theme') || 'hearth',
  audioOn: localStorage.getItem('audioOn') !== 'off',
  busy: false,
};

const $ = (id) => document.getElementById(id);
const thread = $('thread'), empty = $('empty'), qInput = $('q');

/* ---------- top-bar controls (#7) ---------- */
function applyTheme(t) { document.documentElement.setAttribute('data-theme', t); state.theme = t; localStorage.setItem('theme', t); }
applyTheme(state.theme); $('theme').value = state.theme;
$('theme').onchange = (e) => applyTheme(e.target.value);

function setUnits(u) {
  state.units = u; localStorage.setItem('units', u);
  document.querySelectorAll('#units button').forEach(b => b.classList.toggle('active', b.dataset.u === u));
}
setUnits(state.units);
document.querySelectorAll('#units button').forEach(b => b.onclick = () => setUnits(b.dataset.u));

function setAudio(on) {
  state.audioOn = on; localStorage.setItem('audioOn', on ? 'on' : 'off');
  const t = $('audioToggle'); t.classList.toggle('on', on);
  t.querySelector('.material-symbols-outlined').textContent = on ? 'volume_up' : 'volume_off';
  if (!on) window.speechSynthesis.cancel();
}
setAudio(state.audioOn);
$('audioToggle').onclick = () => setAudio(!state.audioOn);

$('newBtn').onclick = $('home').onclick = newChat;
function newChat() { state.messages = []; render(); window.speechSynthesis.cancel(); qInput.value = ''; qInput.focus(); }
$('insightsBtn').onclick = () => { window.location.href = '/insights'; };

/* voice persona list (browser-aware, like the Streamlit app) */
function fillVoices() {
  const sel = $('voice'); const voices = window.speechSynthesis.getVoices();
  const want = [['James — default', 'en'], ['British', 'en-gb'], ['American', 'en-us'],
                ['Irish', 'en-ie'], ['Australian', 'en-au'], ['Indian', 'en-in']];
  sel.innerHTML = '';
  want.forEach(([label, lang]) => {
    const ok = lang === 'en' || voices.some(v => v.lang.toLowerCase().startsWith(lang));
    const o = document.createElement('option'); o.value = lang; o.textContent = label + (ok ? '' : ' · needs Edge');
    o.disabled = !ok; sel.appendChild(o);
  });
}
fillVoices(); window.speechSynthesis.onvoiceschanged = fillVoices;

function speak(text) {
  if (!state.audioOn || !text) return;
  const u = new SpeechSynthesisUtterance(text);
  const lang = $('voice').value, voices = window.speechSynthesis.getVoices();
  const v = voices.find(v => v.lang.toLowerCase().startsWith(lang)) || voices.find(v => /^en/i.test(v.lang));
  if (v) u.voice = v;
  window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
}

/* ---------- ask flow ---------- */
async function ask(text) {
  text = (text || '').trim();
  if (!text || state.busy) return;
  state.busy = true; qInput.value = '';
  state.messages.push({ role: 'user', content: text });
  state.messages.push({ role: 'assistant', content: '', pending: true });
  render();
  try {
    const res = await fetch('/api/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: state.messages.filter(m => !m.pending).map(m => ({ role: m.role, content: m.content })), units: state.units })
    });
    const data = await res.json();
    const a = state.messages[state.messages.length - 1];
    a.pending = false; a.content = data.answer || data.error || '(no answer)';
    a.context = data.context || ''; a.follow_ups = (data.follow_ups || []).slice(0, 3);
    a.recipe_suggestion = data.recipe_suggestion || '';
    render();
    speak(a.content);
  } catch (e) {
    const a = state.messages[state.messages.length - 1];
    a.pending = false; a.content = 'Connection hiccup — try again.'; render();
  }
  state.busy = false;
}

/* ---------- render (newest-first #1) ---------- */
function render() {
  empty.classList.toggle('hidden', state.messages.length > 0);
  // pair user+assistant into turns
  const turns = [];
  for (let i = 0; i < state.messages.length; i += 2)
    turns.push({ q: state.messages[i], a: state.messages[i + 1] });
  thread.innerHTML = '';
  turns.reverse().forEach((turn, idxFromTop) => {
    const isLatest = idxFromTop === 0;
    const div = document.createElement('div'); div.className = 'turn';
    div.appendChild(el('p', 'q', `🎙️ “${turn.q.content}”`));
    const a = turn.a || {};
    if (a.context) div.appendChild(el('p', 'ctx', a.context));
    const rowEl = document.createElement('div'); rowEl.className = 'row';
    const ans = document.createElement('div'); ans.className = a.pending ? 'answer thinking' : 'answer';
    ans.textContent = a.pending ? 'Su Chef is thinking…' : (a.content || '');
    rowEl.appendChild(ans);
    if (!a.pending) {
      const tools = document.createElement('div'); tools.className = 'answer-tools';
      const say = tbtn('volume_up', () => speak(a.content));
      const pin = tbtn('push_pin', (b) => { b.classList.toggle('on'); });
      tools.append(say, pin); rowEl.appendChild(tools);
    }
    div.appendChild(rowEl);
    // chips + inline follow-up only under the latest turn
    if (isLatest && !a.pending) {
      const chips = document.createElement('div'); chips.className = 'chips';
      (a.follow_ups || []).slice(0, a.recipe_suggestion ? 2 : 3).forEach(f =>
        chips.appendChild(chip(f, false)));
      if (a.recipe_suggestion) chips.appendChild(chip(a.recipe_suggestion, true));
      if (chips.children.length) div.appendChild(chips);
    }
    thread.appendChild(div);
  });
}

function el(tag, cls, text) { const e = document.createElement(tag); e.className = cls; if (text != null) e.textContent = text; return e; }
function tbtn(icon, fn) {
  const b = document.createElement('button'); b.className = 'tbtn';
  b.innerHTML = `<span class="material-symbols-outlined">${icon}</span>`;
  b.onclick = () => fn(b); return b;
}
function chip(text, isRecipe) {
  const b = document.createElement('button'); b.className = 'chip' + (isRecipe ? ' recipe' : '');
  b.textContent = (isRecipe ? '🍳 ' : '') + text; b.onclick = () => ask(text); return b;
}

/* ---------- input wiring (#6: the always-visible composer is the follow-up field) ---------- */
$('send').onclick = () => ask(qInput.value);
qInput.addEventListener('keydown', e => { if (e.key === 'Enter') ask(qInput.value); });
qInput.focus();
