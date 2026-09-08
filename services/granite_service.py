from __future__ import annotations

"""
services/granite_service.py — IBM watsonx.ai / Granite integration.

All communication with IBM Granite happens here.
Credentials are read from environment variables only — never hard-coded.

Public API:
    call_granite(prompt, max_tokens=800) -> str
    build_simplify_prompt(content, level, language) -> str
    build_keypoints_prompt(content, level, language) -> str
    build_terms_prompt(content, level, language) -> str
    build_example_prompt(content, level, language) -> str
    build_summary_prompt(content, level, language) -> str
    build_questions_prompt(content, level, language) -> str
    build_followup_prompt(content, level, language, question) -> str
"""

import os
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

# ── Model identifier ─────────────────────────────────────────────────────────
MODEL_ID = "ibm/granite-4-h-small"

# ── Custom exception ─────────────────────────────────────────────────────────

class GraniteError(Exception):
    """Raised when the IBM Granite API call fails for any reason."""


# ── Lazy-initialised model client ────────────────────────────────────────────
# The client is created once on the first call, not at import time,
# so that missing env vars produce a clear GraniteError at call time.

_model: ModelInference | None = None


def _get_model() -> ModelInference:
    """Return a cached ModelInference client, creating it if needed."""
    global _model
    if _model is not None:
        return _model

    api_key = os.environ.get("WATSONX_APIKEY")
    project_id = os.environ.get("WATSONX_PROJECT_ID")
    url = os.environ.get("WATSONX_URL")

    missing = [name for name, val in [
        ("WATSONX_APIKEY", api_key),
        ("WATSONX_PROJECT_ID", project_id),
        ("WATSONX_URL", url),
    ] if not val]

    if missing:
        raise GraniteError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Please check your .env file."
        )

    try:
        credentials = Credentials(url=url, api_key=api_key)
        _model = ModelInference(
            model_id=MODEL_ID,
            credentials=credentials,
            project_id=project_id,
        )
    except Exception as exc:
        # Do not include the API key in the error message.
        raise GraniteError(f"Failed to initialise Granite client: {exc}") from exc

    return _model


# ── Core inference call ───────────────────────────────────────────────────────

