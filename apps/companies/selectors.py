from __future__ import annotations

import uuid as _uuid

from django.db.models import QuerySet

from apps.users.models import Customer

from .models import Company, CompanyMember


def get_company_by_id(company_id: _uuid.UUID) -> Company | None:
    return Company.objects.filter(CompanyId=company_id).first()


def get_company_by_code(code: str) -> Company | None:
    return Company.objects.filter(Code=code).first()


def list_all_companies() -> QuerySet[Company]:
    return Company.objects.all().order_by("-CreatedOn")


def list_companies_owned_by(customer: Customer) -> QuerySet[Company]:
    return Company.objects.filter(Owner=customer).order_by("-CreatedOn")


def get_membership_for_customer(customer: Customer) -> CompanyMember | None:
    return (
        CompanyMember.objects
        .filter(Customer=customer)
        .select_related("Company")
        .first()
    )


def is_member(company: Company, customer: Customer) -> bool:
    return CompanyMember.objects.filter(Company=company, Customer=customer).exists()


def list_company_members(company: Company) -> QuerySet[CompanyMember]:
    return CompanyMember.objects.filter(Company=company).select_related("Customer")
