"""
Standardized API response helpers.

Every endpoint returns a consistent envelope:

    {
        "status": "success" | "error",
        "data": { ... } | null,
        "message": "Human-readable message" | null,
        "errors": { "field": ["..."] } | null
    }
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def success_response(
    data: Any = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return Response(
        {
            "status": "success",
            "data": data,
            "message": message,
            "errors": None,
        },
        status=status_code,
    )


def error_response(
    message: str = _("An error occurred."),
    errors: dict | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    return Response(
        {
            "status": "error",
            "data": None,
            "message": message,
            "errors": errors,
        },
        status=status_code,
    )


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """DRF exception handler that wraps errors in the standard envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    errors = response.data if isinstance(response.data, dict) else {"detail": response.data}
    return error_response(
        message=str(errors.get("detail", _("Validation error."))),
        errors=errors,
        status_code=response.status_code,
    )
