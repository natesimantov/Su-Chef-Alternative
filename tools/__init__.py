"""Backend tools the agents call.

These live inside our own backend (we own them), so they are plain function
tools, not MCP. All are deterministic and run without any API key — the model
shouldn't guess at arithmetic or allergen cross-reactions.
"""

from tools.allergen_check import AllergenConflict, allergen_check
from tools.culinary_math import scale_amount, scale_ingredients
from tools.profile_store import load_profiles, save_profiles

__all__ = [
    "allergen_check",
    "AllergenConflict",
    "scale_amount",
    "scale_ingredients",
    "load_profiles",
    "save_profiles",
]
