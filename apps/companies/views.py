from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.common.response import error_response, success_response
from apps.users.models import Customer

from . import selectors, services
from .serializers import CompanyMemberSerializer, CompanySerializer


def _get_customer(request: Request) -> Customer | None:
    user = request.user
    return user if isinstance(user, Customer) else None


@extend_schema(tags=["Companies"], summary="List all companies")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_companies(request: Request):
    companies = selectors.list_all_companies()
    return success_response(data=CompanySerializer(companies, many=True).data)


@extend_schema(tags=["Companies"], summary="Get company by ID")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_company(request: Request, company_id):
    company = selectors.get_company_by_id(company_id)
    if not company:
        return error_response("Company not found.", status_code=status.HTTP_404_NOT_FOUND)
    return success_response(data=CompanySerializer(company).data)


@extend_schema(tags=["Companies"], summary="Join company by code")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_company(request: Request):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    try:
        member = services.join_company(customer=customer, code=request.data.get("code", ""))
    except ValueError as e:
        return error_response(str(e))

    company = member.Company
    return success_response(
        data={
            "message": f"Joined {company.Name} successfully.",
            "company": CompanySerializer(company).data,
        },
        status_code=status.HTTP_201_CREATED,
    )


@extend_schema(tags=["Companies"], summary="List company members (owner only)")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_company_members(request: Request, company_id):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    company = selectors.get_company_by_id(company_id)
    if not company:
        return error_response("Company not found.", status_code=status.HTTP_404_NOT_FOUND)

    if company.Owner_id != customer.CustomerId:
        return error_response("Only the company owner can view members.", status_code=status.HTTP_403_FORBIDDEN)

    members = selectors.list_company_members(company)
    return success_response(data=CompanyMemberSerializer(members, many=True).data)


@extend_schema(tags=["Companies"], summary="Company report (owner only)")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_report(request: Request, company_id):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    company = selectors.get_company_by_id(company_id)
    if not company:
        return error_response("Company not found.", status_code=status.HTTP_404_NOT_FOUND)

    if company.Owner_id != customer.CustomerId:
        return error_response("Only the company owner can access reports.", status_code=status.HTTP_403_FORBIDDEN)

    return success_response(data=services.build_company_report(company))


@extend_schema(tags=["Companies"], summary="All companies report (owner)")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def all_companies_report(request: Request):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    companies = selectors.list_companies_owned_by(customer)
    reports = [services.build_company_report(c) for c in companies]
    return success_response(data={"total_companies": len(reports), "companies": reports})


@extend_schema(tags=["Companies"], summary="Send invitations to employees")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_invitations(request: Request, company_id):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    company = selectors.get_company_by_id(company_id)
    if not company:
        return error_response("Company not found.", status_code=status.HTTP_404_NOT_FOUND)

    if company.Owner_id != customer.CustomerId:
        return error_response("Only the company owner can send invitations.", status_code=status.HTTP_403_FORBIDDEN)

    emails = request.data.get("emails", [])
    if not emails or not isinstance(emails, list):
        return error_response("A list of emails is required.")

    result = services.send_invitations(company=company, emails=emails)
    return success_response(data=result, status_code=status.HTTP_200_OK)


@extend_schema(tags=["Companies"], summary="Send weekly report email (owner only)")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_weekly_report(request: Request, company_id):
    customer = _get_customer(request)
    if not customer:
        return error_response("Customer not found.", status_code=status.HTTP_404_NOT_FOUND)

    company = selectors.get_company_by_id(company_id)
    if not company:
        return error_response("Company not found.", status_code=status.HTTP_404_NOT_FOUND)

    if company.Owner_id != customer.CustomerId:
        return error_response("Only the company owner can trigger reports.", status_code=status.HTTP_403_FORBIDDEN)

    ok = services.send_weekly_report_for_company(company)
    if ok:
        return success_response(data={"message": f"Weekly report sent to {company.Owner.Email}."})
    return error_response("Failed to send weekly report.", status_code=status.HTTP_502_BAD_GATEWAY)
