from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.users.models import Customer

from .models import Assessment


def create_assessment(*, customer: Customer | None, data: dict[str, Any]) -> Assessment:
    return Assessment.objects.create(
        Customer=customer,
        Title=data.get("title", ""),
        Objective=data.get("objective", ""),
        ObjectiveBilingual=data.get("objective_bilingual") or {},
        Role=data.get("role", ""),
        Questions=data.get("questions", []),
        Responses=data.get("responses", []),
        OverallProgress=data.get("overall_progress"),
        TopStrength=data.get("top_strength", ""),
        GrowthArea=data.get("growth_area", ""),
        Skills=data.get("skills", []),
        TechnicalSkills=data.get("technical_skills", []),
        Status=data.get("status", "in_progress"),
    )


def update_assessment(assessment: Assessment, data: dict[str, Any]) -> Assessment:
    field_map = {
        "title": "Title",
        "objective": "Objective",
        "objective_bilingual": "ObjectiveBilingual",
        "role": "Role",
        "questions": "Questions",
        "responses": "Responses",
        "overall_progress": "OverallProgress",
        "top_strength": "TopStrength",
        "growth_area": "GrowthArea",
        "skills": "Skills",
        "technical_skills": "TechnicalSkills",
        "status": "Status",
    }
    for key, field in field_map.items():
        if key in data:
            setattr(assessment, field, data[key])

    assessment.UpdatedOn = timezone.now()
    assessment.save()
    return assessment


def save_evaluation_results(
    assessment: Assessment,
    responses: list,
    results: dict[str, Any],
) -> Assessment:
    assessment.Responses = responses
    assessment.OverallProgress = None
    assessment.TopStrength = results.get("top_strength", "")
    assessment.GrowthArea = results.get("growth_area", "")
    assessment.Skills = {
        "overall_level": results.get("overall_level", ""),
        "category_results": results.get("category_results", []),
        "strengths": results.get("strengths", []),
        "weaknesses": results.get("weaknesses", []),
        "recommended_courses": results.get("recommended_courses", []),
    }
    assessment.TechnicalSkills = []
    assessment.Status = "completed"
    assessment.UpdatedOn = timezone.now()
    assessment.save()
    return assessment


def save_bilingual_evaluation_results(
    assessment: Assessment,
    responses: list,
    results_en: dict[str, Any],
    results_ar: dict[str, Any],
    *,
    primary_language: str = "en",
) -> Assessment:
    """Persist EN + AR evaluation JSON on Skills; mirror summary fields from primary_language."""
    assessment.Responses = responses
    assessment.OverallProgress = None

    primary = results_ar if primary_language == "ar" else results_en
    assessment.TopStrength = primary.get("top_strength", "")
    assessment.GrowthArea = primary.get("growth_area", "")

    assessment.Skills = {
        "en": {
            "overall_level": results_en.get("overall_level", ""),
            "category_results": results_en.get("category_results", []),
            "strengths": results_en.get("strengths", []),
            "weaknesses": results_en.get("weaknesses", []),
            "recommended_courses": results_en.get("recommended_courses", []),
        },
        "ar": {
            "overall_level": results_ar.get("overall_level", ""),
            "category_results": results_ar.get("category_results", []),
            "strengths": results_ar.get("strengths", []),
            "weaknesses": results_ar.get("weaknesses", []),
            "recommended_courses": results_ar.get("recommended_courses", []),
        },
    }
    assessment.TechnicalSkills = []
    assessment.Status = "completed"
    assessment.UpdatedOn = timezone.now()
    assessment.save()
    return assessment


def update_customer_assessment_tracking(customer: Customer) -> None:
    from . import selectors
    customer.HasCompletedAssessment = True
    customer.AssessmentCount = selectors.count_completed_assessments(customer)
    customer.UpdatedOn = timezone.now()
    customer.save()
