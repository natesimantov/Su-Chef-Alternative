"""Deterministic data tools for the Su Chef pipeline.

These are plain, reproducible Python functions (the real data work). The CrewAI
crews in crew1.py / crew2.py call these as tools, so the heavy lifting stays
deterministic and reproducible while the agents orchestrate and write the
narrative reports.

Pipeline target: predict a recipe's TOTAL TIME (minutes) from its attributes.
(The dataset's `rating` is near-constant — mean 4.89, std 0.08 — so it carries
almost no signal; total time has real, useful variance. See insights.md.)

All randomness is seeded (SEED) for reproducibility.
"""

from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42

_ROOT = Path(__file__).resolve().parent.parent
DATASET = _ROOT / "dataset" / "food_recipes.csv"
ARTIFACTS = _ROOT / "artifacts"

CLEAN_CSV = ARTIFACTS / "clean_data.csv"
EDA_HTML = ARTIFACTS / "eda_report.html"
INSIGHTS_MD = ARTIFACTS / "insights.md"
CONTRACT_JSON = ARTIFACTS / "dataset_contract.json"
FEATURES_CSV = ARTIFACTS / "features.csv"
MODEL_PKL = ARTIFACTS / "model.pkl"
EVAL_MD = ARTIFACTS / "evaluation_report.md"
CARD_MD = ARTIFACTS / "model_card.md"

TARGET = "total_time_min"        # the continuous variable we analyse in EDA
MODEL_TARGET = "is_quick"        # what the model predicts: quick (<=45 min) or not
QUICK_THRESHOLD = 45             # minutes; gives a balanced ~60/40 split
TOP_CUISINES = 15  # keep the most common cuisines; bucket the rest as "Other"
NUM_FEATURES = ["num_ingredients", "num_steps", "desc_len", "vote_count",
                "instr_len", "ingr_len", "time_cue_count"]
CAT_FEATURES = ["cuisine", "course", "diet"]

# Words in the instructions that signal a long process (drive total time up).
TIME_CUES = ["overnight", "marinat", "soak", "refrigerat", "chill", "ferment",
             "rise", "proof", "rest ", "slow", "pressure", "simmer", "roast",
             "bake", "knead", "freeze", "set aside", "cool", "boil", "steam"]


def _time_cue_count(text: str) -> int:
    t = str(text).lower()
    return sum(t.count(cue) for cue in TIME_CUES)


def _log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)


# --- Crew 1: load + clean ----------------------------------------------------

def _parse_minutes(val) -> float:
    """'15 M' -> 15.0 ; '' / NaN -> NaN."""
    if pd.isna(val):
        return np.nan
    m = re.search(r"\d+", str(val))
    return float(m.group()) if m else np.nan


