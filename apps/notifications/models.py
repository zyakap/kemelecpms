from django.conf import settings
from django.db import models
from django.urls import reverse


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------


class Notification(models.Model):
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    OVERDUE = "OVERDUE"
    MILESTONE_DUE = "MILESTONE_DUE"
    SUBMISSION = "SUBMISSION"
    PAYMENT = "PAYMENT"
    GENERAL = "GENERAL"

    NOTIFICATION_TYPE_CHOICES = [
        (APPROVAL_REQUIRED, "Approval Required"),
        (OVERDUE, "Overdue"),
        (MILESTONE_DUE, "Milestone Due"),
        (SUBMISSION, "Submission"),
        (PAYMENT, "Payment"),
        (GENERAL, "General"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=25,
        choices=NOTIFICATION_TYPE_CHOICES,
        default=GENERAL,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL to the relevant record (relative or absolute).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title} → {self.recipient}"

    def get_absolute_url(self):
        return reverse("notifications:notification-list")

    @property
    def icon_class(self):
        """Bootstrap icon class per notification type."""
        icon_map = {
            self.APPROVAL_REQUIRED: "bi-check-circle",
            self.OVERDUE: "bi-exclamation-triangle",
            self.MILESTONE_DUE: "bi-calendar-event",
            self.SUBMISSION: "bi-upload",
            self.PAYMENT: "bi-cash",
            self.GENERAL: "bi-bell",
        }
        return icon_map.get(self.notification_type, "bi-bell")


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class Task(models.Model):
    PRIORITY_LOW = "LOW"
    PRIORITY_MEDIUM = "MEDIUM"
    PRIORITY_HIGH = "HIGH"
    PRIORITY_URGENT = "URGENT"

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_URGENT, "Urgent"),
    ]

    STATUS_PENDING = "PENDING"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_tasks",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tasks",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    due_date = models.DateField()
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM,
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ["due_date", "-priority"]
        indexes = [
            models.Index(fields=["assigned_to", "status", "due_date"]),
        ]

    def __str__(self):
        return f"{self.title} → {self.assigned_to}"

    def get_absolute_url(self):
        return reverse("notifications:task-list")

    @property
    def is_overdue(self):
        if self.status in (self.STATUS_COMPLETED, self.STATUS_CANCELLED):
            return False
        from django.utils import timezone
        return self.due_date < timezone.now().date()

    @property
    def priority_colour(self):
        colour_map = {
            self.PRIORITY_LOW: "success",
            self.PRIORITY_MEDIUM: "info",
            self.PRIORITY_HIGH: "warning",
            self.PRIORITY_URGENT: "danger",
        }
        return colour_map.get(self.priority, "secondary")
