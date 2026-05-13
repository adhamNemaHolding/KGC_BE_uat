"""
Views — thin HTTP layer. All logic delegated to services/selectors.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request

from apps.common.response import error_response, success_response
from apps.common.throttling import check_ratelimit, rate_limit_auth

from . import selectors, services
from .models import Customer
from .serializers import (
    CustomerEmailVerificationSerializer,
    CustomerProfileSerializer,
    CustomerSerializer,
    PasswordResetSerializer,
    ProfessionalProfileSerializer,
)


def _get_customer(request: Request) -> Customer | None:
    user = request.user
    return user if isinstance(user, Customer) else None


def _customer_dict(customer: Customer) -> dict:
    return CustomerSerializer(customer).data


# ============================================================================
# Auth
# ============================================================================

@extend_schema(
    tags=["Auth"],
    summary="List active users (public)",
    responses={200: OpenApiResponse(description="List of active user summaries")},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def available_users(request: Request):
    customers = selectors.list_active_customers()
    data = customers.values("Email", "Provider", "IsActive", "Role", "CreatedOn")
    return success_response(data=list(data))


@extend_schema(
    tags=["Auth"],
    summary="Register a new account",
    request=inline_serializer(
        name="SignupRequest",
        fields={
            "email": drf_serializers.EmailField(),
            "password": drf_serializers.CharField(min_length=8),
            "role": drf_serializers.ChoiceField(choices=["user", "company"], default="user"),
            "company_name": drf_serializers.CharField(required=False, help_text="Required for company role"),
            "company_code": drf_serializers.CharField(required=False, help_text="Join existing company (individual role only)"),
        },
    ),
    responses={201: OpenApiResponse(description="Account created with tokens")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_auth
@check_ratelimit
def signup(request: Request):
    data = request.data
    try:
        result = services.signup(
            email=data.get("email") or data.get("Email", ""),
            password=data.get("password", ""),
            canvas_user_id=data.get("canvas_user_id") or data.get("CanvasUserId", ""),
            provider=data.get("provider") or data.get("Provider", "local"),
            role=data.get("role") or data.get("Role", "user"),
            company_name=data.get("company_name") or data.get("CompanyName"),
            company_code=data.get("company_code") or data.get("CompanyCode"),
            invite_token=data.get("invite_token"),
        )
    except (ValueError, PermissionError) as e:
        return error_response(str(e))

    company_data = None
    if result.company:
        company_data = {
            "CompanyId": str(result.company.CompanyId),
            "Name": result.company.Name,
            "Code": result.company.Code,
        }

    # Check if the new account is already verified (e.g. invited users)
    from .models import CustomerEmailVerification
    ver = CustomerEmailVerification.objects.filter(
        CustomerId=result.customer.CustomerId
    ).first()
    is_verified = ver.IsEmailVerified if ver else False

    return success_response(
        data={
            "customer": _customer_dict(result.customer),
            "tokens": result.tokens.to_dict(),
            "account_type": "company" if company_data else "individual",
            "company": company_data,
            "is_email_verified": is_verified,
        },
        status_code=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["Auth"],
    summary="Login with email & password",
    request=inline_serializer(
        name="LoginRequest",
        fields={
            "email": drf_serializers.EmailField(),
            "password": drf_serializers.CharField(),
        },
    ),
    responses={200: OpenApiResponse(description="Customer data with JWT tokens")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_auth
@check_ratelimit
def login(request: Request):
    try:
        result = services.login(
            email=request.data.get("email", ""),
            password=request.data.get("password", ""),
        )
    except ValueError as e:
        return error_response(str(e))
    except PermissionError as e:
        return error_response(str(e), status_code=status.HTTP_401_UNAUTHORIZED)

    return success_response(data={
        "customer": _customer_dict(result.customer),
        "tokens": result.tokens.to_dict(),
        "is_email_verified": result.is_email_verified,
        "has_profile": result.has_profile,
        "account_type": "company" if result.customer.Role == "company" else "individual",
        "company": result.company_data,
    })


@extend_schema(
    tags=["Auth"],
    summary="Refresh JWT access token",
    request=inline_serializer(
        name="RefreshTokenRequest",
        fields={"refresh": drf_serializers.CharField()},
    ),
    responses={200: OpenApiResponse(description="New access + refresh tokens")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request: Request):
    try:
        tokens = services.refresh_access_token(request.data.get("refresh", ""))
    except (ValueError, Exception) as e:
        return error_response(str(e), status_code=status.HTTP_401_UNAUTHORIZED)
    return success_response(data=tokens)


@extend_schema(
    tags=["Auth"],
    summary="Logout (blacklist refresh token)",
    request=inline_serializer(
        name="LogoutRequest",
        fields={"refresh": drf_serializers.CharField()},
    ),
    responses={200: OpenApiResponse(description="Logged out successfully")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def logout(request: Request):
    services.logout(request.data.get("refresh", ""))
    return success_response(message="Logged out successfully.")


@extend_schema(
    tags=["Auth"],
    summary="Google OAuth login/signup",
    request=inline_serializer(
        name="GoogleAuthRequest",
        fields={
            "code": drf_serializers.CharField(help_text="Google authorization code"),
            "redirect_uri": drf_serializers.CharField(help_text="Must match the URI used in the frontend consent screen"),
        },
    ),
    responses={200: OpenApiResponse(description="Customer data with JWT tokens")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_auth
@check_ratelimit
def google_auth(request: Request):
    try:
        result = services.google_auth(
            code=request.data.get("code", ""),
            redirect_uri=request.data.get("redirect_uri", ""),
        )
    except ValueError as e:
        return error_response(str(e))
    except PermissionError as e:
        return error_response(str(e), status_code=status.HTTP_401_UNAUTHORIZED)

    return success_response(data={
        "customer": _customer_dict(result.customer),
        "tokens": result.tokens.to_dict(),
        "is_email_verified": result.is_email_verified,
        "has_profile": result.has_profile,
        "account_type": "company" if result.customer.Role == "company" else "individual",
        "company": result.company_data,
    })


@extend_schema(
    tags=["Auth"],
    summary="Request password reset",
    request=inline_serializer(
        name="PasswordResetRequest",
        fields={"email": drf_serializers.EmailField()},
    ),
    responses={200: OpenApiResponse(description="Reset link sent if email exists")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_auth
@check_ratelimit
def request_password_reset(request: Request):
    try:
        services.request_password_reset(request.data.get("email", ""))
    except ValueError as e:
        return error_response(str(e))

    # Always return the same message — never reveal whether the email exists
    return success_response(data={"message": "If the email exists, a reset link has been sent."})


@extend_schema(
    tags=["Auth"],
    summary="Confirm password reset",
    request=inline_serializer(
        name="PasswordResetConfirmRequest",
        fields={
            "token": drf_serializers.CharField(),
            "new_password": drf_serializers.CharField(min_length=8),
        },
    ),
    responses={200: OpenApiResponse(description="Password reset successfully")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def confirm_password_reset(request: Request):
    try:
        services.confirm_password_reset(
            token=request.data.get("token", ""),
            new_password=request.data.get("new_password", ""),
        )
    except ValueError as e:
        return error_response(str(e))
    return success_response(message="Password reset successfully.")


@extend_schema(
    tags=["Auth"],
    summary="Verify email address",
    request=inline_serializer(
        name="VerifyEmailRequest",
        fields={"token": drf_serializers.CharField()},
    ),
    responses={200: OpenApiResponse(description="Email verified successfully")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request: Request):
    try:
        services.verify_email(request.data.get("token", ""))
    except ValueError as e:
        return error_response(str(e))
    return success_response(message="Email verified successfully.")


@extend_schema(
    tags=["Auth"],
    summary="Resend verification email",
    request=inline_serializer(
        name="ResendVerificationRequest",
        fields={"email": drf_serializers.EmailField()},
    ),
    responses={200: OpenApiResponse(description="Verification email resent if applicable")},
)
@api_view(["POST"])
@permission_classes([AllowAny])
@rate_limit_auth
@check_ratelimit
def resend_verification(request: Request):
    try:
        services.resend_verification_email(request.data.get("email", ""))
    except ValueError as e:
        return error_response(str(e))
    return success_response(message="If the email exists and is unverified, a new link has been sent.")


# ============================================================================
# Professional Profile
# ============================================================================

@extend_schema(tags=["Users"], summary="Create or update professional profile")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_professional_profile(request: Request):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    profile, created = services.upsert_professional_profile(customer, request.data)
    serializer = ProfessionalProfileSerializer(profile)
    code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return success_response(data=serializer.data, status_code=code)


@extend_schema(tags=["Users"], summary="Get own professional profile")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_professional_profile(request: Request):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    profile = selectors.get_professional_profile(customer)
    if not profile:
        return error_response("Professional profile not found.", status_code=status.HTTP_404_NOT_FOUND)

    return success_response(data=ProfessionalProfileSerializer(profile).data)


@extend_schema(tags=["Users"], summary="Get professional profile by customer ID")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_professional_profile_by_customer(request: Request, customer_id):
    profile = selectors.get_professional_profile_by_customer_id(customer_id)
    if not profile:
        return error_response("Professional profile not found.", status_code=status.HTTP_404_NOT_FOUND)
    return success_response(data=ProfessionalProfileSerializer(profile).data)


# ============================================================================
# CRUD — synced tables (read-only endpoints)
# ============================================================================

@extend_schema(tags=["Users"], summary="List all customers")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_customers(request: Request):
    customers = selectors.list_all_customers()
    return success_response(data=CustomerSerializer(customers, many=True).data)


@extend_schema(tags=["Users"], summary="List email verifications")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_email_verifications(request: Request):
    rows = selectors.list_email_verifications()
    return success_response(data=CustomerEmailVerificationSerializer(rows, many=True).data)


@extend_schema(tags=["Users"], summary="List customer profiles")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_profiles(request: Request):
    customer_id = request.query_params.get("customer_id")
    rows = selectors.list_customer_profiles(customer_id)
    return success_response(data=CustomerProfileSerializer(rows, many=True).data)


@extend_schema(tags=["Users"], summary="List refresh tokens")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_refresh_tokens(request: Request):
    rows = selectors.list_refresh_tokens()
    data = rows.values("Id", "CustomerId", "ExpiresOn", "CreatedOn", "UpdatedOn")
    return success_response(data=list(data))


@extend_schema(tags=["Users"], summary="List password resets")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_password_resets(request: Request):
    rows = selectors.list_password_resets()
    return success_response(data=PasswordResetSerializer(rows, many=True).data)
