"""Prompt to turn a raw career-objective string into polished EN + AR text."""

from .base import SYSTEM_PERSONA


def build_prompt(raw_career_objective: str) -> str:
    return f"""{SYSTEM_PERSONA}

The user provided the following career development / objective text, OR structured profile lines
(current role, target role, interests, challenges). It may be in English, Arabic, or mixed, and may
include section labels (e.g. career goals, skills, success vision).

---
{raw_career_objective.strip()}
---

Return a single JSON object with exactly two keys, "en" and "ar":
- "en": Polished English with the same meaning. Keep a clear structure (short labeled sections or sentences). Do not invent new goals or skills.
- "ar": Natural Modern Standard Arabic (فصحى معاصرة) with the same meaning and parallel structure. Professional tone suitable for HR and career summaries.

Rules:
- Preserve all factual content from the input; you may fix grammar and clarity only.
- JSON keys must be exactly "en" and "ar". Values must be non-null strings.
- Each value should stay under 3500 characters.
- Output valid JSON only (no markdown).
"""
