from django.urls import path

from . import views

urlpatterns = [
    path("users/", views.available_users, name="available-users"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login, name="login"),
    path("refresh/", views.refresh_token, name="token-refresh"),
    path("logout/", views.logout, name="logout"),
    path("google/", views.google_auth, name="google-auth"),
    path("verify-email/", views.verify_email, name="verify-email"),
    path("resend-verification/", views.resend_verification, name="resend-verification"),
    path("password-reset/", views.request_password_reset, name="password-reset"),
    path("password-reset/confirm/", views.confirm_password_reset, name="password-reset-confirm"),
]
