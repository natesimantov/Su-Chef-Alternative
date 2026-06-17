"""Su Chef — Flask web app (the final UI).

A proper web app: this Flask server serves a single-page Warm Hearth frontend and
exposes JSON/SSE API endpoints that wrap the SAME Python brain the Streamlit app
uses (companion.py, rag.py, pipeline/tools.py, voice.py, artifacts/). One brain,
two front ends. Run locally:  python web/server.py
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_key() -> None:
    """Put ANTHROPIC_API_KEY in the environment from Streamlit secrets if needed."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if secrets.exists():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY"):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
                break


_load_key()

import companion  # noqa: E402  (after sys.path + key setup)

app = Flask(__name__, template_folder="templates", static_folder="static")
# Dev ergonomics: pick up template edits without a restart (Jinja caches templates
# when debug is off). Harmless in production.
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

_STATIC = Path(__file__).resolve().parent / "static"


def _asset_v() -> str:
    """A cache-busting version string from the static files' mtimes, so browsers
    fetch fresh app.js/app.css after every deploy."""
    try:
        return str(int(max((_STATIC / f).stat().st_mtime
                           for f in ("app.js", "app.css"))))
    except Exception:
        return "1"


@app.after_request
def _no_store_html(resp):
    """Never cache the HTML page — it carries the asset version, so it must always
    be fresh (the static files themselves are cache-busted by ?v=)."""
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-store"
    return resp


# --- Spend guardrails (defense-in-depth on top of the Console hard cap) --------
# Only the Anthropic-billed endpoints are guarded; edge-tts, the local model, and
# the dataset search are free and untouched. State is in-memory and per-process —
# Railway runs a single instance here, so this is the real ceiling; if ever scaled
# to multiple instances the cap becomes per-instance (fine for this use).
_BILLED_PATHS = {
    "/api/ask", "/api/build", "/api/expert-review", "/api/rescale",
    "/api/recipe-ideas", "/api/calc-nutrition",
}
_DAILY_AI_CAP = int(os.environ.get("SU_CHEF_DAILY_AI_CAP", "500"))   # ~ well under $20
_IP_PER_MIN = int(os.environ.get("SU_CHEF_IP_PER_MIN", "15"))        # anti-burst
_guard_lock = threading.Lock()
_day_key = ""          # current UTC date string
_day_count = 0         # billed AI calls so far today
_ip_hits: dict[str, deque] = defaultdict(deque)  # client IP -> recent timestamps

_LIMIT_MSG = ("Su Chef has hit its safety limit on AI requests for now (a spending "
              "guard to protect the project's budget). Please try again in a little "
              "while.")


def _client_ip() -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "?"


@app.before_request
def _spend_guard():
    """Cap billed AI calls: a global per-day ceiling plus a per-IP burst throttle."""
    if request.path not in _BILLED_PATHS:
        return None
    global _day_key, _day_count
    now = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ip = _client_ip()
    with _guard_lock:
        if today != _day_key:           # new UTC day -> reset the daily counter
            _day_key, _day_count = today, 0
            _ip_hits.clear()
        if _day_count >= _DAILY_AI_CAP:
            return _limit_response()
        hits = _ip_hits[ip]
        while hits and now - hits[0] > 60:   # slide the 60s window
            hits.popleft()
        if len(hits) >= _IP_PER_MIN:
            return _limit_response()
        hits.append(now)
        _day_count += 1
    return None


def _limit_response():
    # Shaped so the existing frontend renders it cleanly: ask() reads `answer`,
    # the lab/calc handlers read `error`.
    resp = jsonify({"error": "rate_limited", "answer": _LIMIT_MSG,
                    "follow_ups": [], "limit": True})
    resp.status_code = 429
    return resp


@app.route("/")
def index():
    return render_template("index.html", asset_v=_asset_v())


@app.post("/api/ask")
def api_ask():
    """Answer a question (non-streaming for now). Body: {messages:[...], units}."""
    data = request.get_json(force=True, silent=True) or {}
    messages = data.get("messages") or []
    units = data.get("units", "metric")
    if not messages:
        return jsonify({"error": "no messages"}), 400
    reply = companion.answer(messages, units=units)
    return jsonify(reply)


_TTS_VOICES = {
    "american-f": "en-US-AriaNeural", "american-m": "en-US-GuyNeural",
    "british-f": "en-GB-SoniaNeural", "british-m": "en-GB-RyanNeural",
    "irish-f": "en-IE-EmilyNeural", "irish-m": "en-IE-ConnorNeural",
    "australian-f": "en-AU-NatashaNeural", "australian-m": "en-AU-WilliamNeural",
    "indian-f": "en-IN-NeerjaNeural", "indian-m": "en-IN-PrabhatNeural",
    # legacy keys (older saved prefs)
    "en": "en-US-AriaNeural", "en-us": "en-US-AriaNeural",
    "en-gb": "en-GB-SoniaNeural", "en-ie": "en-IE-EmilyNeural",
    "en-au": "en-AU-NatashaNeural", "en-in": "en-IN-NeerjaNeural",
}


