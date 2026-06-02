from django.contrib import admin
from django.utils.html import format_html

from .models import Correspondence, Drawing, DrawingRevision, ProjectDocument, RFI, Submittal


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


class DrawingRevisionInline(admin.TabularInline):
    model = DrawingRevision
    fields = ("revision", "date", "uploaded_by", "file", "notes")
    extra = 0
    ordering = ("-date",)


@admin.register(Drawing)
class DrawingAdmin(admin.ModelAdmin):
    list_display = (
        "drawing_number",
        "title",
        "project",
        "discipline",
        "current_revision",
        "current_revision_date",
        "status_badge",
    )
    list_filter = ("project", "discipline", "status")
    search_fields = ("drawing_number", "title", "notes")
    inlines = [DrawingRevisionInline]

    @admin.display(description="Status")
    def status_badge(self, obj):
        colour_map = {
            Drawing.STATUS_IFC: "#28a745",
            Drawing.STATUS_FOR_REVIEW: "#fd7e14",
            Drawing.STATUS_SUPERSEDED: "#6c757d",
            Drawing.STATUS_FOR_INFO: "#17a2b8",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )


@admin.register(DrawingRevision)
class DrawingRevisionAdmin(admin.ModelAdmin):
    list_display = ("drawing", "revision", "date", "uploaded_by")
    list_filter = ("drawing__project", "drawing__discipline")
    search_fields = ("drawing__drawing_number", "revision", "notes")
    date_hierarchy = "date"


# ---------------------------------------------------------------------------
# RFI
# ---------------------------------------------------------------------------


@admin.register(RFI)
class RFIAdmin(admin.ModelAdmin):
    list_display = (
        "rfi_number",
        "project",
        "subject",
        "date_raised",
        "raised_by",
        "directed_to",
        "status_badge",
        "schedule_impact_days",
        "cost_impact",
    )
    list_filter = ("project", "status")
    search_fields = ("rfi_number", "subject", "question", "directed_to")
    date_hierarchy = "date_raised"
    readonly_fields = ("rfi_number",)

    @admin.display(description="Status")
    def status_badge(self, obj):
        colour_map = {
            RFI.STATUS_OPEN: "#dc3545",
            RFI.STATUS_RESPONDED: "#fd7e14",
            RFI.STATUS_CLOSED: "#28a745",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )


# ---------------------------------------------------------------------------
# Submittal
# ---------------------------------------------------------------------------


@admin.register(Submittal)
class SubmittalAdmin(admin.ModelAdmin):
    list_display = (
        "submittal_number",
        "project",
        "submittal_type",
        "title",
        "submitted_date",
        "submitted_by",
        "status_badge",
        "revision",
    )
    list_filter = ("project", "submittal_type", "status")
    search_fields = ("submittal_number", "title", "review_notes")
    date_hierarchy = "submitted_date"
    readonly_fields = ("submittal_number",)

    @admin.display(description="Status")
    def status_badge(self, obj):
        colour_map = {
            Submittal.STATUS_SUBMITTED: "#007bff",
            Submittal.STATUS_APPROVED: "#28a745",
            Submittal.STATUS_APPROVED_AS_NOTED: "#fd7e14",
            Submittal.STATUS_REVISE_RESUBMIT: "#ffc107",
            Submittal.STATUS_REJECTED: "#dc3545",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )


# ---------------------------------------------------------------------------
# Correspondence
# ---------------------------------------------------------------------------


@admin.register(Correspondence)
class CorrespondenceAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "project",
        "date",
        "direction",
        "subject",
        "sender",
        "recipient",
        "action_required",
        "is_responded",
    )
    list_filter = ("project", "direction", "action_required", "is_responded")
    search_fields = ("reference_number", "subject", "sender", "recipient", "summary")
    date_hierarchy = "date"
    readonly_fields = ("reference_number",)


# ---------------------------------------------------------------------------
# ProjectDocument
# ---------------------------------------------------------------------------


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "document_type",
        "version",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("document_type",)
    search_fields = ("title", "document_type", "description")
    date_hierarchy = "created_at"
    raw_id_fields = ("project",)
