"""DONE screen — finish & close.

Port of the Stitch `cooking_complete` mockup: "Nicely done!", the dish, a path
to the next dish, and a note that the session was saved. Writes a SessionLog to
data/sessions/ (the lightweight memory layer the Head Chef reads next time).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from shared.models import SessionLog
from ui import sample_data

_SESSIONS_DIR = Path(__file__).resolve().parents[2] / "data" / "sessions"


def _save_session(log: SessionLog) -> Path:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = _SESSIONS_DIR / f"{stamp}.json"
    path.write_text(json.dumps(log.model_dump(by_alias=True), indent=2),
                    encoding="utf-8")
    return path


def render() -> None:
    recipe = st.session_state.get("recipe", sample_data.SAMPLE_RECIPE)

    # Write the session log once per finish.
    if not st.session_state.get("session_saved"):
        log = SessionLog(
            dish=recipe.title,
            questions_asked=st.session_state.get("questions_asked", []),
            rescues=st.session_state.get("rescues", []),
            adaptations=[f.message for f in recipe.dietary_flags
                         if f.kind in ("substitution", "allergen")],
        )
        _save_session(log)
        st.session_state["session_saved"] = True

    st.markdown(
        "<h1 style='text-align:center;font-size:56px;margin-top:24px'>"
        "Nicely done!</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='text-align:center;font-size:24px;color:#55433c'>{recipe.title}</p>",
        unsafe_allow_html=True)

    # Dish "photo" placeholder (no image asset in the MVP).
    st.markdown(
        "<div style='display:flex;justify-content:center;margin:18px 0'>"
        "<div style='width:260px;height:200px;border-radius:24px;background:#ecc7b4;"
        "display:flex;align-items:center;justify-content:center;font-size:80px'>🍽️"
        "</div></div>", unsafe_allow_html=True)

    mid = st.columns([1, 2, 1])[1]
    with mid:
        if st.button("🍴 Start another dish", key="again", type="primary",
                     use_container_width=True):
            for k in ("recipe", "step_index", "constraints", "debate_message",
                      "questions_asked", "rescues", "session_saved", "intent_text"):
                st.session_state.pop(k, None)
            st.session_state["screen"] = "define"
            st.rerun()
        st.markdown(
            "<p style='text-align:center;color:#55433c;margin-top:10px'>"
            "📝 Saved what was tricky for next time.</p>", unsafe_allow_html=True)
