"""COOK screen — the heart of the product.

Port of the Stitch `cook_mode` mockup: one step at a time in large type on a
parchment card with a terracotta left border, the doneness cue beneath it, an
optional step timer, a real "Ask anything" answer, an on-demand reference photo
(honest fallback), and a Back / Repeat / Next bar. Emergency is always top-right.
"""

from __future__ import annotations

import urllib.parse

import streamlit as st

from agents.cook_qa import answer as cook_answer
from ui import sample_data
from ui.components import topbar
from ui.theme import timer_ring


def render() -> None:
    recipe = st.session_state.get("recipe", sample_data.SAMPLE_RECIPE)
    idx = st.session_state.get("step_index", 0)
    idx = max(0, min(idx, len(recipe.steps) - 1))
    step = recipe.steps[idx]
    total = len(recipe.steps)

    topbar()

    st.markdown(f"<p class='sc-eyebrow'>Step {idx + 1} of {total}</p>",
                unsafe_allow_html=True)
    st.progress((idx + 1) / total)

    # A recent answer floats above the step, like the mockup's bottom sheet.
    _render_answer()

    body, timer_col = st.columns([2, 1])
    with body:
        why_html = (f"<div class='sc-why'>ⓘ {step.why}</div>" if step.why else "")
        st.markdown(
            f"<div class='sc-stepcard'>"
            f"<h2 style='font-size:34px;line-height:1.15;margin-top:0'>{step.title}</h2>"
            f"<p style='font-size:20px;color:#55433c'>{step.instruction}</p>"
            f"{why_html}</div>",
            unsafe_allow_html=True,
        )
        if st.button("📷 How should this look?", key=f"ref_btn_{idx}",
                     type="secondary"):
            st.session_state["show_reference"] = idx
            st.rerun()
        if st.session_state.get("show_reference") == idx:
            _render_reference(recipe, idx)

    with timer_col:
        if step.timer:
            running_key = f"timer_running_{idx}"
            st.markdown(
                f"<div style='display:flex;justify-content:center'>"
                f"{timer_ring(step.timer.duration_sec, step.timer.duration_sec)}</div>",
                unsafe_allow_html=True,
            )
            label = "Pause" if st.session_state.get(running_key) else "Start"
            if st.button(label, key=f"timer_btn_{idx}", type="secondary",
                         use_container_width=True):
                st.session_state[running_key] = not st.session_state.get(running_key)
                st.rerun()

    # Ask anything — real grounded answer using the current step as context.
    question = st.chat_input("Ask anything…")
    if question:
        st.session_state.setdefault("questions_asked", []).append(question)
        st.session_state["last_qa"] = (question, cook_answer(question, recipe, idx))
        st.rerun()

    # Bottom bar
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("← Back", key="back", type="secondary", use_container_width=True,
                     disabled=idx == 0):
            _goto(idx - 1)
    with b2:
        if st.button("↺ Repeat", key="repeat", type="secondary",
                     use_container_width=True):
            st.toast("Repeating the step (will speak aloud once voice is wired).")
    with b3:
        if idx + 1 < total:
            if st.button("Next →", key="next", type="primary",
                         use_container_width=True):
                _goto(idx + 1)
        else:
            if st.button("Finish ✓", key="finish", type="primary",
                         use_container_width=True):
                st.session_state["screen"] = "done"
                st.rerun()


def _goto(new_idx: int) -> None:
    """Advance/retreat a step, clearing any open answer/reference popups."""
    st.session_state["step_index"] = new_idx
    st.session_state.pop("last_qa", None)
    st.session_state.pop("show_reference", None)
    st.rerun()


def _render_answer() -> None:
    qa = st.session_state.get("last_qa")
    if not qa:
        return
    question, ans = qa
    st.markdown(
        f"<div style='margin:6px 0 14px'>"
        f"<div class='sc-answer-q'>🎙️ “{question}”</div>"
        f"<div class='sc-answer'>{ans}</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Got it ✕", key="dismiss_qa", type="secondary"):
        st.session_state.pop("last_qa", None)
        st.rerun()


def _render_reference(recipe, idx: int) -> None:
    """Honest visual reference: a written 'what to look for' + a real web link.
    Never fakes a visual judgement (Product Principle #4)."""
    step = recipe.steps[idx]
    look_for = step.why or "Use your judgement — go by colour, texture, and smell."
    query = urllib.parse.quote_plus(f"{recipe.title} {step.title}")
    st.markdown(
        f"<div class='sc-refcard'>"
        f"<b>👁️ Visual Reference</b><br>{look_for}"
        f"<br><span style='color:#7a6a63;font-size:14px'>I won't fake a photo — "
        f"here's what to look for, and you can check real images below.</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<a href='https://www.google.com/search?tbm=isch&q={query}' target='_blank'>"
        "🔎 See reference photos on the web</a>",
        unsafe_allow_html=True,
    )
    if st.button("Close", key=f"close_ref_{idx}", type="secondary"):
        st.session_state.pop("show_reference", None)
        st.rerun()
