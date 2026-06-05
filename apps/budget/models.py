from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class CostCode(TimeStampedModel):
    CATEGORY_CIVIL = "CIVIL"
    CATEGORY_STRUCTURAL = "STRUCTURAL"
    CATEGORY_ELECTRICAL = "ELECTRICAL"
    CATEGORY_MECHANICAL = "MECHANICAL"
    CATEGORY_PLUMBING = "PLUMBING"
    CATEGORY_CARPENTRY = "CARPENTRY"
    CATEGORY_FINISHES = "FINISHES"
    CATEGORY_PRELIMINARIES = "PRELIMINARIES"
    CATEGORY_CONTINGENCY = "CONTINGENCY"
    CATEGORY_OTHER = "OTHER"

    CATEGORY_CHOICES = [
        (CATEGORY_CIVIL, "Civil"),
        (CATEGORY_STRUCTURAL, "Structural"),
        (CATEGORY_ELECTRICAL, "Electrical"),
        (CATEGORY_MECHANICAL, "Mechanical"),
        (CATEGORY_PLUMBING, "Plumbing"),
        (CATEGORY_CARPENTRY, "Carpentry"),
        (CATEGORY_FINISHES, "Finishes"),
        (CATEGORY_PRELIMINARIES, "Preliminaries"),
        (CATEGORY_CONTINGENCY, "Contingency"),
        (CATEGORY_OTHER, "Other"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="cost_codes",
    )
    code = models.CharField(
        max_length=50,
        help_text='Cost code identifier, e.g. "01.CIVIL.EARTHWORKS"',
    )
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_OTHER,
    )
    budget_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    forecast_etc = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Estimate to Complete (PGK)",
        help_text="Forecast remaining cost required to complete this cost code.",
    )
    provisional_sum = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Provisional Sum (PGK)",
        help_text="Allowance held against uncertain scope within this cost code.",
    )
    contingency_drawdown = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Contingency Drawdown (PGK)",
        help_text="Approved contingency consumed by this cost code.",
    )
    is_contingency = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Cost Code"
        verbose_name_plural = "Cost Codes"
        ordering = ["code"]
        unique_together = [("project", "code")]

    def __str__(self):
        return f"{self.code} – {self.name}"

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    @property
    def total_committed(self) -> Decimal:
        result = self.cost_entries.filter(entry_type=CostEntry.TYPE_COMMITTED).aggregate(
            total=models.Sum("amount")
        )["total"]
        return result or Decimal("0.00")

    @property
    def total_actual(self) -> Decimal:
        result = self.cost_entries.filter(entry_type=CostEntry.TYPE_ACTUAL).aggregate(
            total=models.Sum("amount")
        )["total"]
        return result or Decimal("0.00")

    @property
    def total_spent(self) -> Decimal:
        """Combined committed + actual spend."""
        return self.total_committed + self.total_actual

    @property
    def control_budget(self) -> Decimal:
        """Budget available for project control including provisional sums."""
        return self.budget_amount + self.provisional_sum

    @property
    def etc(self) -> Decimal:
        """Estimate to complete."""
        return self.forecast_etc

    @property
    def efc(self) -> Decimal:
        """Estimate final cost."""
        return self.estimate_at_completion

    @property
    def estimate_at_completion(self) -> Decimal:
        """Actual cost plus current commitments plus remaining forecast."""
        return self.total_actual + self.total_committed + self.forecast_etc

    @property
    def forecast_variance(self) -> Decimal:
        """Budget remaining against EFC (positive = forecast under budget)."""
        return self.control_budget - self.estimate_at_completion

    @property
    def forecast_variance_percentage(self) -> Decimal:
        if self.control_budget == 0:
            return Decimal("100.00") if self.estimate_at_completion > 0 else Decimal("0.00")
        return (
            self.estimate_at_completion / self.control_budget * 100
        ).quantize(Decimal("0.01"))

    @property
    def forecast_rag_status(self) -> str:
        pct = self.forecast_variance_percentage
        if pct > 100:
            return "RED"
        if pct >= 90:
            return "AMBER"
        return "GREEN"

    @property
    def variance(self) -> Decimal:
        """Budget remaining (positive = under budget, negative = over budget)."""
        return self.control_budget - self.total_spent

    @property
    def variance_percentage(self) -> Decimal:
        """Percentage of budget consumed (0–100+)."""
        if self.control_budget == 0:
            return Decimal("100.00") if self.total_spent > 0 else Decimal("0.00")
        return (self.total_spent / self.control_budget * 100).quantize(Decimal("0.01"))

    @property
    def rag_status(self) -> str:
        """RED/AMBER/GREEN based on % of budget consumed."""
        pct = self.variance_percentage
        if pct > 100:
            return "RED"
        if pct >= 80:
            return "AMBER"
        return "GREEN"


