"""
Bilingual AI service — generates content in both English and Arabic simultaneously.

This service generates AI responses in both languages in a single API call,
allowing the frontend to instantly display content in either language without
additional requests.
"""

from __future__ import annotations

import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.conf import settings
from django.core.cache import cache

from integrations.openai_client import chat_completion

logger = logging.getLogger(__name__)

# Cache TTL for bilingual AI results — same profile = same answer for an hour.
_BILINGUAL_CACHE_TTL_SECONDS = 60 * 60


def _profile_cache_key(prefix: str, payload: Any) -> str:
    """Stable cache key from any JSON-serialisable payload."""
    blob = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"advisor:bilingual:{prefix}:{digest}"


def _fast_model() -> str | None:
    """
    Optional faster model for non-critical bilingual generation.

    Set OPENAI_FAST_MODEL=gpt-4o-mini in your .env to use a much faster
    model for competencies/interests; falls back to OPENAI_MODEL if unset.
    """
    return getattr(settings, "OPENAI_FAST_MODEL", None) or None


# Fields the questions prompt does NOT need; dropping them shrinks input tokens
# substantially (objective_measurable_behavior is the largest per-category field).
_QUESTIONS_PROMPT_DROP_FIELDS = ("objective_measurable_behavior",)


def _slim_competencies_for_questions(competencies: Any) -> Any:
    """
    Reduce the competencies payload to the minimum the questions prompt needs.

    Two pure-token optimizations (no logic change — the LLM still sees the same
    set of competencies, just less verbose):

      1. If the caller passed the bilingual competencies dict
         ({"en": {...}, "ar": {...}}) we collapse it to just the EN category
         list (the questions prompt only needs ONE language to generate
         statements; it produces both languages itself). This roughly halves
         input tokens.

      2. Strip per-category fields the questions prompt doesn't reference
         (currently `objective_measurable_behavior`, the longest field).
         Each category is left with: name, type, definition, behavioral_description.

    If the input shape is unrecognised, return it unchanged so we never break
    a caller that passes something custom.
    """
    if competencies is None:
        return None

    raw_categories: list[Any] | None = None

    if isinstance(competencies, dict):
        for lang_key in ("en", "ar"):
            block = competencies.get(lang_key)
            if isinstance(block, dict):
                cats = block.get("categories")
                if isinstance(cats, list):
                    raw_categories = cats
                    break
        if raw_categories is None:
            cats = competencies.get("categories")
            if isinstance(cats, list):
                raw_categories = cats
    elif isinstance(competencies, list):
        raw_categories = competencies

    if raw_categories is None:
        return competencies

    slim: list[dict] = []
    for cat in raw_categories:
        if not isinstance(cat, dict):
            slim.append(cat)
            continue
        slim.append({
            k: v for k, v in cat.items()
            if k not in _QUESTIONS_PROMPT_DROP_FIELDS
        })
    return slim


def generate_bilingual_interests(profile_data: dict) -> dict[str, list[str]]:
    """Generate interests in both English and Arabic simultaneously."""
    from .prompts import interests as interests_prompt

    prompt_en = interests_prompt.build_prompt(profile_data, language="en")
    prompt_ar = interests_prompt.build_prompt(profile_data, language="ar")

    # Run EN + AR in parallel — sequential calls roughly doubled wait time.
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_en = pool.submit(chat_completion, prompt_en, temperature=0.7)
        fut_ar = pool.submit(chat_completion, prompt_ar, temperature=0.7)
        result_en = fut_en.result()
        result_ar = fut_ar.result()

    return {
        "en": {
            "interests": result_en.get("interests", []),
        },
        "ar": {
            "interests": result_ar.get("interests", []),
        },
    }


