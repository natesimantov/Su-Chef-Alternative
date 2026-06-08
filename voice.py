"""Voice in and out for the kitchen.

- listen(): a big tap-to-speak mic (browser speech-to-text via
  streamlit-mic-recorder). Returns the transcript string, or None.
- speak(): reads text aloud using the browser's built-in speechSynthesis,
  honouring the chosen accent profile and speed.
- voice_settings(): an accent picker (6 profiles) + speed + test for the sidebar.

Accent trick (free): answers are English, but a French/Italian neural voice
reading English produces authentic French/Italian-accented English. "Southern
US" is approximated with a natural US voice until premium voices are added.

All best-effort: if the mic component isn't installed or speech isn't supported,
the app stays fully usable via the text search bar. The richest voices are the
Microsoft "Online (Natural)" set, which appear in Microsoft Edge.
"""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

# Shared JS: resolve the chosen accent profile to an available voice, then speak.
# `voices` come from speechSynthesis.getVoices(); we match by language first,
# then by preferred (natural) voice names, then fall back gracefully.
_VOICE_JS = """
const SC_ACCENTS = {
  james:  {lang:'en',    names:['Natural','Online','Google US','Google UK','Aria','Jenny','Samantha']},
  alan:   {lang:'en-gb', names:['Ryan','George','Thomas','Natural','Online','Google UK English Male']},
  emma:   {lang:'en-gb', names:['Sonia','Libby','Hazel','Natural','Online','Google UK English Female']},
  thomas: {lang:'en-us', names:['Guy','Davis','Andrew','Tony','Eric','Natural','Online']},
  mia:    {lang:'en-us', names:['Aria','Jenny','Michelle','Ana','Samantha','Natural','Online']},
  liam:   {lang:'en-ie', names:['Connor','Natural','Online']},
  erin:   {lang:'en-ie', names:['Emily','Natural','Online']},
  jack:   {lang:'en-au', names:['William','Ken','Natural','Online']},
  chloe:  {lang:'en-au', names:['Natasha','Freya','Natural','Online']},
  arjun:  {lang:'en-in', names:['Prabhat','Natural','Online']},
  priya:  {lang:'en-in', names:['Neerja','Natural','Online']}
};
const SC_PERSONAS = [
  {id:'james',  name:'James',  accent:'Default'},
  {id:'alan',   name:'Alan',   accent:'British'},
  {id:'emma',   name:'Emma',   accent:'British'},
  {id:'thomas', name:'Thomas', accent:'American'},
  {id:'mia',    name:'Mia',    accent:'American'},
  {id:'liam',   name:'Liam',   accent:'Irish'},
  {id:'erin',   name:'Erin',   accent:'Irish'},
  {id:'jack',   name:'Jack',   accent:'Australian'},
  {id:'chloe',  name:'Chloe',  accent:'Australian'},
  {id:'arjun',  name:'Arjun',  accent:'Indian'},
  {id:'priya',  name:'Priya',  accent:'Indian'}
];
function scNorm(l){ return (l||'').toLowerCase().replace('_','-'); }
function scProfile(){ return SC_ACCENTS[localStorage.getItem('su_chef_accent') || 'james'] || SC_ACCENTS.james; }
function scAvailable(id){
  const prof = SC_ACCENTS[id]; if(!prof) return false;
  if(prof.lang === 'en') return true;  // James / default always works
  return window.speechSynthesis.getVoices().some(v => scNorm(v.lang).startsWith(prof.lang));
}
function scResolve(voices){
  const prof = scProfile();
  let pool = voices.filter(v => scNorm(v.lang).startsWith(prof.lang));
  const exact = pool.length > 0;
  if(!pool.length) pool = voices.filter(v => /^en/i.test(v.lang));
  if(!pool.length) pool = voices;
  let pick = null;
  for(const t of prof.names){
    const hit = pool.find(v => v.name.toLowerCase().includes(t.toLowerCase()));
    if(hit){ pick = hit; break; }
  }
  if(!pick) pick = pool.find(v => /natural|online|google/i.test(v.name)) || pool[0] || null;
  return { voice: pick, exact: exact };
}
function scRate(){
  const r = parseFloat(localStorage.getItem('su_chef_rate'));
  return (r && r >= 0.5 && r <= 2.0) ? r : 1.0;
}
function scSpeak(text){
  const synth = window.speechSynthesis;
  if(!synth) return;
  const go = () => {
    const u = new SpeechSynthesisUtterance(text);
    const r = scResolve(synth.getVoices());
    if(r.voice) u.voice = r.voice;
    u.rate = scRate();
    synth.cancel();
    synth.speak(u);
  };
  if(synth.getVoices().length) go();
  else synth.addEventListener('voiceschanged', go, { once: true });
}
"""


