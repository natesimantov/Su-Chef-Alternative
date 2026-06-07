"""Recipe knowledge search.

In production this is hybrid search (ChromaDB meaning + BM25 keyword) over the
cleaned Kaggle corpus. That needs the corpus ingested and an embedding model, so
until then this module ships a small built-in set of grounded base recipes and
matches on keywords. The interface (`search_recipe(intent) -> Recipe | None`) is
stable, so swapping in ChromaDB later doesn't touch callers.
"""

from __future__ import annotations

from shared.models import Difficulty, Ingredient, Recipe, Step, StepTimer

# --- Built-in grounded base recipes (stand-in for the Kaggle corpus) ---------


def _risotto() -> Recipe:
    return Recipe(
        title="Mushroom Risotto",
        servings=2,
        total_time_min=45,
        difficulty=Difficulty.intermediate,
        summary="A creamy, comforting risotto with golden sautéed mushrooms.",
        heads_up=[
            "Mise en place is key. Chop everything first — risotto needs constant "
            "attention once you start.",
            "Keep your stock hot. Cold stock slows cooking and ruins the creamy "
            "texture.",
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
            Step(title="Mise en place",
                 instruction="Chop the onion, garlic, and mushrooms. Grate the "
                 "parmesan. Have everything within reach before any heat.",
                 why="Risotto demands constant stirring — there's no time to chop "
                 "mid-cook."),
            Step(title="Heat the stock",
                 instruction="Bring the stock to a gentle simmer, then keep it hot "
                 "on low.",
                 why="Cold stock shocks the rice and stalls the cook."),
            Step(title="Sauté the mushrooms until golden brown.",
                 instruction="Heat oil in the wide pan and sauté the mushrooms in a "
                 "single layer until deeply golden.",
                 why="They should shrink significantly and release their juices. Do "
                 "not overcrowd the pan.",
                 timer=StepTimer(label="Mushrooms", duration_sec=8 * 60)),
            Step(title="Soften the aromatics",
                 instruction="Lower the heat, add the onion and garlic, and cook "
                 "until soft and translucent.",
                 why="Sweating, not browning — a sweet base, not bitterness.",
                 timer=StepTimer(label="Aromatics", duration_sec=5 * 60)),
            Step(title="Toast the rice",
                 instruction="Add the Arborio and stir until the edges turn "
                 "translucent.",
                 why="Toasting keeps the grain al dente instead of mushy.",
                 timer=StepTimer(label="Rice toasting", duration_sec=2 * 60)),
            Step(title="Deglaze with wine",
                 instruction="Pour in the wine and stir until almost fully absorbed.",
                 why="Alcohol cooks off and lifts the fond, leaving brightness."),
            Step(title="Add stock, a ladle at a time",
                 instruction="Add hot stock one ladle at a time, stirring, waiting "
                 "for each to absorb before the next.",
                 why="Slow addition coaxes out the starch — that's the creaminess.",
                 timer=StepTimer(label="Stock stage", duration_sec=18 * 60)),
            Step(title="Mantecatura & serve",
                 instruction="Off the heat, beat in the parmesan and a knob of "
                 "butter. Rest two minutes, then plate.",
                 why="Resting off-heat emulsifies the fat for a glossy finish."),
        ],
    )


def _pizza() -> Recipe:
    return Recipe(
        title="Neapolitan Pizza (poolish)",
        servings=4,
        total_time_min=90,
        difficulty=Difficulty.advanced,
        summary="Blistered, airy Neapolitan pizza built on an overnight poolish.",
        heads_up=[
            "Start the poolish the night before — it needs 12–16 hours.",
            "Your oven is the limit. Get it as hot as it goes with a stone or steel "
            "preheated 45+ minutes.",
        ],
        ingredients=[
            Ingredient(item="00 Flour", amount="500g"),
            Ingredient(item="Water", amount="325ml"),
            Ingredient(item="Fresh Yeast", amount="3g"),
            Ingredient(item="Salt", amount="10g"),
            Ingredient(item="San Marzano Tomatoes", amount="400g"),
            Ingredient(item="Fresh Mozzarella (torn)", amount="250g"),
            Ingredient(item="Fresh Basil", amount="1 handful"),
        ],
        equipment=[
            "Pizza stone or steel",
            "Large mixing bowl",
            "Bench scraper",
            "Peel (or flat tray)",
        ],
        steps=[
            Step(title="Make the poolish (night before)",
                 instruction="Mix half the flour, half the water, and the yeast. "
                 "Cover and rest 12–16h at room temperature.",
                 why="The long ferment builds flavour and extensibility you can't "
                 "rush.",
                 timer=StepTimer(label="Poolish", duration_sec=12 * 60 * 60)),
            Step(title="Final dough",
                 instruction="Combine poolish with remaining flour, water, and salt. "
                 "Knead until smooth.",
                 why="Gluten development now gives the cornicione its structure."),
            Step(title="Bulk & ball",
                 instruction="Bulk rise 2 hours, then divide into 250g balls and "
                 "proof.",
                 why="Even balls bake into even, round pies.",
                 timer=StepTimer(label="Bulk rise", duration_sec=2 * 60 * 60)),
            Step(title="Stretch & top",
                 instruction="Gently stretch a ball leaving the rim thick. Top "
                 "sparingly with sauce, mozzarella, basil.",
                 why="Overloading makes a soggy centre — restraint bakes better."),
            Step(title="Bake hot & fast",
                 instruction="Slide onto the screaming-hot stone and bake until the "
                 "crust is leopard-spotted.",
                 why="High heat sets the rim before the base dries out.",
                 timer=StepTimer(label="Bake", duration_sec=90)),
        ],
    )


def _generic(intent: str) -> Recipe:
    return Recipe(
        title=intent.strip().title() or "Quick Dish",
        servings=2,
        total_time_min=30,
        difficulty=Difficulty.easy,
        summary=f"A simple take on “{intent.strip()}”.",
        heads_up=["Taste as you go and adjust seasoning at the end."],
        ingredients=[
            Ingredient(item="Main ingredient", amount="to taste"),
            Ingredient(item="Olive oil", amount="2 tbsp"),
            Ingredient(item="Salt & pepper", amount="to taste"),
        ],
        equipment=["Pan", "Knife", "Cutting board"],
        steps=[
            Step(title="Prep",
                 instruction="Gather and prep your ingredients.",
                 why="Mise en place keeps the cook calm."),
            Step(title="Cook",
                 instruction="Cook over medium heat until done.",
                 why="Medium heat gives you control.",
                 timer=StepTimer(label="Cook", duration_sec=10 * 60)),
            Step(title="Finish & serve",
                 instruction="Season, plate, and serve.",
                 why="Final seasoning makes the dish."),
        ],
    )


def search_recipe(intent: str) -> Recipe | None:
    """Return a grounded base recipe for a loose intent, or None if unmatched.

    The deterministic fallback crew uses None to trigger the generic template.
    """
    text = intent.lower()
    if "pizza" in text:
        return _pizza()
    if "risotto" in text or "mushroom" in text:
        return _risotto()
    return None
