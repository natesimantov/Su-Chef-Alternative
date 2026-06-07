"""PEOPLE screen — family & personal profiles.

Port of the Stitch `people_profiles` mockup: a list of free-text profile cards
(name + notes), inline edit, and Add person. Persists to data/profiles.json via
the profile_store tool — the seam between Nate's UI and Itay's backend.
"""

from __future__ import annotations

import streamlit as st

from shared.models import Profile
from tools.profile_store import load_profiles, save_profiles
from ui.components import topbar


def _profiles() -> list[Profile]:
    if "profiles" not in st.session_state:
        st.session_state["profiles"] = load_profiles()
    return st.session_state["profiles"]


def _persist() -> None:
    save_profiles(st.session_state["profiles"])


def render() -> None:
    topbar()
    st.markdown("<h1 style='font-size:44px;color:var(--sc-primary)'>People Profiles"
                "</h1>", unsafe_allow_html=True)

    profiles = _profiles()
    editing = st.session_state.get("editing_profile")

    for idx, p in enumerate(profiles):
        with st.container():
            if editing == idx:
                name = st.text_input("Name", value=p.name, key=f"name_{idx}")
                notes = st.text_area("Notes (free text)", value=p.notes,
                                     key=f"notes_{idx}", height=80)
                c1, c2, c3 = st.columns([1, 1, 4])
                with c1:
                    if st.button("Save", key=f"save_{idx}", type="primary"):
                        profiles[idx] = Profile(name=name, notes=notes)
                        _persist()
                        st.session_state["editing_profile"] = None
                        st.rerun()
                with c2:
                    if st.button("Delete", key=f"del_{idx}", type="secondary"):
                        profiles.pop(idx)
                        _persist()
                        st.session_state["editing_profile"] = None
                        st.rerun()
            else:
                row = st.columns([6, 1])
                with row[0]:
                    st.markdown(
                        f"<div class='sc-card' style='margin-bottom:4px'>"
                        f"<div style='font-size:24px;font-weight:700'>{p.name}</div>"
                        f"<div style='color:#55433c'>{p.notes}</div></div>",
                        unsafe_allow_html=True)
                with row[1]:
                    if st.button("✏️", key=f"edit_{idx}", help="Edit"):
                        st.session_state["editing_profile"] = idx
                        st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.expander("➕ Add person"):
        new_name = st.text_input("Name", key="new_name",
                                 placeholder="e.g. My brother")
        new_notes = st.text_area("Notes (free text)", key="new_notes",
                                 placeholder="e.g. vegan, hates cilantro")
        if st.button("Add", key="add_person", type="primary"):
            if new_name.strip():
                profiles.append(Profile(name=new_name.strip(),
                                        notes=new_notes.strip()))
                _persist()
                st.rerun()
