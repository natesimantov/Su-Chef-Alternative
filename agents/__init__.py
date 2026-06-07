"""The Su Chef crew (CrewAI).

Five agents do the deep thinking once, at definition time, and output a single
locked recipe contract:

  1. Recipe Builder       — grounded base recipe; sequence, scale, time
  2. Food Scientist       — the why, doneness cues, before-you-start warnings
  3. Dietitian & Safety   — nutrition, allergens, dietary fit, safety calls
  4. Equipment Validator  — checks tools/ingredients; adapts for shortages
  5. Head Chef (lead)     — coordinates the four and assembles the contract

`define_recipe()` is the single entry point. It runs the real CrewAI flow when
an ANTHROPIC_API_KEY is present and crewai is installed; otherwise it uses a
deterministic fallback so the app is fully demoable with no key.
"""

from agents.crew import define_recipe

__all__ = ["define_recipe"]
