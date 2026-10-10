"""
EduNexus AI — Google Gemini Study Assistant Service
Provides real AI tutoring responses using the official `google-genai` SDK
and the Gemini Interactions API (`gemini-3.8-flash`).
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import httpx

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore[assignment]


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_MESSAGE_LENGTH = 4000
MAX_HISTORY_TURNS = 8

_cached_client: Optional[Any] = None
_cached_client_key: Optional[str] = None

PLACEHOLDER_KEYS = {
    "",
    "your_gemini_api_key_here",
    "your-gemini-api-key-here",
    "your_api_key_here",
    "changeme",
    "placeholder",
}


class StudyAssistantError(RuntimeError):
    """Base error for AI Study Assistant failures."""

    def __init__(self, message: str, error_code: str = "ASSISTANT_ERROR", status_code: int = 500):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


class StudyAssistantConfigError(StudyAssistantError):
    """Raised when GEMINI_API_KEY is missing in environment configuration."""

    def __init__(self, message: str, error_code: str = "MISSING_API_KEY", status_code: int = 503):
        super().__init__(message, error_code=error_code, status_code=status_code)


class StudyAssistantAuthError(StudyAssistantError):
    """Raised when GEMINI_API_KEY is rejected by Google Gemini API (401/403)."""

    def __init__(self, message: str):
        super().__init__(message, error_code="INVALID_API_KEY", status_code=401)


class StudyAssistantModelError(StudyAssistantError):
    """Raised when the configured Gemini model name is invalid or unsupported (400/404)."""

    def __init__(self, message: str):
        super().__init__(message, error_code="INVALID_MODEL", status_code=400)


class StudyAssistantQuotaError(StudyAssistantError):
    """Raised when Gemini API quota or rate limits are exceeded (429)."""

    def __init__(self, message: str):
        super().__init__(message, error_code="QUOTA_EXCEEDED", status_code=429)


class StudyAssistantTimeoutError(StudyAssistantError):
    """Raised when a Gemini API request exceeds the timeout limit (504)."""

    def __init__(self, message: str):
        super().__init__(message, error_code="REQUEST_TIMEOUT", status_code=504)


class StudyAssistantNetworkError(StudyAssistantError):
    """Raised when a network connection or DNS error prevents reaching Gemini API (503)."""

    def __init__(self, message: str):
        super().__init__(message, error_code="NETWORK_ERROR", status_code=503)


class StudyAssistantAPIError(StudyAssistantError):
    """Raised when the Gemini API returns an upstream server error or empty output (502)."""

    def __init__(self, message: str):
        super().__init__(message, error_code="GEMINI_API_ERROR", status_code=502)


def _get_api_key() -> str:
    """Loads GEMINI_API_KEY from the project .env file without logging or exposing the value."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    raw_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if (raw_key.startswith('"') and raw_key.endswith('"')) or (
        raw_key.startswith("'") and raw_key.endswith("'")
    ):
        raw_key = raw_key[1:-1].strip()
    return raw_key


def is_gemini_configured() -> bool:
    """Returns True if a non-placeholder GEMINI_API_KEY is present in the environment."""
    key = _get_api_key()
    return bool(key) and key.lower() not in PLACEHOLDER_KEYS


