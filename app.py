"""
app.py — EduSimplify Flask application entry point.

Loads environment variables from .env, registers the API blueprint,
and serves the static frontend from the /static folder.
"""

import os
from flask import Flask, send_from_directory, jsonify
from dotenv import load_dotenv

# Load credentials from .env before any other import that reads env vars.
load_dotenv()

from routes.api import api_bp  # noqa: E402 — must come after load_dotenv()

app = Flask(__name__, static_folder="static")

# Register all /api/* routes from the blueprint.
app.register_blueprint(api_bp, url_prefix="/api")


# ── Static frontend ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main single-page frontend."""
    return send_from_directory(app.static_folder, "index.html")


# ── Global JSON error handlers (no HTML error pages) ────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"result": None, "error": "Resource not found."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"result": None, "error": "Method not allowed."}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"result": None, "error": "Internal server error."}), 500


if __name__ == "__main__":
    # debug=False is intentional for demo — avoids leaking tracebacks.
    app.run(host="0.0.0.0", port=5000, debug=False)
