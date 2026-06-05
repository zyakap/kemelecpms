"""
URL configuration for the safety app.
"""

from django.urls import path

from . import views

app_name = "safety"

urlpatterns = [
    # ------------------------------------------------------------------
    # Safety Dashboard
    # ------------------------------------------------------------------
    path("dashboard/", views.SafetyDashboardView.as_view(), name="safety_dashboard"),

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------
    path("incidents/", views.IncidentListView.as_view(), name="incident_list"),
    path("incidents/add/", views.IncidentCreateView.as_view(), name="incident_add"),
    path(
        "incidents/<int:pk>/",
        views.IncidentDetailView.as_view(),
        name="incident_detail",
    ),
    path(
        "incidents/<int:pk>/edit/",
        views.IncidentUpdateView.as_view(),
        name="incident_edit",
    ),

    # ------------------------------------------------------------------
    # Toolbox Talks
    # ------------------------------------------------------------------
    path("toolbox/", views.ToolboxTalkListView.as_view(), name="toolbox_list"),
    path("toolbox/add/", views.ToolboxTalkCreateView.as_view(), name="toolbox_add"),

    # ------------------------------------------------------------------
    # Safety Inductions
    # ------------------------------------------------------------------
    path("inductions/", views.SafetyInductionListView.as_view(), name="induction_list"),
    path(
        "inductions/add/",
        views.SafetyInductionCreateView.as_view(),
        name="induction_add",
    ),

    # ------------------------------------------------------------------
    # Hazard / Risk Register
    # ------------------------------------------------------------------
    path("hazards/", views.HazardRiskListView.as_view(), name="hazard_list"),
    path("hazards/add/", views.HazardRiskCreateView.as_view(), name="hazard_add"),
    path(
        "hazards/<int:pk>/edit/",
        views.HazardRiskUpdateView.as_view(),
        name="hazard_edit",
    ),

    # ------------------------------------------------------------------
    # SWMS
    # ------------------------------------------------------------------
    path("swms/", views.SWMSListView.as_view(), name="swms_list"),
    path("swms/add/", views.SWMSCreateView.as_view(), name="swms_add"),
    path("swms/<int:pk>/edit/", views.SWMSUpdateView.as_view(), name="swms_update"),

    # ------------------------------------------------------------------
    # PPE Issue Records
    # ------------------------------------------------------------------
    path("ppe/", views.PPEIssueListView.as_view(), name="ppe_list"),
    path("ppe/add/", views.PPEIssueCreateView.as_view(), name="ppe_add"),
    path("permits/", views.PermitToWorkListView.as_view(), name="permit_list"),
    path("permits/add/", views.PermitToWorkCreateView.as_view(), name="permit_add"),
    path("permits/<int:pk>/edit/", views.PermitToWorkUpdateView.as_view(), name="permit_edit"),
    path("training/", views.SafetyTrainingRecordListView.as_view(), name="training_list"),
    path("training/add/", views.SafetyTrainingRecordCreateView.as_view(), name="training_add"),
    path("training/<int:pk>/edit/", views.SafetyTrainingRecordUpdateView.as_view(), name="training_edit"),
    path("observations/", views.SafetyObservationListView.as_view(), name="observation_list"),
    path("observations/add/", views.SafetyObservationCreateView.as_view(), name="observation_add"),
    path("observations/<int:pk>/edit/", views.SafetyObservationUpdateView.as_view(), name="observation_edit"),
    path("corrective-actions/", views.SafetyCorrectiveActionListView.as_view(), name="corrective_action_list"),
    path("corrective-actions/add/", views.SafetyCorrectiveActionCreateView.as_view(), name="corrective_action_add"),
    path(
        "corrective-actions/<int:pk>/edit/",
        views.SafetyCorrectiveActionUpdateView.as_view(),
        name="corrective_action_edit",
    ),
]
