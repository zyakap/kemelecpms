from django.contrib import admin
from django.utils.html import format_html

from .models import (
    BoQItem,
    CostCode,
    CostEntry,
    Subcontract,
    SubcontractBackCharge,
    SubcontractClaim,
    SubcontractPerformanceReview,
)


class BoQItemInline(admin.TabularInline):
    model = BoQItem
    fields = ("item_number", "description", "unit", "quantity", "unit_rate", "trade_section")
    extra = 0
    ordering = ("item_number",)


@admin.register(CostCode)
class CostCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "project",
        "budget_amount",
        "forecast_etc",
        "estimate_at_completion",
        "forecast_variance",
        "total_spent",
        "variance",
        "rag_badge",
    )
    list_filter = ("project", "category", "is_contingency")
    search_fields = ("code", "name")
    readonly_fields = (
        "total_committed",
        "total_actual",
        "total_spent",
        "estimate_at_completion",
        "forecast_variance",
        "forecast_variance_percentage",
        "variance",
        "variance_percentage",
        "rag_status",
        "forecast_rag_status",
    )
    inlines = [BoQItemInline]

    @admin.display(description="RAG")
    def rag_badge(self, obj):
        colour_map = {"GREEN": "#28a745", "AMBER": "#fd7e14", "RED": "#dc3545"}
        status = obj.rag_status
        colour = colour_map.get(status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            status,
        )


class CostEntryInline(admin.TabularInline):
    model = CostEntry
    fields = ("entry_type", "description", "amount", "date", "reference", "supplier")
    extra = 0
    ordering = ("-date",)


@admin.register(BoQItem)
class BoQItemAdmin(admin.ModelAdmin):
    list_display = ("item_number", "description", "unit", "quantity", "unit_rate", "amount", "trade_section", "is_variation")
    list_filter = ("project", "trade_section", "is_variation")
    search_fields = ("item_number", "description")
    readonly_fields = ("amount",)


@admin.register(CostEntry)
class CostEntryAdmin(admin.ModelAdmin):
    list_display = ("description", "entry_type", "cost_code", "amount", "date", "supplier", "reference", "project")
    list_filter = ("project", "entry_type", "cost_code", "date")
    search_fields = ("description", "supplier", "reference")
    date_hierarchy = "date"
    autocomplete_fields = ("cost_code", "boq_item")


@admin.register(Subcontract)
class SubcontractAdmin(admin.ModelAdmin):
    list_display = ("company_name", "trade", "project", "contract_value", "amount_approved", "amount_paid", "retention_held", "status")
    list_filter = ("project", "status")
    search_fields = ("company_name", "trade")


@admin.register(SubcontractClaim)
class SubcontractClaimAdmin(admin.ModelAdmin):
    list_display = ("claim_number", "subcontract", "submitted_date", "claimed_amount", "approved_amount", "amount_paid", "status")
    list_filter = ("status", "submitted_date", "subcontract__project")
    search_fields = ("claim_number", "subcontract__company_name", "payment_reference")
    date_hierarchy = "submitted_date"


@admin.register(SubcontractBackCharge)
class SubcontractBackChargeAdmin(admin.ModelAdmin):
    list_display = ("subcontract", "date", "amount", "status", "recovered_from_claim")
    list_filter = ("status", "date", "subcontract__project")
    search_fields = ("subcontract__company_name", "description")
    date_hierarchy = "date"


@admin.register(SubcontractPerformanceReview)
class SubcontractPerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ("subcontract", "review_date", "reviewer", "overall_score")
    list_filter = ("review_date", "subcontract__project")
    search_fields = ("subcontract__company_name", "notes")
    date_hierarchy = "review_date"
