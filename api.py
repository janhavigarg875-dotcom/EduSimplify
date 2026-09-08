from __future__ import annotations

"""
routes/api.py — EduSimplify Flask API Blueprint.

New endpoint (file upload):
    POST /api/upload   multipart/form-data  file=<pdf|txt>
    Response: {"text": "...extracted text...", "filename": "...", "error": null}

All /api/* endpoints are defined here.
Each endpoint validates input, builds a prompt, calls Granite,
and returns a consistent JSON response.

Response shape (all endpoints):
    200 OK:  {"result": "...generated text...", "error": null}
    400 Bad Request: {"result": null, "error": "...reason..."}
    502 Bad Gateway: {"result": null, "error": "...reason..."}
"""

import io
from flask import Blueprint, request, jsonify
from services.granite_service import (
    GraniteError,
    call_granite,
    build_simplify_prompt,
    build_keypoints_prompt,
    build_terms_prompt,
    build_example_prompt,
    build_summary_prompt,
    build_questions_prompt,
    build_followup_prompt,
)

api_bp = Blueprint("api", __name__)

# ── Constants ────────────────────────────────────────────────────────────────

VALID_LEVELS = {"Beginner", "Intermediate", "Advanced"}
VALID_LANGUAGES = {"English", "Hindi"}
MAX_CONTENT_LENGTH = 5000   # characters
MAX_QUESTION_LENGTH = 500   # characters (follow-up question)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024          # 5 MB hard limit
ALLOWED_EXTENSIONS = {"pdf", "txt"}


# ── Input validation helper ──────────────────────────────────────────────────

def _validate(data: dict) -> str | None:
    """
    Validate the common request fields: content, level, language.

    Returns an error message string if validation fails, or None if valid.
    """
    content = (data.get("content") or "").strip()
    level = data.get("level", "")
    language = data.get("language", "")

    if not content:
        return "Content is required and cannot be empty."

    if len(content) > MAX_CONTENT_LENGTH:
        return (
            f"Content is too long ({len(content)} characters). "
            f"Maximum allowed is {MAX_CONTENT_LENGTH} characters."
        )

    if level not in VALID_LEVELS:
        return (
            f"Invalid level '{level}'. "
            f"Choose one of: {', '.join(sorted(VALID_LEVELS))}."
        )

    if language not in VALID_LANGUAGES:
        return (
            f"Invalid language '{language}'. "
            f"Choose one of: {', '.join(sorted(VALID_LANGUAGES))}."
        )

    return None


def _ok(text: str):
    """Return a standard 200 success response."""
    return jsonify({"result": text, "error": None}), 200


def _bad(message: str):
    """Return a standard 400 validation error response."""
    return jsonify({"result": None, "error": message}), 400


def _gateway_error(message: str):
    """Return a standard 502 upstream error response."""
    return jsonify({"result": None, "error": message}), 502


# ── Endpoints ────────────────────────────────────────────────────────────────

@api_bp.route("/simplify", methods=["POST"])
def simplify():
    """Generate a simplified explanation of the provided academic content."""
    data = request.get_json(silent=True) or {}
    err = _validate(data)
    if err:
        return _bad(err)
    try:
        prompt = build_simplify_prompt(data["content"].strip(), data["level"], data["language"])
        return _ok(call_granite(prompt))
    except GraniteError as exc:
        return _gateway_error(str(exc))


@api_bp.route("/keypoints", methods=["POST"])
def keypoints():
    """Extract 5–7 key points from the provided academic content."""
    data = request.get_json(silent=True) or {}
    err = _validate(data)
    if err:
        return _bad(err)
    try:
        prompt = build_keypoints_prompt(data["content"].strip(), data["level"], data["language"])
        return _ok(call_granite(prompt))
    except GraniteError as exc:
        return _gateway_error(str(exc))


@api_bp.route("/terms", methods=["POST"])
def terms():
    """Identify and define difficult technical terms in the provided content."""
    data = request.get_json(silent=True) or {}
    err = _validate(data)
    if err:
        return _bad(err)
    try:
        prompt = build_terms_prompt(data["content"].strip(), data["level"], data["language"])
        return _ok(call_granite(prompt))
    except GraniteError as exc:
        return _gateway_error(str(exc))