import os

# Native mic component (webkitSpeechRecognition + waveform). Returns the latest
# {"text": str, "t": ms} when an utterance finishes; persists across reruns, so
# callers dedupe on "t".
_mic_component = components.declare_component(
    "su_chef_mic", path=os.path.join(os.path.dirname(__file__), "components", "mic")
)


def mic(key: str = "mic") -> dict | None:
    """Render the tap-to-speak mic (live waveform + words). Returns the last
    recognized {text, t} or None."""
    import theme
    p = theme.active_palette()
    return _mic_component(
        default=None, key=key,
        primary=p["primary"], on_primary=p["on_primary"],
        wave=p["primary"], text=p["text_variant"],
    )


@st.cache_resource(show_spinner=False)
def _whisper_model():
    """Load the on-server speech-to-text model once (cached for the app's life).
    Small CPU model so it runs on free hosting; override size via SU_CHEF_WHISPER_MODEL."""
    from faster_whisper import WhisperModel
    name = os.environ.get("SU_CHEF_WHISPER_MODEL", "base.en")
    return WhisperModel(name, device="cpu", compute_type="int8")


def transcribe(audio_bytes: bytes) -> str:
    """Turn recorded audio (WAV bytes from st.audio_input) into text, on-server.

    Works in every browser and on phones because it only needs audio *recording*,
    not the browser's own dictation. Returns "" on empty audio or any failure."""
    if not audio_bytes:
        return ""
    try:
        import io
        segments, _ = _whisper_model().transcribe(
            io.BytesIO(audio_bytes), language="en", beam_size=1)
        return " ".join(s.text for s in segments).strip()
    except Exception:
        return ""


def speak(text: str) -> None:
    """Read `text` aloud with the chosen accent voice."""
    if not text:
        return
    components.html(
        "<script>" + _VOICE_JS + "scSpeak(" + json.dumps(text) + ");</script>",
        height=0,
    )


def speak_button(text: str, key: str) -> None:
    """A small 🔊 replay control that re-reads `text` on click."""
    if st.button("🔊", key=key, type="secondary", help="Read aloud",
                 use_container_width=True):
        speak(text)


