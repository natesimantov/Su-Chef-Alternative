# Su Chef 🍳

An AI cooking companion **and** a complete two-crew CrewAI data project, in one
live web app. Ask any cooking question (by voice or text) and get a fast,
**grounded**, spoken answer; ask to *make* something and get a full recipe with a
panel of expert reviewers; cook to your calorie and macro goals; and check the
nutrition of any meal. Under the hood, a **CrewAI pipeline** turns a real recipe
dataset with measured nutrition into a trained model that estimates a recipe's
per-serving calories and macros.

**Live app:** https://su-chef-alternative-production.up.railway.app

**Stack:** Flask · CrewAI · scikit-learn / pandas · Railway

---

## Two layers, one product

**1. The cooking companion (what users see)** — a Flask single-page web app:
- **Chat** — ask anything mid-cook by **voice** or **typing**; answers show on
  screen and can be **read aloud in real accents**. Answers are **grounded** in
  real recipes retrieved from the dataset (RAG), so it draws on real data instead
  of guessing.
- **Recipe Lab** — set calorie and macro goals, then **find real chef recipes**
  (measured nutrition + a sourced photo) or **generate** a fresh recipe to fit
  (pick from proposed ideas, then build).
- **Nutrition Calculator** — describe any meal in plain words and get an estimated
  calorie and macro breakdown.
- **Consult the Experts** — every recipe can be reviewed by four agents:
  Nutritionist, Dietitian & Safety, Equipment, and Substitutions.
- Each chat is logged; **pin** answers and **save recipes**; recent chats live in
  the sidebar and persist. Light/dark themes, metric/°F, works on desktop + mobile.

**2. The data-science pipeline (what the assignment grades)** — a **CrewAI Flow**
with **two crews** over a real recipe dataset (~38,054 recipes with measured
per-serving nutrition). **Task: estimate a recipe's per-serving calories, protein,
carbs, and fat from its ingredients** (multi-output regression).

```
START
  └─ Crew 1 — Data Analyst (Data Loader · Exploratory Data Analyst · Data Contract Author)
        → clean_data.csv · eda_report.html · insights.md · dataset_contract.json
  └─ VALIDATION CHECKPOINT  (clean data must match the contract, else halt)
  └─ Crew 2 — Data Scientist (Data Validator · Feature Engineer · Model Trainer & Evaluator)
        → features.csv · model.pkl · evaluation_report.md · model_card.md
FINISH
```

The winning model is a **HistGradientBoosting multi-output regressor**, mean
**R² 0.521** (calories 0.52, protein 0.61, carbs 0.49, fat 0.47), compared against
a Ridge model (0.349) and a mean baseline (0.0). Typical error is about ±130 kcal
and 6–15 g per macro. Real "Chef recipes" in the app show their measured nutrition;
generated recipes use quantity-based estimates with the trained model as a
cross-check. The pipeline is deterministic and seeded (seed 42), validates the
hand-off between crews, and commits all eight artifacts to `artifacts/`.

---

## Project structure

Front end, back end, and the data-science pipeline are kept separate:

```
web/                       # THE WEB APP
  server.py                #   back end: Flask server + JSON API endpoints
  templates/index.html     #   front end: page markup
  static/app.js, app.css   #   front end: SPA logic + styling

companion.py               # back-end core: answer()/recipes/nutrition via Claude + RAG
rag.py                     # back-end core: BM25 retrieval over the cleaned recipes
stt.py                     # back-end core: optional server-side speech-to-text

pipeline/                  # DATA-SCIENCE PIPELINE (offline, builds the model)
  tools.py                 #   deterministic data work (clean, EDA, contract,
                           #     features, train/evaluate, inference helpers)
  crews.py                 #   the two CrewAI crews (agents drive the tools)
  flow.py                  #   the CrewAI Flow: Crew 1 → validation → Crew 2
artifacts/                 # the 8 committed output files (read by the live app)

Procfile                   # Railway start command: python web/server.py
requirements.txt           # lean runtime deps for the deployed app
requirements-dev.txt       # pipeline + optional voice-input deps
```

The live app **reads** the committed artifacts (`model.pkl`, `eda_report.html`,
`clean_data.csv` for RAG) and serves the companion. It does **not** run the heavy
CrewAI Flow per visit — that runs offline to (re)generate the artifacts, which are
committed to the repo.

---

## Run it

### The web app
```bash
pip install -r requirements.txt
python web/server.py            # serves on http://localhost:8600
```
Add your key in `.streamlit/secrets.toml` (gitignored) or as an `ANTHROPIC_API_KEY`
environment variable:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```
Without a key the chat still runs from a small built-in knowledge base.

### The CrewAI pipeline (regenerate the 8 artifacts)
```bash
pip install -r requirements-dev.txt    # adds crewai, matplotlib, seaborn, etc.
python -m pipeline.flow                # runs Crew 1 → validation → Crew 2
```
This writes all eight artifacts into `artifacts/`. It is reproducible (seed 42) and
reads the key from `.streamlit/secrets.toml`.

---

## Configuration

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Claude API key (env or `.streamlit/secrets.toml`) |
| `SU_CHEF_MODEL` | `claude-sonnet-4-6` | Model for recipe generation + expert reviews |
| `SU_CHEF_MODEL_FAST` | `claude-haiku-4-5` | Model for the light calls (chat, calculator, ideas, rescale) |
| `SU_CHEF_WHISPER_MODEL` | `base.en` | Optional server-side transcription model |
| `SU_CHEF_DAILY_AI_CAP` | `500` | Spend guard: max billed AI calls per day |
| `SU_CHEF_IP_PER_MIN` | `15` | Spend guard: max billed AI calls per IP per minute |
| `SU_CHEF_VISITS_BASE` | `120` | Baseline for the footer visit counter (estimated pre-tracking visits) |

## Deploy
Deployed on **Railway** from the `web/` app + the shared Python core and committed
artifacts. The build is reproducible: seeded pipeline, committed artifacts, and
pinned dependencies (`scikit-learn==1.7.2`, `joblib==1.5.2`) so the host loads the
exact trained model.

**Visit counter persistence:** the footer counter stores its count in
`RAILWAY_VOLUME_MOUNT_PATH` if a Railway **volume** is attached (otherwise a local
`data/` file that resets on each redeploy). Attach a volume once in the Railway
dashboard to make the count grow durably; the displayed total is
`SU_CHEF_VISITS_BASE` + visits counted since.
