from django.urls import path

from . import views

app_name = "schedule"

urlpatterns = [
    # Programme (master schedule)
    path(
        "projects/<int:project_pk>/programme/",
        views.ProgrammeView.as_view(),
        name="programme",
    ),
    path(
        "projects/<int:project_pk>/programme/create/",
        views.ProgrammeCreateView.as_view(),
        name="programme-create",
    ),
    path(
        "projects/<int:project_pk>/programme/edit/",
        views.ProgrammeUpdateView.as_view(),
        name="programme-update",
    ),
    # WBS
    path(
        "projects/<int:project_pk>/wbs/",
        views.WBSView.as_view(),
        name="wbs",
    ),
    path(
        "projects/<int:project_pk>/wbs/add/",
        views.WBSActivityCreateView.as_view(),
        name="wbs-create",
    ),
    path(
        "projects/<int:project_pk>/wbs/<int:pk>/edit/",
        views.WBSActivityUpdateView.as_view(),
        name="wbs-update",
    ),
    # Activities
    path(
        "projects/<int:project_pk>/activities/",
        views.ActivityListView.as_view(),
        name="activity-list",
    ),
    path(
        "projects/<int:project_pk>/activities/add/",
        views.ActivityCreateView.as_view(),
        name="activity-create",
    ),
    path(
        "projects/<int:project_pk>/activities/<int:pk>/edit/",
        views.ActivityUpdateView.as_view(),
        name="activity-update",
    ),
    # Progress
    path(
        "activities/<int:activity_pk>/progress/add/",
        views.ProgressEntryCreateView.as_view(),
        name="progress-create",
    ),
    # Look-Ahead
    path(
        "projects/<int:project_pk>/lookahead/",
        views.LookAheadListView.as_view(),
        name="lookahead-list",
    ),
    path(
        "projects/<int:project_pk>/lookahead/add/",
        views.LookAheadCreateView.as_view(),
        name="lookahead-create",
    ),
    path(
        "projects/<int:project_pk>/lookahead/<int:pk>/",
        views.LookAheadDetailView.as_view(),
        name="lookahead-detail",
    ),
    # S-Curve data (JSON)
    path(
        "projects/<int:project_pk>/scurve/",
        views.SCurveDataView.as_view(),
        name="scurve-data",
    ),
]
