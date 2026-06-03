from django.contrib import admin
from django.utils.html import format_html

from .models import Certification, IPC, IPCLineItem, Payment, RetentionRelease


# ---------------------------------------------------------------------------
# IPC
# ---------------------------------------------------------------------------


class IPCLineItemInline(admin.TabularInline):
    model = IPCLineItem
    fields = (
        "boq_item",
        "boq_description",
        "boq_quantity",
        "unit_rate",
        "previous_percent",
        "current_percent",
    )
    extra = 0
    autocomplete_fields = ["boq_item"]


class CertificationInline(admin.StackedInline):
    model = Certification
    fields = (
        "certified_by",
        "certifier_org",
        "certified_date",
        "amount_certified",
        "retention_deducted",
        "net_certified",
        "disputed_items",
        "notes",
    )
    extra = 0
    max_num = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    fields = ("payment_date", "amount", "payment_reference", "received_by", "notes")
    extra = 0


@admin.register(IPC)
class IPCAdmin(admin.ModelAdmin):
    list_display = (
        "ipc_number",
        "project",
        "claim_period_from",
        "claim_period_to",
        "submitted_date",
        "status_badge",
        "total_claimed_display",
        "amount_certified_display",
        "amount_paid_display",
    )
    list_filter = ("project", "status")
    search_fields = ("ipc_number", "project__name", "project__project_id")
    readonly_fields = ("ipc_number",)
    inlines = [IPCLineItemInline, CertificationInline, PaymentInline]

    @admin.display(description="Status")
    def status_badge(self, obj):
        colour_map = {
            IPC.STATUS_DRAFT: "#6c757d",
            IPC.STATUS_INTERNAL_REVIEW: "#17a2b8",
            IPC.STATUS_SUBMITTED: "#007bff",
            IPC.STATUS_CERTIFIED: "#28a745",
            IPC.STATUS_DISPUTED: "#dc3545",
            IPC.STATUS_PAID: "#6f42c1",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.display(description="Claimed")
    def total_claimed_display(self, obj):
        return f"K {obj.total_claimed:,.2f}"

    @admin.display(description="Certified")
    def amount_certified_display(self, obj):
        return f"K {obj.amount_certified:,.2f}"

    @admin.display(description="Paid")
    def amount_paid_display(self, obj):
        return f"K {obj.amount_paid:,.2f}"


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = (
        "ipc",
        "certified_by",
        "certifier_org",
        "certified_date",
        "amount_certified",
        "retention_deducted",
        "net_certified",
    )
    list_filter = ("ipc__project",)
    search_fields = ("certified_by", "certifier_org", "ipc__ipc_number")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "ipc",
        "payment_date",
        "amount",
        "payment_reference",
        "received_by",
    )
    list_filter = ("ipc__project",)
    search_fields = ("payment_reference", "ipc__ipc_number")
    date_hierarchy = "payment_date"


@admin.register(RetentionRelease)
class RetentionReleaseAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "release_type",
        "amount",
        "release_date",
        "approved_by",
    )
    list_filter = ("project", "release_type")
    date_hierarchy = "release_date"
