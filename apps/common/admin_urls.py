from django.urls import path

from . import admin_views

urlpatterns = [
    path("verify/", admin_views.admin_verify, name="admin-verify"),
    path("users/", admin_views.admin_list_users, name="admin-list-users"),
    path("users/<uuid:customer_id>/", admin_views.admin_user_detail, name="admin-user-detail"),
    path("stats/", admin_views.admin_stats, name="admin-stats"),
]