def generate_bilingual_competencies(profile_data: dict) -> dict[str, Any]:
    """
    Generate competency categories in both English and Arabic.

    Optimized path:
      1. Result cache keyed by profile content (instant for repeats).
      2. ONE OpenAI call that returns {"en": ..., "ar": ...} in a single JSON
         response (eliminates a full network round-trip + JSON-mode TTFT).
      3. Optional faster model via OPENAI_FAST_MODEL (e.g. gpt-4o-mini).

    If the single-call response is malformed in a way we can't recover from,
    fall back to the original two-parallel-calls path so behavior is preserved.
    """
    from .prompts import competencies as competencies_prompt

    cache_key = _profile_cache_key("competencies", profile_data)
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info("bilingual competencies cache hit")
        return cached

    bilingual_prompt = competencies_prompt.build_bilingual_prompt(profile_data)
    fast_model = _fast_model()

    try:
        result = chat_completion(bilingual_prompt, temperature=0.7, model=fast_model)
        en_block = result.get("en") if isinstance(result, dict) else None
        ar_block = result.get("ar") if isinstance(result, dict) else None
        if isinstance(en_block, dict) and isinstance(ar_block, dict):
            payload = {"en": en_block, "ar": ar_block}
            cache.set(cache_key, payload, _BILINGUAL_CACHE_TTL_SECONDS)
            return payload
        logger.warning(
            "Single-call bilingual competencies returned unexpected shape; "
            "falling back to two parallel calls."
        )
    except Exception as exc:
        logger.warning(
            "Single-call bilingual competencies failed (%s); falling back to two parallel calls.",
            exc,
        )

    # Fallback: legacy two-parallel-calls path — same as before the optimization.
    prompt_en = competencies_prompt.build_prompt(profile_data, language="en")
    prompt_ar = competencies_prompt.build_prompt(profile_data, language="ar")

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_en = pool.submit(chat_completion, prompt_en, temperature=0.7)
        fut_ar = pool.submit(chat_completion, prompt_ar, temperature=0.7)
        result_en = fut_en.result()
        result_ar = fut_ar.result()

    payload = {"en": result_en, "ar": result_ar}
    cache.set(cache_key, payload, _BILINGUAL_CACHE_TTL_SECONDS)
    return payload


def generate_bilingual_career_objective_summary(raw: str) -> dict[str, str]:
    """
    Produce polished English and Arabic versions of the user's career objective text.
    Used when creating an assessment so results/IDP can show the right language.
    """
    from .prompts import career_objective_bilingual as co_prompt

    text = (raw or "").strip()
    if not text:
        return {"en": "", "ar": ""}

    prompt = co_prompt.build_prompt(text)
    result = chat_completion(prompt, temperature=0.25)
    en = str(result.get("en", "") or "").strip()
    ar = str(result.get("ar", "") or "").strip()
    if not en and not ar:
        return {"en": text, "ar": text}
    if not ar:
        ar = en
    if not en:
        en = ar
    return {"en": en, "ar": ar}


def generate_bilingual_questions(
    profile_data: dict,
    competencies: list | None = None,
) -> dict[str, Any]:
    """
    Generate assessment questions in both English and Arabic.

    Optimized path:
      1. Result cache keyed by (profile + competencies) content (instant for repeats).
      2. ONE OpenAI call that returns {"en": {...}, "ar": {...}} in a single JSON
         response (eliminates a full network round-trip + JSON-mode TTFT).
      3. Optional faster model via OPENAI_FAST_MODEL (e.g. gpt-4o-mini).

    If the single-call response is malformed in any way, fall back to the
    original two-parallel-calls path so behavior is preserved.
    """
    from .prompts import questions as questions_prompt

    def normalize_questions(result: Any) -> list[dict]:
        """Extract a `questions` list from various AI response shapes."""
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("questions", "data", "assessment"):
                if key in result:
                    val = result[key]
                    if isinstance(val, list):
                        return val
            for val in result.values():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    return val
        return []

    # Slim the competencies payload before sending to the LLM:
    # - Collapse {"en": ..., "ar": ...} → just the EN categories (~50% fewer input tokens).
    # - Drop per-category verbose fields the questions prompt doesn't need (~25% more savings).
    # Same logic, just less to chew on, so the model finishes much faster.
    slim_competencies = _slim_competencies_for_questions(competencies)

    cache_key = _profile_cache_key(
        "questions",
        {"profile": profile_data, "competencies": slim_competencies},
    )
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info("bilingual questions cache hit")
        return cached

    bilingual_prompt = questions_prompt.build_bilingual_prompt(profile_data, slim_competencies)
    fast_model = _fast_model()

    try:
        result = chat_completion(bilingual_prompt, temperature=0.7, model=fast_model)
        en_block = result.get("en") if isinstance(result, dict) else None
        ar_block = result.get("ar") if isinstance(result, dict) else None
        en_list = normalize_questions(en_block)
        ar_list = normalize_questions(ar_block)
        if en_list and ar_list:
            payload = {"en": en_list, "ar": ar_list}
            cache.set(cache_key, payload, _BILINGUAL_CACHE_TTL_SECONDS)
            return payload
        logger.warning(
            "Single-call bilingual questions returned unexpected/empty shape; "
            "falling back to two parallel calls."
        )
    except Exception as exc:
        logger.warning(
            "Single-call bilingual questions failed (%s); falling back to two parallel calls.",
            exc,
        )

    # Fallback: legacy two-parallel-calls path — same as before the optimization.
    def fetch_questions(lang: str) -> list[dict]:
        prompt = questions_prompt.build_prompt(profile_data, slim_competencies, language=lang)
        result = chat_completion(prompt, temperature=0.7)
        return normalize_questions(result)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_en = pool.submit(fetch_questions, "en")
        fut_ar = pool.submit(fetch_questions, "ar")
        en_list = fut_en.result()
        ar_list = fut_ar.result()

    payload = {"en": en_list, "ar": ar_list}
    cache.set(cache_key, payload, _BILINGUAL_CACHE_TTL_SECONDS)
    return payload


