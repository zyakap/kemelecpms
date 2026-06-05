from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Certification, IPC, IPCLineItem, Payment, RetentionRelease


def _apply_form_control(form):
    """Apply Bootstrap form-control class to all visible widgets."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        else:
            widget.attrs.setdefault("class", "form-control")


class IPCForm(forms.ModelForm):
    class Meta:
        model = IPC
        fields = [
            "claim_period_from",
            "claim_period_to",
            "submitted_date",
            "status",
            "notes",
        ]
        widgets = {
            "claim_period_from": forms.DateInput(attrs={"type": "date"}),
            "claim_period_to": forms.DateInput(attrs={"type": "date"}),
            "submitted_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("claim_period_from")
        end = cleaned.get("claim_period_to")
        submitted_date = cleaned.get("submitted_date")
        if start and end and end < start:
            self.add_error("claim_period_to", "Claim period end cannot be before the start date.")
        if end and submitted_date and submitted_date < end:
            self.add_error("submitted_date", "Submitted date cannot be before the claim period end.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class IPCLineItemForm(forms.ModelForm):
    class Meta:
        model = IPCLineItem
        fields = [
            "boq_item",
            "boq_description",
            "boq_quantity",
            "unit_rate",
            "previous_percent",
            "current_percent",
        ]

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            from apps.budget.models import BoQItem
            self.fields["boq_item"].queryset = BoQItem.objects.filter(
                project=project
            ).order_by("item_number")
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        previous = cleaned.get("previous_percent") or Decimal("0.00")
        current = cleaned.get("current_percent") or Decimal("0.00")
        if previous < 0:
            self.add_error("previous_percent", "Previous progress cannot be negative.")
        if current < 0:
            self.add_error("current_percent", "Current claim progress cannot be negative.")
        if previous + current > 100:
            raise ValidationError("Cumulative claimed progress cannot exceed 100%.")
        return cleaned


class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        fields = [
            "certified_by",
            "certifier_org",
            "certified_date",
            "amount_certified",
            "retention_deducted",
            "net_certified",
            "disputed_items",
            "notes",
        ]
        widgets = {
            "certified_date": forms.DateInput(attrs={"type": "date"}),
            "disputed_items": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, ipc=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ipc = ipc
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        amount_certified = cleaned.get("amount_certified")
        retention = cleaned.get("retention_deducted") or Decimal("0.00")
        net = cleaned.get("net_certified")
        if amount_certified is not None and amount_certified <= 0:
            self.add_error("amount_certified", "Certified amount must be greater than zero.")
        if retention < 0:
            self.add_error("retention_deducted", "Retention cannot be negative.")
        if net is not None and net < 0:
            self.add_error("net_certified", "Net certified cannot be negative.")
        if amount_certified is not None and retention > amount_certified:
            self.add_error("retention_deducted", "Retention cannot exceed the certified amount.")
        if amount_certified is not None and net is not None and net > amount_certified:
            self.add_error("net_certified", "Net certified cannot exceed the certified amount.")
        if amount_certified is not None and net is not None and net != amount_certified - retention:
            self.add_error("net_certified", "Net certified must equal certified amount less retention.")
        if self.ipc and amount_certified is not None and self.ipc.total_claimed <= 0:
            self.add_error("amount_certified", "Cannot certify an IPC with no claimed value.")
        if self.ipc and amount_certified is not None and amount_certified > self.ipc.total_claimed:
            self.add_error("amount_certified", "Certified amount cannot exceed the IPC claimed value.")
        return cleaned


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "payment_date",
            "amount",
            "payment_reference",
            "received_by",
            "notes",
        ]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, ipc=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ipc = ipc
        self.fields["received_by"].required = False
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get("amount")
        if amount is not None and amount <= 0:
            self.add_error("amount", "Payment amount must be greater than zero.")
        if self.ipc and not hasattr(self.ipc, "certification"):
            self.add_error("amount", "Payment cannot be recorded before IPC certification.")
        if self.ipc and amount is not None:
            outstanding = self.ipc.amount_outstanding
            if self.instance.pk:
                outstanding += self.instance.amount
            if amount > outstanding:
                self.add_error("amount", "Payment cannot exceed the outstanding certified amount.")
        return cleaned


class RetentionReleaseForm(forms.ModelForm):
    class Meta:
        model = RetentionRelease
        fields = [
            "release_type",
            "amount",
            "release_date",
            "approved_by",
        ]
        widgets = {
            "release_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get("amount")
        if amount is not None and amount <= 0:
            self.add_error("amount", "Retention release amount must be greater than zero.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance
