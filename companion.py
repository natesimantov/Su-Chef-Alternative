"""The chef in your pocket — fast, grounded answers to mid-cook questions.

`answer(messages)` takes the active chat's turns (a list of
{"role": "user"|"assistant", "content": str}) and returns a short, spoken-style
answer. It calls Claude when an ANTHROPIC_API_KEY is available (the smart path),
and falls back to a small deterministic culinary knowledge base otherwise so the
app still does something useful with no key.
"""

from __future__ import annotations

import os

MODEL = os.environ.get("SU_CHEF_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = (
    "You are Su Chef, an expert cooking companion with deep culinary and "
    "food-science knowledge — like a seasoned chef standing at the cook's side. "
    "They are mid-cooking and will ask short, practical questions, often "
    "mentioning what they're making. Answer in 1-3 short, spoken sentences. Be "
    "decisive and specific; briefly say why when it helps. If something is "
    "missing or went wrong, give the best fix. If you genuinely don't know or "
    "it's a food-safety call, say so honestly rather than guessing. No preamble, "
    "no bulleted lists unless truly necessary."
)

NO_KEY_NOTICE = (
    "  \n\n_(Running without an API key, so this is a limited built-in answer. "
    "Add an ANTHROPIC_API_KEY for full chef-grade responses.)_"
)


def _api_key() -> str | None:
    """Resolve the key from Streamlit secrets first, then the environment."""
    try:
        import streamlit as st

        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def answer(messages: list[dict]) -> str:
    """Return Su Chef's reply to the conversation so far."""
    key = _api_key()
    if key:
        try:
            return _ask_claude(messages, key)
        except Exception as exc:  # network/auth/etc. — degrade gracefully
            return (f"I hit a snag reaching my brain ({exc.__class__.__name__}). "
                    "Try again in a moment.")
    # No key: best-effort offline answer for the latest user message.
    latest = next((m["content"] for m in reversed(messages)
                   if m["role"] == "user"), "")
    return _offline_answer(latest) + NO_KEY_NOTICE


def _ask_claude(messages: list[dict], key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=350,
        system=SYSTEM_PROMPT,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


# --- Offline fallback: a small deterministic culinary knowledge base ----------

_SUBSTITUTIONS: dict[str, str] = {
    "baking soda": "No baking soda? Use about 3x the amount of baking powder, or "
                   "for many recipes (like most apple pies) you can simply leave it "
                   "out — the filling and crust don't need it.",
    "baking powder": "Out of baking powder? Mix 1/4 tsp baking soda + 1/2 tsp cream "
                     "of tartar to replace 1 tsp.",
    "shallot": "Use 1/2 a small onion instead — a touch stronger, so chop it finely.",
    "garlic": "A pinch of garlic powder (~1/8 tsp per clove) works in a pinch.",
    "butter": "Swap in the same amount of olive oil; slightly different flavour, "
              "but it works.",
    "wine": "Use stock plus a splash of vinegar or lemon for the acidity.",
    "buttermilk": "Stir 1 tbsp lemon juice or vinegar into 1 cup milk; rest 5 min.",
    "egg": "For binding: 1 tbsp ground flax + 3 tbsp water per egg, rested 5 min.",
    "lemon": "Use the same amount of white wine vinegar, or half as much lime.",
}

_FACTS: list[tuple[tuple[str, ...], str]] = [
    (("cast iron", "stainless", "pan for", "reactive"),
     "For an acidic tomato/pasta sauce, use stainless steel — not bare cast iron. "
     "Acid reacts with reactive metals, picking up a metallic taste and dulling "
     "the colour. Enamelled cast iron is fine."),
    (("split", "broke", "curdl", "separat"),
     "Off the heat, whisk in a tablespoon of warm water (or a splash of cream for "
     "dairy sauces) to bring it back together."),
    (("too salty", "salty"),
     "Dilute with more liquid, simmer a peeled potato in it to absorb salt, or "
     "add a splash of cream; a little acid balances it too."),
    (("rest", "resting", "rest the meat"),
     "Rest meat about half its cook time — roughly 5-10 min for steak — so the "
     "juices redistribute instead of running out."),
]


def _offline_answer(question: str) -> str:
    q = question.lower()
    for ingredient, advice in _SUBSTITUTIONS.items():
        if ingredient in q and any(c in q for c in
                                   ("out of", "no ", "instead", "substitut",
                                    "don't have", "dont have", "replace", "missing",
                                    "without", "ran out")):
            return advice
    for keys, advice in _FACTS:
        if any(k in q for k in keys):
            return advice
    return ("I can't answer that one fully without my full knowledge — but when in "
            "doubt, go slow, taste as you go, and adjust seasoning at the end.")
