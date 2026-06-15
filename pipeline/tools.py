"""Deterministic data tools for the Su Chef pipeline.

These are plain, reproducible Python functions (the real data work). The CrewAI
crews in crews.py call these as tools, so the heavy lifting stays deterministic
and reproducible while the agents orchestrate and write the narrative reports.

Pipeline target: estimate a recipe's PER-SERVING NUTRITION (calories, protein,
carbs, fat) from its ingredients and structure. The model is trained on ~39k
recipes with real, computed nutrition (Edamam "recipes-with-nutrition"). In the
app the model is the learned estimator shown in About and a cross-check on
generated recipes; real recipes always display their measured nutrition.

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

try:  # stable import path for the pickled densifier (see _sk.py)
    from . import _sk
except ImportError:  # pragma: no cover - when run as a bare script
    import _sk

SEED = 42

_ROOT = Path(__file__).resolve().parent.parent
DATASET = _ROOT / "dataset" / "recipes_nutrition.csv"
ARTIFACTS = _ROOT / "artifacts"

CLEAN_CSV = ARTIFACTS / "clean_data.csv"
EDA_HTML = ARTIFACTS / "eda_report.html"
INSIGHTS_MD = ARTIFACTS / "insights.md"
CONTRACT_JSON = ARTIFACTS / "dataset_contract.json"
FEATURES_CSV = ARTIFACTS / "features.csv"
MODEL_PKL = ARTIFACTS / "model.pkl"
EVAL_MD = ARTIFACTS / "evaluation_report.md"
CARD_MD = ARTIFACTS / "model_card.md"

# What the model predicts: per-serving nutrition (multi-output regression).
TARGETS = ["calories", "protein_g", "carbs_g", "fat_g"]
TEXT_FEATURE = "ingredient_text"
NUM_FEATURES = ["num_ingredients", "servings"]
CAT_FEATURES = ["course", "cuisine"]
TOP_CUISINES = 15  # keep the most common cuisines; bucket the rest as "Other"

# Curated diets shown in Recipe Lab -> the boolean column that flags each.
# (High-Protein / Low-Carb are intentionally omitted: the Recipe Lab protein and
# carb target fields already cover those. Keto is a ratio-based pattern a single
# slider can't express, so it earns a chip.)
CURATED_DIETS = {
    "Vegetarian": "is_vegetarian",
    "Vegan": "is_vegan",
    "Gluten-Free": "is_gluten_free",
    "Dairy-Free": "is_dairy_free",
    "Keto": "is_keto",
}

# Course selector options (canonical labels derived from dish/meal type).
COURSES = ["Main", "Breakfast", "Dessert", "Snack", "Appetizer", "Soup",
           "Salad", "Side", "Bread", "Drink"]

# Edamam total_nutrients keys -> our per-recipe columns.
_NUTRIENT_KEYS = {"calories_total": None, "protein_g": "PROCNT", "carbs_g": "CHOCDF",
                  "fat_g": "FAT", "fiber_g": "FIBTG", "sugar_g": "SUGAR",
                  "sodium_mg": "NA"}


def _log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)


# --- small parsers for the dataset's JSON-ish string fields ------------------

def _as_list(val) -> list[str]:
    """Parse a JSON list string like '["a","b"]' into a Python list."""
    if isinstance(val, list):
        return val
    if not isinstance(val, str) or not val.strip():
        return []
    try:
        out = json.loads(val)
        return out if isinstance(out, list) else []
    except Exception:
        return []


def _nutrient(val, key: str) -> float:
    try:
        return float(json.loads(val).get(key, {}).get("quantity"))
    except Exception:
        return np.nan


def _first(lst, default="Other") -> str:
    return str(lst[0]).strip().title() if lst else default


_DISH_TO_COURSE = {
    "main course": "Main", "sandwiches": "Main", "pasta": "Main",
    "desserts": "Dessert", "biscuits and cookies": "Dessert",
    "salad": "Salad", "soup": "Soup", "starter": "Appetizer",
    "condiments and sauces": "Side", "side dish": "Side",
    "bread": "Bread", "pancake": "Breakfast", "cereals": "Breakfast",
    "egg": "Breakfast", "drinks": "Drink", "alcohol cocktail": "Drink",
}


def _course(dish: list[str], meal: list[str]) -> str:
    for d in dish:
        c = _DISH_TO_COURSE.get(str(d).strip().lower())
        if c:
            return c
    m = " ".join(meal).lower()
    if "breakfast" in m or "brunch" in m:
        return "Breakfast"
    if "snack" in m or "teatime" in m:
        return "Snack"
    if "lunch" in m or "dinner" in m:
        return "Main"
    return "Main"


# --- Crew 1: load + clean ----------------------------------------------------

def load_and_clean() -> pd.DataFrame:
    """Load the raw nutrition recipe CSV and produce a clean, typed dataframe
    with per-serving nutrition + diet/course tags. Writes artifacts/clean_data.csv."""
    ARTIFACTS.mkdir(exist_ok=True)
    raw = pd.read_csv(DATASET, low_memory=False)
    _log(f"loaded raw: {raw.shape[0]} rows")

    df = pd.DataFrame()
    df["recipe_name"] = raw["recipe_name"].astype(str).str.strip()
    df["url"] = raw["url"].fillna("").astype(str)
    df["image_url"] = raw.get("image_url", pd.Series([""] * len(raw))).fillna("").astype(str)
    df["servings"] = pd.to_numeric(raw["servings"], errors="coerce")

    ing_lists = raw["ingredient_lines"].map(_as_list)
    df["ingredient_lines"] = ing_lists.map(lambda l: json.dumps(l, ensure_ascii=False))
    df["ingredient_text"] = ing_lists.map(lambda l: " ".join(l))
    df["num_ingredients"] = ing_lists.map(len)

    health = raw["health_labels"].map(_as_list).map(lambda l: {str(x) for x in l})
    diet_l = raw["diet_labels"].map(_as_list).map(lambda l: {str(x) for x in l})
    df["cuisine"] = raw["cuisine_type"].map(_as_list).map(_first)
    df["course"] = [
        _course(_as_list(d), _as_list(m))
        for d, m in zip(raw["dish_type"], raw["meal_type"])
    ]

    # per-recipe nutrition, then per serving
    total_cal = pd.to_numeric(raw["calories"], errors="coerce")
    df["calories"] = total_cal / df["servings"]
    for col, key in _NUTRIENT_KEYS.items():
        if key is None:
            continue
        df[col] = raw["total_nutrients"].map(lambda s, k=key: _nutrient(s, k)) / df["servings"]

    # curated diet flags (heuristic: labels + nutrition thresholds)
    df["is_vegetarian"] = health.map(lambda s: "Vegetarian" in s or "Vegan" in s)
    df["is_vegan"] = health.map(lambda s: "Vegan" in s)
    df["is_gluten_free"] = health.map(lambda s: "Gluten-Free" in s)
    df["is_dairy_free"] = health.map(lambda s: "Dairy-Free" in s)
    # Keto: very low carbs per serving and fat-dominant (heuristic, not a label).
    df["is_keto"] = (df["carbs_g"] <= 10) & (df["fat_g"] >= df["protein_g"]) & (df["fat_g"] >= 12)
    df["diet_tags"] = [
        ", ".join(lbl for lbl, col in CURATED_DIETS.items() if row[col])
        for _, row in df[list(CURATED_DIETS.values())].iterrows()
    ]

    before = len(df)
    df = df[(df["servings"] >= 1) & (df["num_ingredients"] >= 1)]
    df = df[(df["calories"] > 5) & (df["calories"] <= 2000)]
    df = df[(df["protein_g"].between(0, 300)) & (df["carbs_g"].between(0, 500))
            & (df["fat_g"].between(0, 400))]
    df = df.dropna(subset=TARGETS)
    df = df.drop_duplicates(subset=["recipe_name"]).reset_index(drop=True)

    num_cols = TARGETS + ["fiber_g", "sugar_g", "sodium_mg", "servings"]
    df[num_cols] = df[num_cols].round(1)
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
    sns.histplot(df["calories"].clip(upper=1200), bins=30, ax=ax, color="#9e0027")
    ax.set_title("Calories per serving"); ax.set_xlabel("kcal")
    imgs.append(("Calories per serving", _fig_to_b64(fig)))

    fig, axes = plt.subplots(1, 3, figsize=(9, 2.8))
    for ax, col, color in zip(axes, ["protein_g", "carbs_g", "fat_g"],
                              ["#51611f", "#a8481c", "#7a4a8a"]):
        sns.histplot(df[col].clip(upper=df[col].quantile(0.98)), bins=24, ax=ax, color=color)
        ax.set_title(col.replace("_g", " (g)")); ax.set_xlabel("")
    fig.tight_layout()
    imgs.append(("Macronutrient distributions (per serving)", _fig_to_b64(fig)))

    fig, ax = plt.subplots(figsize=(6, 3.2))
    sc = df.sample(min(3000, len(df)), random_state=SEED)
    sns.scatterplot(data=sc, x="fat_g", y="calories", ax=ax, alpha=0.25, color="#9e0027")
    ax.set_xlim(0, sc["fat_g"].quantile(0.98)); ax.set_ylim(0, 1200)
    ax.set_title("Fat drives calories"); ax.set_xlabel("fat (g)"); ax.set_ylabel("kcal")
    imgs.append(("Fat vs. calories", _fig_to_b64(fig)))

    fig, ax = plt.subplots(figsize=(6, 3.4))
    by_course = df.groupby("course")["calories"].median().sort_values(ascending=False)
    sns.barplot(x=by_course.values, y=by_course.index, ax=ax, color="#94806f")
    ax.set_title("Median calories by course"); ax.set_xlabel("kcal/serving")
    imgs.append(("Calories by course", _fig_to_b64(fig)))

    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    corr = df[["calories", "protein_g", "carbs_g", "fat_g", "fiber_g",
               "sugar_g", "sodium_mg"]].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="rocket_r", ax=ax,
                annot_kws={"size": 7}, cbar=False)
    ax.set_title("Nutrient correlations")
    imgs.append(("Nutrient correlations", _fig_to_b64(fig)))

    diet_counts = {lbl: int(df[col].sum()) for lbl, col in CURATED_DIETS.items()}
    stats = {
        "rows": int(len(df)),
        "median_calories": float(df["calories"].median()),
        "mean_calories": round(float(df["calories"].mean()), 1),
        "median_protein": float(df["protein_g"].median()),
        "median_carbs": float(df["carbs_g"].median()),
        "median_fat": float(df["fat_g"].median()),
        "top_course": df["course"].value_counts().idxmax(),
        "veg_share": round(float(df["is_vegetarian"].mean()), 2),
        "diet_counts": diet_counts,
        "corr_calories": df[["protein_g", "carbs_g", "fat_g", "fiber_g",
                             "sugar_g", "sodium_mg"]].corrwith(df["calories"]).round(3).to_dict(),
    }

    cards = "".join(
        f'<div class="card"><h3>{title}</h3>'
        f'<img src="data:image/png;base64,{b64}"/></div>'
        for title, b64 in imgs)
    diet_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in diet_counts.items())
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Su Chef — EDA Report</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;background:#faf9f7;color:#1a1c1b;margin:0;padding:24px}}
 h1{{color:#9e0027}} .grid{{display:flex;flex-wrap:wrap;gap:18px}}
 .card{{background:#fff;border:1px solid #e6e1da;border-radius:12px;padding:14px;
   box-shadow:0 2px 10px rgba(0,0,0,.06)}} .card img{{max-width:100%}}
 table{{border-collapse:collapse;margin-top:8px}} td,th{{border:1px solid #e6e1da;padding:6px 10px}}
</style></head><body>
<h1>Su Chef — Exploratory Data Analysis</h1>
<p>{stats['rows']} cleaned recipes with real per-serving nutrition. Median
 <b>{stats['median_calories']:.0f} kcal</b>, {stats['median_protein']:.0f} g protein,
 {stats['median_carbs']:.0f} g carbs, {stats['median_fat']:.0f} g fat per serving.
 We model these four nutrition targets from a recipe's ingredients and structure.</p>
<div class="grid">{cards}</div>
<h2>Recipes per diet tag</h2>
<table><tr><th>diet</th><th>recipes</th></tr>{diet_rows}</table>
</body></html>"""
    EDA_HTML.write_text(html, encoding="utf-8")
    _log(f"wrote {EDA_HTML.name} ({len(imgs)} charts)")
    return stats