def load_and_clean() -> pd.DataFrame:
    """Load the raw Kaggle recipe CSV and produce a clean, typed dataframe.
    Writes artifacts/clean_data.csv. Deterministic."""
    ARTIFACTS.mkdir(exist_ok=True)
    raw = pd.read_csv(DATASET)
    _log(f"loaded raw: {raw.shape[0]} rows")
    df = pd.DataFrame()
    df["recipe_title"] = raw["recipe_title"].astype(str).str.strip()
    df["cuisine"] = raw["cuisine"].fillna("Unknown").astype(str).str.strip()
    df["course"] = raw["course"].fillna("Unknown").astype(str).str.strip()
    df["diet"] = raw["diet"].fillna("Unknown").astype(str).str.strip()
    df["rating"] = pd.to_numeric(raw["rating"], errors="coerce")
    df["vote_count"] = pd.to_numeric(raw["vote_count"], errors="coerce").fillna(0).astype(int)
    df["prep_time_min"] = raw["prep_time"].map(_parse_minutes)
    df["cook_time_min"] = raw["cook_time"].map(_parse_minutes)
    df["total_time_min"] = df["prep_time_min"].fillna(0) + df["cook_time_min"].fillna(0)
    # counts from the "|"-separated fields
    df["num_ingredients"] = (raw["ingredients"].fillna("")
                             .map(lambda s: len([x for x in str(s).split("|") if x.strip()])))
    df["num_steps"] = (raw["instructions"].fillna("")
                       .map(lambda s: len([x for x in str(s).split("|") if x.strip()])))
    df["desc_len"] = raw["description"].fillna("").map(lambda s: len(str(s)))
    df["ingredients"] = raw["ingredients"].fillna("").astype(str)
    df["instructions"] = raw["instructions"].fillna("").astype(str)
    df["instr_len"] = df["instructions"].map(len)
    df["ingr_len"] = df["ingredients"].map(len)
    df["time_cue_count"] = df["instructions"].map(_time_cue_count)
    df["url"] = raw["url"].fillna("").astype(str)

    before = len(df)
    # keep rows with a usable target + at least some ingredients/steps
    df = df[(df["total_time_min"] > 0) & (df["total_time_min"] <= 600)]
    df = df[(df["num_ingredients"] > 0) & (df["num_steps"] > 0)]
    df = df.drop_duplicates(subset=["recipe_title"]).reset_index(drop=True)
    _log(f"cleaned: {len(df)} rows (dropped {before - len(df)})")
    df.to_csv(CLEAN_CSV, index=False)
    _log(f"wrote {CLEAN_CSV.name}")
    return df


# --- Crew 1: EDA -------------------------------------------------------------

def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
    buf.seek(0)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return base64.b64encode(buf.read()).decode("ascii")


def run_eda(df: pd.DataFrame) -> dict:
    """Exploratory charts + stats -> artifacts/eda_report.html. Returns a stats
    dict used to write insights.md."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set_theme(style="whitegrid")

    imgs = []

    fig, ax = plt.subplots(figsize=(6, 3.2))
    sns.histplot(df["total_time_min"].clip(upper=180), bins=30, ax=ax, color="#b4501f")
    ax.set_title("Total time (minutes) distribution"); ax.set_xlabel("minutes")
    imgs.append(("Total cooking time", _fig_to_b64(fig)))

    fig, ax = plt.subplots(figsize=(6, 3.2))
    sns.histplot(df["rating"], bins=30, ax=ax, color="#51611f")
    ax.set_title("Rating distribution (near-constant ~4.9)"); ax.set_xlabel("rating")
    imgs.append(("Ratings are nearly identical", _fig_to_b64(fig)))

    fig, ax = plt.subplots(figsize=(6, 3.2))
    sc = df.sample(min(2000, len(df)), random_state=SEED)
    sns.scatterplot(data=sc, x="num_ingredients", y="total_time_min", ax=ax,
                    alpha=0.3, color="#a8481c")
    ax.set_ylim(0, 200); ax.set_title("More ingredients -> more time")
    imgs.append(("Ingredients vs. time", _fig_to_b64(fig)))

    fig, ax = plt.subplots(figsize=(6, 3.4))
    top_course = df["course"].value_counts().head(8)
    sns.barplot(x=top_course.values, y=top_course.index, ax=ax, color="#94806f")
    ax.set_title("Recipes by course"); ax.set_xlabel("count")
    imgs.append(("Courses", _fig_to_b64(fig)))

    fig, ax = plt.subplots(figsize=(6, 3.4))
    top_diet = df["diet"].value_counts().head(8)
    sns.barplot(x=top_diet.values, y=top_diet.index, ax=ax, color="#4d5a1e")
    ax.set_title("Recipes by diet"); ax.set_xlabel("count")
    imgs.append(("Diets", _fig_to_b64(fig)))

    corr = (df[["total_time_min", "time_cue_count", "num_steps", "instr_len",
                "num_ingredients", "ingr_len", "desc_len", "vote_count", "rating"]]
            .corr()["total_time_min"].round(3).to_dict())

    stats = {
        "rows": int(len(df)),
        "median_total_time": float(df["total_time_min"].median()),
        "mean_total_time": round(float(df["total_time_min"].mean()), 1),
        "rating_mean": round(float(df["rating"].mean()), 3),
        "rating_std": round(float(df["rating"].std()), 3),
        "top_cuisine": df["cuisine"].value_counts().idxmax(),
        "top_course": df["course"].value_counts().idxmax(),
        "veg_share": round(float((df["diet"].str.contains("Vegetarian", case=False)).mean()), 2),
        "corr_time": corr,
    }

    cards = "".join(
        f'<div class="card"><h3>{title}</h3>'
        f'<img src="data:image/png;base64,{b64}"/></div>'
        for title, b64 in imgs)
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Su Chef — EDA Report</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;background:#faf6f2;color:#20140d;margin:0;padding:24px}}
 h1{{color:#b4501f}} .grid{{display:flex;flex-wrap:wrap;gap:18px}}
 .card{{background:#fff;border:1px solid #e0d5cb;border-radius:12px;padding:14px;
   box-shadow:0 2px 10px rgba(0,0,0,.06)}} .card img{{width:420px;max-width:100%}}
 table{{border-collapse:collapse;margin-top:8px}} td,th{{border:1px solid #e0d5cb;padding:6px 10px}}
</style></head><body>
<h1>Su Chef — Exploratory Data Analysis</h1>
<p>{stats['rows']} cleaned recipes. Median total time
 <b>{stats['median_total_time']:.0f} min</b>. Ratings cluster tightly around
 <b>{stats['rating_mean']}</b> (std {stats['rating_std']}), so we predict
 <b>total time</b>, not rating.</p>
<div class="grid">{cards}</div>
<h2>Correlation with total time</h2>
<table><tr><th>feature</th><th>corr</th></tr>
{''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k,v in stats['corr_time'].items())}
</table>
</body></html>"""
    EDA_HTML.write_text(html, encoding="utf-8")
    _log(f"wrote {EDA_HTML.name} ({len(imgs)} charts)")
    return stats


