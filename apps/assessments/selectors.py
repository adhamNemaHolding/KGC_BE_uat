from __future__ import annotations

import uuid as _uuid

from django.db.models import QuerySet

from apps.users.models import Customer

from .models import Assessment


def get_assessment_by_id(assessment_id: _uuid.UUID) -> Assessment | None:
    return Assessment.objects.filter(AssessmentId=assessment_id).first()


def list_all_assessments() -> QuerySet[Assessment]:
    return Assessment.objects.all().order_by("-CreatedOn")


def list_assessments_for_customer(customer: Customer) -> QuerySet[Assessment]:
    return Assessment.objects.filter(Customer=customer).order_by("-CreatedOn")


def list_assessments_by_customer_id(customer_id: _uuid.UUID) -> QuerySet[Assessment]:
    return Assessment.objects.filter(Customer__CustomerId=customer_id).order_by("-CreatedOn")


def count_completed_assessments(customer: Customer) -> int:
    return Assessment.objects.filter(Customer=customer, Status="completed").count()
