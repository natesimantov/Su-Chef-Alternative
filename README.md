# Su Chef

An AI cooking companion for home cooks — it shapes a recipe *with* you, guides you
hands-free while you cook, adapts when things go sideways, and keeps your family's
dietary needs safe. See the product definition and proposal in `AI FINAL PROJECT/`.

## Status

Early scaffold. The recipe **contract** and the Streamlit **UI shell** are in place;
the DEFINE and COOK screens are a first-pass port of the Stitch mockups, driven by
mock data. The CrewAI crew, RAG, and tools are not built yet.

## Run the UI

```bash
pip install -r requirements.txt
streamlit run ui/app.py
```

Use the **Dev navigation** in the sidebar to jump between screens, or type a dish /
tap a suggestion on DEFINE to walk into COOK mode.

## Layout

```
shared/models.py     # the recipe contract — the one file the team codes against
ui/
  app.py             # Streamlit entry + session state + dev nav
  theme.py           # Warm Hearth design system, ported to CSS
  sample_data.py     # mock recipe + profiles (until the crew produces real ones)
  screens/           # define, cook (more to come: debate, prep, done, people)
data/
  profiles.example.json   # documents the profile shape; real data/ is gitignored
agents/              # CrewAI crew (not built yet)
tools/               # culinary-math, allergen-check, profile_store, ... (not built yet)
```

## Notes

- **Design source:** `AI FINAL PROJECT/stitch_su_chef_ai_companion.zip` — 11 screens
  (HTML/Tailwind) plus the Warm Hearth design system. Tokens are ported in
  `ui/theme.py`; the mockups don't drop into Streamlit natively, so screens are
  rebuilt with Streamlit widgets + injected CSS.
- **Open decision:** the product-definition MD specifies 6 agents, the proposal PDF
  specifies 5 — reconcile before building `agents/`. The recipe contract itself is
  unaffected.
