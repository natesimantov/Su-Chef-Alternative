"""Su Chef — Flask web app (the final UI).

A proper web app: this Flask server serves a single-page Warm Hearth frontend and
exposes JSON/SSE API endpoints that wrap the SAME Python brain the Streamlit app
uses (companion.py, rag.py, pipeline/tools.py, voice.py, artifacts/). One brain,
two front ends. Run locally:  python web/server.py
"""

from __future__ import annotations

import os
import sys
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


@app.route("/")
def index():
    return render_template("index.html")


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
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = _TTS_VOICES.get(data.get("lang", "en"), _TTS_VOICES["en"])
    if not text:
        return jsonify({"error": "no text"}), 400

    async def synth():
        buf = io.BytesIO()
        async for ch in edge_tts.Communicate(text, voice).stream():
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
