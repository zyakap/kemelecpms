"""
Production settings for Kemele Construction CPMS.

REQUIRED environment variables (no defaults — startup fails with
django.core.exceptions.ImproperlyConfigured if missing):

    SECRET_KEY      Django secret key (inherited from base.py; MUST be set —
                    do not rely on the insecure dev default).
    DATABASE_URL    PostgreSQL connection string,
                    e.g. postgres://cpms_user:password@localhost:5432/kemelecpms_db
    REDIS_URL       Redis connection string used for the cache, sessions and
                    Celery broker/result backend,
                    e.g. redis://localhost:6379/0

STRONGLY RECOMMENDED environment variables (have defaults, but should be set):

    ALLOWED_HOSTS   Comma-separated hostnames served by this instance.
    STATIC_ROOT     Where collectstatic outputs files; nginx serves
                    /home/kemelecpms/staticfiles — set it to that path.
    MEDIA_ROOT      Where uploads are stored; nginx serves
                    /home/kemelecpms/media — set it to that path.
    EMAIL_HOST / EMAIL_PORT / EMAIL_USE_TLS / EMAIL_HOST_USER /
    EMAIL_HOST_PASSWORD / DEFAULT_FROM_EMAIL
    SMS_GATEWAY_URL / SMS_API_KEY / SMS_FROM_NUMBER
    SITE_URL / COMPANY_NAME
    CELERY_BROKER_URL / CELERY_RESULT_BACKEND (default to REDIS_URL)

See .env.production.example at the repository root for a full template.
"""
import logging
import os

from .base import *

DEBUG = False

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["cpms.kemeleconstruction.com.pg", "www.cpms.kemeleconstruction.com.pg"],
)

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DATABASES = {
    "default": env.db("DATABASE_URL")
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "TIMEOUT": 300,
        "KEY_PREFIX": "kemelecpms",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Email (production SMTP)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@kemeleconstruction.com.pg")

# Logging: prefer a rotating file in /var/log/gunicorn, but never crash on
# startup if that directory is missing or unwritable — fall back to
# console-only logging instead.
LOG_DIR = "/var/log/gunicorn"
LOG_FILE = os.path.join(LOG_DIR, "kemelecpms_django.log")

try:
    os.makedirs(LOG_DIR, exist_ok=True)
    # Verify we can actually write to the log file before configuring handlers.
    with open(LOG_FILE, "a"):
        pass
    _FILE_LOGGING_AVAILABLE = True
except OSError:
    _FILE_LOGGING_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "Cannot write to %s; falling back to console-only logging.", LOG_FILE
    )

if _FILE_LOGGING_AVAILABLE:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "file": {
                "level": "WARNING",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FILE,
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 5,
                "formatter": "verbose",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "root": {
            "handlers": ["file", "console"],
            "level": "WARNING",
        },
        "loggers": {
            "django": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False,
            },
            "django.security": {
                "handlers": ["file"],
                "level": "ERROR",
                "propagate": False,
            },
        },
    }
else:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "django.security": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
            },
        },
    }