def call_granite(prompt: str, max_tokens: int = 800) -> str:
    """
    Send a prompt to IBM Granite and return the generated text.

    ibm/granite-4-h-small is a chat model — it must be called via
    model.chat(messages=[...]) using the OpenAI-compatible messages format.
    Calling generate_text() on this model returns an empty string.

    Args:
        prompt:     The fully-built instruction prompt (treated as a user message).
        max_tokens: Maximum number of tokens in the response.

    Returns:
        The generated text string (stripped of leading/trailing whitespace).

    Raises:
        GraniteError: On authentication failure, network error, or empty response.
    """
    model = _get_model()

    # Granite 4 chat format: system persona + user content.
    messages = [
        {
            "role": "system",
            "content": (
                "You are EduSimplify, a friendly and patient academic tutor. "
                "Always respond clearly, accurately, and helpfully."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    params = {
        "max_tokens": max_tokens,   # chat API uses "max_tokens", not "max_new_tokens"
        "temperature": 0.7,
    }

    try:
        response = model.chat(messages=messages, params=params)
    except Exception as exc:
        raise GraniteError(f"Granite API call failed: {exc}") from exc

    # Extract text from the chat response structure.
    # Shape: {"choices": [{"message": {"content": "..."}}], ...}
    try:
        text = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        # Fallback: if the response is already a plain string (SDK version difference)
        text = response if isinstance(response, str) else ""

    if not text or not text.strip():
        raise GraniteError("Granite returned an empty response. Please try again.")

    return text.strip()


# ── Shared system preamble ────────────────────────────────────────────────────

_PREAMBLE = (
    "You are EduSimplify, a friendly and patient academic tutor assistant. "
    "Your job is to help students understand complex academic content. "
    "Always be clear, encouraging, and accurate.\n\n"
)


# ── Prompt builders ───────────────────────────────────────────────────────────

def build_simplify_prompt(content: str, level: str, language: str) -> str:
    """
    Build a prompt that asks Granite to re-explain the content
    in simpler language for the given student level.
    """
    lang_instruction = (
        "Respond entirely in Hindi." if language == "Hindi"
        else "Respond in clear, simple English."
    )
    return (
        f"{_PREAMBLE}"
        f"Task: Simplify the following academic content for a {level}-level student.\n"
        f"{lang_instruction}\n"
        f"Use short sentences. Avoid unnecessary jargon. "
        f"If you must use a technical term, explain it briefly in brackets.\n\n"
        f"Academic Content:\n{content}\n\n"
        f"Simplified Explanation:"
    )


def build_keypoints_prompt(content: str, level: str, language: str) -> str:
    """
    Build a prompt that asks Granite to extract 5–7 numbered key points.
    """
    lang_instruction = (
        "Respond entirely in Hindi." if language == "Hindi"
        else "Respond in clear, simple English."
    )
    return (
        f"{_PREAMBLE}"
        f"Task: Extract the 5 to 7 most important key points from the following "
        f"academic content. Write them as a numbered list suitable for a "
        f"{level}-level student.\n"
        f"{lang_instruction}\n\n"
        f"Academic Content:\n{content}\n\n"
        f"Key Points:"
    )


def build_terms_prompt(content: str, level: str, language: str) -> str:
    """
    Build a prompt that asks Granite to identify and define difficult terms.
    """
    lang_instruction = (
        "Respond entirely in Hindi." if language == "Hindi"
        else "Respond in clear, simple English."
    )
    return (
        f"{_PREAMBLE}"
        f"Task: Identify all difficult or technical terms in the following academic "
        f"content and provide a simple definition for each one, suitable for a "
        f"{level}-level student. Format each entry as:\n"
        f"Term: [term name]\nDefinition: [simple definition]\n\n"
        f"{lang_instruction}\n\n"
        f"Academic Content:\n{content}\n\n"
        f"Difficult Terms and Definitions:"
    )


def build_example_prompt(content: str, level: str, language: str) -> str:
    """
    Build a prompt that asks Granite for one clear real-world analogy or example.
    """
    lang_instruction = (
        "Respond entirely in Hindi." if language == "Hindi"
        else "Respond in clear, simple English."
    )
    return (
        f"{_PREAMBLE}"
        f"Task: Give one clear, relatable real-world example or analogy that helps "
        f"a {level}-level student understand the following academic content. "
        f"Keep it simple and relevant.\n"
        f"{lang_instruction}\n\n"
        f"Academic Content:\n{content}\n\n"
        f"Real-World Example:"
    )


def build_summary_prompt(content: str, level: str, language: str) -> str:
    """
    Build a prompt that asks Granite for a 3–5 sentence plain-language summary.
    """
    lang_instruction = (
        "Respond entirely in Hindi." if language == "Hindi"
        else "Respond in clear, simple English."
    )
    return (
        f"{_PREAMBLE}"
        f"Task: Write a short summary (3 to 5 sentences) of the following academic "
        f"content for a {level}-level student. Use simple, plain language.\n"
        f"{lang_instruction}\n\n"
        f"Academic Content:\n{content}\n\n"
        f"Summary:"
    )


def build_questions_prompt(content: str, level: str, language: str) -> str:
    """
    Build a prompt that asks Granite to generate 5 practice questions with answers.
    """
    lang_instruction = (
        "Respond entirely in Hindi." if language == "Hindi"
        else "Respond in clear, simple English."
    )
    return (
        f"{_PREAMBLE}"
        f"Task: Generate exactly 5 practice questions based on the following academic "
        f"content, suitable for a {level}-level student. "
        f"After each question, provide a short answer.\n"
        f"Format:\nQ1. [question]\nA1. [answer]\n(and so on up to Q5/A5)\n\n"
        f"{lang_instruction}\n\n"
        f"Academic Content:\n{content}\n\n"
        f"Practice Questions:"
    )


def build_followup_prompt(
    content: str, level: str, language: str, question: str
) -> str:
    """
    Build a prompt that asks Granite to answer a specific follow-up question
    about the provided academic content.
    """
    lang_instruction = (
        "Respond entirely in Hindi." if language == "Hindi"
        else "Respond in clear, simple English."
    )
    return (
        f"{_PREAMBLE}"
        f"Task: A {level}-level student has read the following academic content and "
        f"is asking a follow-up question. Answer the question clearly and helpfully, "
        f"referring to the content where relevant.\n"
        f"{lang_instruction}\n\n"
        f"Academic Content:\n{content}\n\n"
        f"Student's Question: {question}\n\n"
        f"Answer:"
    )
