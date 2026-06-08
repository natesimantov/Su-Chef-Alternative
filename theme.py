"""Warm Hearth design system (slim) for the Su Chef companion.

Tokens come from the Stitch "Warm Hearth" design system: a calm, kitchen-friendly
palette (cream canvas, terracotta primary, sage accent, charcoal text) with big,
glanceable type. Call `inject_theme()` once at the top of the app.
"""

from __future__ import annotations

import streamlit as st

COLORS = {
    "surface": "#fcf9f8",          # cream canvas
    "card": "#f0eded",             # parchment cards
    "text": "#1b1c1c",             # charcoal
    "text_variant": "#55433c",
    "primary": "#944521",          # terracotta
    "secondary": "#56642b",        # sage
    "secondary_container": "#d6e7a1",
    "on_secondary_container": "#5a682f",
    "outline": "#88726b",
    "error": "#ba1a1a",
}

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Work+Sans:wght@400;600&display=swap');

:root {{
  --sc-surface: {COLORS['surface']};
  --sc-card: {COLORS['card']};
  --sc-text: {COLORS['text']};
  --sc-text-variant: {COLORS['text_variant']};
  --sc-primary: {COLORS['primary']};
  --sc-secondary: {COLORS['secondary']};
}}

.stApp {{
  background: var(--sc-surface);
  color: var(--sc-text);
  font-family: 'Work Sans', sans-serif;
}}
h1, h2, h3, .sc-display {{
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important; letter-spacing: -0.01em; color: var(--sc-text);
}}

