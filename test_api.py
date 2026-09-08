"""
tests/test_api.py — EduSimplify test suite.

Tests are split into two groups:
  1. Unit tests for prompt builder functions (no network calls).
  2. Integration tests for Flask API routes using a mocked call_granite.

Run with:  pytest tests/ -v
"""

import sys
import types
import os
import pytest
from unittest.mock import patch


# ── Stub out ibm_watsonx_ai before importing app modules ─────────────────────
# This prevents ImportError when the SDK is not installed in the test environment.
def _stub_ibm_sdk():
    """Insert a minimal stub for ibm_watsonx_ai into sys.modules."""
    if "ibm_watsonx_ai" in sys.modules:
        return  # already present (real or stub)

    pkg = types.ModuleType("ibm_watsonx_ai")
    creds = types.ModuleType("ibm_watsonx_ai.foundation_models")

    class _Credentials:
        def __init__(self, url=None, api_key=None): pass

    class _ModelInference:
        def __init__(self, **kwargs): pass
        def generate_text(self, prompt, params): return "stub response"
        def chat(self, messages, params=None):
            return {"choices": [{"message": {"content": "stub response"}}]}

    pkg.Credentials = _Credentials
    creds.ModelInference = _ModelInference

    sys.modules["ibm_watsonx_ai"] = pkg
    sys.modules["ibm_watsonx_ai.foundation_models"] = creds
    # Also expose Credentials at the top-level package path used by the service.
    pkg.foundation_models = creds


_stub_ibm_sdk()

# Now safe to import application modules.
from services.granite_service import (  # noqa: E402
    build_simplify_prompt,
    build_keypoints_prompt,
    build_terms_prompt,
    build_example_prompt,
    build_summary_prompt,
    build_questions_prompt,
    build_followup_prompt,
)


# ════════════════════════════════════════════════════════════════════════════
# 1. Unit tests — prompt builder functions
# ════════════════════════════════════════════════════════════════════════════

SAMPLE_CONTENT = "Photosynthesis is the process by which plants convert light energy into glucose."


class TestBuildSimplifyPrompt:
    def test_contains_level(self):
        p = build_simplify_prompt(SAMPLE_CONTENT, "Beginner", "English")
        assert "Beginner" in p

    def test_contains_task_keyword(self):
        p = build_simplify_prompt(SAMPLE_CONTENT, "Intermediate", "English")
        assert "Simplif" in p or "simplif" in p

    def test_hindi_instruction(self):
        p = build_simplify_prompt(SAMPLE_CONTENT, "Beginner", "Hindi")
        assert "Hindi" in p

    def test_content_included(self):
        p = build_simplify_prompt(SAMPLE_CONTENT, "Advanced", "English")
        assert SAMPLE_CONTENT in p


class TestBuildKeypointsPrompt:
    def test_contains_level(self):
        p = build_keypoints_prompt(SAMPLE_CONTENT, "Beginner", "English")
        assert "Beginner" in p

    def test_numbered_list_mention(self):
        p = build_keypoints_prompt(SAMPLE_CONTENT, "Intermediate", "English")
        assert "numbered" in p.lower() or "list" in p.lower()

    def test_hindi_instruction(self):
        p = build_keypoints_prompt(SAMPLE_CONTENT, "Advanced", "Hindi")
        assert "Hindi" in p


class TestBuildTermsPrompt:
    def test_contains_level(self):
        p = build_terms_prompt(SAMPLE_CONTENT, "Beginner", "English")
        assert "Beginner" in p

    def test_format_instruction(self):
        p = build_terms_prompt(SAMPLE_CONTENT, "Intermediate", "English")
        assert "Term" in p and "Definition" in p


class TestBuildExamplePrompt:
    def test_contains_level(self):
        p = build_example_prompt(SAMPLE_CONTENT, "Beginner", "English")
        assert "Beginner" in p

    def test_realworld_keyword(self):
        p = build_example_prompt(SAMPLE_CONTENT, "Intermediate", "English")
        assert "example" in p.lower() or "analogy" in p.lower()


class TestBuildSummaryPrompt:
    def test_contains_level(self):
        p = build_summary_prompt(SAMPLE_CONTENT, "Advanced", "English")
        assert "Advanced" in p

    def test_sentence_count_hint(self):
        p = build_summary_prompt(SAMPLE_CONTENT, "Beginner", "English")
        assert "3" in p and "5" in p


class TestBuildQuestionsPrompt:
    def test_contains_level(self):
        p = build_questions_prompt(SAMPLE_CONTENT, "Intermediate", "English")
        assert "Intermediate" in p

    def test_five_questions_hint(self):
        p = build_questions_prompt(SAMPLE_CONTENT, "Beginner", "English")
        assert "5" in p

    def test_format_includes_answer(self):
        p = build_questions_prompt(SAMPLE_CONTENT, "Beginner", "English")
        assert "answer" in p.lower() or "A1" in p


