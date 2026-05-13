"""
Custom JWT authentication that resolves users from the Customer model
instead of Django's default auth.User.
"""

from __future__ import annotations

import uuid

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings

from .models import Customer


class CustomerJWTAuthentication(JWTAuthentication):

    def get_user(self, validated_token):
        try:
            customer_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken("Token contained no recognizable user identification")

        try:
            normalized = str(uuid.UUID(str(customer_id)))
        except (ValueError, AttributeError):
            raise InvalidToken("Invalid customer ID in token")

        user = Customer.objects.filter(CustomerId=normalized).first()

        if not user:
            raise AuthenticationFailed("User not found", code="user_not_found")
        if not user.IsActive:
            raise AuthenticationFailed("User is inactive", code="user_inactive")

        return user

    def authenticate(self, request):
        try:
            result = super().authenticate(request)
            if result is None:
                return None
            return result
        except (AuthenticationFailed, InvalidToken):
            return None
