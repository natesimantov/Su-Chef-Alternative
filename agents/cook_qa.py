"""Cook-time ask-anything — fast, grounded, short answers.

This is the "fast path" from the proposal: cook-time interactions stay cheap (a
single light call), because latency matters at the stove. With no API key it
answers from a deterministic culinary knowledge base grounded in the current
step; with ANTHROPIC_API_KEY set it asks a small, fast Claude model using the
same context. Answers are short and action-oriented.
"""

from __future__ import annotations

import os

from shared.models import Recipe

# "Out of X?" → a concrete swap. Keyed by ingredient keyword.
_SUBSTITUTIONS: dict[str, str] = {
    "shallot": "Use ½ a small onion instead. It's a bit stronger, so chop it very "
               "finely.",
    "garlic": "A pinch of garlic powder (~⅛ tsp per clove) works, or a little finely "
              "diced shallot.",
    "butter": "Swap in the same amount of olive oil — slightly different flavour, "
              "but it works fine.",
    "white wine": "Use the same amount of stock with a splash of white wine vinegar "
                  "or lemon for the acidity.",
    "wine": "Use stock plus a splash of vinegar or lemon for the acidity it was "
            "adding.",
    "parmesan": "Pecorino works 1:1. Dairy-free? 2 tbsp nutritional yeast gives a "
                "similar savoury hit.",
    "arborio": "Carnaroli is ideal; otherwise any short-grain rice. Avoid long-grain "
               "— it won't go creamy.",
    "rice": "For risotto, stick to short-grain (Arborio/Carnaroli). Long-grain won't "
            "release the starch.",
    "stock": "Water with a bouillon cube works, or lightly salted water with a splash "
             "of soy for depth.",
    "broth": "Water with a bouillon cube works in a pinch.",
    "lemon": "Use the same amount of white wine vinegar, or half as much lime.",
    "onion": "A couple of shallots, or the white parts of a few spring onions.",
    "egg": "For binding: 1 tbsp ground flax + 3 tbsp water per egg, rested 5 minutes.",
    "milk": "Any unsweetened plant milk works 1:1.",
    "mozzarella": "Low-moisture mozzarella or a mild provolone melts similarly.",
}

_SUB_CUES = ("out of", "no ", "instead", "substitut", "don't have", "dont have",
             "replace", "missing", "ran out", "without")

# Rescues — (trigger keywords, advice).
_RESCUES: list[tuple[tuple[str, ...], str]] = [
    (("too salty", "salty", "over salt", "oversalt"),
     "Don't tip it out. Dilute with more stock or water, simmer a peeled raw potato "
     "in it to absorb salt, or add a splash of cream. A little lemon also balances it."),
    (("split", "broke", "broken", "curdl", "separat"),
     "Off the heat, whisk in a tablespoon of warm water (or a splash of cream for "
     "dairy sauces) to bring it back together."),
    (("burn", "burnt", "caught", "scorch"),
     "Stop stirring and don't scrape the bottom. Move the unburnt part to a clean "
     "pan and taste before carrying on."),
    (("watery", "too thin", "runny", "loose"),
     "Keep it on the heat to reduce, or stir in a little cornflour slurry (1 tsp in "
     "cold water). For risotto, just cook a little longer."),
    (("too thick", "gluey", "stodgy", "claggy", "dry"),
     "Loosen with a splash of hot stock or water, a little at a time, until it "
     "flows again."),
    (("too spicy", "too hot", "burning my"),
     "Add dairy (cream or yogurt) or something sweet/acidic. A starch like rice or "
     "potato also soaks up heat."),
    (("lumpy", "lumps"),
     "Whisk hard or pass it through a sieve — a stick blender fixes most lumpy "
     "sauces instantly."),
    (("bland", "needs something", "missing something", "flat tasting"),
     "It's usually salt or acid. Add a pinch of salt, taste, then a squeeze of "
     "lemon or splash of vinegar."),
]

_DONENESS_CUES = ("done", "ready", "look like", "how do i know", "cooked", "when is",
                  "is it ready", "is this right")


def answer(question: str, recipe: Recipe, step_index: int) -> str:
    """Return a short, grounded answer to a mid-cook question."""
    q = question.lower().strip()
    step = recipe.steps[step_index] if 0 <= step_index < len(recipe.steps) else None

    # 1) Substitutions
    if any(cue in q for cue in _SUB_CUES):
        for ingredient, sub in _SUBSTITUTIONS.items():
            if ingredient in q:
                return sub

    # 2) Rescues
    for keys, advice in _RESCUES:
        if any(k in q for k in keys):
            return advice

    # 3) Doneness — lean on the current step's cue
    if any(k in q for k in _DONENESS_CUES) and step and step.why:
        return f"Here's what to look for: {step.why}"

    # 4) Optional fast Claude path (same grounding)
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _ask_claude(question, recipe, step_index)
        except Exception:
            pass

    # 5) Honest fallback
    if step and step.why:
        return (f"I don't have a specific answer, but for this step: {step.why} "
                "When unsure, go slow, taste, and adjust.")
    return ("I'm not certain from the recipe alone — go slow, taste as you go, and "
            "adjust. (Add an API key for fuller answers.)")


def _ask_claude(question: str, recipe: Recipe, step_index: int) -> str:
    """Single light call to a fast Claude model, grounded in the current step."""
    from anthropic import Anthropic  # optional dependency, imported lazily

    step = recipe.steps[step_index]
    model = os.environ.get("SU_CHEF_COOK_MODEL", "claude-haiku-4-5")
    client = Anthropic()
    prompt = (
        f"You are a calm sous-chef. The cook is making {recipe.title}. "
        f"Current step: {step.title} — {step.instruction} "
        f"(doneness cue: {step.why}). Answer in 1–2 short, spoken, action-oriented "
        f"sentences. If unsure, say so honestly.\n\nQuestion: {question}"
    )
    msg = client.messages.create(
        model=model, max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
