# Recipe Dataset — Business Insights

**Dataset:** 38054 cleaned recipes with real, computed nutrition
(Edamam "recipes-with-nutrition").

## Headline findings
- **A typical serving is ~269 kcal** (median; mean
  355), with ~8 g protein,
  ~25 g carbs, ~12 g fat.
- **Fat is the strongest driver of calories** (correlation
  0.848), ahead of carbs (0.627) and protein
  (0.665).
- **62% of recipes are vegetarian.** Diet coverage:
  Vegetarian 23625, Vegan 9602, Gluten-Free 21519, Dairy-Free 18651, Keto 3109.

## What this enables
Because every recipe carries real per-serving nutrition, we can (1) let a cook
search by macro targets and diet, and (2) train a model that estimates nutrition
from ingredients for brand-new, generated recipes that have no measured values.

## Business takeaway
Macro-aware cooking: a cook states a calorie/protein goal and a diet, and Su Chef
finds real matches or builds a custom recipe and estimates how close it lands.
