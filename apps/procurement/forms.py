"""
Procurement forms for kemelecpms.
"""

from django import forms
from django.forms import inlineformset_factory

from .models import (
    GoodsReceivedNote,
    GRNItem,
    Material,
    MaterialCategory,
    MaterialRequisition,
    MRItem,
    POItem,
    PurchaseOrder,
    StockLedger,
    Supplier,
    SupplierInvoice,
)


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name",
            "address",
            "irc_tin",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "contact_person",
            "email",
            "phone",
            "categories",
            "is_preferred",
            "is_blacklisted",
            "blacklist_reason",
            "performance_rating",
            "notes",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "blacklist_reason": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "categories": forms.TextInput(
                attrs={"placeholder": "e.g. HARDWARE,ELECTRICAL"}
            ),
        }

    def clean_performance_rating(self):
        rating = self.cleaned_data.get("performance_rating")
        if rating is not None and (rating < 0 or rating > 5):
            raise forms.ValidationError("Rating must be between 0.0 and 5.0.")
        return rating

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_blacklisted") and not cleaned.get("blacklist_reason"):
            self.add_error(
                "blacklist_reason", "A reason is required when blacklisting a supplier."
            )
        return cleaned


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------


class MaterialCategoryForm(forms.ModelForm):
    class Meta:
        model = MaterialCategory
        fields = ["name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ["item_code", "description", "unit", "category", "min_stock_level"]


# ---------------------------------------------------------------------------
# Material Requisition
# ---------------------------------------------------------------------------


class MaterialRequisitionForm(forms.ModelForm):
    class Meta:
        model = MaterialRequisition
        fields = [
            "project",
            "requested_by",
            "date",
            "required_by_date",
            "justification",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "required_by_date": forms.DateInput(attrs={"type": "date"}),
            "justification": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        required_by = cleaned.get("required_by_date")
        if date and required_by and required_by < date:
            self.add_error(
                "required_by_date",
                "Required-by date cannot be before the requisition date.",
            )
        return cleaned


class MRItemForm(forms.ModelForm):
    class Meta:
        model = MRItem
        fields = [
            "material",
            "description",
            "unit",
            "quantity_requested",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("material") and not cleaned.get("description"):
            raise forms.ValidationError(
                "Either a catalogue material or a description must be provided."
            )
        return cleaned


MRItemFormSet = inlineformset_factory(
    MaterialRequisition,
    MRItem,
    form=MRItemForm,
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class MRRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Rejection Reason",
        help_text="Explain clearly why this requisition is being rejected.",
    )


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "project",
            "supplier",
            "mr",
            "date",
            "delivery_address",
            "expected_delivery_date",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class POItemForm(forms.ModelForm):
    class Meta:
        model = POItem
        fields = [
            "mr_item",
            "material",
            "description",
            "unit",
            "quantity",
            "unit_price",
        ]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("description"):
            raise forms.ValidationError("A description is required for each PO line.")
        return cleaned


POItemFormSet = inlineformset_factory(
    PurchaseOrder,
    POItem,
    form=POItemForm,
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# GRN
# ---------------------------------------------------------------------------


class GoodsReceivedNoteForm(forms.ModelForm):
    class Meta:
        model = GoodsReceivedNote
        fields = [
            "delivery_date",
            "delivered_by",
            "received_by",
            "condition_notes",
            "delivery_photo",
            "is_partial",
            "notes",
        ]
        widgets = {
            "delivery_date": forms.DateInput(attrs={"type": "date"}),
            "condition_notes": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class GRNItemForm(forms.ModelForm):
    class Meta:
        model = GRNItem
        fields = [
            "po_item",
            "quantity_delivered",
            "has_discrepancy",
            "discrepancy_notes",
        ]
        widgets = {
            "discrepancy_notes": forms.Textarea(attrs={"rows": 2}),
        }


# ---------------------------------------------------------------------------
# Supplier Invoice
# ---------------------------------------------------------------------------


class SupplierInvoiceForm(forms.ModelForm):
    class Meta:
        model = SupplierInvoice
        fields = [
            "invoice_number",
            "po",
            "supplier",
            "invoice_date",
            "amount",
            "document",
            "status",
            "is_matched",
            "match_exception_reason",
            "payment_date",
            "payment_reference",
            "notes",
        ]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].required = False
        self.fields["supplier"].disabled = True
        self.fields["is_matched"].required = False
        self.fields["is_matched"].disabled = True
        self.fields["match_exception_reason"].required = False

    def clean(self):
        cleaned = super().clean()
        po = cleaned.get("po")
        amount = cleaned.get("amount")
        if po:
            cleaned["supplier"] = po.supplier
        if po and amount is not None:
            self.instance.po = po
            self.instance.supplier = po.supplier
            self.instance.amount = amount
            is_matched, reason = self.instance.evaluate_match()
            cleaned["is_matched"] = is_matched
            if cleaned.get("status") in (
                SupplierInvoice.STATUS_MATCHED,
                SupplierInvoice.STATUS_APPROVED,
                SupplierInvoice.STATUS_PAID,
            ) and not (is_matched or self.instance.match_exception_approved):
                self.add_error("status", reason)
            if not is_matched and cleaned.get("match_exception_reason") == "":
                cleaned["match_exception_reason"] = reason
        return cleaned


# ---------------------------------------------------------------------------
# Stock Ledger
# ---------------------------------------------------------------------------


class StockLedgerForm(forms.ModelForm):
    class Meta:
        model = StockLedger
        fields = [
            "project",
            "material",
            "date",
            "transaction_type",
            "quantity",
            "reference",
            "recorded_by",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is not None and qty <= 0:
            raise forms.ValidationError("Quantity must be a positive number.")
        return qty
