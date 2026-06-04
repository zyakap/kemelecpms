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
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_update"),

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
]
