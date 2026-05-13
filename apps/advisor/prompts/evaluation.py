import json

from .base import SYSTEM_PERSONA, get_language_instruction


def build_prompt(professional_profile: dict, questions: list, responses: list, language: str = "en") -> str:
    qa_pairs = json.dumps(
        [{"question": q, "response": r} for q, r in zip(questions, responses)],
        indent=2,
    )
    lang_instruction = get_language_instruction(language)

    return f"""{SYSTEM_PERSONA}{lang_instruction}

The user self-assessed their proficiency in various competencies by choosing a level:
Beginner, Intermediate, Advanced, or Expert.

PROFESSIONAL PROFILE:
- Current Role: {professional_profile.get('current_role', 'N/A')}
- Target Role: {professional_profile.get('target_role', 'N/A')}
- Experience Level: {professional_profile.get('experience_level', 'N/A')}
- Career Objective: {professional_profile.get('career_objective', 'N/A')}

QUESTIONS AND RESPONSES:
{qa_pairs}

Analyze the responses and return a JSON object with this EXACT structure:
{{
  "overall_level": "Intermediate",
  "top_strength": "Leadership & Communication",
  "growth_area": "Technical Architecture",
  "category_results": [
    {{
      "category": "Leadership & Communication",
      "response": "Advanced",
      "type": "behavioral"
    }},
    {{
      "category": "System Design",
      "response": "Beginner",
      "type": "technical"
    }}
  ],
  "strengths": [
    {{
      "name": "Leadership & Communication",
      "description": "One brief sentence about this strength."
    }}
  ],
  "weaknesses": [
    {{
      "name": "Technical Architecture",
      "description": "One brief sentence about this area for growth."
    }}
  ],
  "recommended_courses": [
    {{
      "name": "System Design Fundamentals",
      "reason": "Brief reason why this course helps."
    }}
  ]
}}

Rules:
- overall_level must be one of: "Beginner", "Intermediate", "Advanced", "Expert" — derived from the average of all responses
- category_results must include EVERY question's category with the EXACT response the user chose (Beginner/Intermediate/Advanced/Expert)
- type must be "technical" or "behavioral" based on the category
- strengths: list the 2-3 strongest areas (Advanced/Expert) with ONE brief sentence each (max 20 words per description)
- weaknesses: list the 2-3 weakest areas (Beginner/Intermediate) with ONE brief sentence each (max 20 words per description)
- recommended_courses: suggest 3-5 courses that address the weaknesses, with a brief reason each
- Base everything on the actual proficiency levels the user selected"""
