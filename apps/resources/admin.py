from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AttendanceRecord,
    Crew,
    CrewMember,
    Equipment,
    EquipmentAllocation,
    EquipmentUtilisation,
    SubcontractorCompany,
    Worker,
)


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class CrewMemberInline(admin.TabularInline):
    model = CrewMember
    fk_name = "worker"
    fields = ("crew", "date_joined", "date_left")
    extra = 0
    autocomplete_fields = ("crew",)


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = (
        "worker_id",
        "full_name",
        "occupation",
        "classification",
        "employment_type",
        "nationality",
        "project",
        "is_active",
    )
    list_filter = ("is_active", "classification", "employment_type", "nationality", "project")
    search_fields = ("worker_id", "first_name", "last_name", "occupation", "nid_number")
    readonly_fields = ("worker_id", "full_name")
    inlines = [CrewMemberInline]
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "worker_id",
                    ("first_name", "last_name"),
                    "gender",
                    "nationality",
                    "nid_number",
                    "tfn",
                )
            },
        ),
        (
            "Employment",
            {
                "fields": (
                    "occupation",
                    "trade",
                    "classification",
                    "employment_type",
                    "project",
                    "date_joined",
                    "is_active",
                )
            },
        ),
        (
            "Contact",
            {"fields": ("phone", "emergency_contact")},
        ),
    )


# ---------------------------------------------------------------------------
# Crew
# ---------------------------------------------------------------------------


class CrewMemberProjectInline(admin.TabularInline):
    model = CrewMember
    fk_name = "crew"
    fields = ("worker", "date_joined", "date_left")
    extra = 0
    autocomplete_fields = ("worker",)


@admin.register(Crew)
class CrewAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "foreman", "active_member_count")
    list_filter = ("project",)
    search_fields = ("name", "project__name")
    autocomplete_fields = ("foreman",)
    inlines = [CrewMemberProjectInline]
    readonly_fields = ("active_member_count",)


@admin.register(CrewMember)
class CrewMemberAdmin(admin.ModelAdmin):
    list_display = ("worker", "crew", "date_joined", "date_left", "is_current")
    list_filter = ("crew__project",)
    search_fields = ("worker__first_name", "worker__last_name", "crew__name")
    autocomplete_fields = ("worker", "crew")


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "worker",
        "project",
        "date",
        "crew",
        "is_present",
        "time_in",
        "time_out",
        "overtime_hours",
        "recorded_by",
    )
    list_filter = ("project", "date", "is_present", "crew")
    search_fields = ("worker__first_name", "worker__last_name", "worker__worker_id")
    date_hierarchy = "date"
    autocomplete_fields = ("worker", "crew")


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------


class EquipmentAllocationInline(admin.TabularInline):
    model = EquipmentAllocation
    fields = ("project", "allocated_date", "return_date", "hire_rate_daily")
    extra = 0
    show_change_link = True


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "equipment_id",
        "description",
        "equipment_type",
        "ownership_type",
        "model",
        "year",
        "registration_number",
        "is_active",
    )
    list_filter = ("ownership_type", "is_active", "equipment_type")
    search_fields = ("equipment_id", "description", "model", "registration_number")
    readonly_fields = ("equipment_id",)
    inlines = [EquipmentAllocationInline]


class EquipmentUtilisationInline(admin.TabularInline):
    model = EquipmentUtilisation
    fields = ("date", "hours_worked", "hours_idle", "hours_breakdown", "fuel_litres", "operator")
    extra = 0
    ordering = ("-date",)
    autocomplete_fields = ("operator",)


@admin.register(EquipmentAllocation)
class EquipmentAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "equipment",
        "project",
        "allocated_date",
        "return_date",
        "hire_rate_daily",
        "is_current",
    )
    list_filter = ("project", "equipment__ownership_type")
    search_fields = ("equipment__equipment_id", "equipment__description", "project__name")
    inlines = [EquipmentUtilisationInline]
    readonly_fields = ("is_current", "total_hire_cost")


@admin.register(EquipmentUtilisation)
class EquipmentUtilisationAdmin(admin.ModelAdmin):
    list_display = (
        "allocation",
        "date",
        "hours_worked",
        "hours_idle",
        "hours_breakdown",
        "fuel_litres",
        "utilisation_rate",
        "operator",
    )
    list_filter = ("allocation__project", "date")
    search_fields = ("allocation__equipment__equipment_id", "allocation__equipment__description")
    date_hierarchy = "date"
    autocomplete_fields = ("operator",)
    readonly_fields = ("total_hours", "utilisation_rate")


# ---------------------------------------------------------------------------
# Subcontractor Companies
# ---------------------------------------------------------------------------


@admin.register(SubcontractorCompany)
class SubcontractorCompanyAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "trade",
        "contact_person",
        "phone",
        "is_prequalified",
        "is_blacklisted",
        "performance_rating",
        "status_badge",
    )
    list_filter = ("is_prequalified", "is_blacklisted", "trade")
    search_fields = ("company_name", "trade", "contact_person", "irc_tin")
    readonly_fields = ("status_display",)

    @admin.display(description="Status")
    def status_badge(self, obj):
        colour_map = {
            "Blacklisted": "#dc3545",
            "Prequalified": "#28a745",
            "Registered": "#6c757d",
        }
        status = obj.status_display
        colour = colour_map.get(status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            status,
        )