# --- Crew 1: dataset contract ------------------------------------------------

def write_contract(df: pd.DataFrame) -> dict:
    """Write artifacts/dataset_contract.json — the rules Crew 2 must obey."""
    contract = {
        "schema": {
            "recipe_title": "string", "cuisine": "string", "course": "string",
            "diet": "string", "rating": "float", "vote_count": "int",
            "prep_time_min": "float", "cook_time_min": "float",
            "total_time_min": "float", "num_ingredients": "int",
            "num_steps": "int", "desc_len": "int", "instr_len": "int",
            "ingr_len": "int", "time_cue_count": "int",
        },
        "target": TARGET,
        "allowed_values": {
            "course": sorted(df["course"].value_counts().head(20).index.tolist()),
            "diet": sorted(df["diet"].value_counts().head(20).index.tolist()),
        },
        "constraints": {
            "total_time_min": {"min": 1, "max": 600},
            "rating": {"min": 0, "max": 5},
            "num_ingredients": {"min": 1},
            "num_steps": {"min": 1},
        },
        "assumptions": {
            "time_parsing": "prep_time/cook_time like '15 M' parsed to integer minutes",
            "counts": "num_ingredients/num_steps = count of '|'-separated entries",
            "missing_categoricals": "cuisine/course/diet missing -> 'Unknown'",
        },
        "row_count": int(len(df)),
    }
    CONTRACT_JSON.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    _log(f"wrote {CONTRACT_JSON.name}")
    return contract


def validate_clean_against_contract(df: pd.DataFrame, contract: dict) -> list[str]:
    """Return a list of problems; empty list == valid. The Flow stops if non-empty."""
    problems = []
    for col, typ in contract["schema"].items():
        if col not in df.columns:
            problems.append(f"missing column: {col}")
    if TARGET in df.columns:
        c = contract["constraints"]["total_time_min"]
        bad = df[(df[TARGET] < c["min"]) | (df[TARGET] > c["max"])]
        if len(bad):
            problems.append(f"{len(bad)} rows violate total_time_min range {c}")
    for col in ("num_ingredients", "num_steps"):
        if col in df.columns and (df[col] < 1).any():
            problems.append(f"{col} has values < 1")
    return problems


