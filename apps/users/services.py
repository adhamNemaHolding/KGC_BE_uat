"""
Services — all business logic for the users app.

Views call services. Services call selectors for reads and the ORM for writes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.companies import selectors as company_selectors
from apps.companies.models import Company, CompanyMember

import logging

import requests as http_requests

from . import selectors
from .models import (
    Customer,
    CustomerEmailVerification,
    CustomerRefreshToken,
    PasswordReset,
    ProfessionalProfile,
    RoleChoices,
)
from integrations.email_client import send_verification_email as _send_verification_email_sync
from integrations.salesforce_client import create_salesforce_lead

import threading

logger = logging.getLogger(__name__)


def _send_verification_email(email: str, token: str) -> None:
    """Fire-and-forget: send the verification email in a background thread."""
    t = threading.Thread(target=_send_verification_email_sync, args=(email, token), daemon=True)
    t.start()

_ph = PasswordHasher()


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------
@dataclass
class TokenPair:
    access: str
    refresh: str

    def to_dict(self) -> dict[str, str]:
        return {"access": self.access, "refresh": self.refresh}


@dataclass
class SignupResult:
    customer: Customer
    tokens: TokenPair
    company: Company | None


@dataclass
class LoginResult:
    customer: Customer
    tokens: TokenPair
    is_email_verified: bool
    has_profile: bool
    company_data: dict | None


# ---------------------------------------------------------------------------
# Token generation
# ---------------------------------------------------------------------------
def generate_tokens(customer_id: uuid.UUID, email: str) -> TokenPair:
    refresh = RefreshToken()
    refresh["customer_id"] = str(customer_id)
    refresh["email"] = email

    try:
        CustomerRefreshToken.objects.create(
            CustomerId=customer_id,
            RefreshToken=str(refresh),
            ExpiresOn=timezone.now() + timedelta(days=7),
        )
    except Exception:
        pass

    return TokenPair(access=str(refresh.access_token), refresh=str(refresh))


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------
def signup(
    *,
    email: str,
    password: str,
    canvas_user_id: str = "",
    provider: str = "local",
    role: str = RoleChoices.USER,
    company_name: str | None = None,
    company_code: str | None = None,
    invite_token: str | None = None,
) -> SignupResult:
    if not email or not password:
        raise ValueError("Email and password are required.")

    # Normalize email to prevent case-duplicate accounts
    email = email.strip().lower()

    if role not in (RoleChoices.USER, RoleChoices.COMPANY):
        raise ValueError("Role must be 'user' or 'company'.")

    if role == RoleChoices.COMPANY and not company_name:
        raise ValueError("company_name is required for company role.")

    if selectors.customer_email_exists(email):
        raise ValueError("Email already registered.")

    # ── Handle invite token ────────────────────────────────────────
    invited = False
    if invite_token:
        from apps.companies.services import verify_invite_token
        try:
            invite_data = verify_invite_token(invite_token)
        except Exception:
            raise ValueError("Invalid or expired invitation link.")
        # Override company_code from the trusted token
        company_code = invite_data.get("company_code")
        invited = True

    # Validate company_code before creating anything
    join_company = None
    if role == RoleChoices.USER and company_code:
        join_company = company_selectors.get_company_by_code(company_code.strip())
        if not join_company:
            raise ValueError("Invalid company code.")

    # Validate company name uniqueness for company signups (case-insensitive)
    if role == RoleChoices.COMPANY and company_name:
        from apps.companies.models import Company as CompanyModel
        if CompanyModel.objects.filter(Name__iexact=company_name.strip()).exists():
            raise ValueError("A company with this name already exists.")

    # All validations passed — create everything in a single transaction
    with transaction.atomic():
        customer = Customer.objects.create(
            CustomerId=uuid.uuid4(),
            Email=email,
            CanvasUserId=canvas_user_id,
            PasswordHash=_ph.hash(password),
            Provider=provider,
            IsActive=True,
            Role=role,
        )

        company = None

        if role == RoleChoices.COMPANY:
            code = uuid.uuid4().hex[:8].upper()
            company = Company.objects.create(
                Name=company_name.strip(),
                Code=code,
                Owner=customer,
            )
            CompanyMember.objects.create(Company=company, Customer=customer)

        elif join_company:
            # Individual user joining an existing company
            CompanyMember.objects.create(Company=join_company, Customer=customer)
            company = join_company

        # Create email verification record
        verification_token = uuid.uuid4().hex
        CustomerEmailVerification.objects.create(
            CustomerId=customer.CustomerId,
            IsEmailVerified=invited,  # Auto-verify for invited users
            EmailVerificationToken=verification_token,
        )

    # Send verification email only for non-invited users
    if not invited:
        _send_verification_email(email, verification_token)

    # ── Create Salesforce Lead (fire-and-forget) ───────────────────
    def _create_sf_lead():
        name_parts = canvas_user_id.strip().split(None, 1) if canvas_user_id else []
        first = name_parts[0] if len(name_parts) >= 1 else ""
        last = name_parts[1] if len(name_parts) >= 2 else ""

        sf_company = ""
        if role == RoleChoices.COMPANY and company_name:
            sf_company = company_name.strip()
        elif join_company:
            sf_company = join_company.Name

        create_salesforce_lead(
            first_name=first,
            last_name=last,
            email=email,
            company=sf_company,
        )

    threading.Thread(target=_create_sf_lead, daemon=True).start()

    tokens = generate_tokens(customer.CustomerId, email)

    return SignupResult(
        customer=customer,
        tokens=tokens,
        company=company,
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def login(*, email: str, password: str) -> LoginResult:
    if not email or not password:
        raise ValueError("Email and password are required.")

    customer = selectors.get_customer_by_email(email)
    if not customer or not customer.PasswordHash:
        raise PermissionError("Invalid email or password.")

    try:
        _ph.verify(customer.PasswordHash, password)
    except VerifyMismatchError:
        raise PermissionError("Invalid email or password.")

    tokens = generate_tokens(customer.CustomerId, email)

    has_profile = selectors.customer_profile_exists(customer.CustomerId)

    membership = company_selectors.get_membership_for_customer(customer)
    company_data = None
    if membership:
        company_data = {
            "CompanyId": str(membership.Company.CompanyId),
            "Name": membership.Company.Name,
            "Code": membership.Company.Code,
        }

    verification = selectors.get_email_verification(customer.CustomerId)
    is_email_verified = verification.IsEmailVerified if verification else False

    return LoginResult(
        customer=customer,
        tokens=tokens,
        is_email_verified=is_email_verified,
        has_profile=has_profile,
        company_data=company_data,
    )


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------
def refresh_access_token(refresh_token_str: str) -> dict[str, str]:
    if not refresh_token_str:
        raise ValueError("Refresh token is required.")
    token = RefreshToken(refresh_token_str)
    return {"access": str(token.access_token), "refresh": str(token)}


def logout(refresh_token_str: str) -> None:
    """Blacklist the refresh token so it can't be reused."""
    if not refresh_token_str:
        return
    try:
        token = RefreshToken(refresh_token_str)
        token.blacklist()
    except Exception:
        pass  # Token already expired or blacklisted — that's fine


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
def verify_email(token: str) -> None:
    if not token:
        raise ValueError("Verification token is required.")

    verification = selectors.get_pending_verification_by_token(token)
    if not verification:
        # Check if already verified (idempotent — e.g. React strict-mode double call)
        already = CustomerEmailVerification.objects.filter(
            EmailVerificationToken=token, IsEmailVerified=True
        ).exists()
        if already:
            return  # already verified — success
        raise ValueError("Invalid or expired verification link.")

    verification.IsEmailVerified = True
    verification.UpdatedOn = timezone.now()
    verification.save()


