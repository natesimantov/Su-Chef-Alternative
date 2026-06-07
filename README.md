# Su Chef

A knowledgeable chef in your pocket. One prompt — **"How can I help?"** — and you
ask anything mid-cook, by voice (a big tap-to-speak mic for messy hands) or by
typing. Su Chef gives a fast, grounded answer from real culinary and food-science
knowledge, shown on screen **and read aloud**.

- **No setup, no recipe walkthrough.** Just ask. State what you're making inside
  the question ("I'm making apple pie but I'm out of baking soda — what now?").
- **Every question is its own chat**, logged separately like a ChatGPT session.
  The **"Ask a follow-up"** button continues the thread.
- **Pin answers** (a recipe, a conversion, an instruction) with ★ to keep them in
  the sidebar for later.
- Recent chats and pins live in the **sidebar** and persist across restarts.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Add your Anthropic API key so answers are chef-grade. Create
`.streamlit/secrets.toml` (gitignored):

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Without a key the app still runs, answering from a small built-in knowledge base
(clearly marked as limited).

## Layout

```
app.py          # the whole UI: one prompt, chats, sidebar (recent + pinned)
companion.py    # answer(messages) -> str via Claude (claude-haiku-4-5) + offline fallback
voice.py        # tap-to-speak mic (in) + browser read-aloud (out)
storage.py      # local JSON persistence for chats and pins (data/, gitignored)
theme.py        # Warm Hearth design system (CSS)
```

The model is configurable via `SU_CHEF_MODEL` (defaults to `claude-haiku-4-5`;
bump to `claude-sonnet-4-6` for richer answers).
