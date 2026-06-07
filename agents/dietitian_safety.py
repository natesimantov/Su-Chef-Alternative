"""Dietitian & Safety agent logic (deterministic core).

Reads the active profile, audits the full ingredient list via the allergen_check
tool, and either substitutes/removes offending ingredients or flags what it
can't safely swap. It never silently skips an allergen — every action becomes a
DietaryFlag the cook can see.

This deterministic core is what runs in the fallback path and is also the source
of truth the real CrewAI agent is instructed to follow.
"""

from __future__ import annotations

from shared.models import DietaryFlag, Ingredient, Profile, Recipe
from tools.allergen_check import AllergenConflict, allergen_check


def _substitute(ingredient: Ingredient, conflict: AllergenConflict) -> Ingredient | None:
    """Return a safe replacement for an offending ingredient, or None to remove
    it. None of these are guesses — they're a fixed swap table."""
    low = ingredient.item.lower()
    reason = conflict.reason.lower()

    if "lactose" in reason or "dairy" in reason or (
        "vegan" in reason and any(d in low for d in
                                  ("cheese", "parmesan", "butter", "cream", "milk"))
    ):
        if "parmesan" in low or "cheese" in low:
            return ingredient.model_copy(update={
                "item": "Nutritional yeast", "substitute_for": ingredient.item})
        if "butter" in low:
            return ingredient.model_copy(update={
                "item": "Olive oil", "substitute_for": ingredient.item})
        return None  # remove other dairy

    if "vegetarian" in reason or "vegan" in reason:
        if "stock" in low or "broth" in low:
            return ingredient.model_copy(update={
                "item": "Vegetable Stock (hot)", "substitute_for": ingredient.item})
        return None  # remove meat / fish

    # Garlic, shellfish, nuts, plain dislikes: remove (no safe 1:1 swap here)
    return None


def apply_dietary(
    recipe: Recipe, profile: Profile | None
) -> tuple[Recipe, list[DietaryFlag]]:
    """Audit and adjust a recipe against a profile. Returns the adjusted recipe
    and the dietary flags describing every change + what was checked."""
    if profile is None:
        return recipe, []

    conflicts = allergen_check(recipe.ingredients, profile.notes)
    flags: list[DietaryFlag] = [
        DietaryFlag(kind="profile",
                    message=f"Applied {profile.name}'s profile: “{profile.notes}”.")
    ]

    if not conflicts:
        flags.append(DietaryFlag(
            kind="profile",
            message=f"No conflicts found in this recipe based on {profile.name}'s "
                    "profile. Please still verify yourself."))
        return recipe, flags

    by_item: dict[str, AllergenConflict] = {}
    for c in conflicts:
        by_item.setdefault(c.ingredient, c)

    new_ingredients: list[Ingredient] = []
    extra_heads_up: list[str] = []
    for ing in recipe.ingredients:
        conflict = by_item.get(ing.item)
        if conflict is None:
            new_ingredients.append(ing)
            continue
        sub = _substitute(ing, conflict)
        if sub is not None:
            new_ingredients.append(sub)
            flags.append(DietaryFlag(
                kind="substitution",
                message=f"Swapped {ing.item} → {sub.item} ({conflict.reason})."))
        else:
            flags.append(DietaryFlag(
                kind="allergen",
                message=f"Removed {ing.item} ({conflict.reason})."))
            extra_heads_up.append(
                f"{ing.item} was removed for {profile.name} — {conflict.reason}.")

    adjusted = recipe.model_copy(update={
        "ingredients": new_ingredients,
        "heads_up": recipe.heads_up + extra_heads_up,
    })
    return adjusted, flags
