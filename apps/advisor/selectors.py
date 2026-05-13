from __future__ import annotations

import uuid as _uuid

from django.db.models import Q, QuerySet

from apps.users.models import Customer

from .models import IndividualDevelopmentPlan


def get_idp_by_id(idp_id: _uuid.UUID) -> IndividualDevelopmentPlan | None:
    return IndividualDevelopmentPlan.objects.filter(IDPId=idp_id).first()


def get_idp_for_assessment(assessment) -> IndividualDevelopmentPlan | None:
    return IndividualDevelopmentPlan.objects.filter(Assessment=assessment).first()


def list_all_idps() -> QuerySet[IndividualDevelopmentPlan]:
    return IndividualDevelopmentPlan.objects.all().order_by("-CreatedOn")


def list_idps_for_customer(customer: Customer) -> QuerySet[IndividualDevelopmentPlan]:
    return (
        IndividualDevelopmentPlan.objects.filter(
            Q(Customer=customer)
            | Q(Customer__isnull=True, Assessment__Customer=customer)
        )
        .distinct()
        .order_by("-CreatedOn")
    )


def list_idps_by_customer_id(customer_id: _uuid.UUID) -> QuerySet[IndividualDevelopmentPlan]:
    return IndividualDevelopmentPlan.objects.filter(Customer__CustomerId=customer_id).order_by("-CreatedOn")
