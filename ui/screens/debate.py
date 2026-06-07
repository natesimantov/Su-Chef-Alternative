"""DEBATE / ADAPT screen — negotiate the recipe before cooking.

Port of the Stitch `adapt_recipe` mockup: recipe header, an assistant message,
the ingredient list (with swaps shown as old → new), dietary flags, and a field
to keep adjusting ("less sugar", "no onions"). Loops until the cook is happy.
"""

from __future__ import annotations

import streamlit as st

from agents import define_recipe
from shared.models import Profile
from ui import sample_data
from ui.components import flag_chips, recipe_meta, topbar


def _active_profile() -> Profile | None:
    name = st.session_state.get("cooking_for")
    for p in st.session_state.get("profiles", sample_data.SAMPLE_PROFILES):
        if p.name == name:
            return p
    return None


def render() -> None:
    recipe = st.session_state.get("recipe", sample_data.SAMPLE_RECIPE)

    topbar()
    st.markdown(f"<div class='sc-card'><h1 style='font-size:34px;margin:0'>"
                f"{recipe.title}</h1></div>", unsafe_allow_html=True)
    recipe_meta(recipe)

    message = st.session_state.get(
        "debate_message",
        "Here's what I came up with. Tell me what to change, or prep when ready.",
    )
    st.markdown(f"<div class='sc-card' style='margin-top:8px'>🗣️ “{message}”</div>",
                unsafe_allow_html=True)

    st.markdown("<p class='sc-eyebrow' style='margin-top:16px'>Ingredients</p>",
                unsafe_allow_html=True)
    for ing in recipe.ingredients:
        if ing.substitute_for:
            st.markdown(
                f"<div style='padding:6px 0'>"
                f"<span class='sc-diff-old'>{ing.substitute_for}</span> &nbsp;→&nbsp; "
                f"<span class='sc-diff-new'>{ing.amount} {ing.item}</span></div>",
                unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='padding:6px 0'>{ing.amount} — {ing.item}</div>",
                        unsafe_allow_html=True)

    flag_chips(recipe.dietary_flags)

    # Keep negotiating: each request re-runs the crew with the added constraint.
    change = st.chat_input("Change something… (e.g. 'no onions', 'make it for six')")
    if change:
        constraints = st.session_state.setdefault("constraints", [])
        constraints.append(change)
        base_intent = st.session_state.get("intent_text", recipe.title)
        new_intent = f"{base_intent}; " + "; ".join(constraints)
        st.session_state["recipe"] = define_recipe(new_intent, profile=_active_profile())
        st.session_state["debate_message"] = f"Done — I applied: “{change}”. " \
            "Take a look at the updated recipe."
        st.rerun()

    if st.button("Looks good — let's prep →", key="to_prep", type="primary",
                 use_container_width=True):
        st.session_state["screen"] = "prep"
        st.rerun()
