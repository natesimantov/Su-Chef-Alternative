"""Allergen & dietary check — deterministic lookup, never a guess.

Given an ingredient list and a free-text profile, returns conflicts: allergens
present, hard dislikes, and hidden sources (e.g. soy sauce contains gluten).

Honest-about-limits: this is only as good as the table and the profile text. It
never claims a dish is "safe" — callers should say "no conflicts found based on
your profile" and always surface what was checked.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.models import Ingredient

# Allergen/diet keyword -> ingredient substrings that trigger it (incl. hidden
# sources). Lowercased substring match.
_ALLERGEN_SOURCES: dict[str, list[str]] = {
    "gluten": ["flour", "wheat", "bread", "pasta", "soy sauce", "couscous", "barley"],
    "dairy": ["milk", "butter", "cheese", "cream", "parmesan", "yogurt", "ghee"],
    "lactose": ["milk", "butter", "cheese", "cream", "parmesan", "yogurt"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "clam", "mussel", "oyster"],
    "nut": ["almond", "walnut", "pecan", "cashew", "hazelnut", "pistachio", "peanut"],
    "peanut": ["peanut"],
    "soy": ["soy", "tofu", "edamame", "miso"],
    "egg": ["egg"],
    "fish": ["salmon", "tuna", "cod", "anchovy", "fish sauce"],
    "sesame": ["sesame", "tahini"],
}

# Non-allergen hard dislikes worth catching as plain substrings.
_DISLIKE_KEYWORDS = [
    "garlic", "onion", "cilantro", "coriander", "mushroom", "olive",
    "spicy", "chili", "chilli", "shellfish",
]

# Words in a profile that introduce a restriction.
_RESTRICTION_CUES = ["no ", "not ", "avoid", "allerg", "intoleran", "free", "hate",
                     "dislike", "doesn't like", "without", "can't", "cannot"]

_DIET_KEYWORDS = {
    "vegetarian": ["chicken", "beef", "pork", "fish", "shrimp", "bacon", "anchovy",
                   "salmon", "tuna", "lamb", "gelatin"],
    "vegan": ["chicken", "beef", "pork", "fish", "shrimp", "bacon", "milk", "butter",
              "cheese", "cream", "egg", "honey", "parmesan", "yogurt"],
}


@dataclass
class AllergenConflict:
    ingredient: str       # the offending ingredient line
    reason: str           # what triggered it (e.g. "gluten (hidden in soy sauce)")
    profile_term: str     # the phrase in the profile that flagged it


def _profile_terms(notes: str) -> list[str]:
    """Pull restriction-bearing fragments out of free-text profile notes."""
    text = notes.lower()
    terms: list[str] = []
    # split on commas/semicolons; keep fragments that look like a restriction
    for frag in [f.strip() for f in text.replace(";", ",").split(",")]:
        if not frag:
            continue
        if any(cue in frag for cue in _RESTRICTION_CUES) or frag in _DIET_KEYWORDS:
            terms.append(frag)
        elif frag in ("vegetarian", "vegan"):
            terms.append(frag)
    return terms


def allergen_check(
    ingredients: list[Ingredient], profile_notes: str
) -> list[AllergenConflict]:
    """Return any conflicts between the ingredient list and a profile's notes."""
    conflicts: list[AllergenConflict] = []
    items = [(ing.item, ing.item.lower()) for ing in ingredients]

    for term in _profile_terms(profile_notes):
        # Diet (vegetarian/vegan) — expand to a set of banned substrings
        for diet, banned in _DIET_KEYWORDS.items():
            if diet in term:
                for orig, low in items:
                    hit = next((b for b in banned if b in low), None)
                    if hit:
                        conflicts.append(
                            AllergenConflict(orig, f"{diet}: contains {hit}", term)
                        )

        # Named allergens (incl. hidden sources)
        for allergen, sources in _ALLERGEN_SOURCES.items():
            if allergen in term:
                for orig, low in items:
                    hit = next((s for s in sources if s in low), None)
                    if hit:
                        reason = allergen if hit in (allergen, allergen + "s") else \
                            f"{allergen} (in {hit})"
                        conflicts.append(AllergenConflict(orig, reason, term))

        # Plain dislikes / simple ingredients named directly in the term
        for kw in _DISLIKE_KEYWORDS:
            if kw in term:
                for orig, low in items:
                    if kw in low:
                        conflicts.append(
                            AllergenConflict(orig, f"contains {kw}", term)
                        )

    # de-dup by (ingredient, reason)
    seen: set[tuple[str, str]] = set()
    unique: list[AllergenConflict] = []
    for c in conflicts:
        key = (c.ingredient, c.reason)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique
