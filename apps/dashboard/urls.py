from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.HomeRedirectView.as_view(), name="home"),
    path("role/", views.RoleWorkspaceView.as_view(), name="role-workspace"),
    path("switch-project/", views.ProjectSwitchView.as_view(), name="project-switch"),
    path("portfolio/", views.PortfolioDashboardView.as_view(), name="portfolio"),
    path("project/<int:pk>/", views.ProjectDashboardView.as_view(), name="project"),
    # Analytics
    path("analytics/financial/", views.FinancialAnalyticsView.as_view(), name="financial-analytics"),
    path("analytics/safety/", views.SafetyAnalyticsView.as_view(), name="safety-analytics"),
    path("analytics/schedule/", views.ScheduleAnalyticsView.as_view(), name="schedule-analytics"),
    path("analytics/resources/", views.ResourceAnalyticsView.as_view(), name="resource-analytics"),
    # S-curve data (JSON)
    path("api/scurve/<int:project_pk>/", views.SCurveDataView.as_view(), name="scurve-data"),
]
