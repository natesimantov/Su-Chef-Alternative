# Model Card — Nutrition Estimator

## Model purpose
Estimates a recipe's **per-serving nutrition** (calories, protein, carbs, fat)
from its ingredient list and structure (ingredient text, number of ingredients,
servings, course, cuisine). Used in Su Chef as the learned estimator shown in
About and as a cross-check on generated recipes. Real recipes always display
their measured nutrition; the model fills the gap only for novel recipes.

## Training data summary
~38054 recipes with real, computed nutrition from the Edamam
"recipes-with-nutrition" dataset (Western/American-leaning). Targets are
per-serving values (recipe total / servings). Features: ingredient text
(TF-IDF, 600 terms), num_ingredients, servings, course, cuisine (one-hot).

## Metrics (held-out 20% test set, seed 42)
- Best model: **HistGradientBoosting** (mean R² **0.521** vs mean-baseline 0.0)
- **calories**: R² 0.52, MAE 129.8
- **protein_g**: R² 0.607, MAE 6.3
- **carbs_g**: R² 0.485, MAE 15.0
- **fat_g**: R² 0.473, MAE 8.8
Two models (Ridge, HistGradientBoosting) plus a mean baseline were compared; see
`evaluation_report.md`.

## Limitations
- The model reads ingredient **names**, not exact quantities, so it is an
  approximation. For generated recipes the app prefers a quantity-based estimate
  and uses this model as a cross-check.
- The training nutrition values are themselves Edamam estimates, not lab data.
- The corpus skews Western/American, so it may generalise poorly to other cuisines.

## Ethical considerations
- Nutrition figures are estimates and **not medical or dietary advice**; people
  with medical dietary needs should not rely on them.
- No personal data is used; predictions are about recipes, not people.
- Diet tags are heuristic and may mislabel edge cases; treat them as a guide.
