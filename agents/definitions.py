"""The five CrewAI agents and their flow (the real-LLM path).

This module is only imported when an ANTHROPIC_API_KEY is present and crewai is
installed (see agents/crew.py). To stay robust, the crew is *grounded* by our own
deterministic tools: the base recipe from knowledge_search and the allergen
conflicts from allergen_check are injected into the task context, so the agents
reason over real data rather than inventing numbers.

The Head Chef's task emits the locked recipe as `shared.models.Recipe`
(validated via output_pydantic).
"""

from __future__ import annotations

import os

from crewai import LLM, Agent, Crew, Process, Task

from shared.models import Profile, Recipe
from tools.allergen_check import allergen_check
from tools.knowledge_search import search_recipe


def _llm() -> LLM:
    model = os.environ.get("SU_CHEF_MODEL", "anthropic/claude-sonnet-4-6")
    return LLM(model=model, temperature=0.3)


def _agents(llm: LLM) -> dict[str, Agent]:
    return {
        "recipe_builder": Agent(
            role="Recipe Builder",
            goal="Retrieve the grounded base recipe and sequence, scale, and time "
                 "the steps into a coherent plan.",
            backstory="A meticulous line cook who turns a grounded source recipe "
                      "and the cook's constraints into ordered, realistically timed "
                      "steps. Never invents quantities the source didn't support.",
            llm=llm, verbose=False, allow_delegation=False),
        "food_scientist": Agent(
            role="Food Scientist",
            goal="Add the why: reactions, doneness cues, and before-you-start "
                 "warnings for each step.",
            backstory="Explains the chemistry — why acidic sauce shouldn't sit in "
                      "reactive cast iron, what 'golden brown' actually looks like.",
            llm=llm, verbose=False, allow_delegation=False),
        "dietitian_safety": Agent(
            role="Dietitian and Safety",
            goal="Audit the recipe against the active profile for allergens, "
                 "dietary fit, and high-stakes safety. Substitute or remove "
                 "offending items and record every change. Never silently skip an "
                 "allergen; never claim a dish is 'safe'.",
            backstory="A careful dietitian who records safety notes as their own "
                      "section, so this role can later split into a dedicated agent "
                      "without changing the contract.",
            llm=llm, verbose=False, allow_delegation=False),
        "equipment_validator": Agent(
            role="Equipment Validator",
            goal="Check the recipe against the tools and ingredients the cook has, "
                 "and adapt for shortages or the wrong pan size.",
            backstory="Knows a 24cm and a 26cm pan change bake time, and adapts "
                      "rather than failing when something's missing.",
            llm=llm, verbose=False, allow_delegation=False),
        "head_chef": Agent(
            role="Head Chef",
            goal="Coordinate the others and assemble everything into the final "
                 "recipe that matches the contract exactly.",
            backstory="The lead who turns the specialists' work into one clean, "
                      "trustworthy recipe.",
            llm=llm, verbose=False, allow_delegation=True),
    }


def build_crew(intent: str, profile: Profile | None, servings: int | None) -> Crew:
    llm = _llm()
    a = _agents(llm)

    base = search_recipe(intent)
    grounding = (
        base.model_dump_json(by_alias=True, indent=2) if base
        else "No close match in the knowledge base; build a sensible recipe and say "
             "so honestly."
    )
    profile_block = (
        f"Cooking for {profile.name}. Profile (free text): {profile.notes!r}."
        if profile else "No specific profile to apply."
    )
    conflicts = (
        allergen_check(base.ingredients, profile.notes)
        if (base and profile) else []
    )
    conflict_block = (
        "\n".join(f"- {c.ingredient}: {c.reason} (flagged by: {c.profile_term})"
                  for c in conflicts)
        or "No conflicts detected by the deterministic allergen tool."
    )
    serving_block = f"Scale to {servings} servings." if servings else \
        "Keep the source's serving count unless the request implies otherwise."

    build = Task(
        description=f"Cook's request: {intent!r}.\n{serving_block}\n\n"
                    f"Grounded base recipe (JSON):\n{grounding}",
        expected_output="A draft recipe: title, servings, total time, difficulty, "
                        "ordered steps with timings.",
        agent=a["recipe_builder"])
    science = Task(
        description="Add a clear 'why' to every step plus before-you-start warnings "
                    "(headsUp). Keep doneness cues concrete and qualitative — no fake "
                    "precision.",
        expected_output="The recipe with per-step 'why' and a headsUp list.",
        agent=a["food_scientist"], context=[build])
    diet = Task(
        description=f"{profile_block}\n\nThe deterministic allergen tool reported:\n"
                    f"{conflict_block}\n\nSubstitute or remove every conflicting "
                    "ingredient, set substituteFor on swaps, and add a dietaryFlags "
                    "entry for each change and for the profile applied. Never claim "
                    "'safe' — say 'no conflicts found based on the profile'.",
        expected_output="The recipe with conflicts resolved and dietaryFlags filled.",
        agent=a["dietitian_safety"], context=[science])
    equip = Task(
        description="Sanity-check equipment and core ingredients; note any "
                    "adaptations for shortages or wrong pan sizes in headsUp.",
        expected_output="The recipe with equipment validated.",
        agent=a["equipment_validator"], context=[diet])
    assemble = Task(
        description="Assemble the final locked recipe. It MUST match the contract "
                    "exactly (title, servings, totalTimeMin, difficulty, summary, "
                    "headsUp[], dietaryFlags[], ingredients[], equipment[], steps[]).",
        expected_output="The final recipe as the Recipe schema.",
        agent=a["head_chef"], context=[build, science, diet, equip],
        output_pydantic=Recipe)

    return Crew(
        agents=list(a.values()),
        tasks=[build, science, diet, equip, assemble],
        process=Process.sequential,
        verbose=False,
    )


def run_crew(intent: str, profile: Profile | None, servings: int | None) -> Recipe:
    """Run the real crew and return the validated Recipe contract."""
    result = build_crew(intent, profile, servings).kickoff()
    if getattr(result, "pydantic", None) is not None:
        return result.pydantic
    # Last resort: parse the raw JSON the head chef emitted.
    return Recipe.model_validate_json(str(result))
