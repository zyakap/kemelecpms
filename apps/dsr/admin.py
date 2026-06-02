"""
Django admin registrations for the DSR app.
"""

from django.contrib import admin

from .models import (
    DailySiteReport,
    DSRActivity,
    DSREquipment,
    DSRIssue,
    DSRLabour,
    DSRMaterialDelivery,
    DSRMaterialUsage,
    DSRPhoto,
    DSRVisitor,
)


# ---------------------------------------------------------------------------
# Inline definitions
# ---------------------------------------------------------------------------


class DSRActivityInline(admin.TabularInline):
    model = DSRActivity
    extra = 1
    fields = (
        "wbs_activity",
        "description",
        "location_on_site",
        "status",
        "quantity_achieved",
        "unit",
        "percent_complete",
        "crew",
    )
    autocomplete_fields = ("wbs_activity",)


class DSRLabourInline(admin.TabularInline):
    model = DSRLabour
    extra = 1
    fields = ("classification", "nationality", "count")


class DSRVisitorInline(admin.TabularInline):
    model = DSRVisitor
    extra = 0
    fields = ("name", "organization", "purpose", "time_in", "time_out")


class DSREquipmentInline(admin.TabularInline):
    model = DSREquipment
    extra = 0
    fields = (
        "equipment",
        "hours_worked",
        "hours_idle",
        "hours_breakdown",
        "notes",
    )


class DSRMaterialDeliveryInline(admin.TabularInline):
    model = DSRMaterialDelivery
    extra = 0
    fields = ("grn", "description", "quantity", "unit")


class DSRMaterialUsageInline(admin.TabularInline):
    model = DSRMaterialUsage
    extra = 0
    fields = ("material", "quantity_used", "notes")


class DSRPhotoInline(admin.TabularInline):
    model = DSRPhoto
    extra = 0
    fields = ("photo", "caption", "tag", "gps_lat", "gps_lng")
    readonly_fields = ("taken_at",)


class DSRIssueInline(admin.TabularInline):
    model = DSRIssue
    extra = 0
    fields = (
        "issue_type",
        "description",
        "raised_by",
        "date",
        "action_required",
        "resolved",
    )


# ---------------------------------------------------------------------------
# DailySiteReport admin
# ---------------------------------------------------------------------------


@admin.register(DailySiteReport)
class DailySiteReportAdmin(admin.ModelAdmin):
    list_display = (
        "dsr_number",
        "project",
        "date",
        "day_number",
        "weather_am",
        "weather_pm",
        "prepared_by",
        "status",
        "is_locked",
    )
    list_filter = ("status", "is_locked", "project", "date")
    search_fields = ("dsr_number", "project__name", "prepared_by__username")
    readonly_fields = (
        "dsr_number",
        "day_number",
        "created_at",
        "updated_at",
        "approved_at",
    )
    date_hierarchy = "date"
    inlines = [
        DSRActivityInline,
        DSRLabourInline,
        DSRVisitorInline,
        DSREquipmentInline,
        DSRMaterialDeliveryInline,
        DSRMaterialUsageInline,
        DSRPhotoInline,
        DSRIssueInline,
    ]
    fieldsets = (
        (
            "DSR Header",
            {
                "fields": (
                    "dsr_number",
                    "project",
                    "date",
                    "day_number",
                    "weather_am",
                    "weather_pm",
                    "prepared_by",
                    "notes",
                )
            },
        ),
        (
            "Approval",
            {
                "fields": (
                    "status",
                    "approved_by",
                    "approved_at",
                    "return_reason",
                    "is_locked",
                    "pdf_file",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ---------------------------------------------------------------------------
# Standalone admin registrations (for direct access / filtering)
# ---------------------------------------------------------------------------


@admin.register(DSRPhoto)
class DSRPhotoAdmin(admin.ModelAdmin):
    list_display = ("dsr", "tag", "caption", "taken_at")
    list_filter = ("tag", "dsr__project")
    search_fields = ("dsr__dsr_number", "caption")
    readonly_fields = ("taken_at",)


@admin.register(DSRIssue)
class DSRIssueAdmin(admin.ModelAdmin):
    list_display = (
        "dsr",
        "issue_type",
        "description",
        "raised_by",
        "date",
        "resolved",
    )
    list_filter = ("issue_type", "resolved", "dsr__project")
    search_fields = ("dsr__dsr_number", "description")


@admin.register(DSREquipment)
class DSREquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "dsr",
        "equipment",
        "hours_worked",
        "hours_idle",
        "hours_breakdown",
    )
    list_filter = ("dsr__project",)
    search_fields = ("dsr__dsr_number", "equipment__name")
