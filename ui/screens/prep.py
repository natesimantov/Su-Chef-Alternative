"""PREP screen — prep & readiness check.

Port of the Stitch `prep_checklist` mockup: ingredients checklist + equipment +
the "Before you start" warnings, then Start cooking into cook mode.
"""

from __future__ import annotations

import streamlit as st

from ui import sample_data
from ui.components import flag_chips, topbar


def render() -> None:
    recipe = st.session_state.get("recipe", sample_data.SAMPLE_RECIPE)

    topbar()
    st.markdown(f"<h1 style='font-size:40px'>{recipe.title}</h1>",
                unsafe_allow_html=True)
    st.markdown("<p class='sc-eyebrow'>Prep & Readiness</p>", unsafe_allow_html=True)
    flag_chips(recipe.dietary_flags)

    left, right = st.columns(2)
    with left:
        st.markdown("### 🥕 Ingredients")
        for i, ing in enumerate(recipe.ingredients):
            label = f"{ing.amount} — {ing.item}"
            if ing.substitute_for:
                label += f"  _(swapped from {ing.substitute_for})_"
            st.checkbox(label, key=f"ing_{i}")
    with right:
        st.markdown("### 🍳 Equipment")
        for i, eq in enumerate(recipe.equipment):
            st.checkbox(eq, key=f"eq_{i}")

    if recipe.heads_up:
        st.markdown("### ⚠️ Before you start")
        for warning in recipe.heads_up:
            st.markdown(f"<div class='sc-headsup'>{warning}</div>",
                        unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("Start cooking →", key="start_cooking", type="primary",
                 use_container_width=True):
        st.session_state["step_index"] = 0
        st.session_state["screen"] = "cook"
        st.rerun()