@app.post("/api/tts")
def api_tts():
    """Text -> high-quality neural speech (edge-tts), returned as MP3 so any
    browser can play it. Body: {text, lang}."""
    import asyncio
    import io
    import edge_tts
    import re
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = _TTS_VOICES.get(data.get("lang", "en"), _TTS_VOICES["en"])
    rate = data.get("rate", "+0%")
    if not isinstance(rate, str) or not re.fullmatch(r"[+-]\d{1,3}%", rate):
        rate = "+0%"
    if not text:
        return jsonify({"error": "no text"}), 400

    async def synth():
        buf = io.BytesIO()
        async for ch in edge_tts.Communicate(text, voice, rate=rate).stream():
            if ch["type"] == "audio":
                buf.write(ch["data"])
        return buf.getvalue()

    try:
        audio = asyncio.run(synth())
        from flask import Response
        return Response(audio, mimetype="audio/mpeg")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.post("/api/transcribe")
def api_transcribe():
    """Recorded audio blob -> text (faster-whisper, server-side)."""
    f = request.files.get("audio")
    if not f:
        return jsonify({"error": "no audio"}), 400
    try:
        import stt
    except Exception:  # faster-whisper not installed (e.g. lean prod deploy)
        return jsonify({"error": "voice input is not available on this server"}), 503
    return jsonify({"text": stt.transcribe(f.read())})


@app.post("/api/estimate")
def api_estimate():
    """Trained-model per-serving nutrition estimate for the About try-it form.
    Body: {ingredients, servings?, course?, cuisine?, num_ingredients?}."""
    from pipeline import tools as T
    data = request.get_json(force=True, silent=True) or {}
    try:
        return jsonify({"nutrition": T.estimate_nutrition(data)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/calc-nutrition")
def api_calc_nutrition():
    """Free-form meal description -> estimated nutrition (Claude + model cross-check).
    Body: {text, units}."""
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(companion.calc_nutrition(data.get("text", ""),
                                            units=data.get("units", "metric")))


@app.post("/api/search")
def api_search():
    """Recipe Lab: real recipes matching targets/diets/course/query (measured
    nutrition). Body: {targets:{calories,protein_g}, diets:[], course, query}."""
    from pipeline import tools as T
    data = request.get_json(force=True, silent=True) or {}
    try:
        hits = T.search_recipes(
            targets=data.get("targets") or {},
            diets=data.get("diets") or [],
            course=data.get("course"),
            query=data.get("query"),
            k=int(data.get("k", 12)),
        )
        return jsonify({"results": hits})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/build")
def api_build():
    """Recipe Lab: generate a custom recipe to targets/diets/course/query, with
    Claude's quantity-based nutrition + a model cross-check + fit. Body:
    {targets, diets, course, query, units}."""
    data = request.get_json(force=True, silent=True) or {}
    reply = companion.build_macro_recipe(
        targets=data.get("targets") or {},
        diets=data.get("diets") or [],
        course=data.get("course"),
        query=data.get("query"),
        units=data.get("units", "metric"),
    )
    return jsonify(reply)


@app.post("/api/expert-review")
def api_expert_review():
    """Generate the kitchen-crew expert review for any recipe on demand (used for
    recipes that don't already carry one, e.g. measured Chef recipes). Body:
    {title, ingredients, steps?, nutrition?, units}."""
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(companion.expert_review_for(
        title=data.get("title", ""),
        ingredients=data.get("ingredients") or [],
        steps=data.get("steps") or [],
        nutrition=data.get("nutrition") or None,
        units=data.get("units", "metric"),
    ))


@app.post("/api/rescale")
def api_rescale():
    """Rescale a recipe to a new serving count (rewrites ingredient + step amounts;
    per-serving nutrition unchanged). Body: {recipe, servings, units}."""
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(companion.rescale_recipe(
        recipe=data.get("recipe") or {},
        servings=data.get("servings"),
        units=data.get("units", "metric"),
    ))


@app.post("/api/recipe-ideas")
def api_recipe_ideas():
    """Recipe Lab "Generate" step 1: propose pickable recipe ideas before building.
    Body: {targets, diets, course, query, units}."""
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(companion.recipe_ideas(
        targets=data.get("targets") or {},
        diets=data.get("diets") or [],
        course=data.get("course"),
        query=data.get("query"),
        units=data.get("units", "metric"),
    ))


@app.get("/api/insights")
def api_insights():
    """Data for the About data-science section: model card + evaluation + the
    curated diet/course options used by the live estimator form."""
    from pipeline import tools as T
    art = ROOT / "artifacts"
    return jsonify({
        "model_card": (art / "model_card.md").read_text(encoding="utf-8"),
        "evaluation": (art / "evaluation_report.md").read_text(encoding="utf-8"),
        "diets": list(T.CURATED_DIETS.keys()),
        "courses": T.COURSES,
    })


@app.get("/insights/eda")
def insights_eda():
    from flask import Response
    html = (ROOT / "artifacts" / "eda_report.html").read_text(encoding="utf-8")
    return Response(html, mimetype="text/html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "has_key": bool(os.environ.get("ANTHROPIC_API_KEY"))})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8600))  # Railway provides $PORT
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
