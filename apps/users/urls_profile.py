from django.urls import path

from . import views

urlpatterns = [
    # Professional profile
    path("professional-profile/", views.get_professional_profile, name="get-professional-profile"),
    path("professional-profile/save/", views.create_professional_profile, name="save-professional-profile"),
    path("professional-profile/<uuid:customer_id>/", views.get_professional_profile_by_customer, name="get-professional-profile-by-customer"),
    # Admin / synced-data endpoints
    path("customers/", views.list_customers, name="list-customers"),
    path("email-verifications/", views.list_email_verifications, name="list-email-verifications"),
    path("profiles/", views.list_profiles, name="list-profiles"),
    path("refresh-tokens/", views.list_refresh_tokens, name="list-refresh-tokens"),
    path("password-resets/", views.list_password_resets, name="list-password-resets"),
]
