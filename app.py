"""Su Chef — a knowledgeable chef in your pocket.

One prompt: "How can I help?" Ask anything mid-cook by voice or text and get a
fast, grounded, spoken answer. Each starting question is its own logged chat
(like ChatGPT sessions); follow-ups continue it; star an answer to pin it. Recent
chats and pins live in the sidebar and persist across restarts.

Run:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

import companion
import storage
import voice
from theme import inject_theme


def _init_state() -> None:
    st.session_state.setdefault("active_chat", None)   # dict or None (= new chat)
    st.session_state.setdefault("followup_open", False)
    st.session_state.setdefault("pending_speak", None)


def _new_chat() -> None:
    st.session_state["active_chat"] = None
    st.session_state["followup_open"] = False


def _open_chat(chat_id: str) -> None:
    chat = next((c for c in storage.load_chats() if c["id"] == chat_id), None)
    st.session_state["active_chat"] = chat
    st.session_state["followup_open"] = False


def ask(question: str) -> None:
    """Process a question: start or continue the active chat, get an answer,
    persist it, and queue it to be read aloud."""
    question = (question or "").strip()
    if not question:
        return
    chat = st.session_state.get("active_chat")
    if chat is None:
        chat = {"id": storage.new_id(), "title": storage.title_from(question),
                "created_at": storage._now(), "messages": []}
    chat["messages"].append({"role": "user", "content": question})
    reply = companion.answer(chat["messages"])
    chat["messages"].append({"role": "assistant", "content": reply})
    storage.save_chat(chat)
    st.session_state["active_chat"] = chat
    st.session_state["pending_speak"] = reply
    st.session_state["followup_open"] = False
    st.rerun()


# --- Sidebar -----------------------------------------------------------------

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="sc-wordmark">Su&nbsp;Chef</div>',
                    unsafe_allow_html=True)
        if st.button("➕  New question", key="new_chat", type="primary",
                     use_container_width=True):
            _new_chat()
            st.rerun()

        pins = storage.load_pins()
        if pins:
            st.markdown("<p class='sc-eyebrow'>📌 Pinned</p>", unsafe_allow_html=True)
            for p in pins:
                c1, c2 = st.columns([5, 1])
                with c1:
                    snippet = p["text"][:70] + ("…" if len(p["text"]) > 70 else "")
                    if st.button(f"★ {snippet}", key=f"pin_{p['id']}",
                                 use_container_width=True):
                        _open_chat(p["chat_id"])
                        st.rerun()
                with c2:
                    if st.button("✕", key=f"unpin_{p['id']}"):
                        storage.remove_pin(p["id"])
                        st.rerun()

        st.markdown("<p class='sc-eyebrow'>🕘 Recent chats</p>",
                    unsafe_allow_html=True)
        chats = storage.load_chats()
        if not chats:
            st.caption("Your questions will show up here.")
        active_id = (st.session_state.get("active_chat") or {}).get("id")
        for c in chats:
            label = ("• " if c["id"] == active_id else "") + c["title"]
            if st.button(label, key=f"chat_{c['id']}", use_container_width=True):
                _open_chat(c["id"])
                st.rerun()


# --- Main: new-chat empty state ---------------------------------------------

def render_new_chat() -> None:
    st.markdown(
        "<h1 style='text-align:center;font-size:56px;margin:8vh 0 4vh'>"
        "How can I help?</h1>", unsafe_allow_html=True)

    spoken = voice.listen(key="mic_new")
    if spoken:
        ask(spoken)

    typed = st.chat_input("Ask Su Chef anything… (e.g. “out of buttermilk — what now?”)")
    if typed:
        ask(typed)


# --- Main: an active chat ----------------------------------------------------

def render_chat(chat: dict) -> None:
    # Read the freshest answer aloud once.
    if st.session_state.get("pending_speak"):
        voice.speak(st.session_state["pending_speak"])
        st.session_state["pending_speak"] = None

    left, right = st.columns([5, 1])
    with left:
        st.markdown('<div class="sc-wordmark">Su Chef</div>', unsafe_allow_html=True)

    msgs = chat["messages"]
    last_assistant = max((i for i, m in enumerate(msgs)
                          if m["role"] == "assistant"), default=-1)

    for i, m in enumerate(msgs):
        if m["role"] == "user":
            st.markdown(f"<p class='sc-question'>🎙️ “{m['content']}”</p>",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='sc-answer'>{m['content']}</div>",
                        unsafe_allow_html=True)
            _answer_controls(chat, i, is_last=(i == last_assistant))

    if st.session_state.get("followup_open"):
        st.markdown("<p class='sc-eyebrow' style='margin-top:18px'>Continue this "
                    "chat</p>", unsafe_allow_html=True)
        spoken = voice.listen(key="mic_followup")
        if spoken:
            ask(spoken)
        typed = st.chat_input("Ask a follow-up…")
        if typed:
            ask(typed)


def _answer_controls(chat: dict, idx: int, is_last: bool) -> None:
    text = chat["messages"][idx]["content"]
    question = chat["messages"][idx - 1]["content"] if idx > 0 else ""
    cols = st.columns([3, 1, 1, 3])

    if is_last:
        with cols[0]:
            if st.button("↩  Ask a follow-up", key=f"fu_{chat['id']}_{idx}",
                         type="primary", use_container_width=True):
                st.session_state["followup_open"] = True
                st.rerun()

    with cols[1]:
        pinned = storage.is_pinned(text)
        if st.button("★" if pinned else "☆", key=f"pintoggle_{chat['id']}_{idx}",
                     help="Unpin" if pinned else "Pin this answer",
                     use_container_width=True):
            if pinned:
                pid = storage.pin_id_for(text)
                if pid:
                    storage.remove_pin(pid)
            else:
                storage.add_pin(text, question, chat["id"])
            st.rerun()
    with cols[2]:
        voice.speak_button(text, key=f"say_{chat['id']}_{idx}")


def main() -> None:
    st.set_page_config(page_title="Su Chef", page_icon="🍳", layout="centered")
    inject_theme()
    _init_state()

    render_sidebar()
    chat = st.session_state.get("active_chat")
    if chat is None:
        render_new_chat()
    else:
        render_chat(chat)


if __name__ == "__main__":
    main()
