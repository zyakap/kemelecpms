"""
URL configuration for the procurement app.
"""

from django.urls import path

from . import views

app_name = "procurement"

urlpatterns = [
    # ------------------------------------------------------------------
    # Supplier
    # ------------------------------------------------------------------
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/add/", views.SupplierCreateView.as_view(), name="supplier_add"),
    path(
        "suppliers/<int:pk>/edit/",
        views.SupplierUpdateView.as_view(),
        name="supplier_edit",
    ),
    path(
        "suppliers/<int:pk>/",
        views.SupplierDetailView.as_view(),
        name="supplier_detail",
    ),
    # ------------------------------------------------------------------
    # Material catalogue
    # ------------------------------------------------------------------
    path("materials/", views.MaterialListView.as_view(), name="material_list"),
    path("materials/add/", views.MaterialCreateView.as_view(), name="material_add"),
    path(
        "materials/<int:pk>/edit/",
        views.MaterialUpdateView.as_view(),
        name="material_edit",
    ),
    # ------------------------------------------------------------------
    # Material Requisitions (MR)
    # ------------------------------------------------------------------
    path("requisitions/", views.MRListView.as_view(), name="mr_list"),
    path("requisitions/add/", views.MRCreateView.as_view(), name="mr_add"),
    path("requisitions/<int:pk>/", views.MRDetailView.as_view(), name="mr_detail"),
    path(
        "requisitions/<int:pk>/submit/",
        views.MRSubmitView.as_view(),
        name="mr_submit",
    ),
    path(
        "requisitions/<int:pk>/approve/",
        views.MRApproveView.as_view(),
        name="mr_approve",
    ),
    path(
        "requisitions/<int:pk>/reject/",
        views.MRRejectView.as_view(),
        name="mr_reject",
    ),
    # ------------------------------------------------------------------
    # Purchase Orders (PO)
    # ------------------------------------------------------------------
    path("orders/", views.POListView.as_view(), name="po_list"),
    path("orders/add/", views.POCreateView.as_view(), name="po_add"),
    path("orders/<int:pk>/", views.PODetailView.as_view(), name="po_detail"),
    path("orders/<int:pk>/edit/", views.POUpdateView.as_view(), name="po_edit"),
    path(
        "orders/<int:pk>/submit/",
        views.POSubmitView.as_view(),
        name="po_submit",
    ),
    path(
        "orders/<int:pk>/approve/",
        views.POApproveView.as_view(),
        name="po_approve",
    ),
    # ------------------------------------------------------------------
    # Goods Received Notes (GRN)
    # ------------------------------------------------------------------
    path(
        "orders/<int:po_pk>/grn/create/",
        views.GRNCreateView.as_view(),
        name="grn_create",
    ),
    path("grns/<int:pk>/", views.GRNDetailView.as_view(), name="grn_detail"),
    # ------------------------------------------------------------------
    # Supplier Invoices
    # ------------------------------------------------------------------
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/add/", views.InvoiceCreateView.as_view(), name="invoice_add"),
    # ------------------------------------------------------------------
    # Stock Ledger
    # ------------------------------------------------------------------
    path("stock/", views.StockLedgerView.as_view(), name="stock_ledger"),
    path(
        "stock/record/",
        views.StockLedgerCreateView.as_view(),
        name="stock_record",
    ),
]