@api_bp.route("/example", methods=["POST"])
def example():
    """Generate a real-world example or analogy for the provided content."""
    data = request.get_json(silent=True) or {}
    err = _validate(data)
    if err:
        return _bad(err)
    try:
        prompt = build_example_prompt(data["content"].strip(), data["level"], data["language"])
        return _ok(call_granite(prompt))
    except GraniteError as exc:
        return _gateway_error(str(exc))


@api_bp.route("/summary", methods=["POST"])
def summary():
    """Generate a short 3–5 sentence summary of the provided content."""
    data = request.get_json(silent=True) or {}
    err = _validate(data)
    if err:
        return _bad(err)
    try:
        prompt = build_summary_prompt(data["content"].strip(), data["level"], data["language"])
        return _ok(call_granite(prompt))
    except GraniteError as exc:
        return _gateway_error(str(exc))


@api_bp.route("/questions", methods=["POST"])
def questions():
    """Generate 5 practice questions with answers for the provided content."""
    data = request.get_json(silent=True) or {}
    err = _validate(data)
    if err:
        return _bad(err)
    try:
        prompt = build_questions_prompt(data["content"].strip(), data["level"], data["language"])
        return _ok(call_granite(prompt))
    except GraniteError as exc:
        return _gateway_error(str(exc))


@api_bp.route("/followup", methods=["POST"])
def followup():
    """Answer a student's follow-up question about the provided content."""
    data = request.get_json(silent=True) or {}

    # Validate common fields first.
    err = _validate(data)
    if err:
        return _bad(err)

    # Also validate the follow-up question field.
    question = (data.get("question") or "").strip()
    if not question:
        return _bad("A follow-up question is required.")
    if len(question) > MAX_QUESTION_LENGTH:
        return _bad(
            f"Question is too long ({len(question)} characters). "
            f"Maximum allowed is {MAX_QUESTION_LENGTH} characters."
        )

    try:
        prompt = build_followup_prompt(
            data["content"].strip(),
            data["level"],
            data["language"],
            question,
        )
        return _ok(call_granite(prompt))
    except GraniteError as exc:
        return _gateway_error(str(exc))


# ── File upload / text extraction ────────────────────────────────────────────

@api_bp.route("/upload", methods=["POST"])
def upload():
    """
    Accept a PDF or plain-text file, extract its text, and return it.

    Validates:
      - A file was included in the request.
      - File extension is .pdf or .txt.
      - File size does not exceed MAX_UPLOAD_BYTES (5 MB).

    Returns:
        200: {"text": "...extracted text...", "filename": "...", "error": null}
        400: {"text": null, "filename": null, "error": "...reason..."}
    """
    if "file" not in request.files:
        return jsonify({"text": None, "filename": None,
                        "error": "No file was included in the request."}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"text": None, "filename": None,
                        "error": "No file was selected."}), 400

    # Validate extension.
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"text": None, "filename": None,
                        "error": (
                            f"Unsupported file type '.{ext}'. "
                            "Please upload a PDF (.pdf) or plain text (.txt) file."
                        )}), 400

    # Read bytes and check size before processing.
    file_bytes = file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        mb = len(file_bytes) / (1024 * 1024)
        return jsonify({"text": None, "filename": None,
                        "error": (
                            f"File is too large ({mb:.1f} MB). "
                            "Maximum allowed size is 5 MB."
                        )}), 400

    # Extract text.
    try:
        if ext == "pdf":
            text = _extract_pdf(file_bytes)
        else:
            # .txt — decode with UTF-8, fall back to latin-1.
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = file_bytes.decode("latin-1")
    except Exception as exc:
        return jsonify({"text": None, "filename": None,
                        "error": f"Could not extract text from the file: {exc}"}), 400

    text = text.strip()
    if not text:
        return jsonify({"text": None, "filename": None,
                        "error": "The file appears to be empty or contains no readable text."}), 400

    return jsonify({"text": text, "filename": file.filename, "error": None}), 200


def _extract_pdf(file_bytes: bytes) -> str:
    """
    Extract plain text from a PDF given its raw bytes.
    Uses pypdf (pure-Python, no system dependencies).

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Concatenated plain text from all pages, pages separated by newlines.

    Raises:
        Exception: If pypdf cannot parse the file.
    """
    from pypdf import PdfReader  # import here so the rest of the app works
                                  # even if pypdf is not installed yet.

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text)

    return "\n\n".join(pages)
