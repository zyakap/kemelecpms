from django.contrib import admin
from django.utils.html import format_html

from .models import Defect, ITP, ITPItem, InspectionRecord, MaterialTestResult, NCR


# ---------------------------------------------------------------------------
# ITP
# ---------------------------------------------------------------------------


class ITPItemInline(admin.TabularInline):
    model = ITPItem
    fields = ("sequence", "description", "inspection_type", "responsible_party", "status")
    extra = 0
    ordering = ("sequence",)


@admin.register(ITP)
class ITPAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "trade_section", "status", "total_items", "completion_percentage")
    list_filter = ("project", "status", "trade_section")
    search_fields = ("title", "description", "trade_section")
    readonly_fields = ("total_items", "passed_items", "completion_percentage")
    inlines = [ITPItemInline]

    @admin.display(description="Items")
    def total_items(self, obj):
        return obj.total_items

    @admin.display(description="% Complete")
    def completion_percentage(self, obj):
        return f"{obj.completion_percentage}%"


@admin.register(ITPItem)
class ITPItemAdmin(admin.ModelAdmin):
    list_display = ("itp", "sequence", "description", "inspection_type", "responsible_party", "status")
    list_filter = ("itp__project", "inspection_type", "responsible_party", "status")
    search_fields = ("description", "acceptance_criteria")
    ordering = ("itp", "sequence")


# ---------------------------------------------------------------------------
# Inspection Record
# ---------------------------------------------------------------------------


class InspectionRecordInline(admin.TabularInline):
    model = InspectionRecord
    fields = ("date", "inspector_name", "inspector_org", "location", "result")
    extra = 0
    ordering = ("-date",)


@admin.register(InspectionRecord)
class InspectionRecordAdmin(admin.ModelAdmin):
    list_display = ("itp_item", "date", "inspector_name", "inspector_org", "location", "result_badge", "signed_off_by")
    list_filter = ("result", "date", "itp_item__itp__project")
    search_fields = ("inspector_name", "inspector_org", "location", "notes")
    date_hierarchy = "date"

    @admin.display(description="Result")
    def result_badge(self, obj):
        colour_map = {
            InspectionRecord.RESULT_PASS: "#28a745",
            InspectionRecord.RESULT_FAIL: "#dc3545",
            InspectionRecord.RESULT_CONDITIONAL: "#fd7e14",
        }
        colour = colour_map.get(obj.result, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_result_display(),
        )


# ---------------------------------------------------------------------------
# NCR
# ---------------------------------------------------------------------------


@admin.register(NCR)
class NCRAdmin(admin.ModelAdmin):
    list_display = (
        "ncr_number",
        "project",
        "severity_badge",
        "status",
        "raised_by",
        "raised_date",
        "due_date",
        "responsible_person",
        "is_overdue",
    )
    list_filter = ("project", "severity", "status")
    search_fields = ("ncr_number", "description", "location", "trade_responsible")
    date_hierarchy = "raised_date"
    readonly_fields = ("ncr_number", "is_overdue")

    @admin.display(description="Severity")
    def severity_badge(self, obj):
        colour_map = {
            NCR.SEVERITY_MINOR: "#fd7e14",
            NCR.SEVERITY_MAJOR: "#dc3545",
            NCR.SEVERITY_CRITICAL: "#6f42c1",
        }
        colour = colour_map.get(obj.severity, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_severity_display(),
        )

    @admin.display(description="Overdue", boolean=True)
    def is_overdue(self, obj):
        return obj.is_overdue


# ---------------------------------------------------------------------------
# MaterialTestResult
# ---------------------------------------------------------------------------


@admin.register(MaterialTestResult)
class MaterialTestResultAdmin(admin.ModelAdmin):
    list_display = (
        "sample_reference",
        "project",
        "test_type",
        "test_date",
        "location",
        "specified_value",
        "actual_value",
        "passed",
        "ncr",
    )
    list_filter = ("project", "test_type", "passed")
    search_fields = ("sample_reference", "location", "notes")
    date_hierarchy = "test_date"

    @admin.display(description="Passed", boolean=True)
    def passed(self, obj):
        return obj.passed


# ---------------------------------------------------------------------------
# Defect
# ---------------------------------------------------------------------------


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = (
        "defect_number",
        "project",
        "trade",
        "severity_badge",
        "phase",
        "status",
        "identified_date",
        "target_rectification_date",
        "is_overdue",
    )
    list_filter = ("project", "severity", "phase", "status")
    search_fields = ("defect_number", "description", "location", "trade", "responsible_party")
    date_hierarchy = "identified_date"
    readonly_fields = ("defect_number", "is_overdue")

    @admin.display(description="Severity")
    def severity_badge(self, obj):
        colour_map = {
            Defect.SEVERITY_MINOR: "#fd7e14",
            Defect.SEVERITY_MAJOR: "#dc3545",
            Defect.SEVERITY_CRITICAL: "#6f42c1",
        }
        colour = colour_map.get(obj.severity, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_severity_display(),
        )

    @admin.display(description="Overdue", boolean=True)
    def is_overdue(self, obj):
        return obj.is_overdue
