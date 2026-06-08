"""Theming for the Su Chef companion.

Six palettes (four light, two dark), all driven by CSS variables so the whole app
recolors at runtime. `inject_theme(name)` sets the active palette and injects the
CSS; `active_palette()` exposes it for the in-iframe components (voice panel, mic).

Note: Streamlit's own widget chrome doesn't fully follow a runtime dark switch —
the app surface, sidebar, content, buttons, inputs, and cards recolor, but a few
native-widget internals may stay light.
"""

from __future__ import annotations

import streamlit as st

# Each palette: surface (canvas), card, answer (answer-card bg), text,
# text_variant, primary, on_primary, secondary, secondary_container,
# on_secondary_container, outline, sugg_bg, sugg_border.
THEMES: dict[str, dict] = {
    "Warm Hearth": {
        "surface": "#fcf9f8", "card": "#f0eded", "answer": "#ffffff",
        "text": "#1b1c1c", "text_variant": "#55433c",
        "primary": "#944521", "on_primary": "#ffffff",
        "secondary": "#56642b", "secondary_container": "#d6e7a1",
        "on_secondary_container": "#5a682f", "outline": "#88726b",
        "sugg_bg": "#f6f3f2", "sugg_border": "#e4e2e1",
    },
    "Herb Garden": {
        "surface": "#f3f7f0", "card": "#e6efe1", "answer": "#ffffff",
        "text": "#1c2a1f", "text_variant": "#3e4c39",
        "primary": "#3f7d4f", "on_primary": "#ffffff",
        "secondary": "#b9742f", "secondary_container": "#ead9c4",
        "on_secondary_container": "#7a4d20", "outline": "#7d8a78",
        "sugg_bg": "#eef3ea", "sugg_border": "#dce6d5",
    },
    "Slate & Citrus": {
        "surface": "#f4f6f8", "card": "#e7edf2", "answer": "#ffffff",
        "text": "#1b2733", "text_variant": "#3c4a57",
        "primary": "#2f5d7c", "on_primary": "#ffffff",
        "secondary": "#d97e1f", "secondary_container": "#f6e2c4",
        "on_secondary_container": "#8a5512", "outline": "#7a8794",
        "sugg_bg": "#eef2f6", "sugg_border": "#dde5ec",
    },
    "Berry": {
        "surface": "#f9f4f7", "card": "#efe2ec", "answer": "#ffffff",
        "text": "#2a1c25", "text_variant": "#4d3a45",
        "primary": "#8a3a64", "on_primary": "#ffffff",
        "secondary": "#6a8a3a", "secondary_container": "#dbe7c4",
        "on_secondary_container": "#4d6526", "outline": "#94818c",
        "sugg_bg": "#f4ebf1", "sugg_border": "#e7d6e1",
    },
    "Midnight": {  # dark, warm
        "surface": "#1c1714", "card": "#2a221d", "answer": "#322821",
        "text": "#f3ebe4", "text_variant": "#c9b8ad",
        "primary": "#e0865c", "on_primary": "#2a160c",
        "secondary": "#a9c06b", "secondary_container": "#3e4c2a",
        "on_secondary_container": "#cde29a", "outline": "#6a5b52",
        "sugg_bg": "#241d18", "sugg_border": "#3a2f28",
    },
    "Deep Sea": {  # dark, cool
        "surface": "#121a1d", "card": "#1d2a2e", "answer": "#24343a",
        "text": "#e7f1f2", "text_variant": "#aac3c6",
        "primary": "#4bb3a7", "on_primary": "#062420",
        "secondary": "#e0a85c", "secondary_container": "#27383a",
        "on_secondary_container": "#f0d8a8", "outline": "#4f6669",
        "sugg_bg": "#18242a", "sugg_border": "#2c3e42",
    },
}
THEME_NAMES = list(THEMES.keys())
DEFAULT_THEME = "Warm Hearth"

_ACTIVE: dict = THEMES[DEFAULT_THEME]


def active_palette() -> dict:
    """The currently injected palette (for components rendered in iframes)."""
    return _ACTIVE


