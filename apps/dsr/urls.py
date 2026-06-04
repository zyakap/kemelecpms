"""
URL configuration for the dsr app.
"""

from django.urls import path

from . import views

app_name = "dsr"

urlpatterns = [
    # List
    path("", views.DSRListView.as_view(), name="dsr_list"),
    # Create
    path("add/", views.DSRCreateView.as_view(), name="dsr_add"),
    # Detail
    path("<int:pk>/", views.DSRDetailView.as_view(), name="dsr_detail"),
    # Update (only draft / returned DSRs)
    path("<int:pk>/edit/", views.DSRUpdateView.as_view(), name="dsr_edit"),
    # Workflow transitions (POST-only)
    path("<int:pk>/submit/", views.DSRSubmitView.as_view(), name="dsr_submit"),
    path("<int:pk>/approve/", views.DSRApproveView.as_view(), name="dsr_approve"),
    path("<int:pk>/return/", views.DSRReturnView.as_view(), name="dsr_return"),
    # AJAX photo upload
    path(
        "<int:pk>/photos/upload/",
        views.DSRPhotoUploadView.as_view(),
        name="dsr_photo_upload",
    ),
    # PDF
    path("<int:pk>/pdf/", views.DSRPDFView.as_view(), name="dsr_pdf"),
]
