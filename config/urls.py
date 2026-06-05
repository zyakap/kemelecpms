from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    # REST API token authentication endpoint
    path("api/auth/token/", obtain_auth_token, name="api-token-auth"),
    path("accounts/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("projects/", include("apps.projects.urls")),
    path("budget/", include("apps.budget.urls")),
    path("schedule/", include("apps.schedule.urls")),
    path("resources/", include("apps.resources.urls")),
    path("procurement/", include("apps.procurement.urls")),
    path("dsr/", include("apps.dsr.urls")),
    path("safety/", include("apps.safety.urls")),
    path("quality/", include("apps.quality.urls")),
    path("maintenance/", include("apps.maintenance.urls")),
    path("ipc/", include("apps.ipc.urls")),
    path("documents/", include("apps.documents.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("compliance/", include("apps.compliance.urls")),
    path("tender/", include("apps.tender.urls")),
    path("reports/", include("apps.reports.urls")),
    path("api/", include("apps.core.api_urls")),
    path("", include("apps.dashboard.home_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
