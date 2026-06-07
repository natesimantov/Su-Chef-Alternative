"""Mock data so the UI runs before the crew exists.

The Mushroom Risotto here matches the Stitch mockups (8 steps, step 3 is the
golden-brown saute with an 8:00 timer). Swap this out for real crew output once
agents/ produces a validated Recipe.
"""

from __future__ import annotations

from shared.models import (
    Difficulty,
    Ingredient,
    Profile,
    Recipe,
    Step,
    StepTimer,
)

SAMPLE_PROFILES: list[Profile] = [
    Profile(name="My wife", notes="no garlic, light dishes, no shellfish"),
    Profile(name="My kids", notes="no spicy food, love pasta, one lactose intolerant"),
    Profile(name="Guest", notes="vegetarian, nut allergy"),
]

SAMPLE_RECIPE = Recipe(
    title="Mushroom Risotto",
    servings=2,
    total_time_min=45,
    difficulty=Difficulty.intermediate,
    summary="A creamy, comforting risotto with golden sautéed mushrooms.",
    heads_up=[
        "Mise en place is key. Chop everything first — risotto needs constant "
        "attention once you start.",
        "Keep your stock hot. Adding cold stock to hot rice slows cooking and ruins "
        "the creamy texture.",
    ],
    ingredients=[
        Ingredient(item="Mixed Mushrooms (sliced)", amount="500g"),
        Ingredient(item="Arborio rice", amount="2 cups"),
        Ingredient(item="Chicken or Vegetable Stock (hot)", amount="1L"),
        Ingredient(item="Large Onion (finely diced)", amount="1"),
        Ingredient(item="Garlic (minced)", amount="2 cloves"),
        Ingredient(item="Dry White Wine", amount="1/2 cup"),
        Ingredient(item="Parmesan Cheese (grated)", amount="1 cup"),
    ],
    equipment=[
        "Large, wide saucepan or Dutch oven",
        "Medium saucepan (for stock)",
        "Sturdy wooden spoon",
        "Ladle",
    ],
    steps=[
        Step(
            title="Mise en place",
            instruction="Chop the onion, garlic, and mushrooms. Grate the parmesan. "
            "Have everything within reach before any heat goes on.",
            why="Risotto demands constant stirring once it starts — there's no "
            "time to chop mid-cook.",
        ),
        Step(
            title="Heat the stock",
            instruction="Bring the stock to a gentle simmer in the medium saucepan, "
            "then keep it hot on low.",
            why="Cold stock shocks the rice and stalls the cook.",
        ),
        Step(
            title="Sauté the mushrooms until golden brown.",
            instruction="Heat oil in the wide pan and sauté the mushrooms in a "
            "single layer until deeply golden.",
            why="They should shrink significantly and release their juices. Do not "
            "overcrowd the pan.",
            timer=StepTimer(label="Mushrooms", duration_sec=8 * 60),
        ),
        Step(
            title="Soften the aromatics",
            instruction="Lower the heat, add the onion and garlic, and cook until "
            "soft and translucent.",
            why="Sweating, not browning — you want a sweet base, not bitterness.",
            timer=StepTimer(label="Aromatics", duration_sec=5 * 60),
        ),
        Step(
            title="Toast the rice",
            instruction="Add the Arborio and stir for a minute or two until the edges "
            "turn translucent.",
            why="Toasting sets the grain so it stays al dente instead of turning to mush.",
            timer=StepTimer(label="Rice toasting", duration_sec=2 * 60),
        ),
        Step(
            title="Deglaze with wine",
            instruction="Pour in the white wine and stir until it has almost fully "
            "absorbed.",
            why="The alcohol cooks off and lifts the fond, leaving brightness behind.",
        ),
        Step(
            title="Add stock, a ladle at a time",
            instruction="Add hot stock one ladle at a time, stirring, waiting until "
            "each addition absorbs before the next.",
            why="Slow addition coaxes the starch out gradually — that's the creaminess.",
            timer=StepTimer(label="Stock stage", duration_sec=18 * 60),
        ),
        Step(
            title="Mantecatura & serve",
            instruction="Off the heat, beat in the parmesan and a knob of butter. Rest "
            "two minutes, then plate.",
            why="Resting off-heat emulsifies the fat for a glossy, loose finish.",
        ),
    ],
)
