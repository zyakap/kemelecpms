from django.contrib import admin

from .models import (
    AuthorityPermit,
    ComplianceCalendarEntry,
    ComplianceCalendarTemplate,
    FunderReportPack,
    IRCTaxInvoice,
    LocalContentRecord,
    OTMLTCSReport,
    PublicProcurementRecord,
)


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


@admin.register(PublicProcurementRecord)
class PublicProcurementRecordAdmin(admin.ModelAdmin):
    list_display = ["tender_number", "project", "procurement_method", "status", "approval_reference"]
    list_filter = ["procurement_method", "status", "project"]
    search_fields = ["tender_number", "project__name", "approval_reference"]


@admin.register(LocalContentRecord)
class LocalContentRecordAdmin(admin.ModelAdmin):
    list_display = ["project", "period_from", "period_to", "png_labour_count", "expat_labour_count"]
    list_filter = ["project"]
    date_hierarchy = "period_to"


@admin.register(AuthorityPermit)
class AuthorityPermitAdmin(admin.ModelAdmin):
    list_display = ["project", "authority", "permit_type", "reference_number", "status", "expiry_date"]
    list_filter = ["authority", "status", "project"]
    search_fields = ["permit_type", "reference_number", "project__name"]


@admin.register(FunderReportPack)
class FunderReportPackAdmin(admin.ModelAdmin):
    list_display = ["project", "funder_type", "pack_type", "period_from", "period_to", "status"]
    list_filter = ["funder_type", "pack_type", "status", "project"]
    date_hierarchy = "period_to"


@admin.register(ComplianceCalendarTemplate)
class ComplianceCalendarTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "frequency", "default_reminder_days", "is_active"]
    list_filter = ["category", "frequency", "is_active"]
    search_fields = ["name", "description"]