# --- Crew 1: dataset contract ------------------------------------------------

def write_contract(df: pd.DataFrame) -> dict:
    """Write artifacts/dataset_contract.json — the rules Crew 2 must obey."""
    contract = {
        "schema": {
            "recipe_name": "string", "url": "string", "image_url": "string",
            "servings": "float", "num_ingredients": "int",
            "ingredient_text": "string", "ingredient_lines": "string",
            "course": "string", "cuisine": "string", "diet_tags": "string",
            "calories": "float", "protein_g": "float", "carbs_g": "float",
            "fat_g": "float", "fiber_g": "float", "sugar_g": "float",
            "sodium_mg": "float",
        },
        "target": TARGETS,
        "allowed_values": {
            "diet": list(CURATED_DIETS.keys()),
            "course": sorted(df["course"].value_counts().index.tolist()),
        },
        "constraints": {
            "calories": {"min": 5, "max": 2000},
            "servings": {"min": 1},
            "num_ingredients": {"min": 1},
        },
        "assumptions": {
            "per_serving": "nutrition columns = recipe total / servings",
            "nutrients": "protein/carbs/fat/fiber/sugar from Edamam total_nutrients "
                         "(PROCNT/CHOCDF/FAT/FIBTG/SUGAR); sodium NA in mg",
            "diet_tags": "heuristic from Edamam health labels (Vegetarian/Vegan/"
                         "Gluten-Free/Dairy-Free) + Keto (carbs <=10 g, fat-dominant "
                         "per serving)",
        },
        "row_count": int(len(df)),
    }
    CONTRACT_JSON.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    _log(f"wrote {CONTRACT_JSON.name}")
    return contract


