"""Warm Hearth design system, ported to Streamlit.

Tokens are copied verbatim from the Stitch export
(stitch_su_chef_ai_companion/warm_hearth_design_system/DESIGN.md). Streamlit
can't consume the Tailwind HTML directly, so we inject the same palette, fonts,
and shape language as CSS and restyle Streamlit's own widgets to match.

Call `inject_theme()` once at the top of the app.
"""

from __future__ import annotations

import streamlit as st

# --- Color tokens (Warm Hearth) ---------------------------------------------
COLORS = {
    "surface": "#fcf9f8",          # cream canvas
    "surface_container": "#f0eded",  # parchment cards
    "surface_container_low": "#f6f3f2",
    "on_surface": "#1b1c1c",        # charcoal text
    "on_surface_variant": "#55433c",
    "outline": "#88726b",
    "outline_variant": "#dbc1b8",
    "primary": "#944521",           # terracotta
    "on_primary": "#ffffff",
    "primary_container": "#b35c37",
    "secondary": "#56642b",         # sage
    "on_secondary": "#ffffff",
    "secondary_container": "#d6e7a1",
    "on_secondary_container": "#5a682f",
    "tertiary": "#006768",
    "error": "#ba1a1a",
    "on_error": "#ffffff",
    "error_container": "#ffdad6",
}

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Work+Sans:wght@400;600&display=swap');

:root {{
  --sc-surface: {COLORS['surface']};
  --sc-card: {COLORS['surface_container']};
  --sc-text: {COLORS['on_surface']};
  --sc-text-variant: {COLORS['on_surface_variant']};
  --sc-primary: {COLORS['primary']};
  --sc-secondary: {COLORS['secondary']};
  --sc-secondary-container: {COLORS['secondary_container']};
  --sc-on-secondary-container: {COLORS['on_secondary_container']};
  --sc-error: {COLORS['error']};
}}

/* Canvas + base type */
.stApp {{
  background: var(--sc-surface);
  color: var(--sc-text);
  font-family: 'Work Sans', sans-serif;
}}
/* Keep content clear of the pinned chat input at the bottom */
.block-container {{ padding-bottom: 120px; }}
h1, h2, h3, .sc-display {{
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  letter-spacing: -0.01em;
  color: var(--sc-text);
}}

/* Buttons -> pills. Primary = terracotta, secondary = parchment. */
.stButton > button {{
  border-radius: 9999px;
  font-family: 'Work Sans', sans-serif;
  font-weight: 600;
  min-height: 56px;
  padding: 0 28px;
  border: none;
  transition: filter .12s ease;
}}
.stButton > button:hover {{ filter: brightness(0.96); }}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {{
  background: var(--sc-primary);
  color: #fff;
}}
.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {{
  background: var(--sc-card);
  color: var(--sc-text);
  border: 1px solid var(--sc-outline, #88726b);
}}

/* Text + chat inputs -> soft parchment pills */
.stTextInput > div > div > input,
.stChatInput textarea {{
  border-radius: 9999px !important;
  background: var(--sc-card) !important;
  border: 1px solid transparent !important;
  padding: 14px 22px !important;
  font-size: 18px !important;
}}
.stTextInput > div > div > input:focus {{
  border: 2px solid var(--sc-primary) !important;
}}

/* Progress bar in terracotta */
.stProgress > div > div > div > div {{ background-color: var(--sc-primary); }}

/* Reusable component classes */
.sc-topbar {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}}
.sc-wordmark {{
  font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700;
  font-size: 24px; color: var(--sc-primary);
}}
.sc-card {{
  background: var(--sc-card); border-radius: 24px; padding: 32px;
}}
.sc-why {{
  background: var(--sc-secondary-container); color: var(--sc-on-secondary-container);
  border-radius: 16px; padding: 18px 20px; font-size: 18px; line-height: 1.5;
  margin-top: 18px;
}}
.sc-eyebrow {{
  color: var(--sc-secondary); font-weight: 600; letter-spacing: 0.05em;
  text-transform: uppercase; font-size: 14px;
}}
.sc-emergency {{
  width: 44px; height: 44px; border-radius: 9999px;
  background: var(--sc-error-container, #ffdad6); color: var(--sc-error);
  display: flex; align-items: center; justify-content: center; font-size: 22px;
}}

/* "Before you start" warning block (amber) */
.sc-headsup {{
  background: #ffedd5; color: #7c4a03; border-radius: 16px;
  padding: 16px 20px; font-size: 17px; line-height: 1.5; margin-bottom: 10px;
}}
.sc-meta {{ color: var(--sc-text-variant); font-weight: 600; font-size: 17px; }}

/* Ingredient diff (old -> new) on the debate screen */
.sc-diff-old {{ color: #9a8a84; text-decoration: line-through; }}
.sc-diff-new {{
  background: var(--sc-primary); color: #fff; border-radius: 9999px;
  padding: 2px 12px; font-weight: 600;
}}

/* Dietary flag chips */
.sc-flag {{
  display: inline-block; border-radius: 9999px; padding: 4px 14px; margin: 3px 4px;
  font-size: 15px; font-weight: 600;
}}
.sc-flag-allergen {{ background: #ffdad6; color: #93000a; }}
.sc-flag-substitution {{ background: var(--sc-secondary-container); color: var(--sc-on-secondary-container); }}
.sc-flag-profile {{ background: var(--sc-card); color: var(--sc-text-variant); }}

/* Cooking Step Card — parchment block with a 4px terracotta left border */
.sc-stepcard {{
  background: var(--sc-card); border-radius: 24px;
  padding: 28px 28px 28px 26px; border-left: 6px solid var(--sc-primary);
}}

/* Ask-anything answer (terracotta left border, like the mockup) */
.sc-answer {{
  border-left: 4px solid var(--sc-primary); background: #fff;
  padding: 16px 20px; border-radius: 8px; font-size: 20px; line-height: 1.45;
}}
.sc-answer-q {{ color: #7a6a63; font-size: 16px; margin-bottom: 6px; }}

/* Visual Reference card */
.sc-refcard {{
  background: var(--sc-card); border-radius: 16px; padding: 18px 20px;
  font-size: 17px; line-height: 1.5;
}}

/* Pulsing "listening" aura behind the mic on Define */
@keyframes sc-pulse {{
  0%   {{ box-shadow: 0 0 0 0 rgba(148,69,33,0.35); }}
  70%  {{ box-shadow: 0 0 0 28px rgba(148,69,33,0); }}
  100% {{ box-shadow: 0 0 0 0 rgba(148,69,33,0); }}
}}
.sc-mic {{
  width: 160px; height: 160px; border-radius: 9999px; background: var(--sc-primary);
  display: flex; align-items: center; justify-content: center;
  animation: sc-pulse 2.2s infinite;
}}

/* Tidy the People edit pencils (keyed edit_*) */
[class*="st-key-edit_"] button {{
  background: transparent !important; border: 1px solid var(--sc-outline, #88726b) !important;
  border-radius: 9999px !important; min-height: 44px !important;
}}

/* Emergency button (keyed) — Streamlit tags the wrapper .st-key-<key> */
.st-key-emergency button {{
  background: #ffdad6 !important; color: #ba1a1a !important;
  border: none !important; border-radius: 9999px !important;
  min-height: 48px !important; font-size: 20px !important; font-weight: 700 !important;
}}
</style>
"""


def inject_theme() -> None:
    """Inject the Warm Hearth CSS. Call once per page load."""
    st.markdown(_CSS, unsafe_allow_html=True)


def timer_ring(remaining_sec: int, total_sec: int, size: int = 140) -> str:
    """Return SVG for a Glanceable Timer ring (terracotta stroke on a track)."""
    pct = 0.0 if total_sec <= 0 else max(0.0, min(1.0, remaining_sec / total_sec))
    r = size / 2 - 10
    circ = 2 * 3.14159 * r
    dash = circ * pct
    mm, ss = divmod(max(0, remaining_sec), 60)
    cx = cy = size / 2
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
              stroke="{COLORS['surface_container']}" stroke-width="10"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
              stroke="{COLORS['primary']}" stroke-width="10" stroke-linecap="round"
              stroke-dasharray="{dash} {circ}"
              transform="rotate(-90 {cx} {cy})"/>
      <text x="50%" y="50%" text-anchor="middle" dominant-baseline="central"
            font-family="Plus Jakarta Sans" font-size="34" font-weight="700"
            fill="{COLORS['primary']}">{mm}:{ss:02d}</text>
    </svg>
    """
