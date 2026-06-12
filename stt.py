"""Server-side speech-to-text for the Flask app (Streamlit-free).

`voice.py`'s transcription is wrapped in Streamlit's cache decorator, so the Flask
server uses this light module instead: the same faster-whisper model, cached in a
plain module global. Works in any browser because the client only records audio.
"""

from __future__ import annotations

import io
import os

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        name = os.environ.get("SU_CHEF_WHISPER_MODEL", "base.en")
        _model = WhisperModel(name, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_bytes: bytes) -> str:
    """Recorded audio (any browser format) -> text. "" on empty/failure."""
    if not audio_bytes:
        return ""
    try:
        segments, _ = _get_model().transcribe(
            io.BytesIO(audio_bytes), language="en", beam_size=1)
        return " ".join(s.text for s in segments).strip()
    except Exception:
        return ""
