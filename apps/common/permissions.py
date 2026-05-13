from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.users.models import Customer


class IsAdminEmail(BasePermission):
    """Allow access only if the authenticated user's email matches ADMIN_EMAIL."""

    def has_permission(self, request: Request, view) -> bool:
        user = request.user
        if not isinstance(user, Customer):
            return False
        return user.Email.lower() == getattr(settings, "ADMIN_EMAIL", "").lower()


class IsCompanyOwner(BasePermission):
    """Allow access only if the authenticated user owns the company in the URL."""

    def has_object_permission(self, request: Request, view, obj) -> bool:  # type: ignore[override]
        user = request.user
        if not isinstance(user, Customer):
            return False
        return obj.Owner_id == user.CustomerId


class IsResourceOwner(BasePermission):
    """
    IDOR protection — checks that the resource's Customer FK matches the
    authenticated user.

    Works on any model that has a `Customer` FK or `Customer_id` field
    pointing to Customer.CustomerId.
    """

    def has_object_permission(self, request: Request, view, obj) -> bool:  # type: ignore[override]
        user = request.user
        if not isinstance(user, Customer):
            return False
        # The FK field stores CustomerId (UUID), not the PK
        return getattr(obj, "Customer_id", None) == user.CustomerId