def validate_clean_against_contract(df: pd.DataFrame, contract: dict) -> list[str]:
    """Return a list of problems; empty list == valid. The Flow stops if non-empty."""
    problems = []
    for col in contract["schema"]:
        if col not in df.columns:
            problems.append(f"missing column: {col}")
    c = contract["constraints"]["calories"]
    if "calories" in df.columns:
        bad = df[(df["calories"] < c["min"]) | (df["calories"] > c["max"])]
        if len(bad):
            problems.append(f"{len(bad)} rows violate calories range {c}")
    for col in ("num_ingredients", "servings"):
        if col in df.columns and (df[col] < 1).any():
            problems.append(f"{col} has values < 1")
    return problems


# --- Crew 2: feature engineering --------------------------------------------

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build the modelling table -> artifacts/features.csv. Buckets rare cuisines
    and keeps the ingredient text + structure features and the 4 nutrition targets."""
    feats = df.copy()
    top = feats["cuisine"].value_counts().head(TOP_CUISINES).index
    feats["cuisine"] = feats["cuisine"].where(feats["cuisine"].isin(top), "Other")
    cols = [TEXT_FEATURE] + NUM_FEATURES + CAT_FEATURES + TARGETS
    feats = feats[cols].dropna(subset=TARGETS).reset_index(drop=True)
    feats = feats[feats[TEXT_FEATURE].str.strip().astype(bool)]
    feats.to_csv(FEATURES_CSV, index=False)
    _log(f"wrote {FEATURES_CSV.name} ({feats.shape[0]} rows, {feats.shape[1]} cols)")
    return feats


def validate_features(feats: pd.DataFrame) -> list[str]:
    problems = []
    for col in [TEXT_FEATURE] + NUM_FEATURES + CAT_FEATURES + TARGETS:
        if col not in feats.columns:
            problems.append(f"features.csv missing required column: {col}")
    return problems


# --- Crew 2: train + evaluate ------------------------------------------------

def _build_pre():
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    return ColumnTransformer([
        ("txt", TfidfVectorizer(max_features=600, min_df=5, stop_words="english"),
         TEXT_FEATURE),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
        ("num", StandardScaler(with_mean=False), NUM_FEATURES),
    ])


def train_and_evaluate(feats: pd.DataFrame) -> dict:
    """Train >=2 multi-output regressors to estimate per-serving nutrition,
    compare them against a mean baseline, save the best as artifacts/model.pkl,
    and write evaluation_report.md. Reproducible (SEED)."""
    import joblib
    from sklearn.dummy import DummyRegressor
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.multioutput import MultiOutputRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import FunctionTransformer
    from sklearn.model_selection import train_test_split

    X = feats[[TEXT_FEATURE] + NUM_FEATURES + CAT_FEATURES]
    y = feats[TARGETS].to_numpy()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED)

    def scores(pred) -> dict:
        per = {t: {"r2": round(float(r2_score(y_test[:, i], pred[:, i])), 3),
                   "mae": round(float(mean_absolute_error(y_test[:, i], pred[:, i])), 1)}
               for i, t in enumerate(TARGETS)}
        per["mean_r2"] = round(float(np.mean([per[t]["r2"] for t in TARGETS])), 3)
        return per

    dummy = DummyRegressor(strategy="mean").fit(X_train, y_train)
    baseline = scores(dummy.predict(X_test))

    candidates = {
        "Ridge": Pipeline([("pre", _build_pre()), ("model", Ridge(alpha=1.0))]),
        "HistGradientBoosting": Pipeline([
            ("pre", _build_pre()),
            ("dense", FunctionTransformer(_sk.to_dense, accept_sparse=True)),
            ("model", MultiOutputRegressor(HistGradientBoostingRegressor(
                max_iter=300, learning_rate=0.08, random_state=SEED))),
        ]),
    }
    results, fitted = {}, {}
    for name, pipe in candidates.items():
        pipe.fit(X_train, y_train)
        results[name] = scores(pipe.predict(X_test))
        fitted[name] = pipe
        _log(f"{name}: mean_r2={results[name]['mean_r2']}")

    best = max(results, key=lambda n: results[n]["mean_r2"])
    defaults = {
        "num_ingredients": float(feats["num_ingredients"].median()),
        "servings": float(feats["servings"].median()),
        "course": feats["course"].mode().iat[0],
        "cuisine": feats["cuisine"].mode().iat[0],
    }
    joblib.dump({"pipeline": fitted[best], "targets": TARGETS,
                 "text_feature": TEXT_FEATURE, "num_features": NUM_FEATURES,
                 "cat_features": CAT_FEATURES, "defaults": defaults,
                 "model_name": best}, MODEL_PKL)
    _log(f"wrote {MODEL_PKL.name} (best: {best})")

    def row(name, s):
        return (f"| {name} | {s['mean_r2']} | "
                + " | ".join(f"{s[t]['r2']} / {s[t]['mae']}" for t in TARGETS) + " |")

    header = "| Model | Mean R² | " + " | ".join(f"{t} R²/MAE" for t in TARGETS) + " |"
    sep = "|" + "---|" * (len(TARGETS) + 2)
    rows = "\n".join(row(n, results[n]) for n in results)
    EVAL_MD.write_text(
        f"""# Evaluation Report — Nutrition Estimator

Task: estimate a recipe's **per-serving nutrition** (calories, protein, carbs,
fat) from its ingredient text + structure. Multi-output regression, train/test
split 80/20, seed {SEED}. Metric: R² (higher better) and MAE (lower better) per
target, plus the mean R² across the four targets.

Mean-prediction baseline mean R² (by definition ~0.0): **{baseline['mean_r2']}**.

{header}
{sep}
{row('Baseline (mean)', baseline)}
{rows}

**Winner: {best}** (highest mean R²), saved as `model.pkl`.

Interpretation: R² above the {baseline['mean_r2']} baseline means the ingredient
text and structure carry real signal about a recipe's nutrition. Calories and fat
are the easiest to predict; protein and carbs are harder because they depend on
exact quantities the model does not see.
""", encoding="utf-8")
    _log(f"wrote {EVAL_MD.name}")
    return {"results": results, "baseline": baseline, "best": best}


def write_insights(stats: dict) -> None:
    """Deterministic business summary -> artifacts/insights.md."""
    corr = stats["corr_calories"]
    diet = stats["diet_counts"]
    INSIGHTS_MD.write_text(
        f"""# Recipe Dataset — Business Insights

**Dataset:** {stats['rows']} cleaned recipes with real, computed nutrition
(Edamam "recipes-with-nutrition").