def resend_verification_email(email: str) -> None:
    """Re-generate token and resend the verification email."""
    if not email:
        raise ValueError("Email is required.")

    customer = selectors.get_customer_by_email(email)
    if not customer:
        return  # Silent — don't reveal whether the email exists

    verification = selectors.get_email_verification(customer.CustomerId)
    if not verification or verification.IsEmailVerified:
        return  # Already verified or no record

    new_token = uuid.uuid4().hex
    verification.EmailVerificationToken = new_token
    verification.UpdatedOn = timezone.now()
    verification.save()

    _send_verification_email(email, new_token)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
def request_password_reset(email: str) -> str | None:
    """Returns the reset token (or None if user not found — silent for security)."""
    if not email:
        raise ValueError("Email is required.")

    customer = selectors.get_customer_by_email(email)
    if not customer:
        return None

    reset_token = uuid.uuid4().hex
    PasswordReset.objects.create(
        CustomerId=customer.CustomerId,
        PasswordResetToken=reset_token,
        PasswordResetTokenExpiry=timezone.now() + timedelta(hours=1),
        IsUsed=False,
    )
    return reset_token


def confirm_password_reset(*, token: str, new_password: str) -> None:
    if not token or not new_password:
        raise ValueError("Token and new_password are required.")

    reset = selectors.get_valid_password_reset(token)
    if not reset:
        raise ValueError("Invalid or expired reset token.")

    customer = selectors.get_customer_by_id(reset.CustomerId)
    if not customer:
        raise ValueError("Customer not found.")

    customer.PasswordHash = _ph.hash(new_password)
    customer.UpdatedOn = timezone.now()
    customer.save()

    reset.IsUsed = True
    reset.UpdatedOn = timezone.now()
    reset.save()


