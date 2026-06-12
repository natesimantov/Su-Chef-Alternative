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


@app.post("/api/transcribe")
def api_transcribe():
    """Recorded audio blob -> text (faster-whisper, server-side)."""
    f = request.files.get("audio")
    if not f:
        return jsonify({"error": "no audio"}), 400
    import stt
    return jsonify({"text": stt.transcribe(f.read())})


@app.post("/api/predict")
def api_predict():
    """P(quick) for the Insights form. Body: numeric + categorical inputs."""
    from pipeline import tools as T
    data = request.get_json(force=True, silent=True) or {}
    try:
        p = T.predict_quick({
            "num_ingredients": int(data.get("num_ingredients", 8)),
            "num_steps": int(data.get("num_steps", 6)),
            "cuisine": data.get("cuisine", "Other"),
            "course": data.get("course", "Lunch"),
            "diet": data.get("diet", "Unknown"),
        })
        return jsonify({"quick_prob": p})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/insights")
def insights_page():
    """The data-science view: EDA report + live prediction + model card."""
    import json
    art = ROOT / "artifacts"
    contract = json.loads((art / "dataset_contract.json").read_text(encoding="utf-8"))
    return render_template(
        "insights.html",
        eda=(art / "eda_report.html").read_text(encoding="utf-8"),
        model_card=(art / "model_card.md").read_text(encoding="utf-8"),
        evaluation=(art / "evaluation_report.md").read_text(encoding="utf-8"),
        courses=contract["allowed_values"]["course"],
        diets=contract["allowed_values"]["diet"],
    )


@app.get("/insights/eda")
def insights_eda():
    from flask import Response
    html = (ROOT / "artifacts" / "eda_report.html").read_text(encoding="utf-8")
    return Response(html, mimetype="text/html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "has_key": bool(os.environ.get("ANTHROPIC_API_KEY"))})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8600, debug=False, threaded=True)
