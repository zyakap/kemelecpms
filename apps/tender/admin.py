from django.contrib import admin

from .models import BidEstimate, BidEstimateItem, CostRate, LessonsLearned, TenderArchive, TenderDocument


class BidEstimateItemInline(admin.TabularInline):
    model = BidEstimateItem
    extra = 0


@admin.register(TenderArchive)
class TenderArchiveAdmin(admin.ModelAdmin):
    list_display = ["project", "archived_date", "original_contract_value", "final_contract_value", "margin_pct"]
    search_fields = ["project__name", "searchable_tags", "key_scope"]


@admin.register(CostRate)
class CostRateAdmin(admin.ModelAdmin):
    list_display = ["description", "trade", "unit", "unit_rate", "region", "year", "is_verified"]
    list_filter = ["trade", "region", "year", "is_verified"]
    search_fields = ["description"]


@admin.register(BidEstimate)
class BidEstimateAdmin(admin.ModelAdmin):
    list_display = ["tender_reference", "title", "client_name", "status", "estimate_total", "bid_amount", "tender_due_date"]
    list_filter = ["status"]
    inlines = [BidEstimateItemInline]


@admin.register(LessonsLearned)
class LessonsLearnedAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "category", "recorded_by", "created_at"]
    list_filter = ["category", "project"]
    search_fields = ["title", "recommendation"]


@admin.register(TenderDocument)
class TenderDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "doc_type", "trade_category", "version", "is_current", "created_at"]
    list_filter = ["doc_type", "is_current", "trade_category"]
    search_fields = ["title", "tags", "description"]