def build_system_instruction(student_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Builds the academic tutor system instruction for Gemini, grounding in verified
    student performance metrics only when explicitly available.
    """
    base_instruction = (
        "You are the EduNexus AI Study Assistant, an academic tutor for university "
        "computer science and information technology students.\n\n"
        "Core Academic Guidelines:\n"
        "1. Explain academic concepts in clear, structured, beginner-friendly language.\n"
        "2. Help students with Python, Java, C, SQL, DBMS, Data Structures, Algorithms, "
        "Web Development, Computer Networks, Operating Systems, and related subjects.\n"
        "3. Provide step-by-step explanations and concise, well-commented code examples "
        "when appropriate.\n"
        "4. Help students practice by offering short quizzes, trace walkthroughs, or "
        "coding exercises when requested.\n"
        "5. Clearly distinguish verified student data from assumptions.\n"
        "6. Never claim to know a student's grades, scores, attendance, or academic "
        "performance unless that exact information is provided in the Verified Student "
        "Analytics section below."
    )

    if student_context and isinstance(student_context, dict):
        profile = student_context.get("profile") or {}
        metrics = student_context.get("metrics") or {}
        topic_scores = student_context.get("topic_scores") or []
        weak_topics = student_context.get("weak_topics") or []

        topic_summary = ", ".join(
            f"{t.get('topic')}: {t.get('score')}%"
            for t in topic_scores
            if isinstance(t, dict) and t.get("topic") is not None
        ) or "None recorded"

        weak_summary = ", ".join(
            f"{w.get('topic')} ({w.get('score')}% - {w.get('reason', 'needs review')})"
            for w in weak_topics
            if isinstance(w, dict) and w.get("topic") is not None
        ) or "No weak topics currently flagged"

        verified_section = (
            "\n\nVerified Student Analytics (from EduNexus AI database):\n"
            f"- Student Name: {profile.get('name', 'Student')}\n"
            f"- Course: {profile.get('course', 'Data Structures')}\n"
            f"- Overall Score: {metrics.get('overall_score', 'N/A')}%\n"
            f"- On-Time Completion Rate: {metrics.get('completion_rate', 'N/A')}%\n"
            f"- Total Recorded Submissions: {metrics.get('total_submissions', 0)}\n"
            f"- Topic Scores: {topic_summary}\n"
            f"- Detected Weak Topics: {weak_summary}\n"
            "Note: Only the metrics listed above are verified. Do not assume any other "
            "grades or course records not listed here."
        )
        return base_instruction + verified_section

    return (
        base_instruction
        + "\n\nVerified Student Analytics:\n"
        "- No verified individual student performance record is attached to this request. "
        "Do not claim to know the student's personal scores or grades unless the student "
        "explicitly shares them in the conversation."
    )


def _format_input_with_history(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Formats recent conversation turns with the current user message when stateless."""
    if not history or not isinstance(history, list):
        return message

    cleaned_turns: List[str] = []
    for item in history[-MAX_HISTORY_TURNS:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or item.get("text") or "").strip()
        if not content or role not in ("user", "assistant", "model"):
            continue
        speaker = "Student" if role == "user" else "Assistant"
        cleaned_turns.append(f"{speaker}: {content[:1500]}")

    if not cleaned_turns:
        return message

    transcript = "\n\n".join(cleaned_turns)
    return (
        "Recent conversation context:\n"
        f"{transcript}\n\n"
        f"Current student message:\n{message}"
    )


def _extract_interaction_text(interaction: Any) -> str:
    """Extracts the model response text from a Gemini Interaction object."""
    if interaction is None:
        return ""

    # 1. Check convenience property `output_text` on Interaction
    output_text = getattr(interaction, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    # 2. Check `steps` array on Interaction
    steps = getattr(interaction, "steps", None)
    if isinstance(steps, list) and steps:
        collected_parts: List[str] = []
        for step in reversed(steps):
            step_type = getattr(step, "type", None) or (
                step.get("type") if isinstance(step, dict) else None
            )
            if step_type == "model_output":
                content_list = getattr(step, "content", None) or (
                    step.get("content") if isinstance(step, dict) else []
                )
                if isinstance(content_list, list):
                    for part in content_list:
                        part_text = getattr(part, "text", None) or (
                            part.get("text") if isinstance(part, dict) else None
                        )
                        if isinstance(part_text, str) and part_text.strip():
                            collected_parts.append(part_text.strip())
                if collected_parts:
                    break
        if collected_parts:
            return "\n\n".join(collected_parts)

    # 3. Fallback if response has `.text` attribute
    direct_text = getattr(interaction, "text", None)
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    return ""


def _sanitize_error_text(raw_error: str, api_key: str) -> str:
    """Ensures the API key is never included in any error message."""
    if not raw_error:
        return "Unknown error"
    sanitized = raw_error
    if api_key and len(api_key) >= 4:
        sanitized = sanitized.replace(api_key, "[REDACTED]")
    return sanitized


def generate_study_assistant_reply(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    previous_interaction_id: Optional[str] = None,
    student_context: Optional[Dict[str, Any]] = None,
    client_override: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Sends the student's prompt to Google Gemini using the official `google-genai` SDK
    and returns the real model-generated response.
    """
    cleaned_message = (message or "").strip()
    if not cleaned_message:
        raise ValueError("Please enter a question or message for the AI Study Assistant.")

    if len(cleaned_message) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Message is too long ({len(cleaned_message)} characters). "
            f"Please keep messages under {MAX_MESSAGE_LENGTH} characters."
        )

    api_key = _get_api_key()
    if client_override is None and genai is None:
        raise StudyAssistantConfigError(
            "The 'google-genai' SDK is not installed in the active Python environment. "
            "Run '.venv\\Scripts\\pip install -r requirements.txt' and start Flask with '.venv\\Scripts\\python app.py'.",
            error_code="MISSING_SDK",
            status_code=503,
        )

    if client_override is None and (not api_key or api_key.lower() in PLACEHOLDER_KEYS):
        raise StudyAssistantConfigError(
            "AI Study Assistant is unavailable because GEMINI_API_KEY is not configured "
            "on the server. Add your Google AI Studio key to the .env file and restart Flask.",
            error_code="MISSING_API_KEY",
            status_code=503,
        )

    model_name = (os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    system_instruction = build_system_instruction(student_context=student_context)

    try:
        global _cached_client, _cached_client_key
        if client_override is not None:
            client = client_override
        else:
            if _cached_client is None or _cached_client_key != api_key:
                _cached_client = genai.Client(api_key=api_key)
                _cached_client_key = api_key
            client = _cached_client

        thinking_level = "minimal" if "lite" in model_name.lower() else "low"
        interaction_kwargs: Dict[str, Any] = {
            "model": model_name,
            "system_instruction": system_instruction,
            "generation_config": {
                "thinking_level": thinking_level,
                "max_output_tokens": 800,
            },
            "timeout": DEFAULT_TIMEOUT_SECONDS,
        }

        prev_id = (previous_interaction_id or "").strip()
        if prev_id:
            interaction_kwargs["input"] = cleaned_message
            interaction_kwargs["previous_interaction_id"] = prev_id
        else:
            interaction_kwargs["input"] = _format_input_with_history(cleaned_message, history)

        interaction = client.interactions.create(**interaction_kwargs)
        reply_text = _extract_interaction_text(interaction)

        if not reply_text:
            raise StudyAssistantAPIError(
                "Gemini returned an empty response. Please rephrase your question and try again."
            )

        return {
            "reply": reply_text,
            "model": model_name,
            "interaction_id": getattr(interaction, "id", None),
            "grounded_in_student_data": bool(student_context),
        }

    except StudyAssistantError:
        raise
    except (httpx.TimeoutException, TimeoutError) as exc:
        raise StudyAssistantTimeoutError(
            "The request to Google Gemini timed out while generating a response. Please try again."
        ) from exc
    except (httpx.ConnectError, httpx.NetworkError, ConnectionError) as exc:
        raise StudyAssistantNetworkError(
            "Unable to connect to Google Gemini API. Please check your internet connection and try again."
        ) from exc
    except Exception as exc:
        exc_type_name = type(exc).__name__
        status_code = getattr(exc, "status_code", None)
        safe_msg = _sanitize_error_text(str(exc), api_key)
        safe_lower = safe_msg.lower()

        # 1. Distinguish client/server timeouts (e.g. google-genai APITimeoutError)
        if exc_type_name == "APITimeoutError" or "timed out" in safe_lower or "timeout" in safe_lower:
            raise StudyAssistantTimeoutError(
                "The request to Google Gemini timed out while generating a response. Please try again."
            ) from exc

        # 2. Distinguish authentication / invalid API key errors (401 / 403 / API_KEY_INVALID)
        if (
            status_code in (401, 403)
            or exc_type_name in ("AuthenticationError", "PermissionDeniedError")
            or any(
                token in safe_lower
                for token in (
                    "api_key_invalid",
                    "invalid api key",
                    "api key not valid",
                    "permission_denied",
                    "unauthenticated",
                )
            )
        ):
            raise StudyAssistantAuthError(
                "Google Gemini authentication failed: The configured GEMINI_API_KEY was rejected. "
                "Please verify your key in the .env file."
            ) from exc

        # 3. Distinguish quota / rate-limit errors (429 / RESOURCE_EXHAUSTED)
        if (
            status_code == 429
            or exc_type_name == "RateLimitError"
            or any(
                token in safe_lower
                for token in ("429", "quota", "resource_exhausted", "rate limit", "too many requests")
            )
        ):
            raise StudyAssistantQuotaError(
                "The Google Gemini API quota or rate limit has been reached. Please wait a moment and try again."
            ) from exc

        # 4. Distinguish invalid/unsupported model or bad request parameter errors (400 / 404)
        if (
            status_code in (400, 404)
            or exc_type_name in ("NotFoundError", "BadRequestError")
            or ("model" in safe_lower and ("not found" in safe_lower or "not supported" in safe_lower))
        ):
            raise StudyAssistantModelError(
                f"Gemini API rejected the request for model '{model_name}': {safe_msg}"
            ) from exc

        # 5. Distinguish network connection errors (e.g. APIConnectionError)
        if exc_type_name == "APIConnectionError" or any(
            token in safe_lower for token in ("connecterror", "connection error", "name or service not known", "getaddrinfo")
        ):
            raise StudyAssistantNetworkError(
                "Unable to reach Google Gemini API due to a network connection failure. Please check your internet connection."
            ) from exc

        raise StudyAssistantAPIError(
            "Google Gemini API encountered an upstream error while generating a response. Please try again shortly."
        ) from exc
