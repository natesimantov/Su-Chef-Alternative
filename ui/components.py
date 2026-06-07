"""Small reusable UI pieces shared across screens."""

from __future__ import annotations

import streamlit as st

from shared.models import DietaryFlag, Recipe


def topbar(*, emergency: bool = True) -> None:
    """Su Chef wordmark on the left; always-visible emergency button on the right.
    Sets st.session_state['screen'] = 'emergency' when tapped."""
    left, right = st.columns([5, 1])
    with left:
        st.markdown('<div class="sc-wordmark">Su Chef</div>', unsafe_allow_html=True)
    with right:
        if emergency and st.button("◈", key="emergency", help="Emergency / STOP",
                                   use_container_width=True):
            st.session_state["screen"] = "emergency"
            st.rerun()


def recipe_meta(recipe: Recipe) -> None:
    """The servings · time · difficulty row under a recipe title."""
    st.markdown(
        f"<p class='sc-meta'>👥 {recipe.servings} servings &nbsp;·&nbsp; "
        f"⏱ {recipe.total_time_min} mins &nbsp;·&nbsp; "
        f"🔥 {recipe.difficulty.value}</p>",
        unsafe_allow_html=True,
    )


def flag_chips(flags: list[DietaryFlag]) -> None:
    """Render dietary flags as colored chips."""
    if not flags:
        return
    html = "".join(
        f"<span class='sc-flag sc-flag-{f.kind}'>{f.message}</span>" for f in flags
    )
    st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)