class BoQItem(TimeStampedModel):
    UNIT_CHOICES = [
        ("m2", "m²"),
        ("m3", "m³"),
        ("m", "m"),
        ("nr", "nr"),
        ("kg", "kg"),
        ("t", "t"),
        ("l", "l"),
        ("hr", "hr"),
        ("day", "day"),
        ("lump", "lump"),
        ("allow", "allow"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="boq_items",
    )
    cost_code = models.ForeignKey(
        CostCode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="boq_items",
    )
    item_number = models.CharField(
        max_length=20,
        help_text='Hierarchical item number, e.g. "1.1.1"',
    )
    description = models.TextField()
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="nr")
    quantity = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))
    unit_rate = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))
    is_variation = models.BooleanField(
        default=False,
        help_text="True if this item was added via a variation order.",
    )
    variation = models.ForeignKey(
        "projects.Variation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="boq_items",
    )
    trade_section = models.CharField(
        max_length=20,
        choices=CostCode.CATEGORY_CHOICES,
        default=CostCode.CATEGORY_OTHER,
    )

    class Meta:
        verbose_name = "BoQ Item"
        verbose_name_plural = "BoQ Items"
        ordering = ["item_number"]
        unique_together = [("project", "item_number")]

    def __str__(self):
        return f"{self.item_number} – {self.description[:60]}"

    @property
    def amount(self) -> Decimal:
        return (self.quantity * self.unit_rate).quantize(Decimal("0.01"))


class CostEntry(TimeStampedModel):
    TYPE_COMMITTED = "COMMITTED"
    TYPE_ACTUAL = "ACTUAL"

    ENTRY_TYPE_CHOICES = [
        (TYPE_COMMITTED, "Committed"),
        (TYPE_ACTUAL, "Actual"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="cost_entries",
    )
    cost_code = models.ForeignKey(
        CostCode,
        on_delete=models.PROTECT,
        related_name="cost_entries",
    )
    boq_item = models.ForeignKey(
        BoQItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cost_entries",
    )
    entry_type = models.CharField(
        max_length=10,
        choices=ENTRY_TYPE_CHOICES,
        default=TYPE_ACTUAL,
    )
    description = models.CharField(max_length=500)
    supplier = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField()
    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Invoice or Purchase Order number.",
    )
    document = models.FileField(
        upload_to="cost_entries/",
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_cost_entries",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Cost Entry"
        verbose_name_plural = "Cost Entries"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_entry_type_display()} – {self.description[:60]} ({self.amount})"


class Subcontract(TimeStampedModel):
    STATUS_ACTIVE = "ACTIVE"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_TERMINATED = "TERMINATED"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_TERMINATED, "Terminated"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="subcontracts",
    )
    trade = models.CharField(max_length=100)
    company_name = models.CharField(max_length=200)
    scope = models.TextField()
    contract_value = models.DecimalField(max_digits=14, decimal_places=2)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    retention_held = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total retention amount currently withheld (PGK).",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Subcontract"
        verbose_name_plural = "Subcontracts"
        ordering = ["company_name"]

    def __str__(self):
        return f"{self.company_name} – {self.trade} ({self.project})"

    @property
    def retention_percentage(self) -> Decimal:
        if self.contract_value == 0:
            return Decimal("0.00")
        return (self.retention_held / self.contract_value * 100).quantize(Decimal("0.01"))

    @property
    def amount_claimed(self) -> Decimal:
        return self.claims.aggregate(total=models.Sum("claimed_amount"))["total"] or Decimal("0.00")

    @property
    def amount_approved(self) -> Decimal:
        return self.claims.aggregate(total=models.Sum("approved_amount"))["total"] or Decimal("0.00")

    @property
    def amount_paid(self) -> Decimal:
        return self.claims.aggregate(total=models.Sum("amount_paid"))["total"] or Decimal("0.00")

    @property
    def approved_backcharges(self) -> Decimal:
        return (
            self.backcharges.filter(status=SubcontractBackCharge.STATUS_APPROVED)
            .aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )

    @property
    def outstanding_payment(self) -> Decimal:
        return self.amount_approved - self.amount_paid

    @property
    def latest_performance_score(self):
        latest = self.performance_reviews.order_by("-review_date", "-created_at").first()
        return latest.overall_score if latest else None


