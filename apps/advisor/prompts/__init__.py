"""
Prompt Management Layer.

Each module defines a function that builds the prompt string for a specific
AI task. This makes prompts easy to find, tweak, and A/B test without
touching any service logic.

Usage:
    from apps.advisor.prompts import interests
    prompt = interests.build_prompt(profile_data)
"""
