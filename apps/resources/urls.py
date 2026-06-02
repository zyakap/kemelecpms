from django.urls import path

from . import views

app_name = "resources"

urlpatterns = [
    # -------------------------------------------------------------------
    # Workers (global – not project-scoped so workers can span projects)
    # -------------------------------------------------------------------
    path(
        "workers/",
        views.WorkerListView.as_view(),
        name="worker-list",
    ),
    path(
        "workers/add/",
        views.WorkerCreateView.as_view(),
        name="worker-create",
    ),
    path(
        "workers/<int:pk>/",
        views.WorkerDetailView.as_view(),
        name="worker-detail",
    ),
    path(
        "workers/<int:pk>/edit/",
        views.WorkerUpdateView.as_view(),
        name="worker-update",
    ),
    # -------------------------------------------------------------------
    # Attendance (project-scoped)
    # -------------------------------------------------------------------
    path(
        "projects/<int:project_pk>/attendance/",
        views.AttendanceView.as_view(),
        name="attendance",
    ),
    path(
        "projects/<int:project_pk>/attendance/bulk/",
        views.AttendanceBulkCreateView.as_view(),
        name="attendance-bulk",
    ),
    path(
        "projects/<int:project_pk>/attendance/add/",
        views.AttendanceCreateView.as_view(),
        name="attendance-create",
    ),
    # -------------------------------------------------------------------
    # Equipment (global)
    # -------------------------------------------------------------------
    path(
        "equipment/",
        views.EquipmentListView.as_view(),
        name="equipment-list",
    ),
    path(
        "equipment/add/",
        views.EquipmentCreateView.as_view(),
        name="equipment-create",
    ),
    path(
        "equipment/<int:pk>/edit/",
        views.EquipmentUpdateView.as_view(),
        name="equipment-update",
    ),
    # Equipment Allocation (project-scoped)
    path(
        "projects/<int:project_pk>/equipment/allocate/",
        views.EquipmentAllocationCreateView.as_view(),
        name="equipment-allocate",
    ),
    # Equipment Utilisation (allocation-scoped)
    path(
        "allocations/<int:allocation_pk>/utilisation/add/",
        views.EquipmentUtilisationCreateView.as_view(),
        name="equipment-utilisation-create",
    ),
    # -------------------------------------------------------------------
    # Crews (project-scoped)
    # -------------------------------------------------------------------
    path(
        "projects/<int:project_pk>/crews/",
        views.CrewListView.as_view(),
        name="crew-list",
    ),
    path(
        "projects/<int:project_pk>/crews/add/",
        views.CrewCreateView.as_view(),
        name="crew-create",
    ),
    path(
        "projects/<int:project_pk>/crews/<int:pk>/",
        views.CrewDetailView.as_view(),
        name="crew-detail",
    ),
    # -------------------------------------------------------------------
    # Subcontractor Companies (global)
    # -------------------------------------------------------------------
    path(
        "subcontractors/",
        views.SubcontractorListView.as_view(),
        name="subcontractor-list",
    ),
    path(
        "subcontractors/add/",
        views.SubcontractorCreateView.as_view(),
        name="subcontractor-create",
    ),
    path(
        "subcontractors/<int:pk>/edit/",
        views.SubcontractorUpdateView.as_view(),
        name="subcontractor-update",
    ),
]