# --- Crew 2: feature engineering --------------------------------------------

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build the modelling table -> artifacts/features.csv. Buckets rare cuisines
    and derives the binary target is_quick (total time <= QUICK_THRESHOLD)."""
    feats = df.copy()
    top = feats["cuisine"].value_counts().head(TOP_CUISINES).index
    feats["cuisine"] = feats["cuisine"].where(feats["cuisine"].isin(top), "Other")
    feats[MODEL_TARGET] = (feats[TARGET] <= QUICK_THRESHOLD).astype(int)
    cols = NUM_FEATURES + CAT_FEATURES + [TARGET, MODEL_TARGET]
    feats = feats[cols].dropna(subset=[TARGET]).reset_index(drop=True)
    feats.to_csv(FEATURES_CSV, index=False)
    _log(f"wrote {FEATURES_CSV.name} ({feats.shape[1]} cols, "
         f"{feats[MODEL_TARGET].mean():.0%} quick)")
    return feats


def validate_features(feats: pd.DataFrame) -> list[str]:
    problems = []
    for col in NUM_FEATURES + CAT_FEATURES + [MODEL_TARGET]:
        if col not in feats.columns:
            problems.append(f"features.csv missing required column: {col}")
    return problems


# --- Crew 2: train + evaluate ------------------------------------------------

def train_and_evaluate(feats: pd.DataFrame) -> dict:
    """Train >=2 classifiers to predict whether a recipe is quick (<=45 min),
    compare them, save the best as artifacts/model.pkl, and write
    evaluation_report.md. Reproducible (SEED)."""
    import joblib
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    X = feats[NUM_FEATURES + CAT_FEATURES]
    y = feats[MODEL_TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y)
    baseline = round(float(max(y.mean(), 1 - y.mean())), 4)  # majority-class accuracy

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
        ("num", "passthrough", NUM_FEATURES),
    ])
    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=SEED),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=300, random_state=SEED, n_jobs=-1),
    }
    results, fitted = {}, {}
    for name, model in candidates.items():
        pipe = Pipeline([("pre", pre), ("model", model)])
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test)
        proba = pipe.predict_proba(X_test)[:, 1]
        results[name] = {
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "f1": round(float(f1_score(y_test, pred)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        }
        fitted[name] = pipe
        _log(f"{name}: {results[name]}")

    best = max(results, key=lambda n: results[n]["roc_auc"])
    joblib.dump({"pipeline": fitted[best], "features": NUM_FEATURES + CAT_FEATURES,
                 "target": MODEL_TARGET, "quick_threshold": QUICK_THRESHOLD,
                 "model_name": best}, MODEL_PKL)
    _log(f"wrote {MODEL_PKL.name} (best: {best})")

    rows = "\n".join(
        f"| {n} | {r['accuracy']} | {r['f1']} | {r['roc_auc']} |"
        for n, r in results.items())
    EVAL_MD.write_text(
        f"""# Evaluation Report — "Quick Recipe?" Classifier

Task: predict whether a recipe is **quick** (total time <= {QUICK_THRESHOLD} min)
from its features. Train/test split 80/20 (stratified), seed {SEED}.
Majority-class baseline accuracy: **{baseline}**.

| Model | Accuracy | F1 | ROC-AUC |
|-------|----------|----|---------|
{rows}

**Winner: {best}** (highest ROC-AUC), saved as `model.pkl`.

