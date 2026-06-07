"""Su Chef — Streamlit entry point.

Run from the project root:

    streamlit run ui/app.py

A dev-only screen picker lives in the sidebar; the real flow is DEFINE → COOK
(the rest of the journey lands as screens are built).
"""

from __future__ import annotations

import os
import sys

# Allow `from ui...`/`from shared...` imports when launched via `streamlit run`.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st  # noqa: E402

from tools.profile_store import load_profiles  # noqa: E402
from ui import sample_data  # noqa: E402
from ui.screens import cook, debate, define, done, emergency, people, prep  # noqa: E402
from ui.theme import inject_theme  # noqa: E402

# The real journey, in order. Emergency is reached via the button, not the nav.
SCREENS = {
    "define": define.render,
    "debate": debate.render,
    "prep": prep.render,
    "cook": cook.render,
    "done": done.render,
    "people": people.render,
    "emergency": emergency.render,
}
NAV = ["define", "debate", "prep", "cook", "done", "people"]


def main() -> None:
    st.set_page_config(page_title="Su Chef", page_icon="🍳", layout="centered")
    inject_theme()

    # Seed session state
    st.session_state.setdefault("screen", "define")
    st.session_state.setdefault("recipe", sample_data.SAMPLE_RECIPE)
    st.session_state.setdefault("step_index", 0)
    st.session_state.setdefault("profiles", load_profiles() or sample_data.SAMPLE_PROFILES)

    with st.sidebar:
        st.caption("Dev navigation (not part of the real flow)")
        current = st.session_state["screen"]
        choice = st.radio(
            "Screen",
            NAV,
            index=NAV.index(current) if current in NAV else 0,
        )
        # Only honor the dev nav from a NAV screen — on emergency you exit via
        # the screen's own buttons (otherwise the radio's default would kick you
        # out of the red takeover on the next rerun).
        if choice != current and current in NAV:
            st.session_state["screen"] = choice

    render = SCREENS.get(st.session_state["screen"], define.render)
    render()


if __name__ == "__main__":
    main()
