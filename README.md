# Su Chef 🍳

An AI cooking companion **and** a complete two-crew CrewAI data project, in one
app. Ask any cooking question (by voice or text) and get a fast, **grounded**,
spoken answer; ask to *make* something and get a full recipe; and under the hood,
a **CrewAI Flow** turns ~8,000 real recipes into a trained model that predicts how
long a recipe will take.

**Live app:** https://suchef.streamlit.app

---

## Two layers, one product

**1. The cooking companion (what users see)**
- One prompt — *"Let me help."* Ask anything mid-cook by **voice** (tap-to-speak,
  auto-stops when you pause, transcribed on-server) or **typing**. Answers show on
  screen **and read aloud**.
- Answers are **grounded** in real recipes retrieved from the dataset (RAG), so
  it draws on real data instead of guessing.
- Ask to **make a dish** → a full grounded recipe (ingredients + steps + a source
  link) plus a model-predicted *quick vs. involved* estimate.
- Each question is its own logged chat; **pin** answers; recent chats + pins live
  in the sidebar and persist. Light/dark themes, metric/°F.

**2. The data-science pipeline (what the assignment grades)** — a **CrewAI Flow**
with **two crews** over the Kaggle `food_recipes` dataset. **Business question:
will a recipe be quick (≤45 min) or involved?** (We predict *time*, not rating —
ratings are near-constant at ~4.9, so they carry no signal; see `insights.md`.)

```
START
  └─ Crew 1 — Recipe Analyst (3 agents: Loader, EDA Analyst, Contract Author)
        → clean_data.csv · eda_report.html · insights.md · dataset_contract.json
  └─ VALIDATION CHECKPOINT  (clean_data must match the contract, else halt)
  └─ Crew 2 — Recipe Scientist (3 agents: Feature Engineer, Trainer, Evaluator)
        → features.csv · model.pkl · evaluation_report.md · model_card.md
FINISH
```

The model (LogisticRegression vs RandomForest, compared) reaches **~0.70 accuracy
/ 0.76 F1 / 0.75 ROC-AUC**, beating the 0.60 majority baseline. The trained model
powers the live **"will this be quick?"** prediction in the app's **📊 Recipe
Insights** view (EDA report + prediction + model card).

---

## Run it

### The app (lean — for local use or Streamlit Cloud)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Add your key in `.streamlit/secrets.toml` (gitignored):
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```
Without a key the app still runs from a small built-in knowledge base.

### The CrewAI pipeline (regenerate the 8 artifacts)
```bash
pip install -r requirements-dev.txt    # adds crewai, chromadb, matplotlib, seaborn
python -m pipeline.flow                 # runs Crew 1 → validation → Crew 2
```
This writes all eight artifacts into `artifacts/`. It is reproducible (seed 42)
and reads the key from `.streamlit/secrets.toml`.

---

## Layout

```
app.py             # the UI: companion, recipe-builder, sidebar, Insights view
companion.py       # answer(messages) -> grounded reply via Claude + RAG + offline fallback
rag.py             # BM25 retrieval over the cleaned recipes (the RAG layer)
voice.py           # tap-to-speak mic (auto-stop) + on-server transcription + read-aloud
storage.py         # local JSON for chats + pins (data/, gitignored)
theme.py           # design system (3 themes) + CSS
pipeline/
  tools.py         # deterministic, reproducible data work (clean, EDA, contract,
                   #   feature engineering, train/evaluate, inference helpers)
  crews.py         # the two CrewAI crews (agents drive the tools)
  flow.py          # the CrewAI Flow: Crew 1 → validation → Crew 2
dataset/food_recipes.csv   # the raw Kaggle dataset
artifacts/         # the 8 required output files (committed)
```

The chat model is configurable via `SU_CHEF_MODEL` (default `claude-sonnet-4-6`);
the transcription model via `SU_CHEF_WHISPER_MODEL` (default `base.en`).

## Deploy note
The deployed app is intentionally lean: it **reads** the committed artifacts
(`model.pkl`, `eda_report.html`, `clean_data.csv` for RAG) and serves the
companion. It does **not** run the heavy CrewAI Flow per visit — that is run
locally to (re)generate the artifacts, which are committed to the repo.
