from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    # -----------------------------------------------------------------------
    # Projects
    # -----------------------------------------------------------------------
    path("", views.ProjectListView.as_view(), name="project_list"),
    path("create/", views.ProjectCreateView.as_view(), name="project_create"),
    path("<int:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("<int:pk>/setup/", views.ProjectSetupView.as_view(), name="project_setup"),
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_update"),
    path("<int:project_pk>/members/add/", views.ProjectMembershipCreateView.as_view(), name="membership_create"),
    path(
        "<int:project_pk>/members/<int:pk>/edit/",
        views.ProjectMembershipUpdateView.as_view(),
        name="membership_update",
    ),

    # -----------------------------------------------------------------------
    # Contract  (nested under a project)
    # -----------------------------------------------------------------------
    path(
        "<int:project_pk>/contract/add/",
        views.ContractCreateView.as_view(),
        name="contract_create",
    ),
    path(
        "<int:project_pk>/contract/edit/",
        views.ContractUpdateView.as_view(),
        name="contract_update",
    ),

    # -----------------------------------------------------------------------
    # Variations  (nested under a project)
    # -----------------------------------------------------------------------
    path(
        "<int:project_pk>/variations/",
        views.VariationListView.as_view(),
        name="variation_list",
    ),
    path(
        "<int:project_pk>/variations/create/",
        views.VariationCreateView.as_view(),
        name="variation_create",
    ),
    path(
        "<int:project_pk>/variations/<int:pk>/edit/",
        views.VariationUpdateView.as_view(),
        name="variation_update",
    ),

    # -----------------------------------------------------------------------
    # Milestones  (nested under a project)
    # -----------------------------------------------------------------------
    path(
        "<int:project_pk>/milestones/",
        views.MilestoneListView.as_view(),
        name="milestone_list",
    ),
    path(
        "<int:project_pk>/milestones/create/",
        views.MilestoneCreateView.as_view(),
        name="milestone_create",
    ),
    path(
        "<int:project_pk>/milestones/<int:pk>/edit/",
        views.MilestoneUpdateView.as_view(),
        name="milestone_update",
    ),

    # -----------------------------------------------------------------------
    # Clients
    # -----------------------------------------------------------------------
    path("clients/", views.ClientListView.as_view(), name="client_list"),
    path("clients/create/", views.ClientCreateView.as_view(), name="client_create"),

    # -----------------------------------------------------------------------
    # Funders
    # -----------------------------------------------------------------------
    path("funders/", views.FunderListView.as_view(), name="funder_list"),
    path("funders/create/", views.FunderCreateView.as_view(), name="funder_create"),
    path("funders/<int:pk>/edit/", views.FunderUpdateView.as_view(), name="funder_update"),
    # Closeout
    path("<int:pk>/closeout/", views.ProjectCloseoutView.as_view(), name="project_closeout"),

    # -----------------------------------------------------------------------
    # Work Packages
    # -----------------------------------------------------------------------
    path("<int:project_pk>/work-packages/", views.WorkPackageListView.as_view(), name="work_package_list"),
    path("<int:project_pk>/work-packages/add/", views.WorkPackageCreateView.as_view(), name="work_package_create"),
    path("<int:project_pk>/work-packages/<int:pk>/edit/", views.WorkPackageUpdateView.as_view(), name="work_package_update"),
    path("<int:project_pk>/work-packages/<int:pk>/progress/", views.WorkPackageProgressCreateView.as_view(), name="work_package_progress"),

    # -----------------------------------------------------------------------
    # AJAX Quick-Create (used by project form modals)
    # -----------------------------------------------------------------------
    path("ajax/client/create/", views.QuickCreateClientView.as_view(), name="ajax_client_create"),
    path("ajax/funder/create/", views.QuickCreateFunderView.as_view(), name="ajax_funder_create"),
    path("ajax/staff/create/", views.QuickCreateStaffView.as_view(), name="ajax_staff_create"),
]
