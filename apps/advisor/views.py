from __future__ import annotations

from django.db.utils import OperationalError
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request

from apps.assessments import selectors as assessment_selectors
from apps.assessments.serializers import AssessmentSerializer
from apps.common.response import error_response, success_response
from apps.common.throttling import check_ratelimit, rate_limit_ai
from apps.users.models import Customer

from . import selectors, services
from .serializers import IDPSerializer


def _get_customer(request: Request) -> Customer | None:
    user = request.user
    return user if isinstance(user, Customer) else None


def _get_language(request: Request) -> str:
    """Prefer explicit JSON body `language`, then a short Accept-Language code."""
    body_lang = request.data.get("language") if hasattr(request, "data") else None
    if body_lang in ("en", "ar"):
        return body_lang
    header = (request.headers.get("Accept-Language") or "en").split(",")[0].strip().lower()
    if header.startswith("ar"):
        return "ar"
    return "en"


def _check_assessment_access(assessment, customer: Customer | None) -> str | None:
    """Return error message if the user doesn't own the assessment, or None if OK."""
    if not assessment.Customer_id:
        return None  # Guest assessment — no ownership to check
    if not customer:
        return "Authentication required for this assessment."
    if str(assessment.Customer_id) != str(customer.CustomerId):
        return "You do not have access to this assessment."
    return None


# ============================================================================
# AI endpoints — authenticated + rate-limited
# ============================================================================