/* Buttons -> pills. Primary = terracotta, secondary = parchment. */
.stButton > button {{
  border-radius: 9999px; font-family: 'Work Sans', sans-serif; font-weight: 600;
  min-height: 52px; padding: 0 22px; border: none; transition: filter .12s ease;
  white-space: nowrap;
}}
.stButton > button:hover {{ filter: brightness(0.96); }}
.stButton > button[kind="primary"] {{ background: var(--sc-primary); color: #fff; }}
.stButton > button[kind="secondary"] {{
  background: var(--sc-card); color: var(--sc-text);
  border: 1px solid var(--sc-outline);
}}

/* Big search bar: make the WRAPPER the pill so the focus border is one clean
   rounded edge (the textarea itself stays transparent — no second border). */
[data-testid="stChatInput"] > div {{
  border-radius: 9999px !important; background: var(--sc-card) !important;
}}
.stChatInput textarea {{
  border-radius: 9999px !important; background: transparent !important;
  border: none !important; padding: 16px 24px !important; font-size: 20px !important;
}}
/* Text inputs (context-edit field) as soft parchment pills */
.stTextInput > div > div {{ border-radius: 9999px !important; }}
.stTextInput > div > div > input {{
  border-radius: 9999px !important; background: var(--sc-card) !important;
  border: none !important; padding: 14px 22px !important; font-size: 18px !important;
}}

/* Pulsing "listening" mic blob */
@keyframes sc-pulse {{
  0%   {{ box-shadow: 0 0 0 0 rgba(148,69,33,0.35); }}
  70%  {{ box-shadow: 0 0 0 30px rgba(148,69,33,0); }}
  100% {{ box-shadow: 0 0 0 0 rgba(148,69,33,0); }}
}}
.sc-mic {{
  width: 180px; height: 180px; border-radius: 9999px; background: var(--sc-primary);
  display: flex; align-items: center; justify-content: center; margin: 0 auto;
  animation: sc-pulse 2.2s infinite;
}}

/* The mic component (streamlit-mic-recorder) styled large & terracotta */
[class*="st-key-mic"] button, [class*="st-key-mic"] [role="button"] {{
  min-height: 96px !important; border-radius: 24px !important;
  background: var(--sc-primary) !important; color: #fff !important;
  font-size: 22px !important; font-weight: 700 !important; border: none !important;
}}

/* Answer card */
.sc-answer {{
  background: #fff; border-left: 5px solid var(--sc-primary);
  border-radius: 12px; padding: 22px 26px; font-size: 22px; line-height: 1.5;
  color: var(--sc-text);
}}
.sc-question {{ color: var(--sc-text-variant); font-size: 17px; margin-bottom: 6px; }}
.sc-eyebrow {{
  color: var(--sc-secondary); font-weight: 600; letter-spacing: 0.05em;
  text-transform: uppercase; font-size: 14px;
}}
.sc-wordmark {{
  font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700;
  font-size: 24px; color: var(--sc-primary);
}}

/* Pinned items in the sidebar */
.sc-pin {{
  background: var(--sc-secondary_container, #d6e7a1); color: #3e4c16;
  border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; font-size: 15px;
}}

/* Context-understanding line above each answer (plain, not italic) */
.sc-context {{
  color: #7a6a63; font-size: 16px; margin: 8px 0 6px;
}}

/* Big read-aloud button (keyed say_) on the right of the answer */
[class*="st-key-say_"] button {{
  min-height: 64px !important; font-size: 26px !important; padding: 0 !important;
  background: var(--sc-card) !important; border: 1px solid var(--sc-primary) !important;
}}
/* Compact pin + edit buttons */
[class*="st-key-pintoggle_"] button {{ min-height: 42px !important; font-size: 20px !important; padding: 0 !important; }}
[class*="st-key-ctxedit_"] button {{ min-height: 38px !important; padding: 0 !important; }}

/* Suggested follow-up chips (Gmail Smart-Reply style, light gray) */
[class*="st-key-sugg_"] button {{
  background: #f6f3f2 !important; color: #55433c !important; font-weight: 500 !important;
  font-style: italic !important;
  border: 1px solid #e4e2e1 !important; text-align: left !important;
  justify-content: flex-start !important; min-height: 44px !important;
}}

/* "Su Chef is thinking…" loader — a gently bobbing chef's toque */
.sc-loader {{ display: flex; flex-direction: column; align-items: center;
  gap: 10px; padding: 22px 0; }}
.sc-loader svg {{ animation: sc-bob 1.1s ease-in-out infinite; }}
@keyframes sc-bob {{ 0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-9px); }} }}
.sc-loading-text {{ color: var(--sc-primary); font-weight: 600; font-size: 18px; }}
.sc-dots span {{ animation: sc-blink 1.2s infinite both; }}
.sc-dots span:nth-child(2) {{ animation-delay: .2s; }}
.sc-dots span:nth-child(3) {{ animation-delay: .4s; }}
@keyframes sc-blink {{ 0%, 80%, 100% {{ opacity: .2; }} 40% {{ opacity: 1; }} }}
</style>
"""

# A self-contained chef's-toque loader (Warm Hearth terracotta, no assets).
_TOQUE = (
    "<svg width='72' height='72' viewBox='0 0 84 84'>"
    "<path fill='#944521' d='M28 62 L28 50 C18 50 12 42 12 33 C12 24 19 18 27 18 "
    "C29 11 35 7 42 7 C49 7 55 11 57 18 C65 18 72 24 72 33 C72 42 66 50 56 50 "
    "L56 62 C56 63 55 64 54 64 L30 64 C29 64 28 63 28 62 Z'/>"
    "<line x1='28' y1='51' x2='56' y2='51' stroke='#fcf9f8' stroke-width='2.5'/>"
    "<line x1='38' y1='51' x2='38' y2='64' stroke='#fcf9f8' stroke-width='2.5'/>"
    "<line x1='48' y1='51' x2='48' y2='64' stroke='#fcf9f8' stroke-width='2.5'/>"
    "</svg>"
)


def loader_html(message: str = "Su Chef is thinking") -> str:
    """HTML for the bobbing-toque 'thinking' loader."""
    return (
        f"<div class='sc-loader'>{_TOQUE}"
        f"<div class='sc-loading-text'>{message}"
        "<span class='sc-dots'><span>.</span><span>.</span><span>.</span></span>"
        "</div></div>"
    )


def inject_theme() -> None:
    """Inject the Warm Hearth CSS. Call once per page load."""
    st.markdown(_CSS, unsafe_allow_html=True)
