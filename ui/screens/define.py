"""DEFINE screen — "What are we cooking?"

First-pass port of the Stitch `define_dish` mockup: wordmark + "Cooking for"
selector, the big terracotta mic, a type-it fallback, and suggestion chips.

Voice is voice-first / tap-always: the mic is a button, but real speech-to-text
in the browser is a "half works" item, so the text field is the live path here.
"""

from __future__ import annotations

import streamlit as st

from agents import define_recipe
from shared.models import Profile
from ui import sample_data

_SUGGESTIONS = [
    "🍽️  Mushroom risotto for two",
    "🌿  Use up zucchini & eggs",
    "🍕  Neapolitan pizza for friends",
]


def render() -> None:
    profiles = st.session_state.get("profiles", sample_data.SAMPLE_PROFILES)

    # Top bar: wordmark + "Cooking for" selector
    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="sc-wordmark">Su Chef</div>', unsafe_allow_html=True)
    with right:
        st.selectbox(
            "Cooking for",
            options=[p.name for p in profiles],
            key="cooking_for",
            label_visibility="collapsed",
        )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h1 style='text-align:center;font-size:56px;margin-bottom:24px'>"
        "What are we cooking?</h1>",
        unsafe_allow_html=True,
    )

    # The big mic with a pulsing "listening" aura (decorative; tap-to-speak below)
    st.markdown(
        """
        <div style="display:flex;justify-content:center;margin:8px 0 4px;">
          <div class="sc-mic"><span style="font-size:64px;">🎙️</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mic_col = st.columns([1, 2, 1])[1]
    with mic_col:
        if st.button("Tap to speak", key="mic", use_container_width=True):
            st.toast("Voice capture is a Phase-2 item — type your dish below for now.")

    st.markdown(
        "<p class='sc-eyebrow' style='text-align:center;margin-top:18px'>or type it…</p>",
        unsafe_allow_html=True,
    )

    intent = st.text_input(
        "Dish",
        key="intent",
        placeholder="e.g. A quick pasta dish",
        label_visibility="collapsed",
    )
    if intent:
        _start_definition(intent)

    # Suggestion chips
    c1, c2, c3 = st.columns(3)
    for col, label in zip((c1, c2, c3), _SUGGESTIONS):
        with col:
            if st.button(label, key=f"chip_{label}", use_container_width=True):
                _start_definition(label)


def _active_profile() -> Profile | None:
    name = st.session_state.get("cooking_for")
    for p in st.session_state.get("profiles", sample_data.SAMPLE_PROFILES):
        if p.name == name:
            return p
    return None


def _start_definition(intent: str) -> None:
    """Hand the intent to the 5-agent crew, then move to the debate/adapt screen.

    The crew runs the real CrewAI flow when an ANTHROPIC_API_KEY is set, and a
    deterministic fallback otherwise — either way it returns a locked recipe.
    """
    clean = intent.split("  ")[-1].strip()  # drop any leading emoji from chips
    st.session_state["intent_text"] = clean
    st.session_state["constraints"] = []
    with st.spinner("The crew is shaping your recipe…"):
        st.session_state["recipe"] = define_recipe(clean, profile=_active_profile())
    st.session_state["debate_message"] = (
        "Here's what I came up with. Tell me what to change, or prep when ready."
    )
    st.session_state["step_index"] = 0
    st.session_state["screen"] = "debate"
    st.rerun()
