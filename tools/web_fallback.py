"""Trusted web search fallback (Tavily), used only when the corpus is thin.

Honest-about-limits: with no TAVILY_API_KEY configured, this returns None rather
than bluffing. Restricted to vetted recipe domains when live.
"""

from __future__ import annotations

import os

_TRUSTED_DOMAINS = [
    "seriouseats.com", "kingarthurbaking.com", "bbcgoodfood.com",
    "americastestkitchen.com", "bonappetit.com",
]


def web_search(query: str, max_results: int = 3) -> list[dict] | None:
    """Search trusted recipe sites. Returns None if Tavily isn't configured."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None
    try:
        from tavily import TavilyClient  # imported lazily; optional dependency
    except ImportError:
        return None
    client = TavilyClient(api_key=api_key)
    res = client.search(
        query=query,
        max_results=max_results,
        include_domains=_TRUSTED_DOMAINS,
    )
    return res.get("results", [])
