from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Client,
    Contract,
    DelayEvent,
    Funder,
    Milestone,
    Project,
    ProjectMembership,
    Variation,
)


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------


class ContractInline(admin.StackedInline):
    model = Contract
    can_delete = False
    extra = 0
    verbose_name_plural = "Contract"
    fields = (
        "contract_number",
        "contract_type",
        "original_value",
        "start_date",
        "original_completion_date",
        "revised_completion_date",
        "retention_percentage",
        "retention_cap_percentage",
        "payment_terms_days",
        "dlp_months",
        "liquidated_damages_rate",
        "letter_of_award",
    )


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0
    fields = ("name", "milestone_type", "target_date", "actual_date", "is_achieved")
    readonly_fields = ()


class VariationInline(admin.TabularInline):
    model = Variation
    extra = 0
    fields = ("ref_number", "variation_type", "status", "date_instructed", "amount")
    readonly_fields = ("ref_number",)


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0
    fields = ("user", "role", "can_edit", "can_approve", "is_active")
    raw_id_fields = ("user",)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "client_type", "contact_person", "email", "phone")
    list_filter = ("client_type",)
    search_fields = ("name", "contact_person", "email")
    ordering = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "client_type")}),
        (
            "Contact Information",
            {"fields": ("contact_person", "email", "phone", "address")},
        ),
    )


# ---------------------------------------------------------------------------
# Funder
# ---------------------------------------------------------------------------


@admin.register(Funder)
class FunderAdmin(admin.ModelAdmin):
    list_display = ("name", "funder_type", "contact_person", "email", "phone")
    list_filter = ("funder_type",)
    search_fields = ("name", "contact_person", "email")
    ordering = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "funder_type")}),
        (
            "Contact Information",
            {"fields": ("contact_person", "email", "phone")},
        ),
    )


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "project_id",
        "name",
        "project_type",
        "status",
        "client",
        "project_manager",
        "start_date",
        "target_completion_date",
    )
    list_filter = ("status", "project_type", "province")
    search_fields = (
        "project_id",
        "name",
        "province",
        "district",
        "client__name",
    )
    readonly_fields = ("project_id", "created_at", "updated_at")
    ordering = ("-created_at",)
    raw_id_fields = ("project_manager", "site_supervisor", "client", "funder")
    inlines = [ContractInline, MilestoneInline, VariationInline, ProjectMembershipInline]

    fieldsets = (
        (
            "Project Identification",
            {"fields": ("project_id", "name", "project_type", "status", "description")},
        ),
        (
            "Location",
            {
                "fields": (
                    "province",
                    "district",
                    "site_address",
                    "gps_lat",
                    "gps_lng",
                )
            },
        ),
        (
            "Key Personnel",
            {"fields": ("project_manager", "site_supervisor")},
        ),
        (
            "Client & Funder",
            {"fields": ("client", "funder")},
        ),
        (
            "Dates",
            {
                "fields": (
                    "start_date",
                    "target_completion_date",
                    "actual_completion_date",
                )
            },
        ),
        (
            "Media",
            {"fields": ("thumbnail",), "classes": ("collapse",)},
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "contract_number",
        "project",
        "contract_type",
        "original_value",
        "start_date",
        "original_completion_date",
    )
    list_filter = ("contract_type",)
    search_fields = (
        "contract_number",
        "project__name",
        "project__project_id",
    )
    ordering = ("-created_at",)
    raw_id_fields = ("project",)


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "can_edit", "can_approve", "is_active")
    list_filter = ("role", "can_edit", "can_approve", "is_active")
    search_fields = ("project__project_id", "project__name", "user__email", "user__first_name", "user__last_name")
    raw_id_fields = ("project", "user")


# ---------------------------------------------------------------------------
# Variation
# ---------------------------------------------------------------------------


@admin.register(Variation)
class VariationAdmin(admin.ModelAdmin):
    list_display = (
        "ref_number",
        "project",
        "variation_type",
        "status",
        "date_instructed",
        "amount",
    )
    list_filter = ("status", "variation_type", "project__status")
    search_fields = (
        "ref_number",
        "project__name",
        "project__project_id",
        "description",
    )
    readonly_fields = ("ref_number", "created_at", "updated_at")
    raw_id_fields = ("project",)
    ordering = ("project", "ref_number")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "project",
                    "ref_number",
                    "variation_type",
                    "status",
                    "date_instructed",
                    "amount",
                )
            },
        ),
        ("Details", {"fields": ("description", "supporting_document")}),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project",
        "milestone_type",
        "target_date",
        "actual_date",
        "is_achieved",
    )
    list_filter = ("milestone_type", "is_achieved", "project__status")
    search_fields = ("name", "project__name", "project__project_id", "description")
    raw_id_fields = ("project",)
    ordering = ("project", "target_date")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "project",
                    "name",
                    "milestone_type",
                    "description",
                )
            },
        ),
        (
            "Dates & Achievement",
            {"fields": ("target_date", "actual_date", "is_achieved", "evidence")},
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Delay Event
# ---------------------------------------------------------------------------


@admin.register(DelayEvent)
class DelayEventAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "date",
        "delay_type",
        "responsible_party",
        "impact_days",
    )
    list_filter = ("delay_type", "responsible_party", "project__status")
    search_fields = ("project__name", "project__project_id", "description")
    raw_id_fields = ("project", "linked_milestone")
    ordering = ("project", "-date")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "project",
                    "date",
                    "delay_type",
                    "responsible_party",
                    "impact_days",
                    "linked_milestone",
                )
            },
        ),
        ("Description", {"fields": ("description",)}),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")
