"""
Daily Site Report (DSR) models for kemelecpms.

Covers the full DSR workflow: header, activities, labour, visitors,
equipment usage, material deliveries, material usage, photos, and issues.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# Weather / status choices (module-level for reuse)
# ---------------------------------------------------------------------------

WEATHER_SUNNY = "SUNNY"
WEATHER_PARTLY_CLOUDY = "PARTLY_CLOUDY"
WEATHER_OVERCAST = "OVERCAST"
WEATHER_LIGHT_RAIN = "LIGHT_RAIN"
WEATHER_HEAVY_RAIN = "HEAVY_RAIN"
WEATHER_STORM = "STORM"

WEATHER_CHOICES = [
    (WEATHER_SUNNY, "Sunny"),
    (WEATHER_PARTLY_CLOUDY, "Partly Cloudy"),
    (WEATHER_OVERCAST, "Overcast"),
    (WEATHER_LIGHT_RAIN, "Light Rain"),
    (WEATHER_HEAVY_RAIN, "Heavy Rain"),
    (WEATHER_STORM, "Storm / Severe Weather"),
]


# ---------------------------------------------------------------------------
# DailySiteReport
# ---------------------------------------------------------------------------


class DailySiteReport(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_RETURNED = "RETURNED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_RETURNED, "Returned for Revision"),
    ]

    dsr_number = models.CharField(
        max_length=30, unique=True, editable=False, db_index=True
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="daily_site_reports",
    )
    date = models.DateField(db_index=True)
    day_number = models.IntegerField(
        default=1,
        verbose_name="Day Number from Project Start",
        help_text="Automatically calculated from project start date.",
    )
    weather_am = models.CharField(
        max_length=20, choices=WEATHER_CHOICES, default=WEATHER_SUNNY,
        verbose_name="Weather (AM)"
    )
    weather_pm = models.CharField(
        max_length=20, choices=WEATHER_CHOICES, default=WEATHER_SUNNY,
        verbose_name="Weather (PM)"
    )
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dsrs_prepared",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsrs_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    return_reason = models.TextField(blank=True)
    is_locked = models.BooleanField(
        default=False,
        help_text="Locked DSRs cannot be edited. Set automatically on approval.",
    )
    pdf_file = models.FileField(
        upload_to="dsr_pdfs/", null=True, blank=True, verbose_name="Generated PDF"
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Daily Site Report"
        verbose_name_plural = "Daily Site Reports"
        ordering = ["-date", "-dsr_number"]
        unique_together = [("project", "date")]

    def __str__(self):
        return f"{self.dsr_number} – {self.project} ({self.date})"

    def save(self, *args, **kwargs):
        if not self.dsr_number:
            # Format: DSR-{project_pk}-{sequence padded to 4}
            seq = (
                DailySiteReport.objects.filter(project=self.project).count() + 1
            )
            self.dsr_number = f"DSR-{self.project_id}-{seq:04d}"
        if not self.day_number or self.day_number == 1:
            project = self.project
            if project.start_date and self.date:
                self.day_number = (self.date - project.start_date).days + 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("dsr:dsr_detail", kwargs={"pk": self.pk})

    @property
    def can_edit(self):
        return not self.is_locked and self.status in (
            self.STATUS_DRAFT,
            self.STATUS_RETURNED,
        )


# ---------------------------------------------------------------------------
# DSRActivity
# ---------------------------------------------------------------------------


class DSRActivity(TimeStampedModel):
    STATUS_COMPLETED = "COMPLETED"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_NOT_STARTED = "NOT_STARTED"

    STATUS_CHOICES = [
        (STATUS_COMPLETED, "Completed"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_NOT_STARTED, "Not Started"),
    ]

    dsr = models.ForeignKey(
        DailySiteReport, on_delete=models.CASCADE, related_name="activities"
    )
    wbs_activity = models.ForeignKey(
        "schedule.WBSActivity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_activities",
    )
    schedule_activity = models.ForeignKey(
        "schedule.Activity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_activity_evidence",
        help_text="Schedule activity supported by this DSR progress entry.",
    )
    ipc_line_item = models.ForeignKey(
        "ipc.IPCLineItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_activity_evidence",
        help_text="IPC line item supported by this DSR evidence.",
    )
    description = models.CharField(max_length=500)
    location_on_site = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS
    )
    quantity_achieved = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    unit = models.CharField(max_length=30, blank=True)
    percent_complete = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Cumulative % Complete",
    )
    constraints = models.TextField(
        blank=True,
        help_text="For NOT_STARTED status: explain reason / constraint.",
    )
    crew = models.ForeignKey(
        "resources.Crew",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_activities",
    )

    class Meta:
        verbose_name = "DSR Activity"
        verbose_name_plural = "DSR Activities"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.dsr.dsr_number} – {self.description[:60]}"


# ---------------------------------------------------------------------------
# DSRLabour
# ---------------------------------------------------------------------------


class DSRLabour(TimeStampedModel):
    NATIONALITY_PNG = "PNG"
    NATIONALITY_EXPAT = "EXPAT"

    NATIONALITY_CHOICES = [
        (NATIONALITY_PNG, "PNG National"),
        (NATIONALITY_EXPAT, "Expatriate"),
    ]

    dsr = models.ForeignKey(
        DailySiteReport, on_delete=models.CASCADE, related_name="labour_records"
    )
    classification = models.CharField(
        max_length=100,
        help_text="e.g. Labourer, Carpenter, Electrician, Operator, Supervisor",
    )
    nationality = models.CharField(
        max_length=10, choices=NATIONALITY_CHOICES, default=NATIONALITY_PNG
    )
    count = models.IntegerField(default=0)

    class Meta:
        verbose_name = "DSR Labour Record"
        verbose_name_plural = "DSR Labour Records"
        ordering = ["classification", "nationality"]

    def __str__(self):
        return f"{self.dsr.dsr_number} – {self.classification} ({self.nationality}) x{self.count}"


# ---------------------------------------------------------------------------
# DSRVisitor
# ---------------------------------------------------------------------------


class DSRVisitor(TimeStampedModel):
    dsr = models.ForeignKey(
        DailySiteReport, on_delete=models.CASCADE, related_name="visitors"
    )
    name = models.CharField(max_length=150)
    organization = models.CharField(max_length=150)
    purpose = models.CharField(max_length=255)
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name = "DSR Visitor"
        verbose_name_plural = "DSR Visitors"
        ordering = ["time_in"]

    def __str__(self):
        return f"{self.name} ({self.organization}) – {self.dsr.dsr_number}"


# ---------------------------------------------------------------------------
# DSREquipment
# ---------------------------------------------------------------------------


class DSREquipment(TimeStampedModel):
    dsr = models.ForeignKey(
        DailySiteReport, on_delete=models.CASCADE, related_name="equipment_records"
    )
    equipment = models.ForeignKey(
        "resources.Equipment",
        on_delete=models.PROTECT,
        related_name="dsr_records",
    )
    hours_worked = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    hours_idle = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    hours_breakdown = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "DSR Equipment Record"
        verbose_name_plural = "DSR Equipment Records"
        ordering = ["equipment"]

    def __str__(self):
        return f"{self.dsr.dsr_number} – {self.equipment}"

    @property
    def total_hours(self):
        return self.hours_worked + self.hours_idle + self.hours_breakdown

    @property
    def utilisation_pct(self):
        total = self.total_hours
        if total > 0:
            return round((self.hours_worked / total) * 100, 1)
        return 0


# ---------------------------------------------------------------------------
# DSRMaterialDelivery
# ---------------------------------------------------------------------------


class DSRMaterialDelivery(TimeStampedModel):
    dsr = models.ForeignKey(
        DailySiteReport, on_delete=models.CASCADE, related_name="material_deliveries"
    )
    grn = models.ForeignKey(
        "procurement.GoodsReceivedNote",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_deliveries",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    unit = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "DSR Material Delivery"
        verbose_name_plural = "DSR Material Deliveries"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.dsr.dsr_number} – {self.description}"


# ---------------------------------------------------------------------------
# DSRMaterialUsage
# ---------------------------------------------------------------------------


class DSRMaterialUsage(TimeStampedModel):
    dsr = models.ForeignKey(
        DailySiteReport, on_delete=models.CASCADE, related_name="material_usages"
    )
    material = models.ForeignKey(
        "procurement.Material",
        on_delete=models.PROTECT,
        related_name="dsr_usages",
    )
    quantity_used = models.DecimalField(max_digits=10, decimal_places=3)
    stock_ledger_entry = models.ForeignKey(
        "procurement.StockLedger",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_usage_evidence",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "DSR Material Usage"
        verbose_name_plural = "DSR Material Usages"
        ordering = ["material"]

    def __str__(self):
        return f"{self.dsr.dsr_number} – {self.material.item_code} x{self.quantity_used}"


# ---------------------------------------------------------------------------
# DSRPhoto
# ---------------------------------------------------------------------------


class DSRPhoto(TimeStampedModel):
    TAG_ACTIVITY = "ACTIVITY"
    TAG_AREA = "AREA"
    TAG_EQUIPMENT = "EQUIPMENT"
    TAG_DEFECT = "DEFECT"
    TAG_SAFETY = "SAFETY"
    TAG_PROGRESS = "PROGRESS"
    TAG_OTHER = "OTHER"

    TAG_CHOICES = [
        (TAG_ACTIVITY, "Activity"),
        (TAG_AREA, "Site Area"),
        (TAG_EQUIPMENT, "Equipment"),
        (TAG_DEFECT, "Defect"),
        (TAG_SAFETY, "Safety"),
        (TAG_PROGRESS, "Progress"),
        (TAG_OTHER, "Other"),
    ]

    dsr = models.ForeignKey(
        DailySiteReport, on_delete=models.CASCADE, related_name="photos"
    )
    photo = models.ImageField(upload_to="dsr_photos/")
    caption = models.CharField(max_length=255, blank=True)
    tag = models.CharField(
        max_length=20, choices=TAG_CHOICES, default=TAG_PROGRESS
    )
    wbs_activity = models.ForeignKey(
        "schedule.WBSActivity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_photo_evidence",
    )
    schedule_activity = models.ForeignKey(
        "schedule.Activity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_photo_evidence",
    )
    rfi = models.ForeignKey(
        "documents.RFI",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_photo_evidence",
    )
    ncr = models.ForeignKey(
        "quality.NCR",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_photo_evidence",
    )
    defect = models.ForeignKey(
        "quality.Defect",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_photo_evidence",
    )
    incident = models.ForeignKey(
        "safety.Incident",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_photo_evidence",
    )
    gps_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS Latitude"
    )
    gps_lng = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="GPS Longitude"
    )
    taken_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "DSR Photo"
        verbose_name_plural = "DSR Photos"
        ordering = ["taken_at"]

    def __str__(self):
        return f"{self.dsr.dsr_number} – {self.get_tag_display()} photo"


# ---------------------------------------------------------------------------
# DSRIssue
# ---------------------------------------------------------------------------


class DSRIssue(TimeStampedModel):
    ISSUE_INSTRUCTION = "INSTRUCTION"
    ISSUE_RFI = "RFI"
    ISSUE_MATERIAL_DELAY = "MATERIAL_DELAY"
    ISSUE_DESIGN = "DESIGN"
    ISSUE_ACCESS = "ACCESS"
    ISSUE_OTHER = "OTHER"

    ISSUE_TYPE_CHOICES = [
        (ISSUE_INSTRUCTION, "Site Instruction"),
        (ISSUE_RFI, "Request for Information (RFI)"),
        (ISSUE_MATERIAL_DELAY, "Material Delay"),
        (ISSUE_DESIGN, "Design / Drawing Issue"),
        (ISSUE_ACCESS, "Access / Clearance"),
        (ISSUE_OTHER, "Other"),
    ]

    dsr = models.ForeignKey(
        DailySiteReport, on_delete=models.CASCADE, related_name="issues"
    )
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES)
    description = models.TextField()
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dsr_issues_raised",
    )
    date = models.DateField()
    action_required = models.TextField(blank=True)
    rfi = models.ForeignKey(
        "documents.RFI",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_issue_evidence",
    )
    ncr = models.ForeignKey(
        "quality.NCR",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_issue_evidence",
    )
    incident = models.ForeignKey(
        "safety.Incident",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_issue_evidence",
    )
    delay_event = models.ForeignKey(
        "projects.DelayEvent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dsr_issue_evidence",
    )
    resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "DSR Issue"
        verbose_name_plural = "DSR Issues"
        ordering = ["-date", "issue_type"]

    def __str__(self):
        return (
            f"{self.dsr.dsr_number} – {self.get_issue_type_display()}: "
            f"{self.description[:60]}"
        )
