from django import forms

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)


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

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance
