"""
Procurement models for kemelecpms.

Covers: Supplier, Material catalogue, Material Requisitions (MR),
Purchase Orders (PO), Goods Received Notes (GRN), Supplier Invoices,
and Stock Ledger.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------


class Supplier(TimeStampedModel):
    CATEGORY_HARDWARE = "HARDWARE"
    CATEGORY_ELECTRICAL = "ELECTRICAL"
    CATEGORY_MECHANICAL = "MECHANICAL"
    CATEGORY_FUEL = "FUEL"
    CATEGORY_PLANT_HIRE = "PLANT_HIRE"
    CATEGORY_OTHER = "OTHER"

    CATEGORY_CHOICES = [
        (CATEGORY_HARDWARE, "Hardware"),
        (CATEGORY_ELECTRICAL, "Electrical"),
        (CATEGORY_MECHANICAL, "Mechanical"),
        (CATEGORY_FUEL, "Fuel"),
        (CATEGORY_PLANT_HIRE, "Plant Hire"),
        (CATEGORY_OTHER, "Other"),
    ]

    name = models.CharField(max_length=255, db_index=True)
    address = models.TextField(blank=True)
    irc_tin = models.CharField(
        max_length=50, blank=True, verbose_name="IRC TIN / Tax ID"
    )
    bank_name = models.CharField(max_length=150, blank=True)
    bank_account_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    # Comma-separated list of category keys, e.g. "HARDWARE,ELECTRICAL"
    categories = models.TextField(
        blank=True,
        help_text=(
            "Comma-separated supplier categories: "
            "HARDWARE, ELECTRICAL, MECHANICAL, FUEL, PLANT_HIRE, OTHER"
        ),
    )
    is_preferred = models.BooleanField(default=False)
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)
    performance_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="Performance Rating (0.0 – 5.0)",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("procurement:supplier_detail", kwargs={"pk": self.pk})

    def get_category_list(self):
        """Return categories as a list of strings."""
        return [c.strip() for c in self.categories.split(",") if c.strip()]

    def get_category_display_list(self):
        """Return human-readable category labels."""
        label_map = dict(self.CATEGORY_CHOICES)
        return [label_map.get(c, c) for c in self.get_category_list()]


# ---------------------------------------------------------------------------
# Material Catalogue
# ---------------------------------------------------------------------------


class MaterialCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Material Category"
        verbose_name_plural = "Material Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Material(TimeStampedModel):
    item_code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=30, help_text="Unit of measure, e.g. m3, kg, EA")
    category = models.ForeignKey(
        MaterialCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="materials",
    )
    min_stock_level = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal("0.000"),
        verbose_name="Minimum Stock Level",
    )

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materials"
        ordering = ["item_code"]

    def __str__(self):
        return f"{self.item_code} – {self.description}"

    def get_absolute_url(self):
        return reverse("procurement:material_list")

    def stock_on_site(self, project):
        """
        Return net stock quantity for this material on a given project.
        Receipts increase stock; Issues, Transfers out, Wastage reduce it.
        """
        qs = StockLedger.objects.filter(project=project, material=self)
        receipts = qs.filter(
            transaction_type__in=[
                StockLedger.TYPE_RECEIPT,
                StockLedger.TYPE_RETURN,
            ]
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        outflows = qs.filter(
            transaction_type__in=[
                StockLedger.TYPE_ISSUE,
                StockLedger.TYPE_TRANSFER,
                StockLedger.TYPE_WASTAGE,
            ]
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        adjustments = qs.filter(
            transaction_type=StockLedger.TYPE_ADJUSTMENT
        ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        return receipts - outflows + adjustments


# ---------------------------------------------------------------------------
# Material Requisition (MR)
# ---------------------------------------------------------------------------


class MaterialRequisition(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_ORDERED = "ORDERED"
    STATUS_DELIVERED = "DELIVERED"
    STATUS_CLOSED = "CLOSED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_ORDERED, "Ordered"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_REJECTED, "Rejected"),
    ]

    mr_number = models.CharField(
        max_length=20, unique=True, editable=False, db_index=True
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="material_requisitions",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="material_requisitions_raised",
    )
    date = models.DateField()
    required_by_date = models.DateField(verbose_name="Required By Date")
    justification = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="material_requisitions_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Material Requisition"
        verbose_name_plural = "Material Requisitions"
        ordering = ["-date", "-mr_number"]

    def __str__(self):
        return f"{self.mr_number} – {self.project}"

    def save(self, *args, **kwargs):
        if not self.mr_number:
            count = MaterialRequisition.objects.count() + 1
            self.mr_number = f"MR-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("procurement:mr_detail", kwargs={"pk": self.pk})


class MRItem(TimeStampedModel):
    mr = models.ForeignKey(
        MaterialRequisition, on_delete=models.CASCADE, related_name="items"
    )
    material = models.ForeignKey(
        Material,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mr_items",
    )
    # Free-text description when material is not in catalogue
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Required when material is not selected from catalogue",
    )
    unit = models.CharField(max_length=30)
    quantity_requested = models.DecimalField(max_digits=10, decimal_places=3)
    quantity_ordered = models.DecimalField(
        max_digits=10, decimal_places=3, default=Decimal("0.000")
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "MR Item"
        verbose_name_plural = "MR Items"
        ordering = ["pk"]

    def __str__(self):
        label = self.material.description if self.material else self.description
        return f"{self.mr.mr_number} – {label}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.material and not self.description:
            raise ValidationError(
                "Either a catalogue material or a description must be provided."
            )


# ---------------------------------------------------------------------------
# Purchase Order (PO)
# ---------------------------------------------------------------------------


class PurchaseOrder(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
    STATUS_APPROVED = "APPROVED"
    STATUS_SENT = "SENT"
    STATUS_PARTIALLY_DELIVERED = "PARTIALLY_DELIVERED"
    STATUS_DELIVERED = "DELIVERED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING_APPROVAL, "Pending Approval"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_SENT, "Sent to Supplier"),
        (STATUS_PARTIALLY_DELIVERED, "Partially Delivered"),
        (STATUS_DELIVERED, "Fully Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    po_number = models.CharField(
        max_length=20, unique=True, editable=False, db_index=True
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="purchase_orders"
    )
    mr = models.ForeignKey(
        MaterialRequisition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_orders",
        verbose_name="Material Requisition",
    )
    date = models.DateField()
    delivery_address = models.CharField(max_length=255)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Total Amount (PGK)",
    )
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_orders_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        ordering = ["-date", "-po_number"]

    def __str__(self):
        return f"{self.po_number} – {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.po_number:
            count = PurchaseOrder.objects.count() + 1
            self.po_number = f"PO-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("procurement:po_detail", kwargs={"pk": self.pk})

    def recalculate_total(self):
        """Recalculate and persist total_amount from line items."""
        total = (
            self.items.aggregate(
                total=Sum(
                    models.F("quantity") * models.F("unit_price"),
                    output_field=models.DecimalField(max_digits=14, decimal_places=2),
                )
            )["total"]
            or Decimal("0.00")
        )
        PurchaseOrder.objects.filter(pk=self.pk).update(total_amount=total)
        self.total_amount = total

    @property
    def total_delivered_value(self):
        total = Decimal("0.00")
        for item in self.items.all():
            delivered_qty = (
                item.grn_items.aggregate(total=Sum("quantity_delivered"))["total"]
                or Decimal("0.000")
            )
            total += delivered_qty * item.unit_price
        return total.quantize(Decimal("0.01"))

    @property
    def total_invoiced_amount(self):
        result = self.invoices.exclude(
            status=SupplierInvoice.STATUS_RECEIVED
        ).aggregate(total=Sum("amount"))["total"]
        return result or Decimal("0.00")

    @property
    def unmatched_delivery_value(self):
        return (self.total_delivered_value - self.total_invoiced_amount).quantize(Decimal("0.01"))

    @property
    def has_delivery_discrepancies(self):
        return GRNItem.objects.filter(grn__po=self, has_discrepancy=True).exists()

    @property
    def is_fully_delivered_by_quantity(self):
        for item in self.items.all():
            delivered_qty = (
                item.grn_items.aggregate(total=Sum("quantity_delivered"))["total"]
                or Decimal("0.000")
            )
            if delivered_qty < item.quantity:
                return False
        return self.items.exists()


class POItem(TimeStampedModel):
    po = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )
    mr_item = models.ForeignKey(
        MRItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="po_items",
    )
    material = models.ForeignKey(
        Material,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="po_items",
    )
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=30)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=4, verbose_name="Unit Price (PGK)"
    )

    class Meta:
        verbose_name = "PO Item"
        verbose_name_plural = "PO Items"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.po.po_number} – {self.description}"

    @property
    def amount(self):
        """Line total: quantity * unit_price."""
        return self.quantity * self.unit_price


# ---------------------------------------------------------------------------
# Goods Received Note (GRN)
# ---------------------------------------------------------------------------


class GoodsReceivedNote(TimeStampedModel):
    grn_number = models.CharField(
        max_length=20, unique=True, editable=False, db_index=True
    )
    po = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="grns"
    )
    delivery_date = models.DateField()
    delivered_by = models.CharField(max_length=150, verbose_name="Delivered By (Driver / Company)")
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grns_received",
    )
    condition_notes = models.TextField(blank=True)
    delivery_photo = models.FileField(
        upload_to="grn_photos/", null=True, blank=True
    )
    is_partial = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Goods Received Note"
        verbose_name_plural = "Goods Received Notes"
        ordering = ["-delivery_date", "-grn_number"]

    def __str__(self):
        return f"{self.grn_number} – {self.po.po_number}"

    def save(self, *args, **kwargs):
        if not self.grn_number:
            count = GoodsReceivedNote.objects.count() + 1
            self.grn_number = f"GRN-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("procurement:grn_detail", kwargs={"pk": self.pk})

    @property
    def has_discrepancy(self):
        return self.items.filter(has_discrepancy=True).exists()


class GRNItem(TimeStampedModel):
    grn = models.ForeignKey(
        GoodsReceivedNote, on_delete=models.CASCADE, related_name="items"
    )
    po_item = models.ForeignKey(
        POItem, on_delete=models.PROTECT, related_name="grn_items"
    )
    quantity_delivered = models.DecimalField(max_digits=10, decimal_places=3)
    has_discrepancy = models.BooleanField(default=False)
    discrepancy_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "GRN Item"
        verbose_name_plural = "GRN Items"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.grn.grn_number} – {self.po_item.description}"


# ---------------------------------------------------------------------------
# Supplier Invoice
# ---------------------------------------------------------------------------


class SupplierInvoice(TimeStampedModel):
    STATUS_RECEIVED = "RECEIVED"
    STATUS_MATCHED = "MATCHED"
    STATUS_APPROVED = "APPROVED"
    STATUS_PAID = "PAID"

    STATUS_CHOICES = [
        (STATUS_RECEIVED, "Received"),
        (STATUS_MATCHED, "Matched to GRN"),
        (STATUS_APPROVED, "Approved for Payment"),
        (STATUS_PAID, "Paid"),
    ]

    invoice_number = models.CharField(max_length=100, db_index=True)
    po = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="invoices"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="invoices"
    )
    invoice_date = models.DateField()
    amount = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name="Invoice Amount (PGK)"
    )
    document = models.FileField(upload_to="invoices/")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED
    )
    is_matched = models.BooleanField(default=False)
    match_exception_approved = models.BooleanField(default=False)
    match_exception_reason = models.TextField(blank=True)
    match_exception_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supplier_invoice_match_exceptions_approved",
    )
    match_exception_approved_at = models.DateTimeField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Supplier Invoice"
        verbose_name_plural = "Supplier Invoices"
        ordering = ["-invoice_date"]
        unique_together = [("supplier", "invoice_number")]

    def __str__(self):
        return f"{self.invoice_number} – {self.supplier.name} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("procurement:invoice_list")

    def evaluate_match(self):
        """Return (is_matched, reason) for PO/GRN/invoice consistency."""
        if self.supplier_id and self.po_id and self.supplier_id != self.po.supplier_id:
            return False, "Invoice supplier does not match the PO supplier."
        if not self.po.grns.exists():
            return False, "No GRN has been recorded for this PO."
        if self.po.has_delivery_discrepancies:
            return False, "One or more GRNs have unresolved discrepancies."
        delivered_value = self.po.total_delivered_value
        previously_invoiced = (
            self.po.invoices.exclude(pk=self.pk)
            .exclude(status=self.STATUS_RECEIVED)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        if self.amount + previously_invoiced > delivered_value:
            return False, "Invoice amount exceeds delivered value not yet invoiced."
        return True, ""

    @property
    def can_progress_with_exception(self):
        return self.is_matched or self.match_exception_approved


# ---------------------------------------------------------------------------
# Stock Ledger
# ---------------------------------------------------------------------------


class StockLedger(TimeStampedModel):
    TYPE_RECEIPT = "RECEIPT"
    TYPE_ISSUE = "ISSUE"
    TYPE_TRANSFER = "TRANSFER"
    TYPE_RETURN = "RETURN"
    TYPE_ADJUSTMENT = "ADJUSTMENT"
    TYPE_WASTAGE = "WASTAGE"

    TRANSACTION_TYPE_CHOICES = [
        (TYPE_RECEIPT, "Receipt (GRN)"),
        (TYPE_ISSUE, "Issue to Works"),
        (TYPE_TRANSFER, "Transfer Out"),
        (TYPE_RETURN, "Return to Yard"),
        (TYPE_ADJUSTMENT, "Stock Adjustment"),
        (TYPE_WASTAGE, "Wastage / Write-off"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="stock_ledger_entries",
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, related_name="stock_ledger_entries"
    )
    date = models.DateField()
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPE_CHOICES
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text=(
            "Always positive. Sign is derived from transaction_type."
        ),
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="GRN number, Activity name, etc.",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_ledger_entries",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Stock Ledger Entry"
        verbose_name_plural = "Stock Ledger"
        ordering = ["-date", "-pk"]

    def __str__(self):
        return (
            f"{self.date} | {self.get_transaction_type_display()} | "
            f"{self.material.item_code} | {self.quantity} {self.material.unit}"
        )