## Headline findings
- **A typical serving is ~{stats['median_calories']:.0f} kcal** (median; mean
  {stats['mean_calories']:.0f}), with ~{stats['median_protein']:.0f} g protein,
  ~{stats['median_carbs']:.0f} g carbs, ~{stats['median_fat']:.0f} g fat.
- **Fat is the strongest driver of calories** (correlation
  {corr.get('fat_g')}), ahead of carbs ({corr.get('carbs_g')}) and protein
  ({corr.get('protein_g')}).
- **{stats['veg_share']:.0%} of recipes are vegetarian.** Diet coverage:
  {", ".join(f"{k} {v}" for k, v in diet.items())}.

## What this enables
Because every recipe carries real per-serving nutrition, we can (1) let a cook
search by macro targets and diet, and (2) train a model that estimates nutrition
from ingredients for brand-new, generated recipes that have no measured values.

## Business takeaway
Macro-aware cooking: a cook states a calorie/protein goal and a diet, and Su Chef
finds real matches or builds a custom recipe and estimates how close it lands.
""", encoding="utf-8")
    _log(f"wrote {INSIGHTS_MD.name}")


def write_model_card(model_info: dict) -> None:
    """Deterministic model card with all required sections -> model_card.md."""
    best = model_info["best"]
    r = model_info["results"][best]
    base = model_info["baseline"]
    rows = model_info.get("rows", "n/a")
    per = "\n".join(
        f"- **{t}**: R² {r[t]['r2']}, MAE {r[t]['mae']}" for t in TARGETS)
    CARD_MD.write_text(
        f"""# Model Card — Nutrition Estimator