class TestBuildFollowupPrompt:
    def test_contains_question(self):
        question = "What is glucose?"
        p = build_followup_prompt(SAMPLE_CONTENT, "Beginner", "English", question)
        assert question in p

    def test_contains_level(self):
        p = build_followup_prompt(SAMPLE_CONTENT, "Advanced", "English", "Why?")
        assert "Advanced" in p

    def test_hindi_instruction(self):
        p = build_followup_prompt(SAMPLE_CONTENT, "Beginner", "Hindi", "What?")
        assert "Hindi" in p


# ════════════════════════════════════════════════════════════════════════════
# 2. Integration tests — Flask routes with mocked call_granite
# ════════════════════════════════════════════════════════════════════════════

MOCK_RESPONSE = "This is a mock Granite response."

VALID_PAYLOAD = {
    "content": SAMPLE_CONTENT,
    "level": "Beginner",
    "language": "English",
}


@pytest.fixture()
def client():
    """Flask test client with call_granite mocked to avoid real IBM calls."""
    with patch("routes.api.call_granite", return_value=MOCK_RESPONSE):
        # Import app after patching so the mock is active.
        import app as flask_app
        flask_app.app.config["TESTING"] = True
        with flask_app.app.test_client() as c:
            yield c


# ── Helper ───────────────────────────────────────────────────────────────────

def post(client, endpoint, payload):
    return client.post(
        f"/api/{endpoint}",
        json=payload,
        content_type="application/json",
    )


# ── Happy-path tests (one per endpoint) ─────────────────────────────────────

@pytest.mark.parametrize("endpoint", [
    "simplify", "keypoints", "terms", "example", "summary", "questions",
])
def test_feature_endpoints_happy_path(client, endpoint):
    res = post(client, endpoint, VALID_PAYLOAD)
    assert res.status_code == 200
    data = res.get_json()
    assert data["error"] is None
    assert data["result"] == MOCK_RESPONSE


