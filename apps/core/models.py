from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    System-wide audit trail. Record critical user actions for security
    compliance and debugging. Use AuditLog.log() for all writes.
    """

    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_LOGIN = "LOGIN"
    ACTION_LOGOUT = "LOGOUT"
    ACTION_SUBMIT = "SUBMIT"
    ACTION_APPROVE = "APPROVE"
    ACTION_REJECT = "REJECT"
    ACTION_EXPORT = "EXPORT"

    ACTION_CHOICES = [
        (ACTION_CREATE, "Created"),
        (ACTION_UPDATE, "Updated"),
        (ACTION_DELETE, "Deleted"),
        (ACTION_LOGIN, "Logged In"),
        (ACTION_LOGOUT, "Logged Out"),
        (ACTION_SUBMIT, "Submitted"),
        (ACTION_APPROVE, "Approved"),
        (ACTION_REJECT, "Rejected"),
        (ACTION_EXPORT, "Exported"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=50, blank=True, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]

    def __str__(self):
        user_str = str(self.user) if self.user else "anonymous"
        return f"{self.timestamp:%Y-%m-%d %H:%M} — {user_str} {self.action} {self.model_name}"

    @classmethod
    def log(cls, user, action, obj=None, changes="", request=None, model_name="", object_repr=""):
        ip = None
        if request:
            x_fwd = request.META.get("HTTP_X_FORWARDED_FOR")
            ip = x_fwd.split(",")[0].strip() if x_fwd else request.META.get("REMOTE_ADDR")
        cls.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            model_name=obj.__class__.__name__ if obj else model_name,
            object_id=str(obj.pk) if obj else "",
            object_repr=str(obj)[:255] if obj else object_repr,
            changes=changes,
            ip_address=ip,
        )


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True
