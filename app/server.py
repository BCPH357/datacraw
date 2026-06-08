"""Live web server for the LINE persona report.

Flow: the browser loads the React upload page (``/``); the user drops a LINE
``.txt`` which is POSTed to ``/analyze``; the backend runs the full pipeline and
returns the ``APP_DATA`` payload; the same single-page app then renders the main
report screen from that real data — no page reload, no files written to disk.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import cluster_interpreter, pipeline, webreport

DESIGN_DIR = ROOT / "claude_design"
ASSETS_DIR = DESIGN_DIR / "app"
SAMPLE_FILE = ROOT / "tests" / "fixtures" / "sample_chat.txt"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB upload cap


def _app_data_from_text(
    text: str,
    mode: str = "rule",
    cluster_count: str = "auto",
) -> dict:
    """Run the pipeline and return APP_DATA flagged for the live (upload) flow."""

    result = pipeline.analyze_text(text, mode=mode, cluster_count=cluster_count)
    app_data = result["app_data"]
    # In the live flow data arrives *after* upload, so keep the upload/re-analyze
    # affordances available (do not auto-skip the upload screen).
    app_data["__embedded"] = False
    return app_data


@app.get("/")
def index() -> str:
    return webreport.render_upload_page(ASSETS_DIR)


@app.get("/app/<path:filename>")
def assets(filename: str):
    return send_from_directory(ASSETS_DIR, filename)


@app.post("/analyze")
def analyze():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "沒有收到檔案，請選擇一份 LINE 匯出的 .txt。"}), 400
    mode = request.form.get("mode", "rule")
    cluster_count = request.form.get("cluster_count", "auto")
    text = uploaded.read().decode("utf-8-sig", errors="replace")
    try:
        return jsonify(_app_data_from_text(text, mode=mode, cluster_count=cluster_count))
    except cluster_interpreter.ClusterInterpretationError as error:
        return jsonify({"error": str(error)}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:  # noqa: BLE001 - surface a friendly message
        return jsonify({"error": f"分析失敗：{error}"}), 500


@app.get("/sample")
def sample():
    if not SAMPLE_FILE.exists():
        abort(404)
    text = SAMPLE_FILE.read_text(encoding="utf-8")
    mode = request.args.get("mode", "rule")
    cluster_count = request.args.get("cluster_count", "auto")
    try:
        return jsonify(_app_data_from_text(text, mode=mode, cluster_count=cluster_count))
    except cluster_interpreter.ClusterInterpretationError as error:
        return jsonify({"error": str(error)}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


def main() -> None:
    import argparse

    arg_parser = argparse.ArgumentParser(description="Serve the LINE persona report.")
    arg_parser.add_argument("--host", default="127.0.0.1")
    arg_parser.add_argument("--port", type=int, default=8000)
    args = arg_parser.parse_args()
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
