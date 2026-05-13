from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request

from apps.common.response import error_response, success_response
from integrations.sitecore_client import clear_cache, fetch_sitecore_courses

from . import selectors, services
from .serializers import (
    CourseEnrollmentSerializer,
    CourseRatingSerializer,
    CourseSerializer,
    KGCCandidateSerializer,
)


@extend_schema(tags=["Courses"], summary="List active courses", responses={200: CourseSerializer(many=True)})
@api_view(["GET"])
@permission_classes([AllowAny])
def list_courses(request: Request):
    category = request.query_params.get("category")
    qs = selectors.list_active_courses(category)
    return success_response(data=CourseSerializer(qs, many=True).data)


@extend_schema(tags=["Courses"], summary="Get course by ID", responses={200: CourseSerializer})
@api_view(["GET"])
@permission_classes([AllowAny])
def get_course(request: Request, course_id):
    course = selectors.get_course_by_id(course_id)
    if not course:
        return error_response("Course not found.", status_code=status.HTTP_404_NOT_FOUND)
    return success_response(data=CourseSerializer(course).data)


@extend_schema(tags=["Courses"], summary="Create a course")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_course(request: Request):
    try:
        course = services.create_course(request.data)
    except Exception as e:
        return error_response(str(e))
    return success_response(
        data=CourseSerializer(course).data,
        status_code=status.HTTP_201_CREATED,
    )


@extend_schema(tags=["Courses"], summary="List Sitecore CMS courses", responses={200: OpenApiResponse(description="Courses from Sitecore CMS")})
@api_view(["GET"])
@permission_classes([AllowAny])
def list_sitecore_courses(request: Request):
    refresh = request.query_params.get("refresh", "").lower() == "true"
    if refresh:
        clear_cache()
    courses = fetch_sitecore_courses(force_refresh=refresh)
    return success_response(data={"total": len(courses), "source": "sitecore", "courses": courses})


# ---------------------------------------------------------------------------
# Legacy synced-data endpoints
# ---------------------------------------------------------------------------

@extend_schema(tags=["Courses"], summary="List enrollments")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_enrollments(request: Request):
    rows = selectors.list_enrollments()
    return success_response(data=CourseEnrollmentSerializer(rows, many=True).data)


@extend_schema(tags=["Courses"], summary="List ratings")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_ratings(request: Request):
    customer_id = request.query_params.get("customer_id")
    rows = selectors.list_ratings(customer_id)
    return success_response(data=CourseRatingSerializer(rows, many=True).data)


@extend_schema(tags=["Courses"], summary="List KGC candidates")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_candidates(request: Request):
    rows = selectors.list_candidates()
    return success_response(data=KGCCandidateSerializer(rows, many=True).data)


@extend_schema(
    tags=["Courses"],
    summary="Get customer course orders from external DB",
    responses={200: OpenApiResponse(description="Customer orders with course details and progress")},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_orders(request: Request):
    """Return the authenticated customer's orders from the external MSSQL database."""
    customer = request.user

    try:
        data = selectors.get_mssql_customer_orders_by_email(customer.Email)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("MSSQL query failed: %s", e)
        return error_response("Could not fetch orders at this time.", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(data=data)


@extend_schema(
    tags=["Courses"],
    summary="Get course orders for a specific customer (HR view)",
    responses={200: OpenApiResponse(description="Customer orders with course details and progress")},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_orders_by_id(request: Request, customer_id):
    """Return orders for a specific customer — used by HR to view employee courses."""
    try:
        data = selectors.get_mssql_customer_orders(str(customer_id))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("MSSQL query failed: %s", e)
        return error_response("Could not fetch orders at this time.", status_code=status.HTTP_502_BAD_GATEWAY)

    return success_response(data=data)
