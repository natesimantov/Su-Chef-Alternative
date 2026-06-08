"""Theming for the Su Chef companion.

Three cohesive warm themes — **Hearth** (light), **Dusk** (dim sepia), **Charcoal**
(dark) — built as paired semantic tokens (every surface ships with its own
foreground), so contrast is structural. Every text/background pair is verified
to meet WCAG AA (4.5:1; borders 3:1). `inject_theme(name)` sets the active
palette + injects CSS; `active_palette()` exposes it to the in-iframe components.

Key fix: button-internal text is forced to its paired foreground so primary
buttons never render the page's body color on the primary background.
"""

from __future__ import annotations

import streamlit as st

# Each palette is a set of paired tokens. Keys map to semantic roles:
#   surface/text = background/foreground · card = card · answer = elevated
#   text_variant = muted-foreground · primary/on_primary = primary pair
#   secondary = accent text (eyebrow) · secondary_container/on_secondary_container
#   = soft-accent chip pair · outline = border · sugg_bg/sugg_border = chip.
THEMES: dict[str, dict] = {
    "Hearth": {  # warm light
        "surface": "#faf6f2", "card": "#efe7df", "answer": "#ffffff",
        "text": "#20140d", "text_variant": "#6a564a",
        "primary": "#b4501f", "on_primary": "#ffffff",
        "secondary": "#51611f", "secondary_container": "#dce6bf",
        "on_secondary_container": "#3a481c", "outline": "#94806f",
        "sugg_bg": "#f1ebe5", "sugg_border": "#e0d5cb",
    },
    "Dusk": {  # dim sepia
        "surface": "#e4d8c8", "card": "#d6c8b4", "answer": "#f4ede1",
        "text": "#2c2117", "text_variant": "#5b4c3c",
        "primary": "#a8481c", "on_primary": "#ffffff",
        "secondary": "#4d5a1e", "secondary_container": "#c7d49a",
        "on_secondary_container": "#38431a", "outline": "#806c57",
        "sugg_bg": "#ded2c0", "sugg_border": "#cabda8",
    },
    "Charcoal": {  # deep warm dark
        "surface": "#16140f", "card": "#221f19", "answer": "#2a261f",
        "text": "#f2efe9", "text_variant": "#b8b1a6",
        "primary": "#e6a766", "on_primary": "#241502",
        "secondary": "#b7c98a", "secondary_container": "#343a26",
        "on_secondary_container": "#cfe0a0", "outline": "#766c5f",
        "sugg_bg": "#201d17", "sugg_border": "#353128",
    },
}
THEME_NAMES = list(THEMES.keys())
DEFAULT_THEME = "Hearth"

_ACTIVE: dict = THEMES[DEFAULT_THEME]


def active_palette() -> dict:
    """The currently injected palette (for components rendered in iframes)."""
    return _ACTIVE


def _css(p: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700;12..96,800&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');

:root {{
  --sc-surface: {p['surface']}; --sc-card: {p['card']}; --sc-answer: {p['answer']};
  --sc-text: {p['text']}; --sc-text-variant: {p['text_variant']};
  --sc-primary: {p['primary']}; --sc-on-primary: {p['on_primary']};
  --sc-secondary: {p['secondary']}; --sc-secondary-container: {p['secondary_container']};
  --sc-on-secondary-container: {p['on_secondary_container']}; --sc-outline: {p['outline']};
  --sc-sugg-bg: {p['sugg_bg']}; --sc-sugg-border: {p['sugg_border']};
}}

.stApp {{ background: var(--sc-surface); color: var(--sc-text);
  font-family: 'Hanken Grotesk', sans-serif; font-size: 16px; line-height: 1.55; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: var(--sc-card); }}
.stApp p, .stApp span, .stApp label, .stApp li, [data-testid="stMarkdownContainer"] {{
  color: var(--sc-text); }}
h1, h2, h3, .sc-display {{
  font-family: 'Bricolage Grotesque', sans-serif !important;
  font-weight: 700 !important; letter-spacing: -0.02em; color: var(--sc-text); }}

/* Buttons -> pills (cover form-submit buttons too) */
.stButton > button, .stFormSubmitButton button {{
  border-radius: 9999px; font-family: 'Hanken Grotesk', sans-serif; font-weight: 600;
  min-height: 52px; padding: 0 22px; border: none; transition: filter .12s ease;
  white-space: nowrap; }}
.stButton > button:hover, .stFormSubmitButton button:hover {{ filter: brightness(0.94); }}
button[kind="primary"], button[kind="primaryFormSubmit"] {{
  background: var(--sc-primary) !important; color: var(--sc-on-primary) !important; }}
button[kind="secondary"], button[kind="secondaryFormSubmit"] {{
  background: var(--sc-card) !important; color: var(--sc-text) !important;
  border: 1px solid var(--sc-outline) !important; }}
/* CRITICAL: a button's INNER markdown text must use the button's foreground,
   not the page foreground (otherwise primary buttons show dark body text on the
   primary background). */
button[kind="primary"] *, button[kind="primaryFormSubmit"] *,
[data-testid="stSegmentedControl"] button[aria-checked="true"] * {{
  color: var(--sc-on-primary) !important; }}
button[kind="secondary"] *, button[kind="secondaryFormSubmit"] * {{
  color: var(--sc-text) !important; }}

/* Focus-visible rings (never remove focus) */
button:focus-visible, input:focus-visible, [role="option"]:focus-visible,
[data-baseweb="select"]:focus-within {{
  outline: 2px solid var(--sc-primary) !important; outline-offset: 2px !important; }}

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

/* Selectbox + dropdown menu + segmented control (theme-aware) */
[data-baseweb="select"] > div {{ background: var(--sc-card) !important;
  border-color: var(--sc-outline) !important; color: var(--sc-text) !important; }}
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"], ul[role="listbox"] {{
  background: var(--sc-card) !important; }}
[data-baseweb="menu"] li, ul[role="listbox"] li {{ color: var(--sc-text) !important; }}
[data-testid="stSegmentedControl"] button {{ color: var(--sc-text) !important; }}
[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
  background: var(--sc-primary) !important; color: var(--sc-on-primary) !important; }}

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
.sc-wordmark {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800;
  font-size: 25px; letter-spacing: -0.02em; color: var(--sc-primary); }}
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
[class*="st-key-sugg_"] button * {{ color: var(--sc-text-variant) !important; }}

/* Pinned items in the sidebar */
.sc-pin {{ background: var(--sc-secondary-container); color: var(--sc-on-secondary-container);
  border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; font-size: 15px; }}

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

/* Respect reduced-motion */
@media (prefers-reduced-motion: reduce) {{
  *, .sc-loader svg, .sc-dots span {{ animation: none !important; transition: none !important; }}
}}
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
