from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Asset(TimeStampedModel):
    CATEGORY_BUILDING = "BUILDING"
    CATEGORY_PLANT = "PLANT"
    CATEGORY_ELECTRICAL = "ELECTRICAL"
    CATEGORY_MECHANICAL = "MECHANICAL"
    CATEGORY_VEHICLE = "VEHICLE"
    CATEGORY_OTHER = "OTHER"

    CATEGORY_CHOICES = [
        (CATEGORY_BUILDING, "Building / Facility"),
        (CATEGORY_PLANT, "Plant"),
        (CATEGORY_ELECTRICAL, "Electrical"),
        (CATEGORY_MECHANICAL, "Mechanical"),
        (CATEGORY_VEHICLE, "Vehicle"),
        (CATEGORY_OTHER, "Other"),
    ]

    STATUS_ACTIVE = "ACTIVE"
    STATUS_OUT_OF_SERVICE = "OUT_OF_SERVICE"
    STATUS_RETIRED = "RETIRED"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_OUT_OF_SERVICE, "Out of Service"),
        (STATUS_RETIRED, "Retired"),
    ]

    CRITICALITY_LOW = "LOW"
    CRITICALITY_MEDIUM = "MEDIUM"
    CRITICALITY_HIGH = "HIGH"
    CRITICALITY_CHOICES = [
        (CRITICALITY_LOW, "Low"),
        (CRITICALITY_MEDIUM, "Medium"),
        (CRITICALITY_HIGH, "High"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="maintenance_assets",
    )
    asset_code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    location = models.CharField(max_length=255, blank=True)
    make_model = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    installed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    criticality = models.CharField(max_length=10, choices=CRITICALITY_CHOICES, default=CRITICALITY_MEDIUM)
    service_interval_days = models.PositiveIntegerField(default=30)
    last_service_date = models.DateField(null=True, blank=True)
    next_service_due = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["asset_code"]
        unique_together = [("project", "asset_code")]

    def __str__(self):
        return f"{self.asset_code} - {self.name}"

    def get_absolute_url(self):
        return reverse("maintenance:asset-detail", kwargs={"project_pk": self.project_id, "pk": self.pk})

    @property
    def is_service_due(self):
        return bool(self.next_service_due and self.next_service_due <= timezone.now().date())


class WorkOrder(TimeStampedModel):
    TYPE_PREVENTIVE = "PREVENTIVE"
    TYPE_BREAKDOWN = "BREAKDOWN"
    TYPE_CORRECTIVE = "CORRECTIVE"
    TYPE_INSPECTION = "INSPECTION"

    TYPE_CHOICES = [
        (TYPE_PREVENTIVE, "Preventive Maintenance"),
        (TYPE_BREAKDOWN, "Breakdown"),
        (TYPE_CORRECTIVE, "Corrective"),
        (TYPE_INSPECTION, "Inspection"),
    ]

    PRIORITY_LOW = "LOW"
    PRIORITY_MEDIUM = "MEDIUM"
    PRIORITY_HIGH = "HIGH"
    PRIORITY_CRITICAL = "CRITICAL"

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_CRITICAL, "Critical"),
    ]

    STATUS_OPEN = "OPEN"
    STATUS_ASSIGNED = "ASSIGNED"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_SIGNED_OFF = "SIGNED_OFF"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_ASSIGNED, "Assigned"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_SIGNED_OFF, "Signed Off"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="maintenance_work_orders",
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="work_orders",
    )
    work_order_number = models.CharField(max_length=30, editable=False, db_index=True)
    work_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_CORRECTIVE)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    title = models.CharField(max_length=255)
    description = models.TextField()
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="maintenance_work_orders_requested",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_work_orders_assigned",
    )
    requested_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    sla_response_hours = models.PositiveIntegerField(default=24)
    responded_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    signed_off_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_work_orders_signed_off",
    )
    signed_off_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    completion_notes = models.TextField(blank=True)
    labour_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    parts_used = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_date", "-created_at"]
        unique_together = [("project", "work_order_number")]

    def __str__(self):
        return f"{self.work_order_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.work_order_number:
            count = WorkOrder.objects.filter(project=self.project).count() + 1
            self.work_order_number = f"WO-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("maintenance:workorder-detail", kwargs={"project_pk": self.project_id, "pk": self.pk})

    @property
    def is_breakdown(self):
        return self.work_type == self.TYPE_BREAKDOWN

    @property
    def is_signed_off(self):
        return self.status == self.STATUS_SIGNED_OFF

    @property
    def wo_number(self):
        return self.work_order_number

    @property
    def is_overdue(self):
        if self.status in (self.STATUS_COMPLETED, self.STATUS_SIGNED_OFF, self.STATUS_CANCELLED):
            return False
        return bool(self.due_date and self.due_date < timezone.now().date())


class PreventiveMaintenanceSchedule(TimeStampedModel):
    FREQUENCY_DAILY = "DAILY"
    FREQUENCY_WEEKLY = "WEEKLY"
    FREQUENCY_MONTHLY = "MONTHLY"
    FREQUENCY_QUARTERLY = "QUARTERLY"
    FREQUENCY_ANNUAL = "ANNUAL"

    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, "Daily"),
        (FREQUENCY_WEEKLY, "Weekly"),
        (FREQUENCY_MONTHLY, "Monthly"),
        (FREQUENCY_QUARTERLY, "Quarterly"),
        (FREQUENCY_ANNUAL, "Annual"),
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="preventive_schedules",
    )
    title = models.CharField(max_length=255)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    next_due_date = models.DateField()
    checklist = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["next_due_date", "asset__asset_code"]

    def __str__(self):
        return f"{self.asset} - {self.title}"


class ServiceRecord(TimeStampedModel):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="service_records",
    )
    service_date = models.DateField()
    technician = models.CharField(max_length=150)
    work_performed = models.TextField()
    downtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    document = models.FileField(upload_to="maintenance/service_records/", null=True, blank=True)

    class Meta:
        ordering = ["-service_date"]

    def __str__(self):
        return f"{self.work_order.work_order_number} service {self.service_date}"


class SparePartUsage(TimeStampedModel):
    service_record = models.ForeignKey(
        ServiceRecord,
        on_delete=models.CASCADE,
        related_name="spares_used",
    )
    material = models.ForeignKey(
        "procurement.Material",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_spare_usages",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["description"]

    def __str__(self):
        return f"{self.description} x {self.quantity}"

    @property
    def total_cost(self):
        return (self.quantity * self.unit_cost).quantize(Decimal("0.01"))


class BreakdownTicket(TimeStampedModel):
    STATUS_OPEN = "OPEN"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="breakdown_tickets",
    )
    work_order = models.OneToOneField(
        WorkOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="breakdown_ticket",
    )
    reported_at = models.DateTimeField(default=timezone.now)
    restored_at = models.DateTimeField(null=True, blank=True)
    cause = models.TextField(blank=True)
    operational_impact = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    class Meta:
        ordering = ["-reported_at"]

    def __str__(self):
        return f"{self.asset.asset_code} breakdown {self.reported_at:%Y-%m-%d}"

    @property
    def downtime_hours(self):
        if not self.restored_at:
            return None
        return round((self.restored_at - self.reported_at).total_seconds() / 3600, 2)


class SparePart(TimeStampedModel):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="maintenance_spares",
    )
    asset = models.ForeignKey(
        Asset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="spare_parts",
    )
    part_number = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    quantity_on_hand = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    minimum_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["part_number"]
        unique_together = [("project", "part_number")]

    def __str__(self):
        return f"{self.part_number} - {self.description}"

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.minimum_quantity
