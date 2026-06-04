from django.urls import path

from . import views

app_name = "compliance"

urlpatterns = [
    # TCS Reports (project-scoped)
    path(
        "projects/<int:project_pk>/tcs/",
        views.TCSReportListView.as_view(),
        name="tcs-list",
    ),
    path(
        "projects/<int:project_pk>/tcs/new/",
        views.TCSReportCreateView.as_view(),
        name="tcs-create",
    ),
    path(
        "projects/<int:project_pk>/tcs/<int:pk>/",
        views.TCSReportDetailView.as_view(),
        name="tcs-detail",
    ),
    path(
        "projects/<int:project_pk>/tcs/<int:pk>/edit/",
        views.TCSReportUpdateView.as_view(),
        name="tcs-update",
    ),
    path(
        "projects/<int:project_pk>/tcs/<int:pk>/submit/",
        views.TCSReportSubmitView.as_view(),
        name="tcs-submit",
    ),
    # Tax Invoices (project-scoped)
    path(
        "projects/<int:project_pk>/invoices/",
        views.TaxInvoiceListView.as_view(),
        name="invoice-list",
    ),
    path(
        "projects/<int:project_pk>/invoices/new/",
        views.TaxInvoiceCreateView.as_view(),
        name="invoice-create",
    ),
    path(
        "projects/<int:project_pk>/invoices/<int:pk>/",
        views.TaxInvoiceDetailView.as_view(),
        name="invoice-detail",
    ),
    path(
        "projects/<int:project_pk>/invoices/<int:pk>/edit/",
        views.TaxInvoiceUpdateView.as_view(),
        name="invoice-update",
    ),
    path(
        "projects/<int:project_pk>/invoices/<int:pk>/pdf/",
        views.TaxInvoicePDFView.as_view(),
        name="invoice-pdf",
    ),
    # Compliance Calendar (global)
    path("calendar/", views.ComplianceCalendarView.as_view(), name="calendar"),
    path("calendar/new/", views.CalendarEntryCreateView.as_view(), name="calendar-create"),
    path("calendar/<int:pk>/", views.CalendarEntryDetailView.as_view(), name="calendar-detail"),
    path("calendar/<int:pk>/edit/", views.CalendarEntryUpdateView.as_view(), name="calendar-update"),
]