def generate_bilingual_evaluation(
    profile_data: dict,
    questions_en: list,
    questions_ar: list,
    responses: list,
) -> dict[str, Any]:
    """Evaluate assessment responses in both English and Arabic."""
    from .prompts import evaluation as evaluation_prompt

    prompt_en = evaluation_prompt.build_prompt(
        profile_data,
        questions_en,
        responses,
        language="en",
    )
    prompt_ar = evaluation_prompt.build_prompt(
        profile_data,
        questions_ar,
        responses,
        language="ar",
    )

    # Run EN + AR in parallel — sequential calls roughly doubled wait time.
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_en = pool.submit(chat_completion, prompt_en, temperature=0.3)
        fut_ar = pool.submit(chat_completion, prompt_ar, temperature=0.3)
        result_en = fut_en.result()
        result_ar = fut_ar.result()

    return {
        "en": result_en,
        "ar": result_ar,
    }


def generate_bilingual_idp(
    profile_data: dict,
    assessment_results: dict,
    course_catalog: str,
) -> dict[str, Any]:
    """Generate Individual Development Plan in both English and Arabic."""
    from .prompts import idp as idp_prompt

    prompt_en = idp_prompt.build_prompt(
        profile_data,
        assessment_results,
        course_catalog,
        language="en",
    )
    prompt_ar = idp_prompt.build_prompt(
        profile_data,
        assessment_results,
        course_catalog,
        language="ar",
    )

    # Run both LLM calls in parallel — sequential would often exceed HTTP client timeouts
    # (each call can take 30–90s on a large catalog + long JSON schema).
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_en = pool.submit(chat_completion, prompt_en, temperature=0.4)
        fut_ar = pool.submit(chat_completion, prompt_ar, temperature=0.4)
        result_en = fut_en.result()
        result_ar = fut_ar.result()

    return {
        "en": result_en,
        "ar": result_ar,
    }


def merge_bilingual_data(data_en: Any, data_ar: Any) -> dict[str, Any]:
    """
    Merge two language versions of data into a single structure.

    Used in models to store both language versions together.
    """
    return {
        "en": data_en,
        "ar": data_ar,
    }


def get_translated_field(
    bilingual_field: dict | Any,
    language: str = "en",
    fallback_language: str = "en",
) -> Any:
    """
    Extract the appropriate language version from a bilingual field.

    Args:
        bilingual_field: Dict with 'en' and 'ar' keys, or a plain value
        language: Requested language ('en' or 'ar')
        fallback_language: Language to use if requested language not found

    Returns:
        The value in the requested language, or fallback language
    """
    if not isinstance(bilingual_field, dict):
        return bilingual_field

    if language in bilingual_field:
        return bilingual_field[language]

    if fallback_language in bilingual_field:
        return bilingual_field[fallback_language]

    # Return first available language
    for lang in ("en", "ar"):
        if lang in bilingual_field:
            return bilingual_field[lang]

    return bilingual_field
