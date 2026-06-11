from django.urls import path

from . import views

app_name = "subcontractor"

urlpatterns = [
    # Subcontractor-facing portal
    path("", views.PortalView.as_view(), name="portal"),
    path("documents/", views.DocumentListView.as_view(), name="document-list"),
    path("documents/upload/", views.DocumentUploadView.as_view(), name="document-upload"),

    # Staff-facing document review
    path(
        "projects/<int:project_pk>/subcontracts/<int:subcontract_pk>/documents/",
        views.ProjectSubcontractorDocsView.as_view(),
        name="staff-doc-list",
    ),
    path(
        "projects/<int:project_pk>/subcontracts/<int:subcontract_pk>/documents/<int:pk>/review/",
        views.DocumentReviewView.as_view(),
        name="staff-doc-review",
    ),
]