def test_followup_happy_path(client):
    payload = {**VALID_PAYLOAD, "question": "What is photosynthesis?"}
    res = post(client, "followup", payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["error"] is None
    assert data["result"] == MOCK_RESPONSE


# ── Validation: missing content ──────────────────────────────────────────────

@pytest.mark.parametrize("endpoint", [
    "simplify", "keypoints", "terms", "example", "summary", "questions",
])
def test_missing_content_returns_400(client, endpoint):
    payload = {"level": "Beginner", "language": "English"}
    res = post(client, endpoint, payload)
    assert res.status_code == 400
    assert res.get_json()["error"] is not None


# ── Validation: empty content ─────────────────────────────────────────────────

def test_empty_content_returns_400(client):
    payload = {"content": "   ", "level": "Beginner", "language": "English"}
    res = post(client, "simplify", payload)
    assert res.status_code == 400


# ── Validation: content too long ─────────────────────────────────────────────

def test_content_too_long_returns_400(client):
    payload = {"content": "x" * 5001, "level": "Beginner", "language": "English"}
    res = post(client, "simplify", payload)
    assert res.status_code == 400
    assert "5000" in res.get_json()["error"]


# ── Validation: invalid level ─────────────────────────────────────────────────

def test_invalid_level_returns_400(client):
    payload = {**VALID_PAYLOAD, "level": "Expert"}
    res = post(client, "simplify", payload)
    assert res.status_code == 400


# ── Validation: invalid language ─────────────────────────────────────────────

def test_invalid_language_returns_400(client):
    payload = {**VALID_PAYLOAD, "language": "French"}
    res = post(client, "simplify", payload)
    assert res.status_code == 400


# ── Validation: follow-up missing question ────────────────────────────────────

def test_followup_missing_question_returns_400(client):
    res = post(client, "followup", VALID_PAYLOAD)
    assert res.status_code == 400
    assert "question" in res.get_json()["error"].lower()


# ── Validation: follow-up empty question ─────────────────────────────────────

def test_followup_empty_question_returns_400(client):
    payload = {**VALID_PAYLOAD, "question": "   "}
    res = post(client, "followup", payload)
    assert res.status_code == 400


# ── GraniteError → 502 ───────────────────────────────────────────────────────

def test_granite_error_returns_502(client):
    from services.granite_service import GraniteError
    with patch("routes.api.call_granite", side_effect=GraniteError("API down")):
        res = post(client, "simplify", VALID_PAYLOAD)
    assert res.status_code == 502
    assert "API down" in res.get_json()["error"]


# ── 404 returns JSON ──────────────────────────────────────────────────────────

def test_404_returns_json(client):
    res = client.get("/api/nonexistent")
    assert res.status_code == 404
    data = res.get_json()
    assert "error" in data


# ── Check #1: Backend starts and serves frontend ─────────────────────────────

def test_backend_starts_and_serves_frontend(client):
    """The Flask app must start and return the HTML frontend on GET /."""
    res = client.get("/")
    assert res.status_code == 200
    # The page must contain the app name so we know it is the real frontend.
    assert b"EduSimplify" in res.data


# ── Check #16: Missing credentials produce a safe GraniteError ───────────────

def test_missing_credentials_raise_granite_error():
    """
    When env vars are absent, _get_model() must raise GraniteError
    with a helpful message — it must NOT expose the key or crash uncaught.
    """
    import services.granite_service as svc

    # Save and clear the cached model so _get_model() re-runs the credential check.
    original_model = svc._model
    svc._model = None

    # Remove the three required env vars (save originals to restore later).
    keys = ("WATSONX_APIKEY", "WATSONX_PROJECT_ID", "WATSONX_URL")
    saved = {k: os.environ.pop(k, None) for k in keys}

    try:
        with pytest.raises(svc.GraniteError, match="Missing required environment variable"):
            svc._get_model()
    finally:
        # Always restore env and cache — never leave the environment dirty.
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
        svc._model = original_model


# ════════════════════════════════════════════════════════════════════════════
# 3. Upload endpoint tests — /api/upload
#
# Werkzeug's EnvironBuilder requires FileStorage objects for multipart uploads
# when using BytesIO — plain tuples are treated as file paths.
# ════════════════════════════════════════════════════════════════════════════

import io as _io
from werkzeug.datastructures import FileStorage


def _make_file(content: bytes, filename: str, mimetype: str = "text/plain") -> FileStorage:
    """Wrap bytes in a FileStorage so Werkzeug test client handles it correctly."""
    return FileStorage(
        stream=_io.BytesIO(content),
        filename=filename,
        content_type=mimetype,
    )


def _txt_storage(content: str = "Hello world this is test content.", name: str = "test.txt") -> FileStorage:
    return _make_file(content.encode(), name, "text/plain")


def _pdf_bytes_minimal() -> bytes:
    """Return the smallest valid PDF that pypdf can parse (1 empty page)."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    )


# ── Happy path: .txt upload ───────────────────────────────────────────────

def test_upload_txt_happy_path(client):
    res = client.post(
        "/api/upload",
        data={"file": _txt_storage("Photosynthesis converts light into glucose.")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["error"] is None
    assert "Photosynthesis" in data["text"]
    assert data["filename"] == "test.txt"


# ── Happy path: .pdf upload (minimal valid PDF, no text content) ──────────

def test_upload_pdf_accepted(client):
    """A valid PDF is accepted; an empty PDF returns 400 with a clear message."""
    res = client.post(
        "/api/upload",
        data={"file": _make_file(_pdf_bytes_minimal(), "doc.pdf", "application/pdf")},
        content_type="multipart/form-data",
    )
    # The minimal PDF has no text pages — backend returns 400 "empty or no readable text"
    assert res.status_code == 400
    err = res.get_json()["error"].lower()
    assert "empty" in err or "readable" in err


# ── Validation: no file field ─────────────────────────────────────────────

def test_upload_no_file_returns_400(client):
    res = client.post("/api/upload", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert res.get_json()["error"] is not None


# ── Validation: wrong extension ───────────────────────────────────────────

def test_upload_wrong_extension_returns_400(client):
    res = client.post(
        "/api/upload",
        data={"file": _make_file(b"binary content", "notes.docx", "application/octet-stream")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    err = res.get_json()["error"].lower()
    assert "docx" in err or "unsupported" in err


# ── Validation: file too large ────────────────────────────────────────────

def test_upload_too_large_returns_400(client):
    big_content = b"x" * (5 * 1024 * 1024 + 1)   # 5 MB + 1 byte
    res = client.post(
        "/api/upload",
        data={"file": _make_file(big_content, "big.txt", "text/plain")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    err = res.get_json()["error"].lower()
    assert "large" in err or "5 mb" in err or "5.0 mb" in err


# ── Validation: empty .txt file ───────────────────────────────────────────

def test_upload_empty_txt_returns_400(client):
    res = client.post(
        "/api/upload",
        data={"file": _make_file(b"   \n  ", "empty.txt", "text/plain")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert "empty" in res.get_json()["error"].lower()


# ── Response shape always contains text, filename, error keys ────────────

def test_upload_response_shape(client):
    res = client.post(
        "/api/upload",
        data={"file": _txt_storage("Some academic content here.")},
        content_type="multipart/form-data",
    )
    data = res.get_json()
    assert "text" in data
    assert "filename" in data
    assert "error" in data
