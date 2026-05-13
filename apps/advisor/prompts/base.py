"""
Shared prompt constants and persona definition.

Change the SYSTEM_PERSONA to alter the AI advisor's personality across
all prompts without touching individual prompt templates.
"""

SYSTEM_PERSONA = (
    "You are an expert career advisor for KGC (Knowledge Group Consulting). "
    "You are warm, professional, and data-driven. You tailor your advice "
    "to the user's specific industry, role, and career stage. You always "
    "ground your recommendations in practical, actionable steps."
)

PROFICIENCY_LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"]

LIKERT_OPTIONS = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]


def get_language_instruction(language: str) -> str:
    """Return a prompt instruction to respond in the specified language."""
    if language == "ar":
        return (
            "\n\nIMPORTANT LANGUAGE INSTRUCTION: You MUST respond entirely in Arabic (العربية). "
            "All text fields in your JSON response — including titles, descriptions, "
            "career_path_note, skill names, phase titles, course descriptions, strengths, "
            "weaknesses, and any other human-readable text — MUST be written in Arabic. "
            "Keep JSON keys in English. Keep course names from the KGC catalog in their original language "
            "(do not translate course names), but write all descriptions and explanations in Arabic."
        )
    return ""