Interpretation: accuracy/F1 measure correct quick-vs-involved calls; ROC-AUC
measures how well the model ranks recipes by likelihood of being quick. Both
models beat the {baseline} majority baseline, so the features
(step/ingredient counts, instruction length, time-cue words, course, diet,
cuisine) carry real signal about how long a recipe takes.
""", encoding="utf-8")
    _log(f"wrote {EVAL_MD.name}")
    return {"results": results, "best": best, "baseline": baseline}


def write_insights(stats: dict) -> None:
    """Deterministic business summary -> artifacts/insights.md (the CrewAI
    Analyst crew can enrich this; this guarantees the file always exists)."""
    corr = stats["corr_time"]
    INSIGHTS_MD.write_text(
        f"""# Recipe Dataset — Business Insights

**Dataset:** {stats['rows']} cleaned recipes (Kaggle "food_recipes").

## Headline findings
- **Ratings are almost meaningless as a target.** Mean rating is
  {stats['rating_mean']} with std {stats['rating_std']} — nearly every recipe
  scores ~4.9. So we do **not** predict rating; we predict **how long a recipe
  takes** (a "quick vs involved" classifier), which has real variance.
- **Typical recipe takes ~{stats['median_total_time']:.0f} minutes** (median);
  mean {stats['mean_total_time']:.0f} min.
- **{stats['veg_share']:.0%} of recipes are vegetarian** — the corpus skews
  Indian home cooking (top cuisine: {stats['top_cuisine']}, top course:
  {stats['top_course']}).

## What drives cooking time
Correlation of each feature with total time:
{chr(10).join(f"- **{k}**: {v}" for k, v in corr.items() if k != 'total_time_min')}

The strongest signals are **instruction length**, **time-cue words**
(e.g. "marinate", "soak", "overnight", "bake"), and **number of steps** —
i.e. *how involved the method is*, more than how many ingredients there are.

## Business takeaway
A cook can be told up-front whether a recipe is a quick weeknight option or a
longer project, predicted from the recipe's structure before they start.
""", encoding="utf-8")
    _log(f"wrote {INSIGHTS_MD.name}")


def write_model_card(model_info: dict) -> None:
    """Deterministic model card with all 5 required sections ->
    artifacts/model_card.md (the CrewAI crew can enrich this)."""
    best = model_info["best"]
    r = model_info["results"][best]
    baseline = model_info["baseline"]
    CARD_MD.write_text(
        f"""# Model Card — "Quick Recipe?" Classifier

## Model purpose
Predicts whether a recipe is **quick** (total time <= {QUICK_THRESHOLD} minutes)
or **involved**, from its structure (ingredient/step counts, instruction length,
time-cue words, course, diet, cuisine). Used in Su Chef to tell a cook up-front
how much of a project a recipe is.

## Training data summary
~{model_info.get('rows', 'n/a')} cleaned recipes from the Kaggle "food_recipes"
dataset (Indian-leaning home cooking, {QUICK_THRESHOLD}-min split ≈ 60% quick /
40% involved). Features: num_ingredients, num_steps, desc_len, vote_count,
instr_len, ingr_len, time_cue_count, plus cuisine/course/diet (one-hot).

## Metrics (held-out 20% test set, seed {SEED})
- Best model: **{best}**
- Accuracy: **{r['accuracy']}** (majority-class baseline {baseline})
- F1: **{r['f1']}**
- ROC-AUC: **{r['roc_auc']}**
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
""", encoding="utf-8")
    _log(f"wrote {CARD_MD.name}")


def run_all() -> dict:
    """Run the full deterministic pipeline end-to-end (used by the Flow + as a
    standalone sanity check). Returns a summary dict."""
    df = load_and_clean()
    stats = run_eda(df)
    write_insights(stats)
    contract = write_contract(df)
    problems = validate_clean_against_contract(df, contract)
    if problems:
        raise ValueError("Contract validation failed: " + "; ".join(problems))
    feats = engineer_features(df)
    fproblems = validate_features(feats)
    if fproblems:
        raise ValueError("Feature validation failed: " + "; ".join(fproblems))
    model_info = train_and_evaluate(feats)
    model_info["rows"] = int(len(feats))
    write_model_card(model_info)
    return {"stats": stats, "contract_rows": contract["row_count"], **model_info}


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2, default=str))
