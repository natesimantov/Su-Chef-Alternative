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
import re

MODEL = os.environ.get("SU_CHEF_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = (
    "You are Su Chef, a warm and knowledgeable cooking companion — like a friendly, "
    "seasoned chef standing right at the cook's side. They are mid-cooking and ask "
    "short, practical questions, often mentioning what they're making.\n\n"
    "Reply with three things:\n"
    "- context: ONE short, DRY, factual line restating the situation, e.g. "
    "\"Choosing a pan for a tomato sauce.\" or \"Out of buttermilk for pancakes.\" "
    "No exclamation points, no praise (never \"great question\", \"good idea\", "
    "\"classic\"), no enthusiasm, no em dashes. Just plainly state what they're "
    "doing. One sentence, no more.\n"
    "- answer: 1-3 SHORT spoken sentences. Warm and encouraging with a light touch of "
    "personality, but never longer than needed — brevity matters at the stove. Be "
    "decisive; briefly say why when it helps. If you truly don't know or it's a "
    "food-safety call, say so honestly.\n"
    "- follow_ups: 2-3 ULTRA-short follow-up chips, 2-4 words each, phrased as a "
    "quick tap (e.g. \"How long?\", \"Serve with?\", \"Too salty?\", \"Make it spicier?\"). "
    "Keep them short enough to sit side by side.\n\n"
    "NEVER write out URLs, web addresses, or 'http' links in your text — they "
    "aren't clickable and pull the cook out of the app. If a full recipe would "
    "help, don't paste a link; that's what the recipe button is for."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "context": {"type": "string"},
        "answer": {"type": "string"},
        "follow_ups": {"type": "array", "items": {"type": "string"}},
        "recipe_suggestion": {"type": "string"},
    },
    "required": ["context", "answer", "follow_ups"],
    "additionalProperties": False,
}

