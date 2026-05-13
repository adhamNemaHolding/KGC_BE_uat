from __future__ import annotations

import uuid as _uuid

from django.db.models import QuerySet

from .models import Course, CourseEnrollment, CourseRating, KGCCandidate
from integrations.mssql_client import get_customer_orders_with_details, get_customer_by_email


def get_course_by_id(course_id: _uuid.UUID) -> Course | None:
    return Course.objects.filter(CourseId=course_id, IsActive=True).first()


def list_active_courses(category: str | None = None) -> QuerySet[Course]:
    qs = Course.objects.filter(IsActive=True).order_by("Category", "Name")
    if category:
        qs = qs.filter(Category__icontains=category)
    return qs


def get_active_courses_as_dicts() -> list[dict]:
    """Return all active courses as plain dicts for AI service consumption."""
    return list(
        Course.objects.filter(IsActive=True).values(
            "CourseId", "Name", "Description", "Objectives", "Category",
            "SubCategory", "Duration", "Price", "Currency", "Link",
        )
    )


def get_course_name_link_map() -> dict[str, str]:
    """Return a {lowercase_name: link} dict for all active courses with links."""
    courses = Course.objects.filter(IsActive=True).values_list("Name", "Link")
    return {name.lower().strip(): link for name, link in courses if link}


def list_enrollments() -> QuerySet[CourseEnrollment]:
    return CourseEnrollment.objects.all().order_by("-CreatedOn")


def list_ratings(customer_id: _uuid.UUID | None = None) -> QuerySet[CourseRating]:
    qs = CourseRating.objects.all()
    if customer_id:
        qs = qs.filter(CustomerId=customer_id)
    return qs.order_by("-CreatedOn")


def list_candidates() -> QuerySet[KGCCandidate]:
    return KGCCandidate.objects.all().order_by("-CreatedOn")


def get_mssql_customer_orders(customer_id: str) -> dict:
    """Fetch orders + customer info from the external MSSQL database."""
    return get_customer_orders_with_details(customer_id)


def get_mssql_customer_orders_by_email(email: str) -> dict:
    """Look up customer by email in MSSQL, then fetch their orders."""
    customer = get_customer_by_email(email)
    if not customer:
        return {"customer": None, "orders": [], "total_orders": 0}
    mssql_customer_id = str(customer.get("CustomerId", ""))
    return get_customer_orders_with_details(mssql_customer_id)
