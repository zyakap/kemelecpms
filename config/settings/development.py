from .base import *

DEBUG = True

try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
