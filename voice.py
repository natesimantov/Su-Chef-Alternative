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
  auto: {lang:'en',    names:['Natural','Online','Google US','Google UK','Aria','Jenny','Samantha']},
  fr_f: {lang:'fr',    names:['Denise','Amelie','Audrey','Virginie','Natural','Online','Google']},
  fr_m: {lang:'fr',    names:['Henri','Paul','Claude','Natural','Online','Google']},
  it_f: {lang:'it',    names:['Elsa','Alice','Isabella','Natural','Online','Google']},
  it_m: {lang:'it',    names:['Diego','Cosimo','Giuseppe','Natural','Online','Google']},
  us_f: {lang:'en-us', names:['Aria','Jenny','Michelle','Ana','Samantha','Natural','Online']},
  us_m: {lang:'en-us', names:['Guy','Davis','Tony','Mark','Natural','Online']}
};
function scProfile(){ return SC_ACCENTS[localStorage.getItem('su_chef_accent') || 'auto'] || SC_ACCENTS.auto; }
function scNorm(l){ return (l||'').toLowerCase().replace('_','-'); }
function scResolve(voices){
  const prof = scProfile();
  let pool = voices.filter(v => scNorm(v.lang).startsWith(prof.lang));
  if(!pool.length) pool = voices.filter(v => /^en/i.test(v.lang));
  if(!pool.length) pool = voices;
  for(const t of prof.names){
    const hit = pool.find(v => v.name.toLowerCase().includes(t.toLowerCase()));
    if(hit) return hit;
  }
  return pool.find(v => /natural|online|google/i.test(v.name)) || pool[0] || null;
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
    const v = scResolve(synth.getVoices());
    if(v) u.voice = v;
    u.rate = scRate();
    synth.cancel();
    synth.speak(u);
  };
  if(synth.getVoices().length) go();
  else synth.addEventListener('voiceschanged', go, { once: true });
}
"""


def listen(key: str = "mic") -> str | None:
    """Render the tap-to-speak mic; return a transcript when one arrives."""
    try:
        from streamlit_mic_recorder import speech_to_text
    except Exception:
        st.caption("🎙️ Voice input needs `streamlit-mic-recorder` — type below for now.")
        return None

    return speech_to_text(
        language="en",
        start_prompt="🎙️  Tap to speak",
        stop_prompt="⏹️  Stop",
        just_once=True,
        use_container_width=True,
        key=key,
    )


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
  .sc-vs { font-family:'Work Sans',sans-serif; color:#1b1c1c; }
  .sc-vs label { font-size:13px; font-weight:600; color:#55433c; }
  .sc-vs select, .sc-vs input { width:100%; margin:4px 0 10px; border-radius:10px;
    border:1px solid #dbc1b8; padding:8px; background:#fff; }
  .sc-vs button { width:100%; border:none; border-radius:9999px; background:#944521;
    color:#fff; font-weight:600; padding:9px; cursor:pointer; }
  .sc-note { font-size:11px; color:#7a6a63; margin:8px 0 0; line-height:1.4; }
  .sc-using { font-size:12px; color:#56642b; font-weight:600; margin:2px 0 10px; }
</style>
<div class="sc-vs">
  <label>Accent</label>
  <select id="sc-accent" onchange="scSave()">
    <option value="auto">Auto — most natural</option>
    <option value="fr_f">French accent — female</option>
    <option value="fr_m">French accent — male</option>
    <option value="it_f">Italian accent — female</option>
    <option value="it_m">Italian accent — male</option>
    <option value="us_f">Southern US* — female</option>
    <option value="us_m">Southern US* — male</option>
  </select>
  <div class="sc-using" id="sc-using"></div>
  <label>Speed: <span id="sc-rate-label"></span></label>
  <input id="sc-rate" type="range" min="0.7" max="1.3" step="0.05" oninput="scSaveRate()">
  <button onclick="scTest()">▶  Test voice</button>
  <p class="sc-note">*Southern US uses a natural US voice for now — a true Southern
  drawl comes with premium voices later.<br>Tip: open in <b>Microsoft Edge</b> for
  the most natural French/Italian voices.</p>
</div>
<script>
/*VOICE_JS*/
const acc = document.getElementById('sc-accent');
const rate = document.getElementById('sc-rate');
const rlabel = document.getElementById('sc-rate-label');
const using = document.getElementById('sc-using');
acc.value = localStorage.getItem('su_chef_accent') || 'auto';
rate.value = scRate(); rlabel.textContent = (+rate.value).toFixed(2) + 'x';

function showUsing(){
  const v = scResolve(window.speechSynthesis.getVoices());
  using.textContent = v ? ('Using: ' + v.name.replace('Microsoft ','').replace('Google ',''))
                        : 'No matching voice installed — using default.';
}
function scSave(){ localStorage.setItem('su_chef_accent', acc.value); showUsing(); }
function scSaveRate(){
  localStorage.setItem('su_chef_rate', rate.value);
  rlabel.textContent = (+rate.value).toFixed(2) + 'x';
}
function scTest(){
  localStorage.setItem('su_chef_accent', acc.value);
  scSpeak("Ciao! This is how I'll read your answers. Let's get cooking.");
}
showUsing();
window.speechSynthesis.addEventListener('voiceschanged', showUsing);
</script>
"""


def voice_settings() -> None:
    """An accent voice picker (6 profiles + auto), speed, and a test button."""
    components.html(_SETTINGS_HTML.replace("/*VOICE_JS*/", _VOICE_JS), height=320)
