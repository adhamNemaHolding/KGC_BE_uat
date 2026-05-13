from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.common import views as common_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    # API v1
    path("api/auth/", include("apps.users.urls")),
    path("api/users/", include("apps.users.urls_profile")),
    path("api/companies/", include("apps.companies.urls")),
    path("api/assessments/", include("apps.assessments.urls")),
    path("api/advisor/", include("apps.advisor.urls")),
    path("api/courses/", include("apps.courses.urls")),
    path("api/admin-dashboard/", include("apps.common.admin_urls")),
    path("api/translations/<str:language_code>/", common_views.translation_json),
    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
