import json

from .base import SYSTEM_PERSONA, get_language_instruction


def build_bilingual_prompt(professional_profile: dict, competencies: list | None = None) -> str:
    """
    Single-call bilingual variant: ask the LLM to emit BOTH English and Arabic
    Likert-scale questions in one JSON response. Same rules, same shape per
    language as `build_prompt`, just nested under `en` / `ar` keys.

    Used to avoid two round-trips to OpenAI for the bilingual questions endpoint.
    """
    competencies_text = ""
    if competencies:
        competencies_text = (
            f"\nCOMPETENCY CATEGORIES TO ASSESS:\n{json.dumps(competencies, indent=2)}"
        )

    return f"""{SYSTEM_PERSONA}

Based on this professional profile, generate self-assessment statements that the user will rate on a 5-point Likert scale (Strongly Disagree, Disagree, Neutral, Agree, Strongly Agree).

You MUST return BOTH an English version and an Arabic version in a single JSON response.

PROFESSIONAL PROFILE:
- Current Role: {professional_profile.get('current_role', 'N/A')}
- Target Role: {professional_profile.get('target_role', 'N/A')}
- Experience Level: {professional_profile.get('experience_level', 'N/A')}
- Industry: {professional_profile.get('company_industry', 'N/A')}
- Career Objective: {professional_profile.get('career_objective', 'N/A')}
- Professional Interests: {json.dumps(professional_profile.get('professional_interests', []))}
- Biggest Challenges: {json.dumps(professional_profile.get('biggest_challenges', []))}
{competencies_text}

RULES (apply to BOTH `en` and `ar` blocks):
1. Generate EXACTLY 10 statements per language, spread evenly across all competency categories
2. Every statement type MUST be "scale"
3. Each statement should be a first-person behavioral statement the user rates
4. Statements should measure proficiency from beginner to expert level
5. Cover ALL competency categories provided — distribute statements evenly
6. Statements should be about the competency behavioral descriptions (do not invent skills outside the provided categories)
7. Make statements specific and observable, not vague
8. The Arabic list MUST be a faithful translation of the English list — same number of items (10), same order, same `id` values, same `category`/`skill` mapping. Only translate human-readable text.

Return ONLY a valid JSON object with EXACTLY this structure:
{{
  "en": {{
    "questions": [
      {{
        "id": 1,
        "category": "Technical Strategy & Architecture",
        "skill": "System Design",
        "question": "I can design scalable system architectures that handle growing user demands.",
        "type": "scale",
        "options": ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
      }}
    ]
  }},
  "ar": {{
    "questions": [
      {{
        "id": 1,
        "category": "Technical Strategy & Architecture",
        "skill": "System Design",
        "question": "أستطيع تصميم بنى أنظمة قابلة للتوسع تتعامل مع تزايد طلبات المستخدمين.",
        "type": "scale",
        "options": ["غير موافق بشدة", "غير موافق", "محايد", "موافق", "موافق بشدة"]
      }}
    ]
  }}
}}

Language rules:
- The `en` block: `question` text MUST be in English; `options` MUST be the literal English Likert labels above.
- The `ar` block: `question` text MUST be written entirely in Arabic (العربية); `options` MUST be the literal Arabic Likert labels above ("غير موافق بشدة", "غير موافق", "محايد", "موافق", "موافق بشدة").
- `id`, `type`, `category`, and `skill` stay identical across both blocks (English category/skill identifiers in both)."""


def build_prompt(professional_profile: dict, competencies: list | None = None, language: str = "en") -> str:
    competencies_text = ""
    if competencies:
        competencies_text = f"\nCOMPETENCY CATEGORIES TO ASSESS:\n{json.dumps(competencies, indent=2)}"
    lang_instruction = get_language_instruction(language)

    return f"""{SYSTEM_PERSONA}{lang_instruction}

Based on this professional profile, generate self-assessment statements that the user will rate on a 5-point Likert scale (Strongly Disagree, Disagree, Neutral, Agree, Strongly Agree).

PROFESSIONAL PROFILE:
- Current Role: {professional_profile.get('current_role', 'N/A')}
- Target Role: {professional_profile.get('target_role', 'N/A')}
- Experience Level: {professional_profile.get('experience_level', 'N/A')}
- Industry: {professional_profile.get('company_industry', 'N/A')}
- Career Objective: {professional_profile.get('career_objective', 'N/A')}
- Professional Interests: {json.dumps(professional_profile.get('professional_interests', []))}
- Biggest Challenges: {json.dumps(professional_profile.get('biggest_challenges', []))}
{competencies_text}

RULES:
1. Generate EXACTLY 10 statements spread evenly across all competency categories
2. Every statement type MUST be "scale"
3. Each statement should be a first-person behavioral statement the user rates
4. Statements should measure proficiency from beginner to expert level
5. Cover ALL competency categories provided — distribute statements evenly
6. Statements should be about the competency behavioral descriptions that generated before not something extra that is not in the competency categories
7. Make statements specific and observable, not vague

Return ONLY a valid JSON object:
{{
  "questions": [
    {{
      "id": 1,
      "category": "Technical Strategy & Architecture",
      "skill": "System Design",
      "question": "I can design scalable system architectures that handle growing user demands.",
      "type": "scale",
      "options": ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    }}
  ]
}}"""
