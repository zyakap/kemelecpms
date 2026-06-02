from django.urls import path

from . import views

app_name = "budget"

urlpatterns = [
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
]
