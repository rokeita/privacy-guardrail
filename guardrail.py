#!/usr/bin/env python3
"""Privacy guardrail: redact sensitive data, then summarize with Gemini."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors

# Credit cards: 13–19 digits, optional spaces/dashes between groups (e.g. Visa/MC).
CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{1,4}\b|\b\d{13,19}\b"
)

# Standard email addresses.
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# GhanaCard / Ghanaian national ID: GHA-#########-# (9 digits, then check digit).
GHANA_CARD_PATTERN = re.compile(
    r"\bGHA-\d{9}-\d\b",
    re.IGNORECASE,
)

# Common phone formats (international + local-style): +233..., 0XX..., with spaces/dashes.
PHONE_PATTERN = re.compile(
    r"\+?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
)

REDACTION_RULES: list[tuple[re.Pattern[str], str]] = [
    (CREDIT_CARD_PATTERN, "[REDACTED_CREDIT_CARD]"),
    (EMAIL_PATTERN, "[REDACTED_EMAIL]"),
    (GHANA_CARD_PATTERN, "[REDACTED_GHANA_CARD]"),
    (PHONE_PATTERN, "[REDACTED_PHONE]"),
]

# gemini-3.5-flash is available on the free tier for this project.
GEMINI_MODEL = "gemini-3.5-flash"


def redact_sensitive_data(text: str) -> str:
    """Replace matched sensitive patterns with placeholder tokens."""
    redacted = text
    for pattern, replacement in REDACTION_RULES:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def summarize_with_gemini(safe_text: str) -> str:
    """Send redacted text to Gemini and return a short executive summary."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing API key. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment."
        )

    client = genai.Client(api_key=api_key)
    prompt = (
        "Write a short executive summary of the following text. "
        "It has already been privacy-redacted; do not invent missing PII. "
        "Keep the summary concise (3–5 sentences).\n\n"
        f"{safe_text}"
    )

    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            text = (response.text or "").strip()
            if text:
                return text
        except genai_errors.ServerError as exc:
            # 503 high demand: exponential backoff then retry.
            last_error = exc
            wait = min(30, 3 * (2 ** (attempt - 1)))
            print(f"(Model busy, retry {attempt}/5 in {wait}s…)")
            time.sleep(wait)
        except Exception as exc:
            last_error = exc
            wait = min(30, 3 * (2 ** (attempt - 1)))
            print(f"(Request error, retry {attempt}/5 in {wait}s…)")
            time.sleep(wait)

    raise SystemExit(f"Gemini summary failed with {GEMINI_MODEL}: {last_error}")


def main() -> None:
    input_path = Path(__file__).resolve().parent / "text_to_scan.txt"
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    original = input_path.read_text(encoding="utf-8")
    safe = redact_sensitive_data(original)

    print("=== Redacted (safe) text ===")
    print(safe)
    print()

    summary = summarize_with_gemini(safe)
    print("=== Gemini executive summary ===")
    print(summary)


if __name__ == "__main__":
    main()
