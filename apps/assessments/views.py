from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request

from apps.common.response import error_response, success_response
from apps.users.models import Customer

from . import selectors, services
from .serializers import AssessmentSerializer


def _get_customer(request: Request) -> Customer | None:
    user = request.user
    return user if isinstance(user, Customer) else None


@extend_schema(tags=["Assessments"], summary="Create a new assessment")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_assessment(request: Request):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    assessment = services.create_assessment(customer=customer, data=request.data)
    return success_response(
        data=AssessmentSerializer(assessment).data,
        status_code=status.HTTP_201_CREATED,
    )


@extend_schema(tags=["Assessments"], summary="List assessments")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_assessments(request: Request):
    customer = _get_customer(request)
    if not customer:
        return error_response("Authentication required.", status_code=status.HTTP_401_UNAUTHORIZED)
    # Only return the authenticated user's assessments
    qs = selectors.list_assessments_for_customer(customer)
    return success_response(data=AssessmentSerializer(qs, many=True).data)


@extend_schema(tags=["Assessments"], summary="Get assessment by ID", responses={200: AssessmentSerializer})
@api_view(["GET"])
@permission_classes([AllowAny])
def get_assessment(request: Request, assessment_id):
    assessment = selectors.get_assessment_by_id(assessment_id)
    if not assessment:
        return error_response("Assessment not found.", status_code=status.HTTP_404_NOT_FOUND)

    # IDOR check — if assessment belongs to a customer, only that customer can view
    customer = _get_customer(request)
    if assessment.Customer_id:
        if not customer or str(assessment.Customer_id) != str(customer.CustomerId):
            return error_response("Access denied.", status_code=status.HTTP_403_FORBIDDEN)

    return success_response(data=AssessmentSerializer(assessment).data)


@extend_schema(tags=["Assessments"], summary="Update an assessment")
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_assessment(request: Request, assessment_id):
    assessment = selectors.get_assessment_by_id(assessment_id)
    if not assessment:
        return error_response("Assessment not found.", status_code=status.HTTP_404_NOT_FOUND)

    # IDOR check
    customer = _get_customer(request)
    if assessment.Customer_id and (not customer or str(assessment.Customer_id) != str(customer.CustomerId)):
        return error_response("Access denied.", status_code=status.HTTP_403_FORBIDDEN)

    assessment = services.update_assessment(assessment, request.data)
    return success_response(data=AssessmentSerializer(assessment).data)
