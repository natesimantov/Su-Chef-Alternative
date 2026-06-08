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
    """Process a question: start or continue the active chat, get a structured
    answer, persist it, and queue it to be read aloud."""
    question = (question or "").strip()
    if not question:
        return
    chat = st.session_state.get("active_chat")
    if chat is None:
        chat = {"id": storage.new_id(), "title": storage.title_from(question),
                "created_at": storage._now(), "messages": []}
    chat["messages"].append({"role": "user", "content": question})
    reply = companion.answer(chat["messages"])
    chat["messages"].append(_assistant_msg(reply))
    _finish(chat, reply["answer"])


def regenerate(chat: dict, idx: int, corrected_context: str) -> None:
    """Re-answer the assistant turn at `idx` using the cook's corrected context.
    Truncates anything after it (editing rewrites the thread from that point)."""
    convo = [{"role": m["role"], "content": m["content"]} for m in chat["messages"][:idx]]
    convo.append({"role": "user",
                  "content": f"(Quick context correction: {corrected_context}.) "
                             "Please answer again with this in mind."})
    reply = companion.answer(convo)
    new_msg = _assistant_msg(reply)
    if corrected_context.strip():
        new_msg["context"] = corrected_context.strip()
    chat["messages"] = chat["messages"][:idx] + [new_msg]
    st.session_state.pop("edit_context", None)
    _finish(chat, reply["answer"])


def _assistant_msg(reply: dict) -> dict:
    return {"role": "assistant", "content": reply["answer"],
            "context": reply.get("context", ""),
            "follow_ups": reply.get("follow_ups", [])}


def _mic_to_ask(key: str) -> None:
    """Render the mic; when a new utterance arrives (deduped on its timestamp),
    treat it as an asked question."""
    res = voice.mic(key=key)
    if isinstance(res, dict) and res.get("text"):
        seen = f"mic_seen_{key}"
        if st.session_state.get(seen) != res.get("t"):
            st.session_state[seen] = res.get("t")
            ask(res["text"])


def _finish(chat: dict, spoken: str) -> None:
    storage.save_chat(chat)
    st.session_state["active_chat"] = chat
    st.session_state["pending_speak"] = spoken
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
                    if st.button(f"📌 {snippet}", key=f"pin_{p['id']}",
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

        st.markdown("<hr style='margin:16px 0;border:none;border-top:1px solid "
                    "#dbc1b8'>", unsafe_allow_html=True)
        with st.expander("🔊  Voice & accent"):
            voice.voice_settings()


# --- Main: new-chat empty state ---------------------------------------------

def render_new_chat() -> None:
    st.markdown(
        "<h1 style='text-align:center;font-size:56px;margin:7vh 0 1vh'>"
        "How can I help?</h1>"
        "<p style='text-align:center;color:#55433c;font-size:18px;margin-bottom:4vh'>"
        "Ask me anything while you cook — tap the mic or type below.</p>",
        unsafe_allow_html=True)

    mid = st.columns([1, 3, 1])[1]
    with mid:
        _mic_to_ask("mic_new")
        st.markdown("<p class='sc-eyebrow' style='text-align:center;margin-top:6px'>"
                    "or type it</p>", unsafe_allow_html=True)

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
            _render_answer(chat, i, is_last=(i == last_assistant))

    if st.session_state.get("followup_open"):
        st.markdown("<p class='sc-eyebrow' style='margin-top:18px'>Continue this "
                    "chat</p>", unsafe_allow_html=True)
        _mic_to_ask("mic_followup")
        typed = st.chat_input("Ask a follow-up…")
        if typed:
            ask(typed)


def _render_answer(chat: dict, idx: int, is_last: bool) -> None:
    cid = chat["id"]
    m = chat["messages"][idx]
    text = m["content"]
    ctx = m.get("context", "")
    question = chat["messages"][idx - 1]["content"] if idx > 0 else ""

    # 1) Context line ("Sounds like you're making…") with an edit ✎ on the latest.
    if st.session_state.get("edit_context") == idx:
        new_ctx = st.text_input("Correct what I understood", value=ctx,
                                key=f"ctxin_{cid}_{idx}")
        b1, b2, _ = st.columns([1, 1, 5])
        with b1:
            if st.button("Save", key=f"ctxsave_{cid}_{idx}", type="primary",
                         use_container_width=True):
                regenerate(chat, idx, new_ctx)
        with b2:
            if st.button("Cancel", key=f"ctxcancel_{cid}_{idx}",
                         use_container_width=True):
                st.session_state.pop("edit_context", None)
                st.rerun()
    elif ctx:
        if is_last:
            c1, c2 = st.columns([11, 1])
            with c1:
                st.markdown(f"<p class='sc-context'>{ctx}</p>",
                            unsafe_allow_html=True)
            with c2:
                if st.button("✎", key=f"ctxedit_{cid}_{idx}",
                             help="Correct what I understood"):
                    st.session_state["edit_context"] = idx
                    st.rerun()
        else:
            st.markdown(f"<p class='sc-context'>{ctx}</p>",
                        unsafe_allow_html=True)

    # 2) Answer card + pin (top-right) and a big read-aloud button on the right.
    acol, rcol = st.columns([5, 1])
    with acol:
        st.markdown(f"<div class='sc-answer'>{text}</div>", unsafe_allow_html=True)
    with rcol:
        pinned = storage.is_pinned(text)
        if st.button("📌", key=f"pintoggle_{cid}_{idx}",
                     type="primary" if pinned else "secondary",
                     help="Unpin" if pinned else "Pin this answer",
                     use_container_width=True):
            if pinned:
                pid = storage.pin_id_for(text)
                if pid:
                    storage.remove_pin(pid)
            else:
                storage.add_pin(text, question, cid)
            st.rerun()
        if st.button("🔊", key=f"say_{cid}_{idx}", help="Read aloud",
                     use_container_width=True):
            voice.speak(text)

    if not is_last:
        return

    # 3) Suggested follow-ups (Gmail-style), then the custom follow-up composer.
    for j, fu in enumerate(m.get("follow_ups", [])):
        if st.button(fu, key=f"sugg_{cid}_{idx}_{j}", use_container_width=True):
            ask(fu)
    if st.button("↩  Ask a different follow-up", key=f"fu_{cid}_{idx}",
                 type="primary", use_container_width=True):
        st.session_state["followup_open"] = True
        st.rerun()


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
