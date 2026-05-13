from .base import SYSTEM_PERSONA, get_language_instruction


def build_prompt(profile_data: dict, language: str = "en") -> str:
    lang_instruction = get_language_instruction(language)
    return f"""{SYSTEM_PERSONA}{lang_instruction}

Based on this professional profile, suggest relevant professional interest areas
that this person should focus on for career growth.

PROFILE:
- Current Role: {profile_data.get('current_role', 'N/A')}
- Target Role: {profile_data.get('target_role', 'N/A')}
- Company: {profile_data.get('company_name', 'N/A')}
- Industry: {profile_data.get('company_industry', 'N/A')}
- Age Range: {profile_data.get('age_range', 'N/A')}
- Experience Level: {profile_data.get('experience_level', 'N/A')}

Return a JSON object:
{{
  "interests": [
    "Leadership & Management",
    "Data Analytics",
    "Cloud Computing"
  ]
}}

Rules:
- Return 8-12 professional interest areas
- Tailor to the gap between current and target role
- Include a mix of technical and soft skill domains
- Be specific to the industry and experience level
- Each interest should be 2-4 words"""
