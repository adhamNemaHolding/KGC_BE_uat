"""
OpenAI client — single point of contact for all LLM calls.

Every AI service in the project calls `chat_completion()` from here.
Swap the provider (e.g., to Gemini) by changing only this file.

Reliability features:
  - 60s timeout per call
  - Automatic retry (2 attempts) on transient failures
  - JSON parse validation with fallback
  - Structured logging
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from django.conf import settings
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

MAX_RETRIES = 2
TIMEOUT_SECONDS = 60


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=TIMEOUT_SECONDS,
            max_retries=0,  # We handle retries ourselves for better logging
        )
    return _client


def chat_completion(
    prompt: str,
    *,
    temperature: float = 0.7,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Send a prompt and return parsed JSON.

    Retries on transient errors (timeout, connection, rate limit).
    Raises ValueError if the response isn't valid JSON after retries.
    """
    client = _get_client()
    used_model = model or settings.OPENAI_MODEL
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=used_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=temperature,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("OpenAI returned empty content")

            logger.debug("OpenAI response (%s, attempt %d): %s", used_model, attempt, content[:200])

            # Validate JSON
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("OpenAI returned invalid JSON (attempt %d): %s", attempt, content[:500])
                raise ValueError(f"AI returned malformed JSON: {e}") from e

            if not isinstance(parsed, dict):
                raise ValueError(f"AI returned {type(parsed).__name__}, expected dict")

            return parsed

        except (APITimeoutError, APIConnectionError, RateLimitError) as e:
            last_error = e
            wait = 2 ** attempt  # Exponential backoff: 2s, 4s
            logger.warning(
                "OpenAI transient error (attempt %d/%d): %s — retrying in %ds",
                attempt, MAX_RETRIES, e, wait,
            )
            if attempt < MAX_RETRIES:
                time.sleep(wait)
            continue

        except ValueError:
            raise  # Don't retry parse errors

        except Exception as e:
            logger.error("OpenAI unexpected error: %s", e)
            raise

    # All retries exhausted
    raise ConnectionError(f"OpenAI unavailable after {MAX_RETRIES} attempts: {last_error}")