def _css(p: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Work+Sans:wght@400;600&display=swap');

:root {{
  --sc-surface: {p['surface']}; --sc-card: {p['card']}; --sc-answer: {p['answer']};
  --sc-text: {p['text']}; --sc-text-variant: {p['text_variant']};
  --sc-primary: {p['primary']}; --sc-on-primary: {p['on_primary']};
  --sc-secondary: {p['secondary']}; --sc-secondary-container: {p['secondary_container']};
  --sc-on-secondary-container: {p['on_secondary_container']}; --sc-outline: {p['outline']};
  --sc-sugg-bg: {p['sugg_bg']}; --sc-sugg-border: {p['sugg_border']};
}}

.stApp {{ background: var(--sc-surface); color: var(--sc-text);
  font-family: 'Work Sans', sans-serif; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: var(--sc-card); }}
.stApp p, .stApp span, .stApp label, .stApp li, [data-testid="stMarkdownContainer"] {{
  color: var(--sc-text); }}
h1, h2, h3, .sc-display {{
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important; letter-spacing: -0.01em; color: var(--sc-text); }}

/* Buttons -> pills */
.stButton > button {{
  border-radius: 9999px; font-family: 'Work Sans', sans-serif; font-weight: 600;
  min-height: 52px; padding: 0 22px; border: none; transition: filter .12s ease;
  white-space: nowrap; }}
.stButton > button:hover {{ filter: brightness(0.94); }}
.stButton > button[kind="primary"] {{ background: var(--sc-primary); color: var(--sc-on-primary); }}
.stButton > button[kind="secondary"] {{
  background: var(--sc-card); color: var(--sc-text); border: 1px solid var(--sc-outline); }}

/* Search bar: the wrapper is the pill (single clean focus border) */
[data-testid="stChatInput"] > div {{ border-radius: 9999px !important;
  background: var(--sc-card) !important; }}
.stChatInput textarea {{ border-radius: 9999px !important; background: transparent !important;
  border: none !important; padding: 16px 24px !important; font-size: 20px !important;
  color: var(--sc-text) !important; }}
.stTextInput > div > div {{ border-radius: 9999px !important; }}
.stTextInput > div > div > input {{ border-radius: 9999px !important;
  background: var(--sc-card) !important; border: none !important;
  padding: 14px 22px !important; font-size: 18px !important; color: var(--sc-text) !important; }}

/* Selectbox + segmented control (best-effort theming) */
[data-baseweb="select"] > div {{ background: var(--sc-card) !important;
  border-color: var(--sc-outline) !important; color: var(--sc-text) !important; }}
[data-testid="stSegmentedControl"] button {{ color: var(--sc-text) !important; }}

/* Mic component wrapper (the live waveform/transcript) */
[class*="st-key-mic"] button {{ min-height: 96px !important; border-radius: 24px !important;
  background: var(--sc-primary) !important; color: var(--sc-on-primary) !important;
  font-size: 22px !important; font-weight: 700 !important; border: none !important; }}

/* Answer card */
.sc-answer {{ background: var(--sc-answer); border-left: 5px solid var(--sc-primary);
  border-radius: 12px; padding: 22px 26px; font-size: 22px; line-height: 1.5;
  color: var(--sc-text); }}
.sc-question {{ color: var(--sc-text-variant); font-size: 17px; margin-bottom: 6px; }}
.sc-eyebrow {{ color: var(--sc-secondary); font-weight: 600; letter-spacing: 0.05em;
  text-transform: uppercase; font-size: 14px; }}
.sc-wordmark {{ font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700;
  font-size: 24px; color: var(--sc-primary); }}
.sc-context {{ color: var(--sc-text-variant); font-size: 16px; margin: 8px 0 6px; }}

[class*="st-key-say_"] button {{ min-height: 64px !important; font-size: 26px !important;
  padding: 0 !important; background: var(--sc-card) !important; color: var(--sc-text) !important;
  border: 1px solid var(--sc-primary) !important; }}
[class*="st-key-pintoggle_"] button {{ min-height: 42px !important; font-size: 20px !important; padding: 0 !important; }}
[class*="st-key-ctxedit_"] button {{ min-height: 38px !important; padding: 0 !important; }}

/* Suggested follow-up chips */
[class*="st-key-sugg_"] button {{ background: var(--sc-sugg-bg) !important;
  color: var(--sc-text-variant) !important; font-weight: 500 !important;
  font-style: italic !important; border: 1px solid var(--sc-sugg-border) !important;
  text-align: left !important; justify-content: flex-start !important; min-height: 44px !important; }}

/* "Su Chef is thinking…" loader */
.sc-loader {{ display: flex; flex-direction: column; align-items: center;
  gap: 10px; padding: 22px 0; }}
.sc-loader svg {{ animation: sc-bob 1.1s ease-in-out infinite; }}
@keyframes sc-bob {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-9px); }} }}
.sc-loading-text {{ color: var(--sc-primary); font-weight: 600; font-size: 18px; }}
.sc-dots span {{ animation: sc-blink 1.2s infinite both; }}
.sc-dots span:nth-child(2) {{ animation-delay: .2s; }}
.sc-dots span:nth-child(3) {{ animation-delay: .4s; }}
@keyframes sc-blink {{ 0%, 80%, 100% {{ opacity: .2; }} 40% {{ opacity: 1; }} }}
</style>
"""


def loader_html(message: str = "Su Chef is thinking") -> str:
    """HTML for the bobbing-toque 'thinking' loader (uses the active palette)."""
    p = _ACTIVE
    toque = (
        "<svg width='72' height='72' viewBox='0 0 84 84'>"
        f"<path fill='{p['primary']}' d='M28 62 L28 50 C18 50 12 42 12 33 "
        "C12 24 19 18 27 18 C29 11 35 7 42 7 C49 7 55 11 57 18 C65 18 72 24 72 33 "
        "C72 42 66 50 56 50 L56 62 C56 63 55 64 54 64 L30 64 C29 64 28 63 28 62 Z'/>"
        f"<line x1='28' y1='51' x2='56' y2='51' stroke='{p['surface']}' stroke-width='2.5'/>"
        f"<line x1='38' y1='51' x2='38' y2='64' stroke='{p['surface']}' stroke-width='2.5'/>"
        f"<line x1='48' y1='51' x2='48' y2='64' stroke='{p['surface']}' stroke-width='2.5'/>"
        "</svg>"
    )
    return (
        f"<div class='sc-loader'>{toque}"
        f"<div class='sc-loading-text'>{message}"
        "<span class='sc-dots'><span>.</span><span>.</span><span>.</span></span>"
        "</div></div>"
    )


def inject_theme(name: str = DEFAULT_THEME) -> None:
    """Set the active palette and inject its CSS. Call once per page load."""
    global _ACTIVE
    _ACTIVE = THEMES.get(name, THEMES[DEFAULT_THEME])
    st.markdown(_css(_ACTIVE), unsafe_allow_html=True)
