from django.contrib import admin
from django.utils.html import format_html

from .models import BoQItem, CostCode, CostEntry, Subcontract


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
        "total_spent",
        "variance",
        "rag_badge",
    )
    list_filter = ("project", "category", "is_contingency")
    search_fields = ("code", "name")
    readonly_fields = ("total_committed", "total_actual", "total_spent", "variance", "variance_percentage", "rag_status")
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
    list_display = ("company_name", "trade", "project", "contract_value", "retention_held", "status", "start_date", "end_date")
    list_filter = ("project", "status")
    search_fields = ("company_name", "trade")
