from django.conf import settings


def site_context(request):
    return {
        "COMPANY_NAME": getattr(settings, "COMPANY_NAME", "Kemele Construction"),
        "SITE_URL": getattr(settings, "SITE_URL", ""),
    }
