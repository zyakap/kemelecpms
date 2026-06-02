from django.contrib import admin
from django.utils.html import format_html

from .models import Notification, Task


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient",
        "notification_type",
        "is_read",
        "created_at",
        "link",
    )
    list_filter = ("notification_type", "is_read", "recipient")
    search_fields = ("title", "message", "recipient__email", "recipient__first_name")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
    actions = ["mark_read", "mark_unread"]

    @admin.action(description="Mark selected notifications as read")
    def mark_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f"{count} notification(s) marked as read.")

    @admin.action(description="Mark selected notifications as unread")
    def mark_unread(self, request, queryset):
        count = queryset.update(is_read=False)
        self.message_user(request, f"{count} notification(s) marked as unread.")


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "assigned_to",
        "assigned_by",
        "project",
        "due_date",
        "priority_badge",
        "status_badge",
        "is_overdue_display",
    )
    list_filter = ("priority", "status", "project")
    search_fields = ("title", "description", "assigned_to__email", "assigned_to__first_name")
    date_hierarchy = "due_date"
    readonly_fields = ("created_at", "updated_at", "completed_at")
    autocomplete_fields = ["assigned_to", "assigned_by"]

    @admin.display(description="Priority")
    def priority_badge(self, obj):
        colour_map = {
            Task.PRIORITY_LOW: "#28a745",
            Task.PRIORITY_MEDIUM: "#17a2b8",
            Task.PRIORITY_HIGH: "#fd7e14",
            Task.PRIORITY_URGENT: "#dc3545",
        }
        colour = colour_map.get(obj.priority, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_priority_display(),
        )

    @admin.display(description="Status")
    def status_badge(self, obj):
        colour_map = {
            Task.STATUS_PENDING: "#6c757d",
            Task.STATUS_IN_PROGRESS: "#007bff",
            Task.STATUS_COMPLETED: "#28a745",
            Task.STATUS_CANCELLED: "#dc3545",
        }
        colour = colour_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.display(description="Overdue", boolean=True)
    def is_overdue_display(self, obj):
        return obj.is_overdue