## Model purpose
Estimates a recipe's **per-serving nutrition** (calories, protein, carbs, fat)
from its ingredient list and structure (ingredient text, number of ingredients,
servings, course, cuisine). Used in Su Chef as the learned estimator shown in
About and as a cross-check on generated recipes. Real recipes always display
their measured nutrition; the model fills the gap only for novel recipes.

## Training data summary
~{rows} recipes with real, computed nutrition from the Edamam
"recipes-with-nutrition" dataset (Western/American-leaning). Targets are
per-serving values (recipe total / servings). Features: ingredient text
(TF-IDF, 600 terms), num_ingredients, servings, course, cuisine (one-hot).

## Metrics (held-out 20% test set, seed {SEED})
- Best model: **{best}** (mean R² **{r['mean_r2']}** vs mean-baseline {base['mean_r2']})
{per}
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
""", encoding="utf-8")
    _log(f"wrote {CARD_MD.name}")


# --- Inference helpers (used by the live app; no heavy/crewai imports) -------

from functools import lru_cache


@lru_cache(maxsize=1)
def load_predictor():
    """Load the trained model bundle from artifacts/model.pkl."""
    import joblib
    return joblib.load(MODEL_PKL)


@lru_cache(maxsize=1)
def _clean_df() -> pd.DataFrame:
    return pd.read_csv(CLEAN_CSV)


def estimate_nutrition(fields: dict) -> dict:
    """Estimate per-serving {calories, protein_g, carbs_g, fat_g} for a recipe
    from simple inputs. `fields` may include: ingredients (str or list),
    num_ingredients, servings, course, cuisine. Missing values use dataset
    defaults."""
    b = load_predictor()
    ing = fields.get("ingredients", "")
    if isinstance(ing, list):
        ing = " ".join(str(x) for x in ing)
    d = b["defaults"]
    row = {
        TEXT_FEATURE: str(ing or ""),
        "num_ingredients": fields.get("num_ingredients") or d["num_ingredients"],
        "servings": fields.get("servings") or d["servings"],
        "course": fields.get("course") or d["course"],
        "cuisine": fields.get("cuisine") or d["cuisine"],
    }
    pred = b["pipeline"].predict(pd.DataFrame([row]))[0]
    return {t: round(float(max(0.0, v)), 1) for t, v in zip(b["targets"], pred)}


def search_recipes(targets: dict | None = None, diets: list[str] | None = None,
                   course: str | None = None, query: str | None = None,
                   k: int = 12) -> list[dict]:
    """Find real recipes matching macro targets + diets + course + optional text.
    Returns up to k dicts with measured per-serving nutrition."""
    df = _clean_df()
    mask = pd.Series(True, index=df.index)
    for diet in (diets or []):
        col = CURATED_DIETS.get(diet)
        if col and col in df.columns:
            mask &= df[col].astype(bool)
    if course and course != "Any":
        mask &= df["course"] == course
    targets = targets or {}
    cal = targets.get("calories")
    if cal:
        mask &= df["calories"].between(cal * 0.6, cal * 1.4)
    prot = targets.get("protein_g")
    if prot:
        mask &= df["protein_g"] >= prot * 0.7
    sub = df[mask]
    if sub.empty:
        return []

    if query and query.strip():
        try:
            import rag
            bm25, full = rag._index()
            qscore = pd.Series(bm25.get_scores(rag._tok(query)), index=full.index)
            sub = sub.assign(_q=qscore.reindex(sub.index).fillna(0))
            sub = sub[sub["_q"] > 0].sort_values("_q", ascending=False)
        except Exception:
            pass
    if "_q" not in sub.columns:
        if cal:
            sub = sub.assign(_d=(sub["calories"] - cal).abs()).sort_values("_d")
        else:
            sub = sub.sample(min(len(sub), 200), random_state=SEED)

    def _s(v):  # NaN-safe string (missing values are float nan, not "")
        return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)

    def _f(v):  # NaN-safe number -> JSON-valid float
        try:
            v = float(v)
            return 0.0 if pd.isna(v) else round(v, 1)
        except (TypeError, ValueError):
            return 0.0

    out = []
    for _, r in sub.head(k).iterrows():
        out.append({
            "title": _s(r.get("recipe_name")),
            "url": _s(r.get("url")),
            "image_url": _s(r.get("image_url")),
            "course": _s(r.get("course")),
            "cuisine": _s(r.get("cuisine")),
            "diet_tags": _s(r.get("diet_tags")),
            "servings": _f(r.get("servings")),
            "ingredients": _as_list(r.get("ingredient_lines", "[]")),
            "nutrition": {t: _f(r.get(t)) for t in
                          TARGETS + ["fiber_g", "sugar_g", "sodium_mg"]},
            "measured": True,
        })
    return out


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
