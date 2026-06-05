import secrets

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class PortalAccess(TimeStampedModel):
    TYPE_CLIENT = "CLIENT"
    TYPE_FUNDER = "FUNDER"
    TYPE_SUBCONTRACTOR = "SUBCONTRACTOR"
    TYPE_SUPPLIER = "SUPPLIER"

    TYPE_CHOICES = [
        (TYPE_CLIENT, "Client"),
        (TYPE_FUNDER, "Funder"),
        (TYPE_SUBCONTRACTOR, "Subcontractor"),
        (TYPE_SUPPLIER, "Supplier"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="portal_access_records")
    portal_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    organisation = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField()
    access_token = models.CharField(max_length=64, unique=True, editable=False)
    can_view_reports = models.BooleanField(default=True)
    can_view_documents = models.BooleanField(default=True)
    can_submit_claims = models.BooleanField(default=False)
    can_submit_deliveries = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["project", "portal_type", "organisation"]

    def save(self, *args, **kwargs):
        if not self.access_token:
            self.access_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_portal_type_display()} - {self.organisation}"


class SyncConflict(TimeStampedModel):
    STATUS_OPEN = "OPEN"
    STATUS_RESOLVED_CLIENT = "RESOLVED_CLIENT"
    STATUS_RESOLVED_SERVER = "RESOLVED_SERVER"
    STATUS_MERGED = "MERGED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_RESOLVED_CLIENT, "Resolved using client"),
        (STATUS_RESOLVED_SERVER, "Resolved using server"),
        (STATUS_MERGED, "Merged"),
    ]

    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    device_id = models.CharField(max_length=120, blank=True)
    model_name = models.CharField(max_length=120)
    object_reference = models.CharField(max_length=120, blank=True)
    client_payload = models.JSONField(default=dict, blank=True)
    server_payload = models.JSONField(default=dict, blank=True)
    resolution_notes = models.TextField(blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_OPEN)

    class Meta:
        ordering = ["-created_at"]


class BoQImportBatch(TimeStampedModel):
    STATUS_UPLOADED = "UPLOADED"
    STATUS_VALIDATED = "VALIDATED"
    STATUS_IMPORTED = "IMPORTED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_UPLOADED, "Uploaded"),
        (STATUS_VALIDATED, "Validated"),
        (STATUS_IMPORTED, "Imported"),
        (STATUS_REJECTED, "Rejected"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="boq_import_batches")
    revision = models.CharField(max_length=30)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    source_file = models.FileField(upload_to="boq/imports/")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_UPLOADED)
    validation_summary = models.TextField(blank=True)
    rows_total = models.PositiveIntegerField(default=0)
    rows_valid = models.PositiveIntegerField(default=0)
    rows_rejected = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["project", "-created_at"]
        unique_together = [("project", "revision")]


class ScheduledExport(TimeStampedModel):
    FREQ_WEEKLY = "WEEKLY"
    FREQ_MONTHLY = "MONTHLY"
    FREQ_QUARTERLY = "QUARTERLY"

    FREQUENCY_CHOICES = [
        (FREQ_WEEKLY, "Weekly"),
        (FREQ_MONTHLY, "Monthly"),
        (FREQ_QUARTERLY, "Quarterly"),
    ]

    REPORT_CHOICES = [
        ("EXECUTIVE_PACK", "Executive Pack"),
        ("PORTFOLIO", "Portfolio Report"),
        ("PROJECT_MONTHLY", "Project Monthly Report"),
        ("ACCOUNTING", "Accounting Export"),
        ("SAFETY", "Safety Export"),
    ]

    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=180)
    report_type = models.CharField(max_length=30, choices=REPORT_CHOICES)
    frequency = models.CharField(max_length=15, choices=FREQUENCY_CHOICES, default=FREQ_MONTHLY)
    recipients = models.TextField(help_text="Comma-separated email recipients.")
    next_run = models.DateField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["next_run", "name"]


class IntegrationExportLog(TimeStampedModel):
    TYPE_ACCOUNTING = "ACCOUNTING"
    TYPE_PAYROLL = "PAYROLL"
    TYPE_INVENTORY = "INVENTORY"

    TYPE_CHOICES = [
        (TYPE_ACCOUNTING, "Accounting"),
        (TYPE_PAYROLL, "Payroll"),
        (TYPE_INVENTORY, "Inventory"),
    ]

    STATUS_READY = "READY"
    STATUS_SENT = "SENT"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_READY, "Ready"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL)
    export_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_READY)
    external_reference = models.CharField(max_length=120, blank=True)
    exported_file = models.FileField(upload_to="integrations/exports/", null=True, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class BackupRun(TimeStampedModel):
    STATUS_STARTED = "STARTED"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_STARTED, "Started"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_STARTED)
    storage_location = models.CharField(max_length=255, blank=True)
    size_mb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]


class ProductionReadinessItem(TimeStampedModel):
    AREA_SECURITY = "SECURITY"
    AREA_BACKUP = "BACKUP"
    AREA_MONITORING = "MONITORING"
    AREA_AUDIT = "AUDIT"
    AREA_PERFORMANCE = "PERFORMANCE"
    AREA_OPERATIONS = "OPERATIONS"

    AREA_CHOICES = [
        (AREA_SECURITY, "Security"),
        (AREA_BACKUP, "Backup"),
        (AREA_MONITORING, "Monitoring"),
        (AREA_AUDIT, "Audit"),
        (AREA_PERFORMANCE, "Performance"),
        (AREA_OPERATIONS, "Operations"),
    ]

    area = models.CharField(max_length=20, choices=AREA_CHOICES)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    is_complete = models.BooleanField(default=False)
    evidence = models.FileField(upload_to="readiness/evidence/", null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["area", "title"]
