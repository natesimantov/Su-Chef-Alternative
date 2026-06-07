"""EMERGENCY screen — the always-reachable red rescue takeover.

Port of the Stitch `emergency_rescue` mockup. Entering it:
  1. pauses all running timers and speaks the most urgent action,
  2. asks what happened in one tap (burning / overflowing / wrong ingredient / other),
  3. hands off to a short rescue response with options.

Rescue text is canned here; once the cook-time fast model is wired it answers
live using the current step as context.
"""

from __future__ import annotations

import streamlit as st

from ui import sample_data

# Most-urgent first action + a short rescue, per cause.
_RESCUES = {
    "Burning": ("Turn off the heat now and move the pan off the burner.",
                "Don't scrape the burnt layer into the dish. Transfer everything "
                "that isn't stuck to a clean pan and taste — if it's only slightly "
                "bitter, a splash of acid (lemon/vinegar) can rescue it."),
    "Overflowing": ("Lower the heat and lift the pan off for a moment.",
                    "Skim or ladle off the excess, then return to a gentle simmer. "
                    "A wooden spoon laid across the pot helps stop a rolling boil-over."),
    "Wrong Ingredient": ("Stop adding anything else right now.",
                         "If it's still on top and not stirred in, spoon it out. If "
                         "it's mixed, tell me what went in and I'll suggest how to "
                         "rebalance or adapt the dish."),
    "Other": ("Take the pan off the heat so nothing gets worse while we think.",
              "Tell me what happened and I'll suggest the safest next move."),
}


def _pause_all_timers() -> None:
    for key in list(st.session_state.keys()):
        if str(key).startswith("timer_running_"):
            st.session_state[key] = False


def render() -> None:
    # Red takeover styling, scoped to this render.
    st.markdown(
        """
        <style>
        .stApp { background: #ba1a1a !important; }
        .stApp, .stApp h1, .stApp p, .stApp label { color: #ffffff !important; }
        [class*="st-key-cause_"] button {
          background:#ffffff !important;
          min-height:120px !important; border-radius:24px !important;
        }
        /* Beat the .stApp p white rule so the label shows on the white card */
        [class*="st-key-cause_"] button p,
        [class*="st-key-cause_"] button div {
          color:#ba1a1a !important; font-size:22px !important; font-weight:700 !important;
        }
        /* Keep the bottom action buttons legible too (red on parchment) */
        .stApp .stButton button p, .stApp .stButton button div {
          color:#ba1a1a !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.get("timers_paused"):
        _pause_all_timers()
        st.session_state["timers_paused"] = True

    st.markdown("<div class='sc-wordmark' style='color:#fff'>Su Chef</div>",
                unsafe_allow_html=True)

    cause = st.session_state.get("emergency_cause")

    if cause is None:
        st.markdown(
            "<h1 style='text-align:center;font-size:64px;margin:40px 0'>"
            "What happened?</h1>", unsafe_allow_html=True)
        r1 = st.columns(2)
        r2 = st.columns(2)
        cells = [r1[0], r1[1], r2[0], r2[1]]
        for cell, (label, icon) in zip(cells, [
            ("Burning", "🔥"), ("Overflowing", "🌊"),
            ("Wrong Ingredient", "⚗️"), ("Other", "❗"),
        ]):
            with cell:
                if st.button(f"{icon}\n\n{label}", key=f"cause_{label}",
                             use_container_width=True):
                    st.session_state["emergency_cause"] = label
                    st.rerun()
    else:
        urgent, advice = _RESCUES[cause]
        st.markdown(f"<h1 style='font-size:40px;margin-top:24px'>🔊 {urgent}</h1>",
                    unsafe_allow_html=True)
        st.markdown(
            f"<div style='background:#fff;color:#1b1c1c;border-radius:24px;"
            f"padding:24px;font-size:20px;margin-top:12px'>{advice}</div>",
            unsafe_allow_html=True)

        entry = f"{cause}: {urgent}"
        rescues = st.session_state.setdefault("rescues", [])
        if entry not in rescues:  # log each rescue once, not per rerun
            rescues.append(entry)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("← Back to cooking", key="resume", use_container_width=True):
                _exit_emergency()
        with c2:
            if st.button("Adapt the dish", key="adapt_em", use_container_width=True):
                _exit_emergency(to="debate")
        with c3:
            if st.button("Start over", key="restart_em", use_container_width=True):
                _exit_emergency(to="define")


def _exit_emergency(to: str = "cook") -> None:
    for k in ("emergency_cause", "timers_paused"):
        st.session_state.pop(k, None)
    st.session_state["screen"] = to
    st.rerun()
