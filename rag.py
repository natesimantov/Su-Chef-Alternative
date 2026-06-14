"""Lightweight retrieval over the cleaned recipe corpus (the RAG layer).

Uses BM25 (pure Python, fast, no service) so it runs fine on the deployed app.
The index is built once from artifacts/clean_data.csv and cached in-process.
`search(query)` returns the most relevant real recipes, which `companion.py`
feeds to Claude as grounding ("answer from these, don't guess").
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

_CLEAN = Path(__file__).resolve().parent / "artifacts" / "clean_data.csv"
_FIELDS = ["recipe_name", "ingredient_text", "cuisine", "course", "diet_tags"]


_STOP = {"how", "do", "i", "to", "the", "a", "an", "with", "and", "or", "of",
         "for", "my", "me", "can", "you", "is", "it", "make", "making", "made",
         "recipe", "cook", "cooking", "please", "want", "need", "some", "in",
         "on", "at", "this", "that", "best", "easy", "homemade", "good"}


def _tok(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", str(text).lower())
            if w not in _STOP and len(w) > 1]


@lru_cache(maxsize=1)
def _index():
    """Build (and cache) the BM25 index + the backing dataframe."""
    from rank_bm25 import BM25Okapi
    df = pd.read_csv(_CLEAN)
    docs = (df[_FIELDS].fillna("").agg(" ".join, axis=1)).map(_tok).tolist()
    return BM25Okapi(docs), df


def available() -> bool:
    return _CLEAN.exists()


def search(query: str, k: int = 3) -> list[dict]:
    """Return up to k relevant recipes as dicts (title, cuisine, diet, time,
    ingredients, url). Empty list if the corpus or query is unusable."""
    if not query or not _CLEAN.exists():
        return []
    try:
        bm25, df = _index()
        scores = bm25.get_scores(_tok(query))
        if not len(scores):
            return []
        top = scores.argsort()[::-1][:k]
        out = []
        for i in top:
            if scores[i] <= 0:
                continue
            r = df.iloc[int(i)]
            out.append({
                "title": str(r.get("recipe_name", "")),
                "cuisine": str(r.get("cuisine", "")),
                "diet": str(r.get("diet_tags", "")),
                "calories": float(r.get("calories", 0) or 0),
                "ingredients": str(r.get("ingredient_text", "")),
                "url": str(r.get("url", "")),
            })
        return out
    except Exception:
        return []


def grounding_block(query: str, k: int = 3) -> str:
    """A compact text block of relevant real recipes, for the system prompt."""
    hits = search(query, k)
    if not hits:
        return ""
    lines = []
    for h in hits:
        ings = h["ingredients"][:240]
        tags = ", ".join(t for t in (h["cuisine"], h["diet"]) if t)
        lines.append(
            f"- {h['title']} ({tags}, ~{h['calories']:.0f} kcal/serving): {ings}")
    return "Relevant real recipes from our database:\n" + "\n".join(lines)
