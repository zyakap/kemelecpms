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
    def variance(self) -> Decimal:
        """Budget remaining (positive = under budget, negative = over budget)."""
        return self.budget_amount - self.total_spent

    @property
    def variance_percentage(self) -> Decimal:
        """Percentage of budget consumed (0–100+)."""
        if self.budget_amount == 0:
            return Decimal("100.00") if self.total_spent > 0 else Decimal("0.00")
        return (self.total_spent / self.budget_amount * 100).quantize(Decimal("0.01"))

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