@extend_schema(
    tags=["Advisor"],
    summary="Generate AI-suggested interests",
    request=inline_serializer(
        name="GenerateInterestsRequest",
        fields={"profile": drf_serializers.DictField()},
    ),
    responses={200: OpenApiResponse(description="List of suggested interests")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_generate_interests(request: Request):
    profile_data = request.data.get("profile")
    if not profile_data or not isinstance(profile_data, dict):
        return error_response("Profile data is required.")

    try:
        result = services.generate_bilingual_interests(profile_data)
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(data=result)


@extend_schema(
    tags=["Advisor"],
    summary="Generate competency areas",
    request=inline_serializer(
        name="GenerateCompetenciesRequest",
        fields={"profile": drf_serializers.DictField(required=False)},
    ),
    responses={200: OpenApiResponse(description="Competency categories")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_generate_competencies(request: Request):
    customer = _get_customer(request)
    profile_data = services.resolve_profile_data(customer, request.data.get("profile"))
    if not profile_data:
        return error_response("Profile data is required.")

    try:
        result = services.generate_bilingual_competencies(profile_data)
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(data=result)


@extend_schema(
    tags=["Advisor"],
    summary="Generate assessment questions",
    request=inline_serializer(
        name="GenerateQuestionsRequest",
        fields={
            "title": drf_serializers.CharField(required=False, default="Skill Assessment"),
            "competencies": drf_serializers.ListField(required=False),
            "profile": drf_serializers.DictField(required=False),
        },
    ),
    responses={201: OpenApiResponse(description="Assessment created with questions")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_generate_questions(request: Request):
    customer = _get_customer(request)
    profile_data = services.resolve_profile_data(customer, request.data.get("profile"))
    if not profile_data:
        return error_response("Profile data is required.")

    try:
        assessment, bilingual_questions = services.create_assessment_with_bilingual_questions(
            customer=customer,
            profile_data=profile_data,
            competencies=request.data.get("competencies"),
            title=request.data.get("title", "Skill Assessment"),
        )
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(
        data={"assessment_id": str(assessment.AssessmentId), "questions": bilingual_questions},
        status_code=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["Advisor"],
    summary="Evaluate assessment responses",
    request=inline_serializer(
        name="EvaluateAssessmentRequest",
        fields={
            "assessment_id": drf_serializers.UUIDField(),
            "responses": drf_serializers.ListField(),
            "profile": drf_serializers.DictField(required=False),
        },
    ),
    responses={200: AssessmentSerializer},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_evaluate_assessment(request: Request):
    assessment_id = request.data.get("assessment_id")
    responses = request.data.get("responses", [])

    if not assessment_id or not responses:
        return error_response("assessment_id and responses are required.")

    assessment = assessment_selectors.get_assessment_by_id(assessment_id)
    if not assessment:
        return error_response("Assessment not found.", status_code=status.HTTP_404_NOT_FOUND)

    # IDOR check
    customer = _get_customer(request)
    access_error = _check_assessment_access(assessment, customer)
    if access_error:
        return error_response(access_error, status_code=status.HTTP_403_FORBIDDEN)

    try:
        assessment = services.evaluate_assessment(
            assessment=assessment,
            responses=responses,
            request_profile=request.data.get("profile"),
            language=_get_language(request),
        )
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(data=AssessmentSerializer(assessment).data)


@extend_schema(
    tags=["Advisor"],
    summary="Generate IDP from assessment",
    request=inline_serializer(
        name="GenerateIDPRequest",
        fields={
            "assessment_id": drf_serializers.UUIDField(),
            "profile": drf_serializers.DictField(required=False),
        },
    ),
    responses={201: IDPSerializer},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_generate_idp(request: Request):
    assessment_id = request.data.get("assessment_id")
    if not assessment_id:
        return error_response("assessment_id is required.")

    assessment = assessment_selectors.get_assessment_by_id(assessment_id)
    if not assessment:
        return error_response("Assessment not found.", status_code=status.HTTP_404_NOT_FOUND)

    # IDOR check
    customer = _get_customer(request)
    access_error = _check_assessment_access(assessment, customer)
    if access_error:
        return error_response(access_error, status_code=status.HTTP_403_FORBIDDEN)

    try:
        idp = services.generate_idp(
            assessment=assessment,
            request_profile=request.data.get("profile"),
            language=_get_language(request),
        )
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(
        data=IDPSerializer(idp).data,
        status_code=status.HTTP_201_CREATED,
    )


# ============================================================================
# Bilingual AI endpoints — generate in both EN & AR simultaneously
# ============================================================================

@extend_schema(
    tags=["Advisor (Bilingual)"],
    summary="Generate interests in both English & Arabic",
    request=inline_serializer(
        name="GenerateBilingualInterestsRequest",
        fields={"profile": drf_serializers.DictField()},
    ),
    responses={200: OpenApiResponse(description="Interests in English and Arabic")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_generate_interests_bilingual(request: Request):
    """Generate interests in both English and Arabic simultaneously."""
    profile_data = request.data.get("profile")
    if not profile_data or not isinstance(profile_data, dict):
        return error_response("Profile data is required.")

    try:
        result = services.generate_bilingual_interests(profile_data)
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(data=result)


@extend_schema(
    tags=["Advisor (Bilingual)"],
    summary="Generate competencies in both English & Arabic",
    request=inline_serializer(
        name="GenerateBilingualCompetenciesRequest",
        fields={"profile": drf_serializers.DictField(required=False)},
    ),
    responses={200: OpenApiResponse(description="Competencies in English and Arabic")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_generate_competencies_bilingual(request: Request):
    """Generate competency categories in both English and Arabic simultaneously."""
    customer = _get_customer(request)
    profile_data = services.resolve_profile_data(customer, request.data.get("profile"))
    if not profile_data:
        return error_response("Profile data is required.")

    try:
        result = services.generate_bilingual_competencies(profile_data)
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(data=result)


@extend_schema(
    tags=["Advisor (Bilingual)"],
    summary="Generate questions in both English & Arabic",
    request=inline_serializer(
        name="GenerateBilingualQuestionsRequest",
        fields={
            "title": drf_serializers.CharField(required=False, default="Skill Assessment"),
            "competencies": drf_serializers.ListField(required=False),
            "profile": drf_serializers.DictField(required=False),
        },
    ),
    responses={201: OpenApiResponse(description="Assessment with questions in both languages")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_generate_questions_bilingual(request: Request):
    """Generate assessment questions in both English and Arabic simultaneously."""
    customer = _get_customer(request)
    profile_data = services.resolve_profile_data(customer, request.data.get("profile"))
    if not profile_data:
        if request.data.get("competencies"):
            profile_data = services.minimal_profile_for_competencies_only()
        else:
            return error_response("Profile data is required.")

    try:
        assessment, bilingual_questions = services.create_assessment_with_bilingual_questions(
            customer=customer,
            profile_data=profile_data,
            competencies=request.data.get("competencies"),
            title=request.data.get("title", "Skill Assessment"),
        )
    except OperationalError as e:
        err = str(e).lower()
        if "objectivebilingual" in err or "no such column" in err:
            return error_response(
                "Database migration required: run `python manage.py migrate` (app: assessments).",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return error_response(f"Database error: {e}", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(
        data={
            "assessment_id": str(assessment.AssessmentId),
            "questions": bilingual_questions,
        },
        status_code=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["Advisor (Bilingual)"],
    summary="Generate IDP in both English & Arabic",
    request=inline_serializer(
        name="GenerateBilingualIDPRequest",
        fields={
            "assessment_id": drf_serializers.UUIDField(),
            "profile": drf_serializers.DictField(required=False),
        },
    ),
    responses={200: OpenApiResponse(description="IDP in English and Arabic")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_ai
@check_ratelimit
def ai_generate_idp_bilingual(request: Request):
    """Generate IDP in both English and Arabic simultaneously."""
    assessment_id = request.data.get("assessment_id")
    if not assessment_id:
        return error_response("assessment_id is required.")

    assessment = assessment_selectors.get_assessment_by_id(assessment_id)
    if not assessment:
        return error_response("Assessment not found.", status_code=status.HTTP_404_NOT_FOUND)

    # IDOR check
    customer = _get_customer(request)
    access_error = _check_assessment_access(assessment, customer)
    if access_error:
        return error_response(access_error, status_code=status.HTTP_403_FORBIDDEN)

    try:
        idp_data = services.generate_bilingual_idp(
            assessment=assessment,
            request_profile=request.data.get("profile"),
        )
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(f"AI service error: {e}", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(data=idp_data)


# ============================================================================
# IDP CRUD — authenticated with IDOR checks
# ============================================================================

@extend_schema(tags=["Advisor"], summary="List IDPs", responses={200: IDPSerializer(many=True)})
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_idps(request: Request):
    customer = _get_customer(request)
    if not customer:
        return error_response("Authentication required.", status_code=status.HTTP_401_UNAUTHORIZED)
    # Only return the authenticated user's IDPs
    qs = selectors.list_idps_for_customer(customer)
    return success_response(data=IDPSerializer(qs, many=True).data)


@extend_schema(tags=["Advisor"], summary="Get IDP by ID", responses={200: IDPSerializer})
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_idp(request: Request, idp_id):
    idp = selectors.get_idp_by_id(idp_id)
    if not idp:
        return error_response("IDP not found.", status_code=status.HTTP_404_NOT_FOUND)

    # IDOR check
    customer = _get_customer(request)
    if idp.Customer_id and (not customer or str(idp.Customer_id) != str(customer.CustomerId)):
        return error_response("Access denied.", status_code=status.HTTP_403_FORBIDDEN)

    return success_response(data=IDPSerializer(idp).data)


@extend_schema(tags=["Advisor"], summary="Update an IDP")
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_idp(request: Request, idp_id):
    idp = selectors.get_idp_by_id(idp_id)
    if not idp:
        return error_response("IDP not found.", status_code=status.HTTP_404_NOT_FOUND)

    # IDOR check
    customer = _get_customer(request)
    if idp.Customer_id and (not customer or str(idp.Customer_id) != str(customer.CustomerId)):
        return error_response("Access denied.", status_code=status.HTTP_403_FORBIDDEN)

    field_map = {
        "target_role": "TargetRole",
        "current_level": "CurrentLevel",
        "timeline": "Timeline",
        "top_strength": "TopStrength",
        "growth_area": "GrowthArea",
        "skill_proficiency": "SkillProficiency",
        "learning_roadmap": "LearningRoadmap",
        "generated_by": "GeneratedBy",
    }
    for key, field in field_map.items():
        if key in request.data:
            setattr(idp, field, request.data[key])

    idp.UpdatedOn = timezone.now()
    idp.save()
    return success_response(data=IDPSerializer(idp).data)
