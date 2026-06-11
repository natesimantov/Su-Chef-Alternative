# Model Card — "Quick Recipe?" Classifier

## Model purpose
Predicts whether a recipe is **quick** (total time <= 45 minutes)
or **involved**, from its structure (ingredient/step counts, instruction length,
time-cue words, course, diet, cuisine). Used in Su Chef to tell a cook up-front
how much of a project a recipe is.

## Training data summary
~7938 cleaned recipes from the Kaggle "food_recipes"
dataset (Indian-leaning home cooking, 45-min split ≈ 60% quick /
40% involved). Features: num_ingredients, num_steps, desc_len, vote_count,
instr_len, ingr_len, time_cue_count, plus cuisine/course/diet (one-hot).

## Metrics (held-out 20% test set, seed 42)
- Best model: **LogisticRegression**
- Accuracy: **0.6952** (majority-class baseline 0.5989)
- F1: **0.7627**
- ROC-AUC: **0.7549**
Both candidate models (LogisticRegression, RandomForestClassifier) were trained
and compared; see `evaluation_report.md`.

## Limitations
- Moderate accuracy (~70%): cooking time is partly idiosyncratic and not fully
  determined by recipe structure. Treat the output as a hint, not a guarantee.
- Trained on a mostly-Indian, mostly-vegetarian corpus, so it may generalise
  poorly to very different cuisines.
- Times come from the source authors' own estimates, which vary in accuracy.

## Ethical considerations
- Low stakes: a wrong "quick/involved" guess only mis-sets expectations.
- The dataset's cuisine skew could under-serve other food cultures; the corpus
  should be broadened before treating predictions as authoritative.
- No personal data is used; predictions are about recipes, not people.
