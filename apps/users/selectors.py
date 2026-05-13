"""
Selectors — all database reads for the users app.

Every queryset lives here. Views and services never call the ORM directly.
"""

from __future__ import annotations

import uuid as _uuid

from django.db.models import QuerySet

from .models import (
    Customer,
    CustomerEmailVerification,
    CustomerProfile,
    CustomerRefreshToken,
    PasswordReset,
    ProfessionalProfile,
)


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
def get_customer_by_email(email: str, active_only: bool = True) -> Customer | None:
    qs = Customer.objects.filter(Email=email)
    if active_only:
        qs = qs.filter(IsActive=True)
    return qs.first()


def get_customer_by_id(customer_id: _uuid.UUID) -> Customer | None:
    return Customer.objects.filter(CustomerId=customer_id).first()


def customer_email_exists(email: str) -> bool:
    return Customer.objects.filter(Email__iexact=email, IsActive=True).exists()


def list_active_customers() -> QuerySet[Customer]:
    return Customer.objects.filter(IsActive=True).order_by("-CreatedOn")


def list_all_customers() -> QuerySet[Customer]:
    return Customer.objects.all().order_by("-CreatedOn")


# ---------------------------------------------------------------------------
# Professional Profile
# ---------------------------------------------------------------------------
def get_professional_profile(customer: Customer) -> ProfessionalProfile | None:
    return ProfessionalProfile.objects.filter(Customer=customer).select_related("Customer").first()


def get_professional_profile_by_customer_id(customer_id: _uuid.UUID) -> ProfessionalProfile | None:
    return (
        ProfessionalProfile.objects
        .filter(Customer__CustomerId=customer_id)
        .select_related("Customer")
        .first()
    )


def get_profile_data_dict(profile: ProfessionalProfile) -> dict:
    """Convert a ProfessionalProfile into the dict consumed by AI services."""
    return {
        "current_role": profile.CurrentRole,
        "target_role": profile.TargetRole,
        "experience_level": profile.ExperienceLevel,
        "company_industry": profile.CompanyIndustry,
        "career_objective": profile.CareerObjective,
        "professional_interests": profile.ProfessionalInterests,
        "biggest_challenges": profile.BiggestChallenges,
        "study_time_per_week": profile.StudyTimePerWeek,
    }


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------
def get_email_verification(customer_id: _uuid.UUID) -> CustomerEmailVerification | None:
    return CustomerEmailVerification.objects.filter(CustomerId=customer_id).first()


def get_pending_verification_by_token(token: str) -> CustomerEmailVerification | None:
    return CustomerEmailVerification.objects.filter(
        EmailVerificationToken=token,
        IsEmailVerified=False,
    ).first()


def list_email_verifications() -> QuerySet[CustomerEmailVerification]:
    return CustomerEmailVerification.objects.all().order_by("-CreatedOn")


# ---------------------------------------------------------------------------
# Customer Profile (legacy synced table)
# ---------------------------------------------------------------------------
def customer_profile_exists(customer_id: _uuid.UUID) -> bool:
    return CustomerProfile.objects.filter(CustomerId=customer_id).exists()


def list_customer_profiles(customer_id: _uuid.UUID | None = None) -> QuerySet[CustomerProfile]:
    qs = CustomerProfile.objects.all()
    if customer_id:
        qs = qs.filter(CustomerId=customer_id)
    return qs.order_by("-CreatedOn")


# ---------------------------------------------------------------------------
# Refresh Tokens
# ---------------------------------------------------------------------------
def list_refresh_tokens() -> QuerySet[CustomerRefreshToken]:
    return CustomerRefreshToken.objects.all().order_by("-CreatedOn")


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------
def get_valid_password_reset(token: str) -> PasswordReset | None:
    from django.utils import timezone
    return PasswordReset.objects.filter(
        PasswordResetToken=token,
        IsUsed=False,
        PasswordResetTokenExpiry__gte=timezone.now(),
    ).first()


def list_password_resets() -> QuerySet[PasswordReset]:
    return PasswordReset.objects.all().order_by("-CreatedOn")
