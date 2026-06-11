# Evaluation Report — "Quick Recipe?" Classifier

Task: predict whether a recipe is **quick** (total time <= 45 min)
from its features. Train/test split 80/20 (stratified), seed 42.
Majority-class baseline accuracy: **0.5989**.

| Model | Accuracy | F1 | ROC-AUC |
|-------|----------|----|---------|
| LogisticRegression | 0.6952 | 0.7627 | 0.7549 |
| RandomForestClassifier | 0.6902 | 0.7533 | 0.7513 |

**Winner: LogisticRegression** (highest ROC-AUC), saved as `model.pkl`.

Interpretation: accuracy/F1 measure correct quick-vs-involved calls; ROC-AUC
measures how well the model ranks recipes by likelihood of being quick. Both
models beat the 0.5989 majority baseline, so the features
(step/ingredient counts, instruction length, time-cue words, course, diet,
cuisine) carry real signal about how long a recipe takes.
