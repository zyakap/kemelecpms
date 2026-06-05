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
    path(
        "projects/<int:project_pk>/invoices/<int:pk>/void/",
        views.TaxInvoiceVoidView.as_view(),
        name="invoice-void",
    ),
    path("projects/<int:project_pk>/public-procurement/", views.PublicProcurementListView.as_view(), name="public-procurement-list"),
    path("projects/<int:project_pk>/public-procurement/new/", views.PublicProcurementCreateView.as_view(), name="public-procurement-create"),
    path("projects/<int:project_pk>/public-procurement/<int:pk>/edit/", views.PublicProcurementUpdateView.as_view(), name="public-procurement-update"),
    path("projects/<int:project_pk>/local-content/", views.LocalContentListView.as_view(), name="local-content-list"),
    path("projects/<int:project_pk>/local-content/new/", views.LocalContentCreateView.as_view(), name="local-content-create"),
    path("projects/<int:project_pk>/local-content/<int:pk>/edit/", views.LocalContentUpdateView.as_view(), name="local-content-update"),
    path("projects/<int:project_pk>/authority-permits/", views.AuthorityPermitListView.as_view(), name="authority-permit-list"),
    path("projects/<int:project_pk>/authority-permits/new/", views.AuthorityPermitCreateView.as_view(), name="authority-permit-create"),
    path("projects/<int:project_pk>/authority-permits/<int:pk>/edit/", views.AuthorityPermitUpdateView.as_view(), name="authority-permit-update"),
    path("projects/<int:project_pk>/funder-packs/", views.FunderReportPackListView.as_view(), name="funder-pack-list"),
    path("projects/<int:project_pk>/funder-packs/new/", views.FunderReportPackCreateView.as_view(), name="funder-pack-create"),
    path("projects/<int:project_pk>/funder-packs/<int:pk>/edit/", views.FunderReportPackUpdateView.as_view(), name="funder-pack-update"),
    # Compliance Calendar (global)
    path("calendar/", views.ComplianceCalendarView.as_view(), name="calendar"),
    path("calendar/new/", views.CalendarEntryCreateView.as_view(), name="calendar-create"),
    path("calendar/<int:pk>/", views.CalendarEntryDetailView.as_view(), name="calendar-detail"),
    path("calendar/<int:pk>/edit/", views.CalendarEntryUpdateView.as_view(), name="calendar-update"),
    path("calendar/templates/", views.ComplianceCalendarTemplateListView.as_view(), name="calendar-template-list"),
    path("calendar/templates/new/", views.ComplianceCalendarTemplateCreateView.as_view(), name="calendar-template-create"),
    path("calendar/templates/<int:pk>/edit/", views.ComplianceCalendarTemplateUpdateView.as_view(), name="calendar-template-update"),
    path("map/", views.ProjectMapView.as_view(), name="project-map"),
]