# Structured recipe (the recipe widget). Claude fills this for "make me X".
_RECIPE_SCHEMA = {
    "type": "object",
    "properties": {
        "context": {"type": "string"},
        "title": {"type": "string"},
        "intro": {"type": "string"},
        "servings": {"type": "integer"},
        "total_time_min": {"type": "integer"},
        "ingredients": {"type": "array", "items": {"type": "string"}},
        "utensils": {"type": "array", "items": {"type": "string"}},
        "steps": {"type": "array", "items": {"type": "string"}},
        "tip": {"type": "string"},
        "source_url": {"type": "string"},
        "follow_ups": {"type": "array", "items": {"type": "string"}},
        "nutrition": {
            "type": "object",
            "properties": {
                "calories": {"type": "integer"}, "protein_g": {"type": "integer"},
                "carbs_g": {"type": "integer"}, "fat_g": {"type": "integer"},
                "fiber_g": {"type": "integer"}, "sugar_g": {"type": "integer"},
                "sodium_mg": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        # The "kitchen crew" — short expert reviews shown on the recipe card.
        "expert_review": {
            "type": "object",
            "properties": {
                "nutrition_note": {"type": "string"},
                "diet_safety": {
                    "type": "object",
                    "properties": {
                        "diet_flags": {"type": "array", "items": {"type": "string"}},
                        "allergens": {"type": "array", "items": {"type": "string"}},
                        "safety_note": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                "equipment": {
                    "type": "object",
                    "properties": {
                        "tools": {"type": "array", "items": {"type": "string"}},
                        "substitutions": {"type": "array", "items": {"type": "string"}},
                        "note": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
        },
    },
    "required": ["context", "title", "intro", "servings", "total_time_min",
                 "ingredients", "utensils", "steps", "follow_ups"],
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


_RECIPE_HINTS = ("make ", "recipe for", "recipe", "how do i make", "how to make",
                 "how do you make", "i want to make", "i'd like to make",
                 "id like to make", "give me a recipe", "show me how to",
                 "teach me to make", "cook me", "let's make", "lets make",
                 "can you make", "could you make", "what do i need to make",
                 "i'm making", "im making", "what's the recipe")


def _is_recipe_request(text: str) -> bool:
    t = (text or "").lower()
    return any(h in t for h in _RECIPE_HINTS)


def answer(messages: list[dict], units: str = "metric") -> dict:
    """Return Su Chef's structured reply to the conversation so far, grounded in
    real recipes retrieved from our dataset (RAG). A "make me X" request returns
    a fuller recipe plus a predicted quick/involved estimate from the model."""
    latest = next((m["content"] for m in reversed(messages)
                   if m["role"] == "user"), "")
    recipe = _is_recipe_request(latest)
    try:
        import rag
        grounding = rag.grounding_block(latest)
    except Exception:
        grounding = ""

    key = _api_key()
    if not key:
        return _offline_reply(latest)
    try:
        if recipe:
            return _build_recipe(messages, key, units, grounding)
        return _ask_claude(messages, key, units, grounding)
    except Exception as exc:  # network/auth/etc. — degrade gracefully
        return {
            "context": "",
            "answer": (f"I hit a snag reaching my brain "
                       f"({exc.__class__.__name__}). Try again in a moment."),
            "follow_ups": [],
        }


def _model_nutrition(recipe: dict) -> dict | None:
    """Trained-model per-serving nutrition estimate, used as a cross-check."""
    try:
        from pipeline import tools as T
        ings = recipe.get("ingredients", []) or []
        return T.estimate_nutrition({
            "ingredients": ings,
            "num_ingredients": len(ings),
            "servings": recipe.get("servings") or None,
            "course": recipe.get("course") or None,
        })
    except Exception:
        return None


def _macro_fit(targets: dict, nut: dict | None) -> dict | None:
    """Compare a recipe's per-serving nutrition against the cook's targets."""
    if not targets or not nut:
        return None
    tol = {"calories": 0.15, "protein_g": 0.2, "carbs_g": 0.25, "fat_g": 0.25}
    metrics, on_target = [], True
    for k, t in tol.items():
        tgt, val = targets.get(k), nut.get(k)
        if tgt and val is not None:
            ok = abs(val - tgt) <= t * tgt
            metrics.append({"key": k, "target": tgt, "value": val, "ok": bool(ok)})
            on_target = on_target and ok
    if not metrics:
        return None
    return {"metrics": metrics, "on_target": on_target}


def _format_recipe_text(r: dict) -> str:
    """Render a structured recipe to plain text (for Streamlit / read-aloud)."""
    lines = [r.get("intro", ""), "", "Ingredients:"]
    lines += [f"- {i}" for i in r.get("ingredients", [])]
    if r.get("utensils"):
        lines += ["", "You'll need: " + ", ".join(r["utensils"])]
    lines += ["", "Steps:"]
    lines += [f"{n}. {s}" for n, s in enumerate(r.get("steps", []), 1)]
    if r.get("tip"):
        lines += ["", "Tip: " + r["tip"]]
    n = r.get("nutrition")
    if n and n.get("calories"):
        lines += ["", f"Per serving (est.): {n.get('calories')} kcal, "
                  f"{n.get('protein_g', '?')} g protein, {n.get('carbs_g', '?')} g "
                  f"carbs, {n.get('fat_g', '?')} g fat."]
    return "\n".join(lines).strip()


def _build_recipe(messages: list[dict], key: str, units: str, grounding: str,
                  extra_directive: str = "") -> dict:
    """Produce a STRUCTURED recipe (the recipe widget) + a text fallback answer."""
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    system = SYSTEM_PROMPT + "\n\n" + _UNITS.get(units, _UNITS["metric"])
    if grounding:
        system += ("\n\nBase the recipe on these real recipes from our database; "
                   "prefer them over inventing, and set source_url to the one you "
                   "drew on.\n" + grounding)
    system += ("\n\nThe cook wants to MAKE a dish. Honor anything they said earlier "
               "in the conversation (servings, diet, allergies, dislikes, equipment, "
               "skill level) — use the FULL chat context. Fill the structured recipe: "
               "a short title, a one-line intro, servings, your best total_time_min "
               "estimate, ingredients (each as 'amount item'), the utensils needed, "
               "clear numbered steps, an optional tip, and source_url if used. Also a "
               "friendly one-line context and 2-3 ultra-short (2-4 word) follow_ups. "
               "Also give a rough PER-SERVING nutrition estimate (calories, protein_g, "
               "carbs_g, fat_g, and if you can fiber_g, sugar_g, sodium_mg) — these are "
               "estimates, not exact. The context line must be DRY and factual "
               "(e.g. \"Recipe for paneer butter masala for 4.\") — no exclamation "
               "points, no praise, no enthusiasm, no em dashes.")
    system += ("\n\nYou are also Su Chef's KITCHEN CREW reviewing this recipe. Fill "
               "expert_review with SHORT, accurate notes (one line each, no fluff): "
               "nutrition_note = the Nutritionist's qualitative read of the macros "
               "(e.g. \"Lean and high in protein, light on carbs\"). "
               "diet_safety.diet_flags = diets this recipe actually satisfies "
               "(e.g. Vegetarian, Gluten-Free, Vegan, Dairy-Free, Keto). "
               "diet_safety.allergens = common allergens genuinely present, from "
               "{peanuts, tree nuts, dairy, eggs, gluten, soy, shellfish, fish}; "
               "empty if none. diet_safety.safety_note = one practical food-safety "
               "line (e.g. \"Cook chicken to 75C / 165F\"). equipment.tools = key "
               "equipment needed. equipment.substitutions = handy swaps as \"X -> Y\". "
               "equipment.note = one line. Be honest about allergens and diet "
               "compliance; never claim a diet it does not meet.")
    if extra_directive:
        system += "\n\n" + extra_directive
    resp = client.messages.create(
        model=MODEL, max_tokens=1100, system=system,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        output_config={"format": {"type": "json_schema", "schema": _RECIPE_SCHEMA}},
    )
    data = json.loads("".join(b.text for b in resp.content if b.type == "text"))
    recipe = {
        "title": data.get("title", "").strip(),
        "intro": data.get("intro", "").strip(),
        "servings": data.get("servings"),
        "total_time_min": data.get("total_time_min"),
        "ingredients": [str(i) for i in data.get("ingredients", [])],
        "utensils": [str(u) for u in data.get("utensils", [])],
        "steps": [str(s) for s in data.get("steps", [])],
        "tip": data.get("tip", "").strip(),
        "source_url": data.get("source_url", "").strip(),
        "nutrition": data.get("nutrition") or None,
        "expert_review": data.get("expert_review") or None,
    }
    recipe["nutrition_model"] = _model_nutrition(recipe)
    fu = [s for s in data.get("follow_ups", []) if isinstance(s, str)][:3]
    return {
        "context": data.get("context", "").strip(),
        "answer": _format_recipe_text(recipe),
        "follow_ups": fu,
        "recipe": recipe,
    }


def build_macro_recipe(targets: dict | None = None, diets: list[str] | None = None,
                       course: str | None = None, query: str | None = None,
                       units: str = "metric") -> dict:
    """Recipe Lab: generate a custom recipe aimed at per-serving macro targets +
    diets + course, seeded by an optional text query. Returns the recipe (with
    Claude's quantity-based nutrition), a trained-model cross-check, and a fit-to-
    target summary."""
    key = _api_key()
    if not key:
        return {"error": "no_key", "answer": "Add an ANTHROPIC_API_KEY to generate recipes."}
    targets = targets or {}
    diets = diets or []
    seed = (query or "").strip()
    try:
        import rag
        grounding = rag.grounding_block(
            seed or " ".join([course or ""] + diets).strip())
    except Exception:
        grounding = ""

    goal = []
    for k, lab in (("calories", "kcal"), ("protein_g", "g protein"),
                   ("carbs_g", "g carbs"), ("fat_g", "g fat")):
        if targets.get(k):
            goal.append(f"~{targets[k]} {lab}")
    bits = []
    if seed:
        bits.append(f"theme/ingredient focus: {seed}")
    if course and course != "Any":
        bits.append(f"course: {course}")
    if diets:
        bits.append("must comply with diets: " + ", ".join(diets))
    if goal:
        bits.append("per-serving nutrition targets: " + ", ".join(goal))
    user = "Create a single recipe. " + ("; ".join(bits) if bits else "Cook's choice.")
    directive = (
        "This request comes from Recipe Lab: the cook set per-serving nutrition "
        "targets and constraints. Respect the diets STRICTLY (use no disallowed "
        "ingredients). Aim to land the per-serving nutrition as close to the "
        "targets as possible; if a target is not achievable, get close and note "
        "the trade-off in one calm line in the intro. Pick sensible servings.")
    try:
        reply = _build_recipe([{"role": "user", "content": user}], key, units,
                              grounding, extra_directive=directive)
    except Exception as exc:
        return {"error": exc.__class__.__name__,
                "answer": "I hit a snag building that recipe. Try again in a moment."}

    recipe = reply.get("recipe", {})
    if course and course != "Any":
        recipe["course"] = course
        recipe["nutrition_model"] = _model_nutrition(recipe)
    reply["fit"] = _macro_fit(targets, recipe.get("nutrition"))
    reply["targets"] = targets
    return reply


def _ask_claude(messages: list[dict], key: str, units: str = "metric",
                grounding: str = "") -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    system = SYSTEM_PROMPT + "\n\n" + _UNITS.get(units, _UNITS["metric"])
    if grounding:
        system += ("\n\nGround your answer in these real recipes from our "
                   "database when relevant; prefer them over guessing. Do NOT paste "
                   "URLs or recipe links in your answer.\n" + grounding)
    system += ("\n\nIf the cook mentions a dish they could cook (or you reference a "
               "recipe), DON'T describe a full recipe or link to one in the answer — "
               "instead set recipe_suggestion to a short 'Make <dish>' phrase so they "
               "can tap the recipe button and get it in-app. Otherwise leave "
               "recipe_suggestion empty.")
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
        "recipe_suggestion": data.get("recipe_suggestion", "").strip(),
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
