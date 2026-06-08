"""The chef in your pocket — fast, grounded answers to mid-cook questions.

`answer(messages)` takes the active chat's turns (a list of
{"role": "user"|"assistant", "content": str}) and returns a structured reply:

    {"context": str, "answer": str, "follow_ups": [str, ...]}

- context: a short, friendly line proving Su Chef understood the situation.
- answer: 1-3 short, warm, spoken-style sentences.
- follow_ups: 2-3 likely next questions, phrased as the cook would ask them.

It calls Claude when an ANTHROPIC_API_KEY is available (the smart path), and
falls back to a small deterministic culinary knowledge base otherwise so the app
still does something useful with no key.
"""

from __future__ import annotations

import json
import os

MODEL = os.environ.get("SU_CHEF_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = (
    "You are Su Chef, a warm and knowledgeable cooking companion — like a friendly, "
    "seasoned chef standing right at the cook's side. They are mid-cooking and ask "
    "short, practical questions, often mentioning what they're making.\n\n"
    "Reply with three things:\n"
    "- context: ONE short, friendly line showing you understood, e.g. \"Sounds like "
    "you're making a tomato sauce and need a pan tip.\" One sentence, no more.\n"
    "- answer: 1-3 SHORT spoken sentences. Warm and encouraging with a light touch of "
    "personality, but never longer than needed — brevity matters at the stove. Be "
    "decisive; briefly say why when it helps. If you truly don't know or it's a "
    "food-safety call, say so honestly.\n"
    "- follow_ups: 2-3 very short likely next questions, phrased the way the cook "
    "would say them (e.g. \"How long do I cook it?\")."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "context": {"type": "string"},
        "answer": {"type": "string"},
        "follow_ups": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["context", "answer", "follow_ups"],
    "additionalProperties": False,
}

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


_UNITS = {
    "metric": "Use metric units throughout: Celsius for temperature, and "
              "grams/millilitres/litres for measures.",
    "us": "Use US customary units throughout: Fahrenheit for temperature, and "
          "cups/ounces/pounds/teaspoons/tablespoons for measures.",
}


def answer(messages: list[dict], units: str = "metric") -> dict:
    """Return Su Chef's structured reply to the conversation so far."""
    key = _api_key()
    if key:
        try:
            return _ask_claude(messages, key, units)
        except Exception as exc:  # network/auth/etc. — degrade gracefully
            return {
                "context": "",
                "answer": (f"I hit a snag reaching my brain "
                           f"({exc.__class__.__name__}). Try again in a moment."),
                "follow_ups": [],
            }
    latest = next((m["content"] for m in reversed(messages)
                   if m["role"] == "user"), "")
    return _offline_reply(latest)


def _ask_claude(messages: list[dict], key: str, units: str = "metric") -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    system = SYSTEM_PROMPT + "\n\n" + _UNITS.get(units, _UNITS["metric"])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    fu = [s for s in data.get("follow_ups", []) if isinstance(s, str)][:3]
    return {
        "context": data.get("context", "").strip(),
        "answer": data.get("answer", "").strip(),
        "follow_ups": fu,
    }


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


def _offline_reply(question: str) -> dict:
    q = question.lower()
    text = None
    for ingredient, advice in _SUBSTITUTIONS.items():
        if ingredient in q and any(c in q for c in
                                   ("out of", "no ", "instead", "substitut",
                                    "don't have", "dont have", "replace", "missing",
                                    "without", "ran out")):
            text = advice
            break
    if text is None:
        for keys, advice in _FACTS:
            if any(k in q for k in keys):
                text = advice
                break
    if text is None:
        text = ("I can't answer that one fully without my full knowledge — but when "
                "in doubt, go slow, taste as you go, and adjust seasoning at the end.")
    return {
        "context": "Here's what I can help with from my built-in notes.",
        "answer": text + NO_KEY_NOTICE,
        "follow_ups": ["What can I substitute?", "How do I fix it if it goes wrong?"],
    }
