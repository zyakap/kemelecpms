from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    DSRViewSet,
    GRNViewSet,
    IncidentViewSet,
    IPCViewSet,
    MRViewSet,
    POViewSet,
    ProjectViewSet,
    ToolboxTalkViewSet,
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="api-project")
router.register(r"dsr", DSRViewSet, basename="api-dsr")
router.register(r"ipc", IPCViewSet, basename="api-ipc")
router.register(r"mrs", MRViewSet, basename="api-mr")
router.register(r"pos", POViewSet, basename="api-po")
router.register(r"grns", GRNViewSet, basename="api-grn")
router.register(r"incidents", IncidentViewSet, basename="api-incident")
router.register(r"toolbox-talks", ToolboxTalkViewSet, basename="api-toolbox")

urlpatterns = [
    path("v1/", include(router.urls)),
]
