from django.contrib import admin

from .models import ComplianceCalendarEntry, IRCTaxInvoice, OTMLTCSReport


@admin.register(OTMLTCSReport)
class OTMLTCSReportAdmin(admin.ModelAdmin):
    list_display = ["report_number", "project", "period_type", "period_from", "period_to", "status", "overall_progress_pct"]
    list_filter = ["status", "period_type", "project"]
    search_fields = ["report_number", "project__name"]
    date_hierarchy = "period_to"


@admin.register(IRCTaxInvoice)
class IRCTaxInvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "project", "invoice_date", "status", "subtotal", "gst_amount", "total_amount"]
    list_filter = ["status", "project"]
    search_fields = ["invoice_number", "client_name", "project__name"]
    date_hierarchy = "invoice_date"


@admin.register(ComplianceCalendarEntry)
class ComplianceCalendarEntryAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "category", "due_date", "status", "responsible"]
    list_filter = ["status", "category", "project"]
    search_fields = ["title", "description"]
    date_hierarchy = "due_date"
