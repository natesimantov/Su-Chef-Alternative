# Recipe Dataset — Business Insights

**Dataset:** 7938 cleaned recipes (Kaggle "food_recipes").

## Headline findings
- **Ratings are almost meaningless as a target.** Mean rating is
  4.889 with std 0.077 — nearly every recipe
  scores ~4.9. So we do **not** predict rating; we predict **how long a recipe
  takes** (a "quick vs involved" classifier), which has real variance.
- **Typical recipe takes ~40 minutes** (median);
  mean 57 min.
- **81% of recipes are vegetarian** — the corpus skews
  Indian home cooking (top cuisine: Indian, top course:
  Lunch).

## What drives cooking time
Correlation of each feature with total time:
- **time_cue_count**: 0.184
- **num_steps**: 0.159
- **instr_len**: 0.201
- **num_ingredients**: 0.057
- **ingr_len**: 0.066
- **desc_len**: 0.051
- **vote_count**: 0.029
- **rating**: -0.031

The strongest signals are **instruction length**, **time-cue words**
(e.g. "marinate", "soak", "overnight", "bake"), and **number of steps** —
i.e. *how involved the method is*, more than how many ingredients there are.

## Business takeaway
A cook can be told up-front whether a recipe is a quick weeknight option or a
longer project, predicted from the recipe's structure before they start.
