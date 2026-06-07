"""The Su Chef recipe contract — the single shape every recipe takes.

This is the boundary between the CrewAI crew (producer) and the Streamlit UI
(consumer). Both sides import from here so neither blocks the other; they only
need to agree on this file.

Fields use snake_case in Python but serialize to the camelCase names from the
product definition (totalTimeMin, headsUp, dietaryFlags, substituteFor, ...),
so the on-disk / on-wire JSON matches the documented contract exactly. Dump with
`recipe.model_dump(by_alias=True)` and load with `Recipe.model_validate(data)`.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Shared model config: allow constructing by Python name *or* camelCase alias.
_config = ConfigDict(populate_by_name=True)


class Difficulty(str, Enum):
    easy = "Easy"
    intermediate = "Intermediate"
    advanced = "Advanced"


class Ingredient(BaseModel):
    """One line on the ingredient list. `substitute_for` is set when the crew
    swapped something out (e.g. for an allergy or a shortage)."""

    model_config = _config

    item: str
    amount: str
    substitute_for: Optional[str] = Field(default=None, alias="substituteFor")


class StepTimer(BaseModel):
    """A timer a step can offer. The app runs it on the device; the recipe only
    declares it."""

    model_config = _config

    label: str
    duration_sec: int = Field(alias="durationSec")


class Step(BaseModel):
    """One cook-mode step: what to do, why it matters, and an optional timer."""

    model_config = _config

    title: str
    instruction: str
    why: Optional[str] = None
    timer: Optional[StepTimer] = None


class DietaryFlag(BaseModel):
    """A note the Dietary & Safety Guardian attaches to the recipe.

    kind is one of: "allergen" (present in the dish), "substitution" (something
    was swapped/removed), or "profile" (a saved profile was applied).
    """

    model_config = _config

    kind: str
    message: str


class Recipe(BaseModel):
    """The locked recipe contract the crew produces and the UI renders."""

    model_config = _config

    title: str
    servings: int
    total_time_min: int = Field(alias="totalTimeMin")
    difficulty: Difficulty
    summary: str

    heads_up: list[str] = Field(default_factory=list, alias="headsUp")
    dietary_flags: list[DietaryFlag] = Field(default_factory=list, alias="dietaryFlags")
    ingredients: list[Ingredient] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)


# --- Profiles & session memory (local JSON; Phase 2 syncs via MCP) -----------


class Profile(BaseModel):
    """A person the cook cooks for. Free text — no forms, no dropdowns. The
    Dietary & Safety Guardian interprets `notes` (allergies, dislikes, etc.)."""

    model_config = _config

    name: str
    notes: str


class SessionLog(BaseModel):
    """A brief log written at the end of a cooking session and read at the start
    of the next one (the lightweight memory layer, not a separate agent)."""

    model_config = _config

    dish: str
    questions_asked: list[str] = Field(default_factory=list, alias="questionsAsked")
    rescues: list[str] = Field(default_factory=list)
    adaptations: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
