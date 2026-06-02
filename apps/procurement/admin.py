from django.contrib import admin
from django.utils.html import format_html

from .models import (
    GoodsReceivedNote,
    GRNItem,
    Material,
    MaterialCategory,
    MaterialRequisition,
    MRItem,
    POItem,
    PurchaseOrder,
    StockLedger,
    Supplier,
    SupplierInvoice,
)


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "contact_person",
        "phone",
        "email",
        "is_preferred",
        "is_blacklisted",
        "performance_rating",
    )
    list_filter = ("is_preferred", "is_blacklisted")
    search_fields = ("name", "contact_person", "email", "irc_tin")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Supplier Details",
            {
                "fields": (
                    "name",
                    "address",
                    "irc_tin",
                    "categories",
                )
            },
        ),
        (
            "Banking",
            {
                "fields": (
                    "bank_name",
                    "bank_account_name",
                    "bank_account_number",
                )
            },
        ),
        (
            "Contact",
            {"fields": ("contact_person", "email", "phone")},
        ),
        (
            "Status & Performance",
            {
                "fields": (
                    "is_preferred",
                    "is_blacklisted",
                    "blacklist_reason",
                    "performance_rating",
                    "notes",
                )
            },
        ),
        (
            "Audit",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("item_code", "description", "unit", "category", "min_stock_level")
    list_filter = ("category",)
    search_fields = ("item_code", "description")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Material Requisition
# ---------------------------------------------------------------------------


class MRItemInline(admin.TabularInline):
    model = MRItem
    extra = 1
    fields = (
        "material",
        "description",
        "unit",
        "quantity_requested",
        "quantity_ordered",
        "notes",
    )
    autocomplete_fields = ("material",)


@admin.register(MaterialRequisition)
class MaterialRequisitionAdmin(admin.ModelAdmin):
    list_display = (
        "mr_number",
        "project",
        "requested_by",
        "date",
        "required_by_date",
        "status",
    )
    list_filter = ("status", "project")
    search_fields = ("mr_number", "project__name", "requested_by__username")
    readonly_fields = ("mr_number", "created_at", "updated_at", "approved_at")
    inlines = [MRItemInline]
    fieldsets = (
        (
            "Requisition",
            {
                "fields": (
                    "mr_number",
                    "project",
                    "requested_by",
                    "date",
                    "required_by_date",
                    "justification",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "rejection_reason",
                    "approved_by",
                    "approved_at",
                )
            },
        ),
    )


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------


class POItemInline(admin.TabularInline):
    model = POItem
    extra = 1
    fields = (
        "material",
        "description",
        "unit",
        "quantity",
        "unit_price",
        "mr_item",
    )
    autocomplete_fields = ("material",)
    readonly_fields = ()


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        "po_number",
        "project",
        "supplier",
        "date",
        "status",
        "total_amount",
    )
    list_filter = ("status", "project", "supplier")
    search_fields = ("po_number", "supplier__name", "project__name")
    readonly_fields = ("po_number", "created_at", "updated_at", "approved_at", "total_amount")
    inlines = [POItemInline]
    fieldsets = (
        (
            "Purchase Order",
            {
                "fields": (
                    "po_number",
                    "project",
                    "supplier",
                    "mr",
                    "date",
                    "delivery_address",
                    "expected_delivery_date",
                    "notes",
                )
            },
        ),
        (
            "Status & Financials",
            {
                "fields": (
                    "status",
                    "total_amount",
                    "approved_by",
                    "approved_at",
                    "cancelled_reason",
                )
            },
        ),
    )


# ---------------------------------------------------------------------------
# GRN
# ---------------------------------------------------------------------------


class GRNItemInline(admin.TabularInline):
    model = GRNItem
    extra = 1
    fields = (
        "po_item",
        "quantity_delivered",
        "has_discrepancy",
        "discrepancy_notes",
    )


@admin.register(GoodsReceivedNote)
class GoodsReceivedNoteAdmin(admin.ModelAdmin):
    list_display = (
        "grn_number",
        "po",
        "delivery_date",
        "delivered_by",
        "received_by",
        "is_partial",
    )
    list_filter = ("is_partial", "delivery_date")
    search_fields = ("grn_number", "po__po_number", "delivered_by")
    readonly_fields = ("grn_number", "created_at", "updated_at")
    inlines = [GRNItemInline]


# ---------------------------------------------------------------------------
# Supplier Invoice
# ---------------------------------------------------------------------------


@admin.register(SupplierInvoice)
class SupplierInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "supplier",
        "po",
        "invoice_date",
        "amount",
        "status",
        "is_matched",
    )
    list_filter = ("status", "is_matched")
    search_fields = ("invoice_number", "supplier__name", "po__po_number")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Stock Ledger
# ---------------------------------------------------------------------------


@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "project",
        "material",
        "transaction_type",
        "quantity",
        "reference",
        "recorded_by",
    )
    list_filter = ("transaction_type", "project", "date")
    search_fields = ("material__item_code", "material__description", "reference")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"
