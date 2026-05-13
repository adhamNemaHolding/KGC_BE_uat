from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_companies, name="list-companies"),
    path("<uuid:company_id>/", views.get_company, name="get-company"),
    path("<uuid:company_id>/members/", views.list_company_members, name="list-company-members"),
    path("<uuid:company_id>/invite/", views.send_invitations, name="send-invitations"),
    path("report/", views.all_companies_report, name="all-companies-report"),
    path("<uuid:company_id>/report/", views.company_report, name="company-report"),
    path("<uuid:company_id>/weekly-report/", views.send_weekly_report, name="send-weekly-report"),
    path("join/", views.join_company, name="join-company"),
]
