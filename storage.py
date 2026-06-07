"""Local persistence for chats and pinned answers.

Everything lives in two JSON files under data/ (gitignored — it's personal), so
the sidebar's recent chats and pinned answers survive app restarts. Small enough
to load/save whole on every change.

Shapes:
  chat = {"id": str, "title": str, "created_at": iso,
          "messages": [{"role": "user"|"assistant", "content": str}, ...]}
  pin  = {"id": str, "text": str, "question": str, "chat_id": str, "created_at": iso}
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "data"
_CHATS = _DATA / "chats.json"
_PINS = _DATA / "pins.json"


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _write(path: Path, data: list[dict]) -> None:
    _DATA.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def title_from(question: str) -> str:
    q = question.strip().replace("\n", " ")
    return (q[:40] + "…") if len(q) > 40 else (q or "New chat")


# --- Chats -------------------------------------------------------------------

def load_chats() -> list[dict]:
    """Most-recent chat first."""
    return sorted(_read(_CHATS), key=lambda c: c.get("created_at", ""), reverse=True)


def save_chat(chat: dict) -> None:
    """Insert or update a chat by id."""
    chats = [c for c in _read(_CHATS) if c.get("id") != chat["id"]]
    chats.append(chat)
    _write(_CHATS, chats)


def delete_chat(chat_id: str) -> None:
    _write(_CHATS, [c for c in _read(_CHATS) if c.get("id") != chat_id])


# --- Pins --------------------------------------------------------------------

def load_pins() -> list[dict]:
    return sorted(_read(_PINS), key=lambda p: p.get("created_at", ""), reverse=True)


def add_pin(text: str, question: str, chat_id: str) -> None:
    pins = _read(_PINS)
    pins.append({"id": new_id(), "text": text, "question": question,
                 "chat_id": chat_id, "created_at": _now()})
    _write(_PINS, pins)


def remove_pin(pin_id: str) -> None:
    _write(_PINS, [p for p in _read(_PINS) if p.get("id") != pin_id])


def is_pinned(text: str) -> bool:
    return any(p.get("text") == text for p in _read(_PINS))


def pin_id_for(text: str) -> str | None:
    return next((p["id"] for p in _read(_PINS) if p.get("text") == text), None)
