import json

from .base import SYSTEM_PERSONA, get_language_instruction


def build_bilingual_prompt(professional_profile: dict) -> str:
    """
    Single-call bilingual variant: ask the LLM to emit both English and Arabic
    competency sets in one JSON response. Same logic, same rules, same shape per
    language as `build_prompt`, just nested under `en` / `ar` keys.

    Used to avoid two round-trips to OpenAI for the bilingual competencies endpoint.
    """
    return f"""{SYSTEM_PERSONA}

Based on this professional profile, suggest the key competency areas that should be assessed.
You MUST return BOTH an English version and an Arabic version in a single JSON response.

PROFESSIONAL PROFILE:
- Current Role: {professional_profile.get('current_role', 'N/A')}
- Target Role: {professional_profile.get('target_role', 'N/A')}
- Experience Level: {professional_profile.get('experience_level', 'N/A')}
- Industry: {professional_profile.get('company_industry', 'N/A')}
- Career Objective: {professional_profile.get('career_objective', 'N/A')}
- Professional Interests: {json.dumps(professional_profile.get('professional_interests', []))}

Return a JSON object with EXACTLY this structure:
{{
  "en": {{
    "role_summary": "A brief description of what this role requires (in English)",
    "categories": [
      {{
        "name": "Patient-Centered Care & Compassion",
        "type": "technical",
        "definition": "A clear, concise statement of what this competency means in the context of the role.",
        "behavioral_description": "A narrative describing what 'good' looks like — the observable day-to-day behaviors a professional demonstrates when they possess this competency.",
        "objective_measurable_behavior": "Concrete, quantifiable indicators or evidence that prove the competency is being applied (e.g., metrics, documentation, audit results, feedback scores)."
      }}
    ]
  }},
  "ar": {{
    "role_summary": "نفس الوصف ولكن مكتوب بالعربية",
    "categories": [
      {{
        "name": "اسم الكفاءة بالعربية",
        "type": "technical",
        "definition": "تعريف واضح بالعربية.",
        "behavioral_description": "وصف سلوكي بالعربية.",
        "objective_measurable_behavior": "مؤشرات قابلة للقياس بالعربية."
      }}
    ]
  }}
}}

Rules (apply to BOTH `en` and `ar` blocks):
- Generate 6-8 categories total (the SAME categories must appear in both languages — Arabic must be a faithful translation of the English set, in the SAME order)
- EXACTLY 3-4 categories with type "technical"
- EXACTLY 3-4 categories with type "behavioral"
- Each category MUST have a "type" field set to either "technical" or "behavioral"
- "technical" categories cover hard skills, tools, domain expertise, technical knowledge
- "behavioral" categories cover soft skills, leadership, communication, interpersonal abilities
- Aim for roughly equal split between technical and behavioral categories
- Every category MUST include all five fields: name, type, definition, behavioral_description, objective_measurable_behavior
- Tailor competencies to the gap between current role and target role
- Be specific to the user's industry and role
- Definitions should be professional and precise
- Behavioral descriptions should paint a vivid picture of the competency in action
- Objective/measurable behaviors must be concrete and quantifiable

Language rules:
- The `en` block: ALL human-readable text fields (role_summary, name, definition, behavioral_description, objective_measurable_behavior) MUST be in English.
- The `ar` block: ALL human-readable text fields MUST be written entirely in Arabic (العربية).
- JSON keys themselves stay in English in both blocks.
- The `type` field stays as the literal English strings "technical" or "behavioral" in BOTH blocks.
- The `ar` block must be a faithful translation of the `en` block — same number of categories, same types, same order, same overall meaning."""


def build_prompt(professional_profile: dict, language: str = "en") -> str:
    lang_instruction = get_language_instruction(language)
    return f"""{SYSTEM_PERSONA}{lang_instruction}

Based on this professional profile, suggest the key competency areas that should be assessed.

PROFESSIONAL PROFILE:
- Current Role: {professional_profile.get('current_role', 'N/A')}
- Target Role: {professional_profile.get('target_role', 'N/A')}
- Experience Level: {professional_profile.get('experience_level', 'N/A')}
- Industry: {professional_profile.get('company_industry', 'N/A')}
- Career Objective: {professional_profile.get('career_objective', 'N/A')}
- Professional Interests: {json.dumps(professional_profile.get('professional_interests', []))}

Return a JSON object with this structure:
{{
  "role_summary": "A brief description of what this role requires",
  "categories": [
    {{
      "name": "Patient-Centered Care & Compassion",
      "type": "technical",
      "definition": "A clear, concise statement of what this competency means in the context of the role.",
      "behavioral_description": "A narrative describing what 'good' looks like — the observable day-to-day behaviors a professional demonstrates when they possess this competency.",
      "objective_measurable_behavior": "Concrete, quantifiable indicators or evidence that prove the competency is being applied (e.g., metrics, documentation, audit results, feedback scores)."
    }}
  ]
}}

Rules:
- Generate 6-8 categories total
- EXACTLY 3-4 categories with type "technical"
- EXACTLY 3-4 categories with type "behavioral"
- Each category MUST have a "type" field set to either "technical" or "behavioral"
- "technical" categories cover hard skills, tools, domain expertise, technical knowledge
- "behavioral" categories cover soft skills, leadership, communication, interpersonal abilities
- Aim for roughly equal split between technical and behavioral categories
- Every category MUST include all five fields: name, type, definition, behavioral_description, objective_measurable_behavior
- Tailor competencies to the gap between current role and target role
- Be specific to the user's industry and role
- Definitions should be professional and precise
- Behavioral descriptions should paint a vivid picture of the competency in action
- Objective/measurable behaviors must be concrete and quantifiable"""
