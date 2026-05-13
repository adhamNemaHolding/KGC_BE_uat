"""
Advisor services — orchestrates AI calls, assessment evaluation, and IDP generation.

All AI logic lives here. Views never call OpenAI directly.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.conf import settings as django_settings
from django.utils import timezone

from apps.assessments.models import Assessment
from apps.assessments.services import save_bilingual_evaluation_results, update_customer_assessment_tracking
from apps.courses import selectors as course_selectors
from apps.users.models import Customer, ProfessionalProfile
from apps.users.selectors import get_professional_profile, get_profile_data_dict
from integrations.openai_client import chat_completion
from integrations.sitecore_client import fetch_sitecore_courses

from . import selectors
from .models import IndividualDevelopmentPlan
from .prompts import competencies as competencies_prompt
from .prompts import idp as idp_prompt
from .prompts import interests as interests_prompt
from .prompts import questions as questions_prompt
from . import bilingual_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Profile data resolution
# ---------------------------------------------------------------------------
def resolve_profile_data(
    customer: Customer | None,
    fallback: dict | None = None,
) -> dict | None:
    """Get profile data from DB for an authenticated customer, or use fallback."""
    if customer:
        profile = get_professional_profile(customer)
        if profile:
            return get_profile_data_dict(profile)
        # Logged-in user without a saved ProfessionalProfile — use body (e.g. session guest_profile).
        return fallback
    return fallback


def minimal_profile_for_competencies_only() -> dict[str, Any]:
    """Placeholder profile when the client sends full bilingual competencies but no persona payload."""
    return {
        "current_role": "",
        "target_role": "",
        "experience_level": "",
        "company_industry": "",
        "career_objective": "",
        "professional_interests": [],
        "biggest_challenges": [],
    }


def _career_objective_text_for_prompt(assessment: Assessment) -> str:
    """Prefer full AI-normalized text; `Objective` may be truncated to 500 chars for legacy DB field."""
    raw_bn = assessment.ObjectiveBilingual
    if isinstance(raw_bn, dict):
        en = str(raw_bn.get("en", "") or "").strip()
        ar = str(raw_bn.get("ar", "") or "").strip()
        if en:
            return en
        if ar:
            return ar
    return (assessment.Objective or "").strip()


def resolve_profile_from_assessment(
    assessment: Assessment,
    request_profile: dict | None = None,
) -> dict:
    """Get profile data for an assessment — from the linked customer or request body."""
    if assessment.Customer_id:
        profile = ProfessionalProfile.objects.filter(Customer_id=assessment.Customer_id).first()
        if profile:
            return get_profile_data_dict(profile)

    return request_profile or {
        "current_role": assessment.Role,
        "target_role": "",
        "experience_level": "",
        "career_objective": _career_objective_text_for_prompt(assessment),
    }


def _questions_for_language(questions_field: Any, lang: str) -> list:
    """Return question list for evaluate prompts (supports bilingual JSON on Assessment.Questions)."""
    if isinstance(questions_field, dict) and "en" in questions_field and "ar" in questions_field:
        q = questions_field.get(lang)
        return q if isinstance(q, list) else []
    if isinstance(questions_field, list):
        return questions_field
    return []


# ---------------------------------------------------------------------------
# Generate interests
# ---------------------------------------------------------------------------
def generate_interests(profile_data: dict, language: str = "en") -> list[str]:
    prompt = interests_prompt.build_prompt(profile_data, language=language)
    result = chat_completion(prompt, temperature=0.7)
    return result.get("interests", [])


# ---------------------------------------------------------------------------
# Generate competencies
# ---------------------------------------------------------------------------
def generate_competencies(profile_data: dict, language: str = "en") -> dict:
    prompt = competencies_prompt.build_prompt(profile_data, language=language)
    return chat_completion(prompt, temperature=0.7)


# ---------------------------------------------------------------------------
# Generate questions
# ---------------------------------------------------------------------------
def generate_questions_from_ai(
    profile_data: dict,
    competencies: list | None = None,
    language: str = "en",
) -> list[dict]:
    prompt = questions_prompt.build_prompt(profile_data, competencies, language=language)
    result = chat_completion(prompt, temperature=0.7)

    if isinstance(result, dict):
        for key in ("questions", "data", "assessment"):
            if key in result:
                return result[key]
        values = list(result.values())
        return values[0] if values else []
    return result


def build_questions_from_categories(competencies: list[dict]) -> list[dict]:
    """Convert category objects directly into Likert-scale questions (no AI call)."""
    questions = []
    for idx, cat in enumerate(competencies, 1):
        questions.append({
            "id": idx,
            "category": cat.get("type", "technical").capitalize(),
            "skill": cat.get("name", ""),
            "question": cat.get("name", ""),
            "type": "scale",
            "options": ["Beginner", "Intermediate", "Advanced", "Expert"],
        })
    return questions


def create_assessment_with_questions(
    *,
    customer: Customer | None,
    profile_data: dict,
    competencies: list | None,
    title: str,
    language: str = "en",
) -> tuple[Assessment, list[dict]]:
    """Generate questions and create an assessment in one step."""
    questions: list[dict] = []

    # Try building from category objects first
    if competencies and isinstance(competencies, list) and len(competencies) > 0:
        first = competencies[0]
        if isinstance(first, dict) and "definition" in first:
            questions = build_questions_from_categories(competencies)

    # Fall back to AI generation
    if not questions:
        questions = generate_questions_from_ai(profile_data, competencies, language=language)

    assessment = Assessment.objects.create(
        Customer=customer,
        Title=title or "Skill Assessment",
        Objective=profile_data.get("career_objective", ""),
        Role=profile_data.get("current_role", ""),
        Questions=questions,
        Status="in_progress",
    )

    return assessment, questions


def _career_objective_bilingual_safe(raw: str) -> dict[str, str]:
    """LLM call isolated for thread pool; never raises."""
    text = (raw or "").strip()
    if not text:
        return {"en": "", "ar": ""}
    try:
        return bilingual_service.generate_bilingual_career_objective_summary(text)
    except Exception as exc:
        logger.warning("Bilingual career objective generation failed, using raw text: %s", exc)
        return {"en": text, "ar": text}


def _career_context_seed(profile_data: dict, competencies: Any) -> str:
    """
    Text to feed the bilingual career-objective LLM.
    Prefer explicit career_objective; else build from profile; else role_summary from competencies.
    """
    co = (profile_data.get("career_objective") or "").strip()
    if co:
        return co

    lines: list[str] = []
    cr = (profile_data.get("current_role") or "").strip()
    tr = (profile_data.get("target_role") or "").strip()
    el = (profile_data.get("experience_level") or "").strip()
    ind = (profile_data.get("company_industry") or "").strip()
    if cr:
        lines.append(f"Current role: {cr}")
    if tr:
        lines.append(f"Target role: {tr}")
    if el:
        lines.append(f"Experience level: {el}")
    if ind:
        lines.append(f"Industry: {ind}")

    pi = profile_data.get("professional_interests") or []
    if isinstance(pi, (list, tuple)) and pi:
        lines.append(f"Professional interests: {', '.join(str(x) for x in pi[:12])}")

    bc = profile_data.get("biggest_challenges") or []
    if isinstance(bc, (list, tuple)) and bc:
        lines.append(f"Development focus / challenges: {', '.join(str(x) for x in bc[:8])}")

    seed = "\n".join(lines).strip()
    if seed:
        return seed

    if isinstance(competencies, dict):
        for key in ("en", "ar"):
            block = competencies.get(key)
            if isinstance(block, dict):
                rs = (block.get("role_summary") or "").strip()
                if rs:
                    return f"Role and career context:\n{rs}"
    return ""


def create_assessment_with_bilingual_questions(
    *,
    customer: Customer | None,
    profile_data: dict,
    competencies: list | None,
    title: str,
) -> tuple[Assessment, dict[str, Any]]:
    """Generate questions in EN & AR, then create an assessment (Questions stores both)."""
    career_seed = _career_context_seed(profile_data, competencies)
    objective_bn: dict[str, str] = {"en": "", "ar": ""}

    if career_seed:
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_questions = pool.submit(
                bilingual_service.generate_bilingual_questions, profile_data, competencies
            )
            fut_objective = pool.submit(_career_objective_bilingual_safe, career_seed)
            bilingual_questions = fut_questions.result()
            objective_bn = fut_objective.result()
    else:
        bilingual_questions = bilingual_service.generate_bilingual_questions(profile_data, competencies)

    en_line = (objective_bn.get("en") or "")[:500]
    assessment = Assessment.objects.create(
        Customer=customer,
        Title=title or "Skill Assessment",
        Objective=en_line,
        ObjectiveBilingual=objective_bn,
        Role=profile_data.get("current_role", ""),
        Questions=bilingual_questions,
        Status="in_progress",
    )
    return assessment, bilingual_questions


# ---------------------------------------------------------------------------
# Evaluate assessment
# ---------------------------------------------------------------------------
def evaluate_assessment(
    *,
    assessment: Assessment,
    responses: list,
    request_profile: dict | None = None,
    language: str = "en",
) -> Assessment:
    profile_data = resolve_profile_from_assessment(assessment, request_profile)

    questions_en = _questions_for_language(assessment.Questions, "en")
    questions_ar = _questions_for_language(assessment.Questions, "ar")
    if not questions_en and questions_ar:
        questions_en = questions_ar
    if not questions_ar and questions_en:
        questions_ar = questions_en
    if not questions_en and not questions_ar:
        raise ValueError("Assessment has no questions to evaluate.")

    bilingual = bilingual_service.generate_bilingual_evaluation(
        profile_data,
        questions_en,
        questions_ar,
        responses,
    )
    assessment = save_bilingual_evaluation_results(
        assessment,
        responses,
        bilingual["en"],
        bilingual["ar"],
        primary_language=language if language in ("en", "ar") else "en",
    )

    if assessment.Customer_id:
        try:
            customer = Customer.objects.get(CustomerId=assessment.Customer_id)
            update_customer_assessment_tracking(customer)
        except Customer.DoesNotExist:
            pass

    return assessment


# ---------------------------------------------------------------------------
# Generate IDP
# ---------------------------------------------------------------------------
def _get_course_catalog() -> str:
    """Build a compact course catalog string from DB + Sitecore."""
    db_courses = course_selectors.get_active_courses_as_dicts()
    sitecore_courses = fetch_sitecore_courses()

    # Build a lookup of Sitecore courses by lowercase title
    sitecore_by_title: dict[str, dict] = {}
    for sc in sitecore_courses:
        key = (sc.get("title") or "").lower().strip()
        if key:
            sitecore_by_title[key] = sc

    # Enrich DB courses with Sitecore links where titles match
    catalog: list[dict] = []
    seen_titles: set[str] = set()

    for course in db_courses:
        title_lower = (course.get("Name") or "").lower().strip()
        seen_titles.add(title_lower)
        entry: dict = {"name": course.get("Name", ""), "link": course.get("Link", "")}
        if course.get("Category"):
            entry["category"] = course["Category"]
        if course.get("Description"):
            entry["description"] = course["Description"]
        # Override link from Sitecore if available
        if title_lower in sitecore_by_title:
            sc = sitecore_by_title[title_lower]
            if sc.get("link"):
                entry["link"] = sc["link"]
        catalog.append(entry)

    # Add Sitecore-only courses (name + link + description)
    for sc in sitecore_courses:
        title_lower = (sc.get("title") or "").lower().strip()
        if title_lower and title_lower not in seen_titles:
            entry = {
                "name": sc.get("title", ""),
                "link": sc.get("link", ""),
            }
            if sc.get("description"):
                entry["description"] = sc["description"]
            catalog.append(entry)

    if not catalog:
        return "No KGC courses available yet. Recommend external courses as needed."

    logger.info("Course catalog built with %d entries for AI prompt", len(catalog))
    return json.dumps(catalog, default=str)


def _enrich_roadmap_links(roadmap: list[dict]) -> list[dict]:
    """Match roadmap courses to real courses from DB/Sitecore and inject links."""
    all_db_courses = course_selectors.get_course_name_link_map()
    sitecore_courses = fetch_sitecore_courses()

    sitecore_lookup: dict[str, str] = {}
    for sc in sitecore_courses:
        title = (sc.get("title") or "").lower().strip()
        if title and sc.get("link"):
            sitecore_lookup[title] = sc["link"]

    name_to_link = {**all_db_courses, **sitecore_lookup}

    for phase in roadmap:
        for course in phase.get("courses", []):
            course_name = (course.get("name") or "").lower().strip()
            if course_name in name_to_link:
                course["link"] = name_to_link[course_name]
                continue
            matched = False
            for known_name, known_link in name_to_link.items():
                if known_name in course_name or course_name in known_name:
                    course["link"] = known_link
                    matched = True
                    break
            if not matched and not course.get("link"):
                course["link"] = None

    return roadmap


def _persist_idp_from_ai_payload(
    *,
    assessment: Assessment,
    idp_data: dict[str, Any],
    generated_by: str,
) -> IndividualDevelopmentPlan:
    """Create or update the stored IDP from a completed AI payload (used by bilingual save)."""
    if assessment.Status != "completed":
        raise ValueError("Assessment must be completed first.")

    existing_idp = selectors.get_idp_for_assessment(assessment)
    if existing_idp and existing_idp.GenerationCount >= 2:
        raise ValueError("IDP generation limit reached. Maximum 2 generations per assessment.")

    roadmap = idp_data.get("learning_roadmap", [])

    if existing_idp:
        existing_idp.TargetRole = idp_data.get("target_role", "")
        existing_idp.CurrentLevel = idp_data.get("current_level", "")
        existing_idp.NextMilestone = idp_data.get("next_milestone", "")
        existing_idp.Timeline = idp_data.get("timeline", "")
        existing_idp.CareerPathNote = idp_data.get("career_path_note", "")
        existing_idp.TopStrength = idp_data.get("top_strength", "")
        existing_idp.GrowthArea = idp_data.get("growth_area", "")
        existing_idp.SkillProficiency = idp_data.get("skill_proficiency", [])
        existing_idp.LearningRoadmap = roadmap
        existing_idp.GeneratedBy = generated_by
        existing_idp.GenerationCount += 1
        existing_idp.UpdatedOn = timezone.now()
        existing_idp.save()
        return existing_idp

    return IndividualDevelopmentPlan.objects.create(
        Assessment=assessment,
        Customer=assessment.Customer if assessment.Customer_id else None,
        TargetRole=idp_data.get("target_role", ""),
        CurrentLevel=idp_data.get("current_level", ""),
        NextMilestone=idp_data.get("next_milestone", ""),
        Timeline=idp_data.get("timeline", ""),
        CareerPathNote=idp_data.get("career_path_note", ""),
        TopStrength=idp_data.get("top_strength", ""),
        GrowthArea=idp_data.get("growth_area", ""),
        SkillProficiency=idp_data.get("skill_proficiency", []),
        LearningRoadmap=roadmap,
        GeneratedBy=generated_by,
        GenerationCount=1,
    )


def generate_idp(
    *,
    assessment: Assessment,
    request_profile: dict | None = None,
    language: str = "en",
) -> IndividualDevelopmentPlan:
    """Generate or regenerate an IDP from a completed assessment."""
    if assessment.Status != "completed":
        raise ValueError("Assessment must be completed first.")

    existing_idp = selectors.get_idp_for_assessment(assessment)
    if existing_idp and existing_idp.GenerationCount >= 2:
        raise ValueError("IDP generation limit reached. Maximum 2 generations per assessment.")

    profile_data = resolve_profile_from_assessment(assessment, request_profile)

    assessment_results: dict[str, Any] = {
        "overall_progress": assessment.OverallProgress,
        "top_strength": assessment.TopStrength,
        "growth_area": assessment.GrowthArea,
        "skills": assessment.Skills,
        "technical_skills": assessment.TechnicalSkills,
    }

    course_catalog = _get_course_catalog()
    prompt = idp_prompt.build_prompt(profile_data, assessment_results, course_catalog, language=language)
    raw = chat_completion(prompt, temperature=0.4)
    if not isinstance(raw, dict):
        raise ValueError("Invalid IDP response from AI.")
    idp_data: dict[str, Any] = {
        **raw,
        "learning_roadmap": _enrich_roadmap_links(raw.get("learning_roadmap", []) or []),
    }
    model_label = "OpenAI " + getattr(django_settings, "OPENAI_MODEL", "gpt-4o")
    return _persist_idp_from_ai_payload(
        assessment=assessment,
        idp_data=idp_data,
        generated_by=model_label,
    )


# ---------------------------------------------------------------------------
# Bilingual AI functions — generate in both EN & AR simultaneously
# ---------------------------------------------------------------------------
def generate_bilingual_interests(profile_data: dict) -> dict[str, dict]:
    """Generate interests in both English and Arabic in parallel."""
    return bilingual_service.generate_bilingual_interests(profile_data)


def generate_bilingual_competencies(profile_data: dict) -> dict[str, dict]:
    """Generate competency categories in both English and Arabic in parallel."""
    return bilingual_service.generate_bilingual_competencies(profile_data)


def generate_bilingual_questions(
    profile_data: dict,
    competencies: list | None = None,
) -> dict[str, list[dict]]:
    """Generate assessment questions in both English and Arabic in parallel."""
    return bilingual_service.generate_bilingual_questions(profile_data, competencies)


def generate_bilingual_idp(
    *,
    assessment: Assessment,
    request_profile: dict | None = None,
) -> dict[str, Any]:
    """Generate IDP in both English and Arabic in parallel; persists EN snapshot to the IDP table."""
    if assessment.Status != "completed":
        raise ValueError("Assessment must be completed first.")

    existing_idp = selectors.get_idp_for_assessment(assessment)
    if existing_idp and existing_idp.GenerationCount >= 2:
        raise ValueError("IDP generation limit reached. Maximum 2 generations per assessment.")

    profile_data = resolve_profile_from_assessment(assessment, request_profile)

    assessment_results: dict[str, Any] = {
        "overall_progress": assessment.OverallProgress,
        "top_strength": assessment.TopStrength,
        "growth_area": assessment.GrowthArea,
        "skills": assessment.Skills,
        "technical_skills": assessment.TechnicalSkills,
    }

    course_catalog = _get_course_catalog()

    bilingual_data = bilingual_service.generate_bilingual_idp(
        profile_data,
        assessment_results,
        course_catalog,
    )

    # Enrich roadmaps with course links
    for lang in ("en", "ar"):
        if lang in bilingual_data:
            bilingual_data[lang]["learning_roadmap"] = _enrich_roadmap_links(
                bilingual_data[lang].get("learning_roadmap", [])
            )

    en_payload = bilingual_data.get("en")
    if not isinstance(en_payload, dict):
        en_payload = bilingual_data.get("ar")
    if not isinstance(en_payload, dict):
        raise ValueError("Bilingual IDP returned no usable language payload.")

    model_label = (
        "OpenAI " + getattr(django_settings, "OPENAI_MODEL", "gpt-4o") + " (bilingual)"
    )
    _persist_idp_from_ai_payload(
        assessment=assessment,
        idp_data=en_payload,
        generated_by=model_label,
    )

    return bilingual_data
