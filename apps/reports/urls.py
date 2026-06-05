from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    # Project-scoped exports
    path(
        "projects/<int:project_pk>/export/boq/",
        views.BoQExportView.as_view(),
        name="boq-export",
    ),
    path(
        "projects/<int:project_pk>/export/budget/",
        views.BudgetReportExportView.as_view(),
        name="budget-export",
    ),
    path(
        "projects/<int:project_pk>/export/attendance/",
        views.AttendanceReportExportView.as_view(),
        name="attendance-export",
    ),
    path(
        "projects/<int:project_pk>/export/stock/",
        views.StockLedgerExportView.as_view(),
        name="stock-export",
    ),
    path(
        "projects/<int:project_pk>/export/safety/",
        views.SafetyReportExportView.as_view(),
        name="safety-export",
    ),
    path(
        "projects/<int:project_pk>/monthly-report/",
        views.MonthlyProgressReportView.as_view(),
        name="monthly-report",
    ),
    # Portfolio (global)
    path(
        "portfolio/",
        views.PortfolioReportView.as_view(),
        name="portfolio-report",
    ),
    # Accounting export (MYOB-compatible CSV)
    path(
        "projects/<int:project_pk>/export/accounting/",
        views.AccountingExportView.as_view(),
        name="accounting-export",
    ),
    # Reports index (landing page)
    path(
        "",
        views.ReportsIndexView.as_view(),
        name="index",
    ),
    path(
        "strategic-operations/",
        views.StrategicOperationsView.as_view(),
        name="strategic-operations",
    ),
]
