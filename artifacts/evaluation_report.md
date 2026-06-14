# Evaluation Report — Nutrition Estimator

Task: estimate a recipe's **per-serving nutrition** (calories, protein, carbs,
fat) from its ingredient text + structure. Multi-output regression, train/test
split 80/20, seed 42. Metric: R² (higher better) and MAE (lower better) per
target, plus the mean R² across the four targets.

Mean-prediction baseline mean R² (by definition ~0.0): **0.0**.

| Model | Mean R² | calories R²/MAE | protein_g R²/MAE | carbs_g R²/MAE | fat_g R²/MAE |
|---|---|---|---|---|---|
| Baseline (mean) | 0.0 | -0.0 / 202.0 | -0.0 / 12.2 | -0.0 / 22.8 | -0.0 / 13.7 |
| Ridge | 0.349 | 0.3 / 159.6 | 0.493 / 7.7 | 0.289 / 17.6 | 0.316 / 10.3 |
| HistGradientBoosting | 0.521 | 0.52 / 129.8 | 0.607 / 6.3 | 0.485 / 15.0 | 0.473 / 8.8 |

**Winner: HistGradientBoosting** (highest mean R²), saved as `model.pkl`.

Interpretation: R² above the 0.0 baseline means the ingredient
text and structure carry real signal about a recipe's nutrition. Calories and fat
are the easiest to predict; protein and carbs are harder because they depend on
exact quantities the model does not see.
