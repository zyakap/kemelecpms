"""
Tender & Bid Library models.

Converts completed project data into competitive intelligence.
Covers: Tender Archive, Cost Intelligence Database, Bid Estimates,
and Lessons Learned.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# Tender Archive (linked to closed projects)
# ---------------------------------------------------------------------------


class TenderArchive(TimeStampedModel):
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="tender_archive",
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="archived_tenders",
    )
    archived_date = models.DateField(auto_now_add=True)

    # Financial summary snapshot (populated at close-out)
    original_contract_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    final_contract_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Margin %")

    # Duration snapshot
    planned_duration_days = models.PositiveIntegerField(default=0)
    actual_duration_days = models.PositiveIntegerField(default=0)

    # Summary text (auto-generated or manually added)
    executive_summary = models.TextField(blank=True)
    key_scope = models.TextField(blank=True, verbose_name="Key Scope of Works")
    unique_challenges = models.TextField(blank=True)
    searchable_tags = models.TextField(
        blank=True,
        help_text="Comma-separated tags for search: e.g. CONCRETE,ROADS,HIGHLAND",
    )

    class Meta:
        verbose_name = "Tender Archive"
        verbose_name_plural = "Tender Archives"
        ordering = ["-archived_date"]

    def __str__(self):
        return f"Archive — {self.project.project_id}"

    def get_absolute_url(self):
        return reverse("tender:archive-detail", kwargs={"pk": self.pk})


# ---------------------------------------------------------------------------
# Cost Rate (unit rate intelligence)
# ---------------------------------------------------------------------------


class CostRate(TimeStampedModel):
    TRADE_CIVIL = "CIVIL"
    TRADE_STRUCTURAL = "STRUCTURAL"
    TRADE_ELECTRICAL = "ELECTRICAL"
    TRADE_MECHANICAL = "MECHANICAL"
    TRADE_PLUMBING = "PLUMBING"
    TRADE_CARPENTRY = "CARPENTRY"
    TRADE_FINISHES = "FINISHES"
    TRADE_PRELIMS = "PRELIMS"
    TRADE_LABOUR = "LABOUR"
    TRADE_PLANT = "PLANT"
    TRADE_OTHER = "OTHER"

    TRADE_CHOICES = [
        (TRADE_CIVIL, "Civil"),
        (TRADE_STRUCTURAL, "Structural"),
        (TRADE_ELECTRICAL, "Electrical"),
        (TRADE_MECHANICAL, "Mechanical"),
        (TRADE_PLUMBING, "Plumbing"),
        (TRADE_CARPENTRY, "Carpentry"),
        (TRADE_FINISHES, "Finishes"),
        (TRADE_PRELIMS, "Preliminaries"),
        (TRADE_LABOUR, "Labour"),
        (TRADE_PLANT, "Plant & Equipment"),
        (TRADE_OTHER, "Other"),
    ]

    REGION_NATIONAL_CAPITAL = "NCD"
    REGION_HIGHLANDS = "HIGHLANDS"
    REGION_MOMASE = "MOMASE"
    REGION_ISLANDS = "ISLANDS"
    REGION_SOUTHERN = "SOUTHERN"
    REGION_NATIONAL = "NATIONAL"

    REGION_CHOICES = [
        (REGION_NATIONAL_CAPITAL, "National Capital District"),
        (REGION_HIGHLANDS, "Highlands Region"),
        (REGION_MOMASE, "Momase Region"),
        (REGION_ISLANDS, "Islands Region"),
        (REGION_SOUTHERN, "Southern Region"),
        (REGION_NATIONAL, "National (All Regions)"),
    ]

    source_project = models.ForeignKey(
        "projects.Project",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="cost_rates",
        help_text="Project this rate was derived from.",
    )
    archive = models.ForeignKey(
        TenderArchive,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="cost_rates",
    )
    trade = models.CharField(max_length=15, choices=TRADE_CHOICES)
    region = models.CharField(max_length=15, choices=REGION_CHOICES, default=REGION_NATIONAL)
    year = models.PositiveSmallIntegerField(help_text="Year the rate was recorded")

    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=30, help_text="e.g. m², m³, LM, item, day")
    unit_rate = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False, verbose_name="Verified for use in estimates")

    class Meta:
        verbose_name = "Cost Rate"
        verbose_name_plural = "Cost Rates"
        ordering = ["trade", "description", "-year"]

    def __str__(self):
        return f"{self.description} — K{self.unit_rate}/{self.unit} ({self.year}, {self.region})"

    def get_absolute_url(self):
        return reverse("tender:rate-update", kwargs={"pk": self.pk})


# ---------------------------------------------------------------------------
# Bid Estimate
# ---------------------------------------------------------------------------


class BidEstimate(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_FINAL = "FINAL"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_WON = "WON"
    STATUS_LOST = "LOST"
    STATUS_NO_BID = "NO_BID"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_FINAL, "Final"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_WON, "Won"),
        (STATUS_LOST, "Lost"),
        (STATUS_NO_BID, "No Bid"),
    ]

    tender_reference = models.CharField(max_length=100, verbose_name="Tender Reference / RFT Number")
    title = models.CharField(max_length=255)
    client_name = models.CharField(max_length=255)
    funder = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, blank=True)
    tender_due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # Financial
    estimate_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Target Margin %")

    # Source
    cloned_from = models.ForeignKey(
        "self",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="clones",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Bid Estimate"
        verbose_name_plural = "Bid Estimates"
        ordering = ["-tender_due_date"]

    def __str__(self):
        return f"{self.tender_reference} — {self.title}"

    def get_absolute_url(self):
        return reverse("tender:estimate-detail", kwargs={"pk": self.pk})

    @property
    def bid_margin_amount(self):
        return self.bid_amount - self.estimate_total


class BidEstimateItem(TimeStampedModel):
    estimate = models.ForeignKey(BidEstimate, on_delete=models.CASCADE, related_name="items")
    trade = models.CharField(max_length=15, choices=CostRate.TRADE_CHOICES, default=CostRate.TRADE_CIVIL)
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=30)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_rate = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    rate_source = models.ForeignKey(
        CostRate,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="used_in_items",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Bid Estimate Item"
        verbose_name_plural = "Bid Estimate Items"
        ordering = ["trade", "description"]

    def __str__(self):
        return f"{self.description} ({self.estimate})"

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_rate
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Lessons Learned
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Reusable Document Library
# ---------------------------------------------------------------------------


class TenderDocument(TimeStampedModel):
    """
    Company-wide library of reusable tender documents: method statements,
    CVs, certifications, company profiles, contract clause templates.
    """

    DOC_TYPE_METHOD = "METHOD_STATEMENT"
    DOC_TYPE_CV = "CV"
    DOC_TYPE_ORG_CHART = "ORG_CHART"
    DOC_TYPE_CERT = "CERTIFICATION"
    DOC_TYPE_PROFILE = "PROFILE"
    DOC_TYPE_TEMPLATE = "TEMPLATE"
    DOC_TYPE_CLAUSE = "CONTRACT_CLAUSE"
    DOC_TYPE_OTHER = "OTHER"

    DOC_TYPE_CHOICES = [
        (DOC_TYPE_METHOD, "Method Statement"),
        (DOC_TYPE_CV, "Personnel CV"),
        (DOC_TYPE_ORG_CHART, "Organisational Chart"),
        (DOC_TYPE_CERT, "Company Certification"),
        (DOC_TYPE_PROFILE, "Company Profile / Capability Statement"),
        (DOC_TYPE_TEMPLATE, "Document Template"),
        (DOC_TYPE_CLAUSE, "Contract Clause Library"),
        (DOC_TYPE_OTHER, "Other"),
    ]

    title = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, verbose_name="Document Type")
    trade_category = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Leave blank if applicable to all trades.",
    )
    description = models.TextField(blank=True)
    document = models.FileField(upload_to="tender/documents/%Y/", verbose_name="File")
    version = models.CharField(max_length=20, default="1.0")
    is_current = models.BooleanField(default=True, verbose_name="Current Version")
    tags = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated search tags: e.g. CONCRETE,ROADS,ISO9001",
    )

    class Meta:
        verbose_name = "Tender Document"
        verbose_name_plural = "Tender Documents"
        ordering = ["doc_type", "title"]

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def get_absolute_url(self):
        return reverse("tender:document-list")

    @property
    def filename(self):
        import os
        return os.path.basename(self.document.name) if self.document else ""


class LessonsLearned(TimeStampedModel):
    CATEGORY_COST = "COST"
    CATEGORY_SCHEDULE = "SCHEDULE"
    CATEGORY_QUALITY = "QUALITY"
    CATEGORY_SAFETY = "SAFETY"
    CATEGORY_PROCUREMENT = "PROCUREMENT"
    CATEGORY_CLIENT = "CLIENT"
    CATEGORY_DESIGN = "DESIGN"
    CATEGORY_OTHER = "OTHER"

    CATEGORY_CHOICES = [
        (CATEGORY_COST, "Cost"),
        (CATEGORY_SCHEDULE, "Schedule"),
        (CATEGORY_QUALITY, "Quality"),
        (CATEGORY_SAFETY, "Safety"),
        (CATEGORY_PROCUREMENT, "Procurement"),
        (CATEGORY_CLIENT, "Client Relations"),
        (CATEGORY_DESIGN, "Design"),
        (CATEGORY_OTHER, "Other"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="lessons_learned",
    )
    archive = models.ForeignKey(
        TenderArchive,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="lessons_learned",
    )
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    what_went_well = models.TextField(blank=True)
    what_went_wrong = models.TextField(blank=True)
    recommendation = models.TextField(help_text="Specific, actionable recommendation for next project.")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="lessons_recorded",
    )

    class Meta:
        verbose_name = "Lesson Learned"
        verbose_name_plural = "Lessons Learned"
        ordering = ["-created_at", "category"]

    def __str__(self):
        return f"{self.project.project_id} — {self.title}"

    def get_absolute_url(self):
        return reverse("tender:lesson-detail", kwargs={"pk": self.pk})