# Self-contained accent picker. Uses a placeholder so the shared JS is injected
# without f-string brace gymnastics.
_SETTINGS_HTML = """
<style>
  body { background: __PANELBG__; }
  .sc-vs { font-family:'Work Sans',sans-serif; color:__TEXT__; }
  .sc-vs label { font-size:13px; font-weight:600; color:__TV__; }
  .sc-vs select, .sc-vs input { width:100%; margin:4px 0 10px; border-radius:10px;
    border:1px solid __OUTLINE__; padding:8px; background:__INBG__; color:__TEXT__; }
  .sc-vs button { width:100%; border:none; border-radius:9999px; background:__PRIMARY__;
    color:__ONP__; font-weight:600; padding:9px; cursor:pointer; }
  .sc-note { font-size:11px; color:__TV__; margin:8px 0 0; line-height:1.4; }
  .sc-using { font-size:12px; color:__SECONDARY__; font-weight:600; margin:2px 0 10px; }
</style>
<div class="sc-vs">
  <label>Voice</label>
  <select id="sc-accent" onchange="scSave()"></select>
  <div class="sc-using" id="sc-using"></div>
  <label>Speed: <span id="sc-rate-label"></span></label>
  <input id="sc-rate" type="range" min="0.7" max="1.3" step="0.05" oninput="scSaveRate()">
  <button onclick="scTest()">▶  Test voice</button>
  <p class="sc-note">Grayed-out accents aren't available in this browser — open the
  app in <b>Microsoft Edge</b> (online) to use them. Premium voices (French,
  Italian, Southern US) coming soon.</p>
</div>
<script>
/*VOICE_JS*/
const acc = document.getElementById('sc-accent');
const rate = document.getElementById('sc-rate');
const rlabel = document.getElementById('sc-rate-label');
const using = document.getElementById('sc-using');
rate.value = scRate(); rlabel.textContent = (+rate.value).toFixed(2) + 'x';

function fillAccents(){
  const saved = localStorage.getItem('su_chef_accent') || 'james';
  acc.innerHTML = '';
  // Available voices first; the "needs Edge" ones after (James stays first).
  const avail = [], edge = [];
  SC_PERSONAS.forEach(p => { (scAvailable(p.id) ? avail : edge).push(p); });
  avail.concat(edge).forEach(p => {
    const ok = scAvailable(p.id);
    const o = document.createElement('option');
    o.value = p.id;
    o.textContent = p.name + ' · ' + p.accent + (ok ? '' : '  · needs Edge');
    if(!ok){ o.disabled = true; o.title = 'Open app in Edge browser'; }
    if(p.id === saved) o.selected = true;
    acc.appendChild(o);
  });
  const grp = document.createElement('optgroup');
  grp.label = 'Premium — coming soon';
  ['Gabrielle · French','Hugo · French','Lucia · Italian','Marco · Italian',
   'Belle · Southern US','Wyatt · Southern US'].forEach(n => {
    const o = document.createElement('option'); o.textContent = n; o.disabled = true;
    grp.appendChild(o);
  });
  acc.appendChild(grp);
  showUsing();
}
function showUsing(){
  const r = scResolve(window.speechSynthesis.getVoices());
  if(!r.voice){ using.textContent = 'No voice available — using browser default.'; using.style.color='#7a6a63'; return; }
  const nm = r.voice.name.replace('Microsoft ','').replace('Google ','').replace(' Online (Natural)','');
  if(r.exact){ using.textContent = 'Using: ' + nm; using.style.color='#56642b'; }
  else { using.textContent = '⚠ This accent isn\\'t available here — using ' + nm + '. Open in Edge.'; using.style.color='#ba1a1a'; }
}
function scSave(){ localStorage.setItem('su_chef_accent', acc.value); showUsing(); }
function scSaveRate(){
  localStorage.setItem('su_chef_rate', rate.value);
  rlabel.textContent = (+rate.value).toFixed(2) + 'x';
}
function scTest(){
  localStorage.setItem('su_chef_accent', acc.value);
  scSpeak("Hi, I'm Su Chef. This is how I'll read your answers. Let's get cooking!");
}
fillAccents();
window.speechSynthesis.addEventListener('voiceschanged', fillAccents);
</script>
"""


def voice_settings() -> None:
    """An accent voice picker (personas), speed, and a test button — themed."""
    import theme
    p = theme.active_palette()
    html = (_SETTINGS_HTML
            .replace("/*VOICE_JS*/", _VOICE_JS)
            .replace("__PANELBG__", p["card"])
            .replace("__INBG__", p["surface"])
            .replace("__PRIMARY__", p["primary"])
            .replace("__ONP__", p["on_primary"])
            .replace("__TEXT__", p["text"])
            .replace("__TV__", p["text_variant"])
            .replace("__OUTLINE__", p["outline"])
            .replace("__SECONDARY__", p["secondary"]))
    components.html(html, height=320)
