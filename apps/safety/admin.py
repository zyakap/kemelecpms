"""
Django admin registrations for the safety app.
"""

from django.contrib import admin

from .models import (
    HazardRisk,
    Incident,
    PPEIssue,
    SafetyInduction,
    SWMS,
    ToolboxAttendee,
    ToolboxTalk,
)


# ---------------------------------------------------------------------------
# Safety Induction
# ---------------------------------------------------------------------------


@admin.register(SafetyInduction)
class SafetyInductionAdmin(admin.ModelAdmin):
    list_display = (
        "worker",
        "project",
        "date",
        "inducted_by",
        "expiry_date",
        "acknowledged",
    )
    list_filter = ("project", "acknowledged")
    search_fields = (
        "worker__first_name",
        "worker__last_name",
        "inducted_by__username",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"


# ---------------------------------------------------------------------------
# Toolbox Talk
# ---------------------------------------------------------------------------


class ToolboxAttendeeInline(admin.TabularInline):
    model = ToolboxAttendee
    extra = 0
    fields = ("worker",)
    autocomplete_fields = ("worker",)


@admin.register(ToolboxTalk)
class ToolboxTalkAdmin(admin.ModelAdmin):
    list_display = ("date", "project", "topic", "presenter", "attendee_count")
    list_filter = ("project",)
    search_fields = ("topic", "presenter__username")
    readonly_fields = ("attendee_count", "created_at", "updated_at")
    date_hierarchy = "date"
    inlines = [ToolboxAttendeeInline]


# ---------------------------------------------------------------------------
# Incident
# ---------------------------------------------------------------------------


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        "incident_number",
        "project",
        "date",
        "incident_type",
        "is_lti",
        "days_lost",
        "status",
        "reported_by",
    )
    list_filter = ("incident_type", "is_lti", "status", "project")
    search_fields = (
        "incident_number",
        "description",
        "persons_involved",
        "reported_by__username",
    )
    readonly_fields = ("incident_number", "created_at", "updated_at")
    date_hierarchy = "date"
    fieldsets = (
        (
            "Incident Details",
            {
                "fields": (
                    "incident_number",
                    "project",
                    "date",
                    "time",
                    "location",
                    "incident_type",
                    "description",
                    "persons_involved",
                    "body_part",
                    "injury_nature",
                    "treatment_given",
                    "is_lti",
                    "days_lost",
                    "reported_by",
                    "photo",
                )
            },
        ),
        (
            "Investigation & Corrective Action",
            {
                "fields": (
                    "status",
                    "corrective_action",
                    "corrective_action_due",
                    "corrective_action_person",
                    "corrective_action_closed",
                )
            },
        ),
        (
            "Audit",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# ---------------------------------------------------------------------------
# Hazard Risk Register
# ---------------------------------------------------------------------------


@admin.register(HazardRisk)
class HazardRiskAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "activity",
        "hazard_description",
        "likelihood",
        "consequence",
        "risk_level",
        "risk_category",
        "control_type",
    )
    list_filter = ("project", "control_type")
    search_fields = ("activity", "hazard_description")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Risk Level")
    def risk_level(self, obj):
        return obj.risk_level

    @admin.display(description="Risk Category")
    def risk_category(self, obj):
        return obj.risk_category_display


# ---------------------------------------------------------------------------
# SWMS
# ---------------------------------------------------------------------------


@admin.register(SWMS)
class SWMSAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "activity",
        "version",
        "status",
        "approved_by",
        "approved_date",
    )
    list_filter = ("status", "project")
    search_fields = ("title", "activity")
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# PPE Issue
# ---------------------------------------------------------------------------


@admin.register(PPEIssue)
class PPEIssueAdmin(admin.ModelAdmin):
    list_display = (
        "worker",
        "project",
        "ppe_type",
        "size",
        "quantity",
        "date_issued",
        "issued_by",
    )
    list_filter = ("project", "ppe_type")
    search_fields = (
        "worker__first_name",
        "worker__last_name",
        "issued_by__username",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date_issued"
