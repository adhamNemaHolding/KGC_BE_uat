"""
Base settings for KGC AI Skill Advisor.

Shared across all environments. Environment-specific overrides live in
development.py and production.py.

Uses django-environ for 12-factor config.
"""

from datetime import timedelta
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES=(int, 30),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    GOOGLE_CLIENT_ID=(str, ""),
    GOOGLE_CLIENT_SECRET=(str, ""),
    OPENAI_API_KEY=(str, ""),
    OPENAI_MODEL=(str, "gpt-4o"),
    OPENAI_FAST_MODEL=(str, ""),
    EMAIL_HOST=(str, "smtp.gmail.com"),
    EMAIL_PORT=(int, 587),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_FROM=(str, "noreply@kgc.com"),
    FRONTEND_URL=(str, "http://localhost:3000"),
    SITECORE_API_KEY=(str, ""),
    SITECORE_SITE=(str, "corporate-website"),
    SALESFORCE_CLIENT_ID=(str, ""),
    SALESFORCE_CLIENT_SECRET=(str, ""),
    ADMIN_EMAIL=(str, "admin@kgc.com"),
)
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("SECRET_KEY")  # No fallback — crash if missing
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Local apps
    "apps.common",
    "apps.users",
    "apps.companies",
    "apps.assessments",
    "apps.advisor",
    "apps.courses",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database — SQLite optimized for high-concurrency (WAL mode)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA cache_size=-20000;"
                "PRAGMA busy_timeout=5000;"
                "PRAGMA temp_store=MEMORY;"
                "PRAGMA mmap_size=128000000;"
                "PRAGMA foreign_keys=ON;"
            ),
            "transaction_mode": "IMMEDIATE",
            "timeout": 10,
        },
    }
}

# ---------------------------------------------------------------------------
# Admin Dashboard — static email for access
# ---------------------------------------------------------------------------
ADMIN_EMAIL = env("ADMIN_EMAIL")

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.users.authentication.CustomerJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.response.custom_exception_handler",
}

# ---------------------------------------------------------------------------
# DRF Spectacular (OpenAPI / Swagger)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "KGC AI Skill Advisor API",
    "DESCRIPTION": "Backend API for the KGC AI-powered Skill Assessment & Career Development platform.",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/",
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "Auth", "description": "Authentication & registration"},
        {"name": "Users", "description": "User profiles & professional data"},
        {"name": "Companies", "description": "Company management & HR reports"},
        {"name": "Assessments", "description": "Skill assessment CRUD"},
        {"name": "Advisor", "description": "AI-powered career advice & IDP generation"},
        {"name": "Courses", "description": "Course catalog & Sitecore integration"},
    ],
}

# ---------------------------------------------------------------------------
# JWT Configuration
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES"),
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS"),
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "CustomerId",
    "USER_ID_CLAIM": "customer_id",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("EMAIL_FROM")
EMAIL_TIMEOUT = 10  # seconds — prevents SMTP hangs from stalling requests
FRONTEND_URL = env("FRONTEND_URL")

# ---------------------------------------------------------------------------
# AI Provider
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")

# ---------------------------------------------------------------------------
# AI Provider
# ---------------------------------------------------------------------------
OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL")
# Optional faster model used by non-critical bilingual endpoints (competencies, etc.).
# Leave empty to fall back to OPENAI_MODEL. Recommended value: "gpt-4o-mini".
OPENAI_FAST_MODEL = env("OPENAI_FAST_MODEL")

# ---------------------------------------------------------------------------
# Sitecore CMS
# ---------------------------------------------------------------------------
SITECORE_API_KEY = env("SITECORE_API_KEY")
SITECORE_SITE = env("SITECORE_SITE")

# ---------------------------------------------------------------------------
# Salesforce
# ---------------------------------------------------------------------------
SALESFORCE_CLIENT_ID="3MVG9aP2dpFTYBa3CUgjL361B407o_Iklko5TQVtFabeUzc.1cXMpOBciT7N1TomGh9WzCUbhinLbX6nJLCSw"
SALESFORCE_CLIENT_SECRET="261B64018B67F5FF48694795F1F2E65F6BE1A0F3DE58C7147A1FA3A24BC93F70"
SALESFORCE_TOKEN_URL = "https://thekgc--lng.sandbox.my.salesforce.com/services/oauth2/token"

# ---------------------------------------------------------------------------
# Auth / i18n / Static
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Rate Limiting (django-ratelimit)
# ---------------------------------------------------------------------------
RATELIMIT_USE_CACHE = "default"
RATELIMIT_FAIL_OPEN = False  # Block requests if rate limiter errors

LANGUAGE_CODE = "en-us"
LANGUAGES = [
    ("en", _("English")),
    ("ar", _("Arabic")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Cache (used by django-ratelimit)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ratelimit",
    }
}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# External MSSQL Database (KGC Website UAT — read-only)
# ---------------------------------------------------------------------------
MSSQL_CONFIG = {
    "user": env("MSSQL_USER", default="kgcadm"),
    "password": env("MSSQL_PASSWORD", default="H@ppyH0urs%!"),
    "server": env("MSSQL_SERVER", default="kgcazsql.database.windows.net"),
    "database": env("MSSQL_DATABASE", default="Kgcwebsiteuat"),
}
