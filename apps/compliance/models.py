"""
Compliance & Funder Reporting models.

Covers: OTML TCS reports, IRC Tax Invoices, Compliance Calendar entries,
and PNG local content tracking.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.projects.models import Funder


# ---------------------------------------------------------------------------
# OTML TCS Report
# ---------------------------------------------------------------------------


class OTMLTCSReport(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_ACCEPTED = "ACCEPTED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted to OTML"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected / Revision Required"),
    ]

    PERIOD_MONTHLY = "MONTHLY"
    PERIOD_QUARTERLY = "QUARTERLY"
    PERIOD_MILESTONE = "MILESTONE"

    PERIOD_CHOICES = [
        (PERIOD_MONTHLY, "Monthly"),
        (PERIOD_QUARTERLY, "Quarterly"),
        (PERIOD_MILESTONE, "Milestone"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="otml_tcs_reports",
    )
    report_number = models.CharField(max_length=30, db_index=True)
    period_type = models.CharField(max_length=15, choices=PERIOD_CHOICES, default=PERIOD_MONTHLY)
    period_from = models.DateField()
    period_to = models.DateField()
    submission_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # Expenditure data
    total_tcs_budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expenditure_to_date = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expenditure_this_period = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Physical progress
    overall_progress_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="Overall Physical Progress (%)",
    )
    narrative = models.TextField(blank=True, verbose_name="Progress Narrative")
    issues_risks = models.TextField(blank=True, verbose_name="Issues & Risks")

    # PNG Local Content
    local_labour_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="Local Labour % (PNG)",
    )
    expat_labour_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="Expatriate Labour %",
    )
    local_materials_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="Local Materials % (PNG-sourced)",
    )

    # Attachment (completed report PDF)
    attachment = models.FileField(upload_to="compliance/tcs/", blank=True, null=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tcs_reports_submitted",
    )
    reviewer_comments = models.TextField(blank=True)

    class Meta:
        verbose_name = "OTML TCS Report"
        verbose_name_plural = "OTML TCS Reports"
        ordering = ["project", "-period_to"]
        unique_together = [("project", "report_number")]

    def __str__(self):
        return f"{self.report_number} — {self.project.project_id}"

    def save(self, *args, **kwargs):
        if not self.report_number:
            count = OTMLTCSReport.objects.filter(project=self.project).count() + 1
            self.report_number = f"TCS-{self.project.project_id}-{count:03d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("compliance:tcs-detail", kwargs={"project_pk": self.project_id, "pk": self.pk})

    @property
    def remaining_tcs_budget(self):
        return self.total_tcs_budget - self.expenditure_to_date


# ---------------------------------------------------------------------------
# IRC Tax Invoice
# ---------------------------------------------------------------------------


class IRCTaxInvoice(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_ISSUED = "ISSUED"
    STATUS_PAID = "PAID"
    STATUS_VOID = "VOID"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ISSUED, "Issued"),
        (STATUS_PAID, "Paid"),
        (STATUS_VOID, "Void"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="tax_invoices",
    )
    ipc = models.ForeignKey(
        "ipc.IPC",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tax_invoices",
        verbose_name="Linked IPC",
    )
    invoice_number = models.CharField(max_length=30, db_index=True)
    invoice_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # Kemele details (auto-filled from settings / project)
    kemele_tinpng = models.CharField(max_length=30, blank=True, verbose_name="Kemele TINPNG")
    kemele_gst_number = models.CharField(max_length=30, blank=True, verbose_name="Kemele GST No.")

    # Client / recipient details
    client_name = models.CharField(max_length=255)
    client_address = models.TextField(blank=True)
    client_tinpng = models.CharField(max_length=30, blank=True, verbose_name="Client TINPNG")

    # Amounts
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.10"), verbose_name="GST Rate")
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    description = models.TextField(help_text="Description of works / services for this invoice")
    payment_terms = models.CharField(max_length=100, default="Net 30 days", blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    sequence_number = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tax_invoices_voided",
    )
    voided_at = models.DateTimeField(null=True, blank=True)
    exported_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "IRC Tax Invoice"
        verbose_name_plural = "IRC Tax Invoices"
        ordering = ["project", "-invoice_date"]
        unique_together = [("project", "invoice_number")]

    def __str__(self):
        return f"{self.invoice_number} — {self.project.project_id}"

    def save(self, *args, **kwargs):
        if not self.sequence_number:
            last = (
                IRCTaxInvoice.objects.filter(project=self.project)
                .exclude(sequence_number__isnull=True)
                .order_by("-sequence_number")
                .values_list("sequence_number", flat=True)
                .first()
                or 0
            )
            self.sequence_number = last + 1
        if not self.invoice_number:
            self.invoice_number = f"INV-{self.project.project_id}-{self.sequence_number:04d}"
        if self.status == self.STATUS_ISSUED and not self.issued_at:
            self.issued_at = timezone.now()
        # Auto-calculate GST and total
        self.gst_amount = Decimal(self.subtotal) * Decimal(self.gst_rate)
        self.total_amount = Decimal(self.subtotal) + self.gst_amount
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("compliance:invoice-detail", kwargs={"project_pk": self.project_id, "pk": self.pk})

    def void(self, *, user, reason):
        self.status = self.STATUS_VOID
        self.void_reason = reason
        self.voided_by = user
        self.voided_at = timezone.now()
        self.save(update_fields=["status", "void_reason", "voided_by", "voided_at", "updated_at"])


class PublicProcurementRecord(TimeStampedModel):
    METHOD_OPEN_TENDER = "OPEN_TENDER"
    METHOD_SELECT_TENDER = "SELECT_TENDER"
    METHOD_RFQ = "RFQ"
    METHOD_SOLE_SOURCE = "SOLE_SOURCE"

    METHOD_CHOICES = [
        (METHOD_OPEN_TENDER, "Open Tender"),
        (METHOD_SELECT_TENDER, "Selective Tender"),
        (METHOD_RFQ, "Request for Quotation"),
        (METHOD_SOLE_SOURCE, "Sole Source / Direct Award"),
    ]

    STATUS_DRAFT = "DRAFT"
    STATUS_UNDER_REVIEW = "UNDER_REVIEW"
    STATUS_APPROVED = "APPROVED"
    STATUS_AWARDED = "AWARDED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_AWARDED, "Awarded"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="public_procurement_records")
    tender_number = models.CharField(max_length=80, db_index=True)
    procurement_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_OPEN_TENDER)
    procuring_entity = models.CharField(max_length=255, blank=True)
    approval_reference = models.CharField(max_length=120, blank=True)
    approval_history = models.TextField(blank=True)
    evaluation_summary = models.TextField(blank=True)
    probity_notes = models.TextField(blank=True)
    bid_evaluation_file = models.FileField(upload_to="compliance/procurement/", null=True, blank=True)
    award_notice_file = models.FileField(upload_to="compliance/procurement/", null=True, blank=True)
    approval_file = models.FileField(upload_to="compliance/procurement/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    class Meta:
        ordering = ["project", "-created_at"]
        unique_together = [("project", "tender_number")]

    def __str__(self):
        return f"{self.tender_number} - {self.project.project_id}"


class LocalContentRecord(TimeStampedModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="local_content_records")
    period_from = models.DateField()
    period_to = models.DateField()
    png_labour_count = models.PositiveIntegerField(default=0)
    expat_labour_count = models.PositiveIntegerField(default=0)
    local_supplier_spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_supplier_spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    local_subcontractor_spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_subcontractor_spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    png_material_spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_material_spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    evidence_file = models.FileField(upload_to="compliance/local_content/", null=True, blank=True)

    class Meta:
        ordering = ["project", "-period_to"]

    def _pct(self, part, whole):
        return (part / whole * 100) if whole else 0

    @property
    def png_labour_pct(self):
        return self._pct(self.png_labour_count, self.png_labour_count + self.expat_labour_count)

    @property
    def local_supplier_pct(self):
        return self._pct(self.local_supplier_spend, self.total_supplier_spend)

    @property
    def local_subcontractor_pct(self):
        return self._pct(self.local_subcontractor_spend, self.total_subcontractor_spend)

    @property
    def png_material_pct(self):
        return self._pct(self.png_material_spend, self.total_material_spend)

    def __str__(self):
        return f"{self.project.project_id} local content {self.period_from} - {self.period_to}"


class AuthorityPermit(TimeStampedModel):
    AUTHORITY_BUILDING_BOARD = "BUILDING_BOARD"
    AUTHORITY_PROVINCIAL = "PROVINCIAL"
    AUTHORITY_LLG = "LLG"
    AUTHORITY_FIRE = "FIRE"
    AUTHORITY_OCCUPANCY = "OCCUPANCY"
    AUTHORITY_OTHER = "OTHER"

    AUTHORITY_CHOICES = [
        (AUTHORITY_BUILDING_BOARD, "Building Board"),
        (AUTHORITY_PROVINCIAL, "Provincial Authority"),
        (AUTHORITY_LLG, "District / LLG Authority"),
        (AUTHORITY_FIRE, "Fire Authority"),
        (AUTHORITY_OCCUPANCY, "Occupancy / Completion"),
        (AUTHORITY_OTHER, "Other Authority"),
    ]

    STATUS_REQUIRED = "REQUIRED"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_INSPECTED = "INSPECTED"
    STATUS_CERTIFIED = "CERTIFIED"
    STATUS_EXPIRED = "EXPIRED"

    STATUS_CHOICES = [
        (STATUS_REQUIRED, "Required"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_INSPECTED, "Inspected"),
        (STATUS_CERTIFIED, "Certified / Occupancy Issued"),
        (STATUS_EXPIRED, "Expired"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="authority_permits")
    authority = models.CharField(max_length=25, choices=AUTHORITY_CHOICES)
    permit_type = models.CharField(max_length=120)
    reference_number = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_REQUIRED)
    submission_date = models.DateField(null=True, blank=True)
    approval_date = models.DateField(null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    conditions = models.TextField(blank=True)
    certificate_file = models.FileField(upload_to="compliance/authority_permits/", null=True, blank=True)

    class Meta:
        ordering = ["project", "authority", "permit_type"]

    def __str__(self):
        return f"{self.project.project_id} - {self.permit_type}"


class FunderReportPack(TimeStampedModel):
    PACK_MONTHLY = "MONTHLY"
    PACK_QUARTERLY = "QUARTERLY"
    PACK_CLOSEOUT = "CLOSEOUT"
    PACK_ADHOC = "ADHOC"

    PACK_CHOICES = [
        (PACK_MONTHLY, "Monthly"),
        (PACK_QUARTERLY, "Quarterly"),
        (PACK_CLOSEOUT, "Closeout"),
        (PACK_ADHOC, "Ad hoc"),
    ]

    STATUS_DRAFT = "DRAFT"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_ACCEPTED = "ACCEPTED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_ACCEPTED, "Accepted"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="funder_report_packs")
    funder_type = models.CharField(max_length=20, choices=Funder.FUNDER_TYPE_CHOICES)
    pack_type = models.CharField(max_length=15, choices=PACK_CHOICES, default=PACK_MONTHLY)
    period_from = models.DateField()
    period_to = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    narrative = models.TextField(blank=True)
    pack_file = models.FileField(upload_to="compliance/funder_packs/", null=True, blank=True)
    submitted_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["project", "-period_to"]

    def __str__(self):
        return f"{self.project.project_id} {self.get_pack_type_display()} pack"


class ComplianceCalendarTemplate(TimeStampedModel):
    CATEGORY_TCS = "TCS"
    CATEGORY_IRC = "IRC"
    CATEGORY_RPNGC = "RPNGC"
    CATEGORY_SAFETY = "SAFETY"
    CATEGORY_QUALITY = "QUALITY"
    CATEGORY_OTHER = "OTHER"

    CATEGORY_CHOICES = [
        (CATEGORY_TCS, "OTML TCS"),
        (CATEGORY_IRC, "IRC / Tax"),
        (CATEGORY_RPNGC, "RPNGC / Government"),
        (CATEGORY_SAFETY, "Safety"),
        (CATEGORY_QUALITY, "Quality"),
        (CATEGORY_OTHER, "Other"),
    ]

    FREQUENCY_ONCE = "ONCE"
    FREQUENCY_MONTHLY = "MONTHLY"
    FREQUENCY_QUARTERLY = "QUARTERLY"
    FREQUENCY_ANNUAL = "ANNUAL"

    FREQUENCY_CHOICES = [
        (FREQUENCY_ONCE, "Once"),
        (FREQUENCY_MONTHLY, "Monthly"),
        (FREQUENCY_QUARTERLY, "Quarterly"),
        (FREQUENCY_ANNUAL, "Annual"),
    ]

    name = models.CharField(max_length=180)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    frequency = models.CharField(max_length=15, choices=FREQUENCY_CHOICES, default=FREQUENCY_ONCE)
    default_reminder_days = models.PositiveIntegerField(default=14)
    description = models.TextField(blank=True)
    applies_to_government = models.BooleanField(default=True)
    applies_to_private = models.BooleanField(default=True)
    applies_to_maintenance = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Compliance Calendar Entry
# ---------------------------------------------------------------------------


class ComplianceCalendarEntry(TimeStampedModel):
    CATEGORY_TCS = "TCS"
    CATEGORY_IRC = "IRC"
    CATEGORY_RPNGC = "RPNGC"
    CATEGORY_SAFETY = "SAFETY"
    CATEGORY_QUALITY = "QUALITY"
    CATEGORY_OTHER = "OTHER"

    CATEGORY_CHOICES = [
        (CATEGORY_TCS, "OTML TCS"),
        (CATEGORY_IRC, "IRC / Tax"),
        (CATEGORY_RPNGC, "RPNGC / Government"),
        (CATEGORY_SAFETY, "Safety"),
        (CATEGORY_QUALITY, "Quality"),
        (CATEGORY_OTHER, "Other"),
    ]

    STATUS_PENDING = "PENDING"
    STATUS_COMPLETE = "COMPLETE"
    STATUS_OVERDUE = "OVERDUE"
    STATUS_WAIVED = "WAIVED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETE, "Complete"),
        (STATUS_OVERDUE, "Overdue"),
        (STATUS_WAIVED, "Waived / N/A"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="compliance_entries",
        null=True, blank=True,
        help_text="Leave blank for company-wide compliance items.",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    reminder_days = models.PositiveIntegerField(
        default=7,
        help_text="Send reminder this many days before due date.",
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="compliance_responsibilities",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    completed_date = models.DateField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to="compliance/calendar/", blank=True, null=True)

    class Meta:
        verbose_name = "Compliance Calendar Entry"
        verbose_name_plural = "Compliance Calendar Entries"
        ordering = ["due_date", "project"]

    def __str__(self):
        project_str = f"{self.project.project_id} — " if self.project else ""
        return f"{project_str}{self.title} (due {self.due_date})"

    def get_absolute_url(self):
        return reverse("compliance:calendar-detail", kwargs={"pk": self.pk})

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status == self.STATUS_PENDING and self.due_date < timezone.now().date()
