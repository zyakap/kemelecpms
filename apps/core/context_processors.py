from django.conf import settings


def site_context(request):
    context = {
        "COMPANY_NAME": getattr(settings, "COMPANY_NAME", "Kemele Construction"),
        "SITE_URL": getattr(settings, "SITE_URL", ""),
    }
    try:
        from apps.dashboard.services import build_global_context

        context.update(build_global_context(request))
    except Exception:
        pass
    return context