# ---------------------------------------------------------------------------
# Professional Profile
# ---------------------------------------------------------------------------
def upsert_professional_profile(customer: Customer, data: dict[str, Any]) -> tuple[ProfessionalProfile, bool]:
    profile, created = ProfessionalProfile.objects.update_or_create(
        Customer=customer,
        defaults={
            "AgeRange": data.get("age_range", ""),
            "IsWorking": data.get("is_working", False),
            "CompanyName": data.get("company_name", "") if data.get("is_working") else "",
            "CompanyIndustry": data.get("company_industry", "") if data.get("is_working") else "",
            "CurrentRole": data.get("current_role", ""),
            "TargetRole": data.get("target_role", ""),
            "ProfessionalInterests": data.get("professional_interests", []),
            "CareerObjective": data.get("career_objective", ""),
            "ExperienceLevel": data.get("experience_level", ""),
            "BiggestChallenges": data.get("biggest_challenges", []),
            "Recommendations": data.get("recommendations", []),
            "StudyTimePerWeek": data.get("study_time_per_week", ""),
            "UpdatedOn": timezone.now(),
        },
    )
    return profile, created


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def google_auth(*, code: str, redirect_uri: str) -> LoginResult:
    """
    Exchange a Google authorization code for user info, then
    create or login the customer.
    """
    from django.conf import settings as django_settings

    if not code:
        raise ValueError("Authorization code is required.")

    # 1. Exchange code for access token
    token_resp = http_requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": django_settings.GOOGLE_CLIENT_ID,
            "client_secret": django_settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )

    if token_resp.status_code != 200:
        logger.error("Google token exchange failed: %s", token_resp.text)
        raise PermissionError("Google authentication failed.")

    access_token = token_resp.json().get("access_token")
    if not access_token:
        raise PermissionError("Google did not return an access token.")

    # 2. Get user info
    userinfo_resp = http_requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )

    if userinfo_resp.status_code != 200:
        logger.error("Google userinfo failed: %s", userinfo_resp.text)
        raise PermissionError("Failed to get Google user info.")

    userinfo = userinfo_resp.json()
    email = userinfo.get("email")
    if not email:
        raise PermissionError("Google account has no email.")

    # 3. Find or create customer
    customer = selectors.get_customer_by_email(email)

    if not customer:
        customer = Customer.objects.create(
            CustomerId=uuid.uuid4(),
            Email=email,
            CanvasUserId="",
            PasswordHash=None,  # Google users don't have a password
            Provider="google",
            IsActive=True,
            Role=RoleChoices.USER,
        )

    tokens = generate_tokens(customer.CustomerId, email)

    has_profile = selectors.customer_profile_exists(customer.CustomerId)

    membership = company_selectors.get_membership_for_customer(customer)
    company_data = None
    if membership:
        company_data = {
            "CompanyId": str(membership.Company.CompanyId),
            "Name": membership.Company.Name,
            "Code": membership.Company.Code,
        }

    return LoginResult(
        customer=customer,
        tokens=tokens,
        is_email_verified=True,
        has_profile=has_profile,
        company_data=company_data,
    )
