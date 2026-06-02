from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# IPC – Interim Payment Claim
# ---------------------------------------------------------------------------


class IPC(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_INTERNAL_REVIEW = "INTERNAL_REVIEW"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_CERTIFIED = "CERTIFIED"
    STATUS_DISPUTED = "DISPUTED"
    STATUS_PAID = "PAID"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_INTERNAL_REVIEW, "Internal Review"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_CERTIFIED, "Certified"),
        (STATUS_DISPUTED, "Disputed"),
        (STATUS_PAID, "Paid"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ipcs",
    )
    ipc_number = models.CharField(max_length=20, editable=False, db_index=True)
    claim_period_from = models.DateField(verbose_name="Claim Period From")
    claim_period_to = models.DateField(verbose_name="Claim Period To")
    submitted_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "IPC"
        verbose_name_plural = "IPCs"
        ordering = ["project", "ipc_number"]
        unique_together = [("project", "ipc_number")]

    def __str__(self):
        return f"{self.ipc_number} – {self.project.project_id}"

    def save(self, *args, **kwargs):
        if not self.ipc_number:
            count = IPC.objects.filter(project=self.project).count() + 1
            self.ipc_number = f"IPC-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("ipc:ipc-detail", kwargs={"project_pk": self.project_id, "pk": self.pk})

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    @property
    def total_claimed(self) -> Decimal:
        result = self.line_items.aggregate(
            total=models.Sum(
                models.ExpressionWrapper(
                    models.F("boq_quantity")
                    * models.F("unit_rate")
                    * models.F("current_percent")
                    / Decimal("100"),
                    output_field=models.DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["total"]
        return result or Decimal("0.00")

    @property
    def total_cumulative(self) -> Decimal:
        result = self.line_items.aggregate(
            total=models.Sum(
                models.ExpressionWrapper(
                    models.F("boq_quantity")
                    * models.F("unit_rate")
                    * (models.F("previous_percent") + models.F("current_percent"))
                    / Decimal("100"),
                    output_field=models.DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["total"]
        return result or Decimal("0.00")

    @property
    def amount_certified(self) -> Decimal:
        try:
            return self.certification.amount_certified
        except Certification.DoesNotExist:
            return Decimal("0.00")

    @property
    def amount_paid(self) -> Decimal:
        result = self.payments.aggregate(total=models.Sum("amount"))["total"]
        return result or Decimal("0.00")

    @property
    def amount_outstanding(self) -> Decimal:
        return self.amount_certified - self.amount_paid


# ---------------------------------------------------------------------------
# IPCLineItem
# ---------------------------------------------------------------------------


class IPCLineItem(TimeStampedModel):
    ipc = models.ForeignKey(
        IPC,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    boq_item = models.ForeignKey(
        "budget.BoQItem",
        on_delete=models.PROTECT,
        related_name="ipc_line_items",
    )
    # Snapshot fields – stored at the time the IPC is created to preserve history
    boq_description = models.CharField(max_length=500)
    boq_quantity = models.DecimalField(max_digits=12, decimal_places=4)
    unit_rate = models.DecimalField(max_digits=12, decimal_places=4)
    # Progress
    previous_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Previous % Complete",
    )
    current_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="This Claim % Complete",
    )

    class Meta:
        verbose_name = "IPC Line Item"
        verbose_name_plural = "IPC Line Items"
        ordering = ["boq_item__item_number"]
        unique_together = [("ipc", "boq_item")]

    def __str__(self):
        return f"{self.ipc} – {self.boq_description[:60]}"

    @property
    def cumulative_percent(self) -> Decimal:
        """Cumulative percentage, capped at 100."""
        raw = self.previous_percent + self.current_percent
        return min(raw, Decimal("100.00"))

    @property
    def value_this_period(self) -> Decimal:
        """Value claimed in this IPC period."""
        return (
            self.boq_quantity * self.unit_rate * self.current_percent / Decimal("100")
        ).quantize(Decimal("0.01"))

    @property
    def cumulative_value(self) -> Decimal:
        """Total value claimed to date (previous + current), capped at BoQ amount."""
        return (
            self.boq_quantity * self.unit_rate * self.cumulative_percent / Decimal("100")
        ).quantize(Decimal("0.01"))

    @property
    def boq_amount(self) -> Decimal:
        return (self.boq_quantity * self.unit_rate).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# Certification
# ---------------------------------------------------------------------------


class Certification(TimeStampedModel):
    ipc = models.OneToOneField(
        IPC,
        on_delete=models.CASCADE,
        related_name="certification",
    )
    certified_by = models.CharField(max_length=150)
    certifier_org = models.CharField(max_length=200)
    certified_date = models.DateField()
    amount_certified = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Amount Certified (PGK)",
    )
    retention_deducted = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Retention Deducted (PGK)",
    )
    net_certified = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Net Amount Certified (PGK)",
    )
    disputed_items = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Certification"
        verbose_name_plural = "Certifications"

    def __str__(self):
        return f"Cert: {self.ipc} – {self.certified_date}"

    def save(self, *args, **kwargs):
        # Auto-update IPC status when a certification is created
        super().save(*args, **kwargs)
        IPC.objects.filter(pk=self.ipc_id).update(status=IPC.STATUS_CERTIFIED)


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


class Payment(TimeStampedModel):
    ipc = models.ForeignKey(
        IPC,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payment_date = models.DateField()
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Amount Paid (PGK)",
    )
    payment_reference = models.CharField(max_length=100)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_payments",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Payment {self.payment_reference} – {self.ipc} ({self.amount})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # If total payments >= net certified, mark IPC as PAID
        ipc = IPC.objects.get(pk=self.ipc_id)
        try:
            net = ipc.certification.net_certified
        except Certification.DoesNotExist:
            net = Decimal("0.00")
        if net > 0 and ipc.amount_paid >= net:
            IPC.objects.filter(pk=self.ipc_id).update(status=IPC.STATUS_PAID)


# ---------------------------------------------------------------------------
# RetentionRelease
# ---------------------------------------------------------------------------


class RetentionRelease(TimeStampedModel):
    RELEASE_PRACTICAL_COMPLETION = "PRACTICAL_COMPLETION"
    RELEASE_END_OF_DLP = "END_OF_DLP"

    RELEASE_TYPE_CHOICES = [
        (RELEASE_PRACTICAL_COMPLETION, "Practical Completion"),
        (RELEASE_END_OF_DLP, "End of Defects Liability Period"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="retention_releases",
    )
    release_type = models.CharField(
        max_length=25,
        choices=RELEASE_TYPE_CHOICES,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Amount Released (PGK)",
    )
    release_date = models.DateField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_retention_releases",
    )

    class Meta:
        verbose_name = "Retention Release"
        verbose_name_plural = "Retention Releases"
        ordering = ["-release_date"]

    def __str__(self):
        return (
            f"{self.get_release_type_display()} – {self.project.project_id} ({self.release_date})"
        )
