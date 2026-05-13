"""
Rate limiting decorators for views.

Uses django-ratelimit with in-process LocMemCache (no Redis needed).
Keyed by IP for anonymous users, by customer_id for authenticated users.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.request import Request

from apps.common.response import error_response


def _get_rate_key(group: str, request: Request) -> str:
    """Rate-limit key: customer_id if authenticated, else IP."""
    user = request.user
    if hasattr(user, "CustomerId"):
        return str(user.CustomerId)
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit_auth(fn: Callable) -> Callable:
    """5 attempts per minute for login/signup/password-reset."""
    return ratelimit(key=_get_rate_key, rate="5/m", method="POST", block=False)(fn)


def rate_limit_ai(fn: Callable) -> Callable:
    """10 AI calls per minute per user — protects OpenAI billing."""
    return ratelimit(key=_get_rate_key, rate="10/m", method="POST", block=False)(fn)


def check_ratelimit(view_fn: Callable) -> Callable:
    """Wrapper that returns 429 if the request was rate-limited."""
    @wraps(view_fn)
    def wrapper(request: Request, *args, **kwargs):
        if getattr(request, "limited", False):
            return error_response(
                "Too many requests. Please try again later.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return view_fn(request, *args, **kwargs)
    return wrapper
