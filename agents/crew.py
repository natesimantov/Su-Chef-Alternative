"""Crew entry point — `define_recipe()`.

Runs the real 5-agent CrewAI flow when possible, and a deterministic fallback
otherwise, so the app produces a valid recipe contract with or without an API
key. This mirrors the design note that "the crew can fall back to a simpler path
under load."
"""

from __future__ import annotations

import os
import re

from shared.models import Profile, Recipe
from agents.dietitian_safety import apply_dietary
from tools import knowledge_search as ks
from tools.culinary_math import scale_ingredients


def _parse_servings(intent: str) -> int | None:
    """Pull a serving count out of a loose intent ('for two', 'for 6')."""
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "eight": 8}
    m = re.search(r"for\s+(\d+)", intent.lower())
    if m:
        return int(m.group(1))
    for word, n in words.items():
        if re.search(rf"for\s+{word}\b", intent.lower()):
            return n
    return None


def _fallback(intent: str, profile: Profile | None, servings: int | None) -> Recipe:
    """Deterministic assembly using the grounded base recipe + our tools."""
    base = ks.search_recipe(intent) or ks._generic(intent)

    target = servings or _parse_servings(intent)
    if target and target != base.servings:
        base = base.model_copy(update={
            "servings": target,
            "ingredients": scale_ingredients(base.ingredients, base.servings, target),
        })

    recipe, flags = apply_dietary(base, profile)
    return recipe.model_copy(update={"dietary_flags": flags})


def define_recipe(
    intent: str,
    profile: Profile | None = None,
    servings: int | None = None,
    *,
    force_fallback: bool = False,
) -> Recipe:
    """Turn a loose intent (+ optional profile/servings) into a locked Recipe."""
    if not force_fallback and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from agents import definitions  # imported lazily; needs crewai installed
            return definitions.run_crew(intent, profile, servings)
        except Exception as exc:  # honest fallback on any failure
            print(f"[crew] real path unavailable ({exc!r}); using fallback")
    return _fallback(intent, profile, servings)
