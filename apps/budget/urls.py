from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "budget"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="projects:project_list", permanent=False), name="index"),
    # Dashboard
    path(
        "projects/<int:project_pk>/budget/",
        views.BudgetDashboardView.as_view(),
        name="dashboard",
    ),
    # Cost Codes
    path(
        "projects/<int:project_pk>/cost-codes/",
        views.CostCodeListView.as_view(),
        name="costcode-list",
    ),
    path(
        "projects/<int:project_pk>/cost-codes/add/",
        views.CostCodeCreateView.as_view(),
        name="costcode-create",
    ),
    path(
        "projects/<int:project_pk>/cost-codes/<int:pk>/edit/",
        views.CostCodeUpdateView.as_view(),
        name="costcode-update",
    ),
    # Bill of Quantities
    path(
        "projects/<int:project_pk>/boq/",
        views.BoQListView.as_view(),
        name="boq-list",
    ),
    path(
        "projects/<int:project_pk>/boq/add/",
        views.BoQItemCreateView.as_view(),
        name="boq-create",
    ),
    path(
        "projects/<int:project_pk>/boq/<int:pk>/edit/",
        views.BoQItemUpdateView.as_view(),
        name="boq-update",
    ),
    # Cost Entries
    path(
        "projects/<int:project_pk>/cost-entries/",
        views.CostEntryListView.as_view(),
        name="costentry-list",
    ),
    path(
        "projects/<int:project_pk>/cost-entries/add/",
        views.CostEntryCreateView.as_view(),
        name="costentry-create",
    ),
    path(
        "projects/<int:project_pk>/cost-entries/<int:pk>/edit/",
        views.CostEntryUpdateView.as_view(),
        name="costentry-update",
    ),
    # Subcontracts
    path(
        "projects/<int:project_pk>/subcontracts/",
        views.SubcontractListView.as_view(),
        name="subcontract-list",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/add/",
        views.SubcontractCreateView.as_view(),
        name="subcontract-create",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/<int:pk>/edit/",
        views.SubcontractUpdateView.as_view(),
        name="subcontract-update",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/<int:pk>/",
        views.SubcontractDetailView.as_view(),
        name="subcontract-detail",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/<int:subcontract_pk>/claims/add/",
        views.SubcontractClaimCreateView.as_view(),
        name="subcontract-claim-create",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/<int:subcontract_pk>/claims/<int:pk>/edit/",
        views.SubcontractClaimUpdateView.as_view(),
        name="subcontract-claim-update",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/<int:subcontract_pk>/backcharges/add/",
        views.SubcontractBackChargeCreateView.as_view(),
        name="subcontract-backcharge-create",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/<int:subcontract_pk>/backcharges/<int:pk>/edit/",
        views.SubcontractBackChargeUpdateView.as_view(),
        name="subcontract-backcharge-update",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/<int:subcontract_pk>/performance/add/",
        views.SubcontractPerformanceReviewCreateView.as_view(),
        name="subcontract-performance-create",
    ),
    # BoQ Import
    path(
        "projects/<int:project_pk>/boq/import/",
        views.BoQImportView.as_view(),
        name="boq-import",
    ),
]
