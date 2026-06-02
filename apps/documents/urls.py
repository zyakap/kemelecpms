from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    # Drawings
    path(
        "projects/<int:project_pk>/drawings/",
        views.DrawingListView.as_view(),
        name="drawing-list",
    ),
    path(
        "projects/<int:project_pk>/drawings/add/",
        views.DrawingCreateView.as_view(),
        name="drawing-create",
    ),
    path(
        "projects/<int:project_pk>/drawings/<int:pk>/",
        views.DrawingDetailView.as_view(),
        name="drawing-detail",
    ),
    path(
        "projects/<int:project_pk>/drawings/<int:pk>/edit/",
        views.DrawingUpdateView.as_view(),
        name="drawing-update",
    ),
    # Drawing Revisions
    path(
        "drawings/<int:drawing_pk>/revisions/add/",
        views.DrawingRevisionCreateView.as_view(),
        name="drawingrevision-create",
    ),
    # RFIs
    path(
        "projects/<int:project_pk>/rfis/",
        views.RFIListView.as_view(),
        name="rfi-list",
    ),
    path(
        "projects/<int:project_pk>/rfis/add/",
        views.RFICreateView.as_view(),
        name="rfi-create",
    ),
    path(
        "projects/<int:project_pk>/rfis/<int:pk>/",
        views.RFIDetailView.as_view(),
        name="rfi-detail",
    ),
    path(
        "projects/<int:project_pk>/rfis/<int:pk>/edit/",
        views.RFIUpdateView.as_view(),
        name="rfi-update",
    ),
    # Submittals
    path(
        "projects/<int:project_pk>/submittals/",
        views.SubmittalListView.as_view(),
        name="submittal-list",
    ),
    path(
        "projects/<int:project_pk>/submittals/add/",
        views.SubmittalCreateView.as_view(),
        name="submittal-create",
    ),
    path(
        "projects/<int:project_pk>/submittals/<int:pk>/edit/",
        views.SubmittalUpdateView.as_view(),
        name="submittal-update",
    ),
    # Correspondence
    path(
        "projects/<int:project_pk>/correspondence/",
        views.CorrespondenceListView.as_view(),
        name="correspondence-list",
    ),
    path(
        "projects/<int:project_pk>/correspondence/add/",
        views.CorrespondenceCreateView.as_view(),
        name="correspondence-create",
    ),
    path(
        "projects/<int:project_pk>/correspondence/<int:pk>/edit/",
        views.CorrespondenceUpdateView.as_view(),
        name="correspondence-update",
    ),
    # Project Documents
    path(
        "projects/<int:project_pk>/docs/",
        views.ProjectDocumentListView.as_view(),
        name="projectdoc-list",
    ),
    path(
        "projects/<int:project_pk>/docs/add/",
        views.ProjectDocumentCreateView.as_view(),
        name="projectdoc-create",
    ),
    # Company-wide templates
    path(
        "templates/",
        views.ProjectDocumentTemplatesView.as_view(),
        name="projectdoc-templates",
    ),
]
