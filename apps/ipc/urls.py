from django.urls import path

from . import views

app_name = "ipc"

urlpatterns = [
    # IPC list / create / detail
    path(
        "projects/<int:project_pk>/ipcs/",
        views.IPCListView.as_view(),
        name="ipc-list",
    ),
    path(
        "projects/<int:project_pk>/ipcs/add/",
        views.IPCCreateView.as_view(),
        name="ipc-create",
    ),
    path(
        "projects/<int:project_pk>/ipcs/<int:pk>/",
        views.IPCDetailView.as_view(),
        name="ipc-detail",
    ),
    # Submit
    path(
        "projects/<int:project_pk>/ipcs/<int:pk>/submit/",
        views.IPCSubmitView.as_view(),
        name="ipc-submit",
    ),
    # Certification
    path(
        "projects/<int:project_pk>/ipcs/<int:ipc_pk>/certify/",
        views.CertificationCreateView.as_view(),
        name="certification-create",
    ),
    # Payment
    path(
        "projects/<int:project_pk>/ipcs/<int:ipc_pk>/pay/",
        views.PaymentCreateView.as_view(),
        name="payment-create",
    ),
    # Ledger
    path(
        "projects/<int:project_pk>/ipc-ledger/",
        views.IPCLedgerView.as_view(),
        name="ledger",
    ),
    # PDF
    path(
        "projects/<int:project_pk>/ipcs/<int:pk>/pdf/",
        views.IPCPDFView.as_view(),
        name="ipc-pdf",
    ),
]
