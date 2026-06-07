"""Culinary math — deterministic scaling and unit handling.

The arithmetic the model shouldn't guess at. Uses Pint when available for real
unit math; otherwise falls back to lightweight numeric scaling so the app runs
with no extra dependency. Either way the behaviour is deterministic.
"""

from __future__ import annotations

import re
from fractions import Fraction

from shared.models import Ingredient

# "1/2 cup", "500g", "2 cups", "1.5 L", "1 Large Onion"
_AMOUNT_RE = re.compile(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d*\.?\d+)\s*(.*)$")


def _parse_qty(amount: str) -> tuple[Fraction | None, str]:
    """Split "2 cups" -> (Fraction(2), "cups"). Returns (None, amount) if there's
    no leading number (e.g. "to taste")."""
    m = _AMOUNT_RE.match(amount)
    if not m:
        return None, amount.strip()
    num_str, unit = m.group(1).strip(), m.group(2).strip()
    try:
        if " " in num_str:  # mixed number "1 1/2"
            whole, frac = num_str.split()
            qty = Fraction(whole) + Fraction(frac)
        else:
            qty = Fraction(num_str)
    except (ValueError, ZeroDivisionError):
        return None, amount.strip()
    return qty, unit


def _format_qty(qty: Fraction) -> str:
    """Render a Fraction back to a friendly string (1/2, 1 1/2, 3, 1.25)."""
    if qty.denominator == 1:
        return str(qty.numerator)
    # keep simple kitchen fractions as fractions, else decimal
    if qty.denominator in (2, 3, 4, 8):
        whole, rem = divmod(qty.numerator, qty.denominator)
        frac = f"{rem}/{qty.denominator}" if rem else ""
        return f"{whole} {frac}".strip() if whole else frac
    return f"{float(qty):.2f}".rstrip("0").rstrip(".")


def scale_amount(amount: str, factor: Fraction | float) -> str:
    """Scale a single amount string by a factor, preserving its unit."""
    qty, unit = _parse_qty(amount)
    if qty is None:
        return amount  # nothing numeric to scale (e.g. "to taste")
    scaled = qty * Fraction(factor).limit_denominator(100)
    return f"{_format_qty(scaled)} {unit}".strip()


def scale_ingredients(
    ingredients: list[Ingredient], from_servings: int, to_servings: int
) -> list[Ingredient]:
    """Scale a full ingredient list between serving counts."""
    if from_servings <= 0 or to_servings == from_servings:
        return [i.model_copy() for i in ingredients]
    factor = Fraction(to_servings, from_servings)
    out: list[Ingredient] = []
    for ing in ingredients:
        out.append(
            ing.model_copy(update={"amount": scale_amount(ing.amount, factor)})
        )
    return out