class SubcontractClaim(TimeStampedModel):
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_ASSESSED = "ASSESSED"
    STATUS_APPROVED = "APPROVED"
    STATUS_PAID = "PAID"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_ASSESSED, "Assessed"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_PAID, "Paid"),
        (STATUS_REJECTED, "Rejected"),
    ]

    subcontract = models.ForeignKey(
        Subcontract,
        on_delete=models.CASCADE,
        related_name="claims",
    )
    claim_number = models.CharField(max_length=30, editable=False, db_index=True)
    period_from = models.DateField()
    period_to = models.DateField()
    submitted_date = models.DateField()
    claimed_amount = models.DecimalField(max_digits=14, decimal_places=2)
    assessed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    approved_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    retention_deducted = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    backcharge_deducted = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Subcontract Claim"
        verbose_name_plural = "Subcontract Claims"
        ordering = ["subcontract", "-submitted_date", "-claim_number"]
        unique_together = [("subcontract", "claim_number")]

    def __str__(self):
        return f"{self.claim_number} - {self.subcontract.company_name}"

    def save(self, *args, **kwargs):
        if not self.claim_number:
            count = SubcontractClaim.objects.filter(subcontract=self.subcontract).count() + 1
            self.claim_number = f"SC-{self.subcontract_id}-CLM-{count:03d}"
        super().save(*args, **kwargs)

    @property
    def net_approved(self) -> Decimal:
        return self.approved_amount - self.retention_deducted - self.backcharge_deducted

    @property
    def outstanding_amount(self) -> Decimal:
        return self.net_approved - self.amount_paid


class SubcontractBackCharge(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_APPROVED = "APPROVED"
    STATUS_RECOVERED = "RECOVERED"
    STATUS_WAIVED = "WAIVED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_RECOVERED, "Recovered"),
        (STATUS_WAIVED, "Waived"),
    ]

    subcontract = models.ForeignKey(
        Subcontract,
        on_delete=models.CASCADE,
        related_name="backcharges",
    )
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    recovered_from_claim = models.ForeignKey(
        SubcontractClaim,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovered_backcharges",
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Subcontract Back-Charge"
        verbose_name_plural = "Subcontract Back-Charges"
        ordering = ["subcontract", "-date"]

    def __str__(self):
        return f"Back-charge {self.subcontract.company_name} - {self.amount}"


class SubcontractPerformanceReview(TimeStampedModel):
    subcontract = models.ForeignKey(
        Subcontract,
        on_delete=models.CASCADE,
        related_name="performance_reviews",
    )
    review_date = models.DateField()
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="subcontract_performance_reviews",
    )
    quality_score = models.PositiveSmallIntegerField(default=3)
    schedule_score = models.PositiveSmallIntegerField(default=3)
    safety_score = models.PositiveSmallIntegerField(default=3)
    commercial_score = models.PositiveSmallIntegerField(default=3)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Subcontract Performance Review"
        verbose_name_plural = "Subcontract Performance Reviews"
        ordering = ["subcontract", "-review_date"]

    def __str__(self):
        return f"{self.subcontract.company_name} review {self.review_date}"

    @property
    def overall_score(self) -> Decimal:
        total = (
            self.quality_score
            + self.schedule_score
            + self.safety_score
            + self.commercial_score
        )
        return (Decimal(total) / Decimal("4")).quantize(Decimal("0.1"))
