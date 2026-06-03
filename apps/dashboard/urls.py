from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.HomeRedirectView.as_view(), name="home"),
    path("portfolio/", views.PortfolioDashboardView.as_view(), name="portfolio"),
    path("project/<int:pk>/", views.ProjectDashboardView.as_view(), name="project"),
]
