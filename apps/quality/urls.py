from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "quality"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="projects:project_list", permanent=False), name="index"),
    # ITP
    path(
        "projects/<int:project_pk>/itps/",
        views.ITPListView.as_view(),
        name="itp-list",
    ),
    path(
        "projects/<int:project_pk>/itps/add/",
        views.ITPCreateView.as_view(),
        name="itp-create",
    ),
    path(
        "projects/<int:project_pk>/itps/<int:pk>/",
        views.ITPDetailView.as_view(),
        name="itp-detail",
    ),
    path(
        "projects/<int:project_pk>/itps/<int:itp_pk>/checklists/add/",
        views.InspectionChecklistCreateView.as_view(),
        name="checklist-create",
    ),
    path(
        "projects/<int:project_pk>/checklists/<int:checklist_pk>/items/add/",
        views.InspectionChecklistItemCreateView.as_view(),
        name="checklist-item-create",
    ),
    # Inspection Records (scoped to an ITP item)
    path(
        "projects/<int:project_pk>/itp-items/<int:itp_item_pk>/inspect/",
        views.InspectionRecordCreateView.as_view(),
        name="inspection-create",
    ),
    # NCRs
    path(
        "projects/<int:project_pk>/ncrs/",
        views.NCRListView.as_view(),
        name="ncr-list",
    ),
    path(
        "projects/<int:project_pk>/ncrs/add/",
        views.NCRCreateView.as_view(),
        name="ncr-create",
    ),
    path(
        "projects/<int:project_pk>/ncrs/<int:pk>/",
        views.NCRDetailView.as_view(),
        name="ncr-detail",
    ),
    path(
        "projects/<int:project_pk>/ncrs/<int:pk>/edit/",
        views.NCRUpdateView.as_view(),
        name="ncr-update",
    ),
    # Material Test Results
    path(
        "projects/<int:project_pk>/material-tests/",
        views.MaterialTestListView.as_view(),
        name="materialtest-list",
    ),
    path(
        "projects/<int:project_pk>/material-tests/add/",
        views.MaterialTestCreateView.as_view(),
        name="materialtest-create",
    ),
    # Defects
    path(
        "projects/<int:project_pk>/defects/",
        views.DefectListView.as_view(),
        name="defect-list",
    ),
    path(
        "projects/<int:project_pk>/defects/add/",
        views.DefectCreateView.as_view(),
        name="defect-create",
    ),
    path(
        "projects/<int:project_pk>/defects/<int:pk>/edit/",
        views.DefectUpdateView.as_view(),
        name="defect-update",
    ),
]
