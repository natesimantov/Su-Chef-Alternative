"""Voice in and out for the kitchen.

- listen(): a big tap-to-speak mic (browser speech-to-text via
  streamlit-mic-recorder). Returns the transcript string, or None.
- speak(): reads text aloud using the browser's built-in speechSynthesis,
  preferring a high-quality natural voice and honouring the user's choice.
- voice_settings(): a small picker (voice + speed) for the sidebar.

All best-effort: if the mic component isn't installed or speech isn't supported,
the app stays fully usable via the text search bar.
"""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

# Shared JS: choose the best voice (honouring a saved preference), then speak.
# Priority list favours the natural / neural voices across platforms; falls back
# to any English voice, then the system default.
_VOICE_PICKER_JS = """
function scPickVoice(voices) {
  const saved = localStorage.getItem('su_chef_voice');
  if (saved) {
    const exact = voices.find(v => v.name === saved);
    if (exact) return exact;
  }
  const en = voices.filter(v => /^en/i.test(v.lang));
  const pool = en.length ? en : voices;
  const PRIORITY = [
    'Natural', 'Neural', 'Online', 'Google US English', 'Google UK English Female',
    'Microsoft Aria', 'Microsoft Jenny', 'Microsoft Sonia', 'Microsoft Guy',
    'Samantha', 'Serena', 'Karen', 'Daniel', 'Google'
  ];
  for (const token of PRIORITY) {
    const hit = pool.find(v => v.name.toLowerCase().includes(token.toLowerCase()));
    if (hit) return hit;
  }
  return pool[0] || null;
}
function scRate() {
  const r = parseFloat(localStorage.getItem('su_chef_rate'));
  return (r && r >= 0.5 && r <= 2.0) ? r : 1.0;
}
function scSpeak(text) {
  const synth = window.speechSynthesis;
  if (!synth) return;
  const go = () => {
    const u = new SpeechSynthesisUtterance(text);
    const v = scPickVoice(synth.getVoices());
    if (v) u.voice = v;
    u.rate = scRate();
    synth.cancel();
    synth.speak(u);
  };
  if (synth.getVoices().length) go();
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
    """Read `text` aloud in the browser with the preferred natural voice."""
    if not text:
        return
    components.html(
        f"<script>{_VOICE_PICKER_JS}\nscSpeak({json.dumps(text)});</script>",
        height=0,
    )


def speak_button(text: str, key: str) -> None:
    """A small 🔊 replay control that re-reads `text` on click."""
    if st.button("🔊", key=key, type="secondary", help="Read aloud",
                 use_container_width=True):
        speak(text)


def voice_settings() -> None:
    """A self-contained voice picker (voice + speed + test) for the sidebar.

    Choices are stored in localStorage and read by speak(); the Test button
    previews the current selection regardless."""
    components.html(
        f"""
        <style>
          .sc-vs {{ font-family: 'Work Sans', sans-serif; color: #1b1c1c; }}
          .sc-vs label {{ font-size: 13px; font-weight: 600; color: #55433c; }}
          .sc-vs select, .sc-vs input {{ width: 100%; margin: 4px 0 10px;
            border-radius: 10px; border: 1px solid #dbc1b8; padding: 8px; }}
          .sc-vs button {{ width: 100%; border: none; border-radius: 9999px;
            background: #944521; color: #fff; font-weight: 600; padding: 9px;
            cursor: pointer; }}
        </style>
        <div class="sc-vs">
          <label>Voice</label>
          <select id="sc-voice" onchange="scSaveVoice()"></select>
          <label>Speed: <span id="sc-rate-label"></span></label>
          <input id="sc-rate" type="range" min="0.7" max="1.3" step="0.05"
                 oninput="scSaveRate()">
          <button onclick="scTest()">▶  Test voice</button>
        </div>
        <script>
          {_VOICE_PICKER_JS}
          const sel = document.getElementById('sc-voice');
          const rate = document.getElementById('sc-rate');
          const rlabel = document.getElementById('sc-rate-label');
          rate.value = scRate(); rlabel.textContent = (+rate.value).toFixed(2) + 'x';

          function fillVoices() {{
            const voices = window.speechSynthesis.getVoices()
                .filter(v => /^en/i.test(v.lang));
            const saved = localStorage.getItem('su_chef_voice');
            const best = scPickVoice(window.speechSynthesis.getVoices());
            sel.innerHTML = '';
            voices.forEach(v => {{
              const o = document.createElement('option');
              o.value = v.name;
              o.textContent = v.name.replace('Microsoft ', '').replace('Google ', '')
                              + '  (' + v.lang + ')';
              if (v.name === (saved || (best && best.name))) o.selected = true;
              sel.appendChild(o);
            }});
          }}
          function scSaveVoice() {{ localStorage.setItem('su_chef_voice', sel.value); }}
          function scSaveRate() {{
            localStorage.setItem('su_chef_rate', rate.value);
            rlabel.textContent = (+rate.value).toFixed(2) + 'x';
          }}
          function scTest() {{
            localStorage.setItem('su_chef_voice', sel.value);
            scSpeak("Hi, I'm Su Chef. This is how I'll read your answers.");
          }}
          fillVoices();
          window.speechSynthesis.addEventListener('voiceschanged', fillVoices);
        </script>
        """,
        height=210,
    )
