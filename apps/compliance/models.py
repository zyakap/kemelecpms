"""
Compliance & Funder Reporting models.

Covers: OTML TCS reports, IRC Tax Invoices, Compliance Calendar entries,
and PNG local content tracking.
"""

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


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
    gst_rate = models.DecimalField(max_digits=5, decimal_places=4, default="0.10", verbose_name="GST Rate")
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    description = models.TextField(help_text="Description of works / services for this invoice")
    payment_terms = models.CharField(max_length=100, default="Net 30 days", blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "IRC Tax Invoice"
        verbose_name_plural = "IRC Tax Invoices"
        ordering = ["project", "-invoice_date"]
        unique_together = [("project", "invoice_number")]

    def __str__(self):
        return f"{self.invoice_number} — {self.project.project_id}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            count = IRCTaxInvoice.objects.filter(project=self.project).count() + 1
            self.invoice_number = f"INV-{self.project.project_id}-{count:04d}"
        # Auto-calculate GST and total
        self.gst_amount = self.subtotal * self.gst_rate
        self.total_amount = self.subtotal + self.gst_amount
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("compliance:invoice-detail", kwargs={"project_pk": self.project_id, "pk": self.pk})


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
