from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    path("projects/<int:project_pk>/", views.MaintenanceDashboardView.as_view(), name="dashboard"),
    path("projects/<int:project_pk>/assets/", views.AssetListView.as_view(), name="asset-list"),
    path("projects/<int:project_pk>/assets/add/", views.AssetCreateView.as_view(), name="asset-create"),
    path("projects/<int:project_pk>/assets/<int:pk>/", views.AssetDetailView.as_view(), name="asset-detail"),
    path("projects/<int:project_pk>/assets/<int:pk>/edit/", views.AssetUpdateView.as_view(), name="asset-update"),
    path("projects/<int:project_pk>/assets/<int:asset_pk>/pm/add/", views.PreventiveMaintenancePlanCreateView.as_view(), name="pm-create"),
    path("projects/<int:project_pk>/work-orders/", views.WorkOrderListView.as_view(), name="workorder-list"),
    path("projects/<int:project_pk>/work-orders/add/", views.WorkOrderCreateView.as_view(), name="workorder-create"),
    path("projects/<int:project_pk>/work-orders/<int:pk>/", views.WorkOrderDetailView.as_view(), name="workorder-detail"),
    path("projects/<int:project_pk>/work-orders/<int:pk>/edit/", views.WorkOrderUpdateView.as_view(), name="workorder-update"),
    path("projects/<int:project_pk>/breakdowns/add/", views.BreakdownTicketCreateView.as_view(), name="breakdown-create"),
    path("projects/<int:project_pk>/service-records/add/", views.ServiceRecordCreateView.as_view(), name="service-create"),
    path(
        "projects/<int:project_pk>/work-orders/<int:work_order_pk>/service-records/add/",
        views.ServiceRecordCreateView.as_view(),
        name="workorder-service-create",
    ),
    path("projects/<int:project_pk>/spares/", views.SparePartListView.as_view(), name="spare-list"),
    path("projects/<int:project_pk>/spares/add/", views.SparePartCreateView.as_view(), name="spare-create"),
]
