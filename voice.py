"""Voice in and out for the kitchen.

- listen(): a big tap-to-speak mic (browser speech-to-text via
  streamlit-mic-recorder). Returns the transcript string, or None.
- speak(): reads text aloud using the browser's built-in speechSynthesis.

Both are best-effort: if the mic component isn't installed or speech isn't
supported, the app stays fully usable via the text search bar.
"""

from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components


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
    """Read `text` aloud in the browser (cancels any prior utterance)."""
    if not text:
        return
    payload = json.dumps(text)
    components.html(
        f"""
        <script>
          const say = () => {{
            try {{
              window.speechSynthesis.cancel();
              const u = new SpeechSynthesisUtterance({payload});
              u.rate = 1.0; u.pitch = 1.0;
              window.speechSynthesis.speak(u);
            }} catch (e) {{}}
          }};
          say();
        </script>
        """,
        height=0,
    )


def speak_button(text: str, key: str) -> None:
    """A small 🔊 replay control that re-reads `text` on click."""
    if st.button("🔊", key=key, type="secondary", help="Read aloud",
                 use_container_width=True):
        speak(text)
