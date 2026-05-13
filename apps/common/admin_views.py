"""
Admin dashboard API views.

Access restricted to the user whose email matches settings.ADMIN_EMAIL.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.advisor.models import IndividualDevelopmentPlan
from apps.advisor.selectors import list_idps_for_customer
from apps.advisor.serializers import IDPSerializer
from apps.assessments.models import Assessment
from apps.assessments.selectors import list_assessments_for_customer
from apps.assessments.serializers import AssessmentSerializer
from apps.common.permissions import IsAdminEmail
from apps.common.response import error_response, success_response
from apps.users.models import (
    Customer,
    CustomerEmailVerification,
    CustomerProfile,
    ProfessionalProfile,
)
from apps.users.selectors import (
    get_customer_by_id,
    get_professional_profile,
    list_all_customers,
)
from apps.users.serializers import (
    CustomerEmailVerificationSerializer,
    CustomerProfileSerializer,
    CustomerSerializer,
    ProfessionalProfileSerializer,
)


@extend_schema(tags=["Admin"], summary="Verify admin access")
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminEmail])
def admin_verify(request: Request):
    return success_response(data={"is_admin": True})


@extend_schema(tags=["Admin"], summary="List all users with summary stats")
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminEmail])
def admin_list_users(request: Request):
    customers = list_all_customers()
    results = []
    for customer in customers:
        profile = ProfessionalProfile.objects.filter(Customer=customer).first()
        assessment_count = Assessment.objects.filter(Customer=customer).count()
        idp_count = IndividualDevelopmentPlan.objects.filter(Customer=customer).count()
        cp = CustomerProfile.objects.filter(CustomerId=customer.CustomerId).first()

        results.append({
            **CustomerSerializer(customer).data,
            "FirstName": cp.FirstName if cp else None,
            "LastName": cp.LastName if cp else None,
            "CurrentRole": profile.CurrentRole if profile else None,
            "TargetRole": profile.TargetRole if profile else None,
            "assessment_count": assessment_count,
            "idp_count": idp_count,
        })

    return success_response(data=results)


@extend_schema(tags=["Admin"], summary="Get full user detail")
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminEmail])
def admin_user_detail(request: Request, customer_id):
    customer = get_customer_by_id(customer_id)
    if not customer:
        return error_response("User not found.", status_code=status.HTTP_404_NOT_FOUND)

    # Professional profile
    profile = get_professional_profile(customer)

    # Legacy profile (name / phone)
    cp = CustomerProfile.objects.filter(CustomerId=customer.CustomerId).first()

    # Email verification
    ev = CustomerEmailVerification.objects.filter(CustomerId=customer.CustomerId).first()

    # Assessments
    assessments = list_assessments_for_customer(customer)

    # IDPs
    idps = list_idps_for_customer(customer)

    data = {
        "customer": CustomerSerializer(customer).data,
        "customer_profile": CustomerProfileSerializer(cp).data if cp else None,
        "professional_profile": ProfessionalProfileSerializer(profile).data if profile else None,
        "email_verification": CustomerEmailVerificationSerializer(ev).data if ev else None,
        "assessments": AssessmentSerializer(assessments, many=True).data,
        "idps": IDPSerializer(idps, many=True).data,
    }

    return success_response(data=data)


@extend_schema(tags=["Admin"], summary="Dashboard summary stats")
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminEmail])
def admin_stats(request: Request):
    total_users = Customer.objects.count()
    active_users = Customer.objects.filter(IsActive=True).count()
    total_assessments = Assessment.objects.count()
    completed_assessments = Assessment.objects.filter(Status="completed").count()
    total_idps = IndividualDevelopmentPlan.objects.count()

    return success_response(data={
        "total_users": total_users,
        "active_users": active_users,
        "total_assessments": total_assessments,
        "completed_assessments": completed_assessments,
        "total_idps": total_idps,
    })
