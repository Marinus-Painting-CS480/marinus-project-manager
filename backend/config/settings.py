"""Django settings for the Marinus Painting app.

All environment-specific values come from backend/.env (see .env.example).
"""

import os
from pathlib import Path

import dj_database_url
import pymysql
from dotenv import load_dotenv

# PyMySQL is a pure-Python MySQL driver, so nobody has to compile mysqlclient.
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false.")
    SECRET_KEY = "dev-only-insecure-key"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.projects",
    "apps.estimates",
    "apps.workorders",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves the built React app and admin static files in production (no extra web server).
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: MySQL via DATABASE_URL (see docker-compose.yml).
DATABASES = {
    "default": dj_database_url.config(
        default="mysql://marinus:marinus@127.0.0.1:3306/marinus",
        conn_max_age=60,
    )
}
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"].setdefault("OPTIONS", {})["charset"] = "utf8mb4"
    DATABASES["default"]["TEST"] = {
        "NAME": "test_marinus",
        "CHARSET": "utf8mb4",
        "COLLATION": "utf8mb4_unicode_ci",
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Language: English and Spanish. Each user also stores their own preference.
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("es", "Español")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "America/Denver"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# The built React app (`npm run build` creates frontend/dist). In production Django serves
# it: files like /assets/*.js come from here, and every other page gets index.html.
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"))
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# Uploaded photos. Never served as public files: only through /api/photos/<id>/file.
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
PHOTO_MAX_BYTES = int(os.environ.get("PHOTO_MAX_MB", "15")) * 1024 * 1024
PHOTO_MAX_FILES_PER_UPLOAD = int(os.environ.get("PHOTO_MAX_FILES_PER_UPLOAD", "20"))
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # bigger uploads go to a temp file
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # non-file request data (JSON, signatures)

# Business settings
SITE_URL = os.environ.get("SITE_URL", "http://localhost:5173")  # used in customer links
PROPOSAL_LINK_DAYS = int(os.environ.get("PROPOSAL_LINK_DAYS", "30"))
DEFAULT_LABOR_ALLOCATION_PERCENT = int(os.environ.get("DEFAULT_LABOR_ALLOCATION_PERCENT", "30"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email: printed to the terminal locally; set SMTP values in production.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Marinus Painting <no-reply@localhost>")

# Session cookies are shared with the React app because both are served from one origin.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Production hardening (active when DJANGO_DEBUG=false). Check with:
#   python manage.py check --deploy
if not DEBUG:
    # The host's proxy (cPanel/Passenger, Render, etc.) terminates HTTPS in front of Django.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_REFERRER_POLICY = "same-origin"  # keep private link tokens out of Referer headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
