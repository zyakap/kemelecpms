from django import forms

from apps.accounts.models import User

from .models import (
    BoQItem,
    CostCode,
    CostEntry,
    Subcontract,
    SubcontractBackCharge,
    SubcontractClaim,
    SubcontractPerformanceReview,
)


class CostCodeForm(forms.ModelForm):
    class Meta:
        model = CostCode
        fields = [
            "code",
            "name",
            "category",
            "budget_amount",
            "forecast_etc",
            "provisional_sum",
            "contingency_drawdown",
            "is_contingency",
            "notes",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"placeholder": "e.g. 01.CIVIL.EARTHWORKS"}),
            "budget_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "forecast_etc": forms.NumberInput(attrs={"step": "0.01"}),
            "provisional_sum": forms.NumberInput(attrs={"step": "0.01"}),
            "contingency_drawdown": forms.NumberInput(attrs={"step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["is_contingency"].widget.attrs["class"] = "form-check-input"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned = super().clean()
        quantity = cleaned.get("quantity")
        unit_rate = cleaned.get("unit_rate")
        is_variation = cleaned.get("is_variation")
        variation = cleaned.get("variation")

        if quantity is not None and quantity < 0:
            self.add_error("quantity", "Quantity cannot be negative.")
        if unit_rate is not None and unit_rate < 0:
            self.add_error("unit_rate", "Unit rate cannot be negative.")
        if is_variation and not variation:
            self.add_error("variation", "Variation-linked BoQ items must reference the approved variation.")
        return cleaned

    def clean(self):
        cleaned = super().clean()
        for field_name in ("budget_amount", "forecast_etc", "provisional_sum", "contingency_drawdown"):
            value = cleaned.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, "Amount cannot be negative.")
        return cleaned


class BoQItemForm(forms.ModelForm):
    class Meta:
        model = BoQItem
        fields = [
            "item_number",
            "description",
            "unit",
            "quantity",
            "unit_rate",
            "cost_code",
            "trade_section",
            "is_variation",
            "variation",
        ]
        widgets = {
            "item_number": forms.TextInput(attrs={"placeholder": "e.g. 1.1.1"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "quantity": forms.NumberInput(attrs={"step": "0.0001"}),
            "unit_rate": forms.NumberInput(attrs={"step": "0.0001"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            self.fields["cost_code"].queryset = CostCode.objects.filter(project=project)
            self.fields["variation"].queryset = project.variations.all()
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get("amount")
        cost_code = cleaned.get("cost_code")
        boq_item = cleaned.get("boq_item")
        if amount is not None and amount <= 0:
            self.add_error("amount", "Cost entry amount must be greater than zero.")
        if cost_code and self.project and cost_code.project_id != self.project.pk:
            self.add_error("cost_code", "Cost code must belong to this project.")
        if boq_item and self.project and boq_item.project_id != self.project.pk:
            self.add_error("boq_item", "BoQ item must belong to this project.")
        return cleaned


class CostEntryForm(forms.ModelForm):
    class Meta:
        model = CostEntry
        fields = [
            "cost_code",
            "boq_item",
            "entry_type",
            "description",
            "supplier",
            "amount",
            "date",
            "reference",
            "document",
            "approved_by",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "amount": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            self.fields["cost_code"].queryset = CostCode.objects.filter(project=project)
            self.fields["boq_item"].queryset = BoQItem.objects.filter(project=project)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault("class", "form-control")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class SubcontractForm(forms.ModelForm):
    class Meta:
        model = Subcontract
        fields = [
            "trade",
            "company_name",
            "scope",
            "contract_value",
            "start_date",
            "end_date",
            "retention_held",
            "status",
            "user",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "scope": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "contract_value": forms.NumberInput(attrs={"step": "0.01"}),
            "retention_held": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields["user"].queryset = User.objects.filter(role=User.ROLE_SUBCONTRACTOR)
        self.fields["user"].required = False
        self.fields["user"].label = "Subcontractor Login Account"
        self.fields["user"].help_text = "Link a subcontractor user account for document upload access."
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["user"].widget.attrs["class"] = "form-select"
        self.fields["status"].widget.attrs["class"] = "form-select"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned = super().clean()
        contract_value = cleaned.get("contract_value")
        retention_held = cleaned.get("retention_held")
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if contract_value is not None and contract_value <= 0:
            self.add_error("contract_value", "Contract value must be greater than zero.")
        if retention_held is not None and retention_held < 0:
            self.add_error("retention_held", "Retention held cannot be negative.")
        if contract_value is not None and retention_held is not None and retention_held > contract_value:
            self.add_error("retention_held", "Retention held cannot exceed contract value.")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be before start date.")
        return cleaned


class SubcontractClaimForm(forms.ModelForm):
    class Meta:
        model = SubcontractClaim
        fields = [
            "period_from",
            "period_to",
            "submitted_date",
            "claimed_amount",
            "assessed_amount",
            "approved_amount",
            "retention_deducted",
            "backcharge_deducted",
            "amount_paid",
            "payment_date",
            "payment_reference",
            "status",
            "notes",
        ]
        widgets = {
            "period_from": forms.DateInput(attrs={"type": "date"}),
            "period_to": forms.DateInput(attrs={"type": "date"}),
            "submitted_date": forms.DateInput(attrs={"type": "date"}),
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "claimed_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "assessed_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "approved_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "retention_deducted": forms.NumberInput(attrs={"step": "0.01"}),
            "backcharge_deducted": forms.NumberInput(attrs={"step": "0.01"}),
            "amount_paid": forms.NumberInput(attrs={"step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, subcontract=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.subcontract = subcontract
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        period_from = cleaned.get("period_from")
        period_to = cleaned.get("period_to")
        submitted_date = cleaned.get("submitted_date")
        claimed = cleaned.get("claimed_amount")
        assessed = cleaned.get("assessed_amount") or 0
        approved = cleaned.get("approved_amount") or 0
        retention = cleaned.get("retention_deducted") or 0
        backcharge = cleaned.get("backcharge_deducted") or 0
        paid = cleaned.get("amount_paid") or 0
        payment_date = cleaned.get("payment_date")
        payment_reference = (cleaned.get("payment_reference") or "").strip()
        status = cleaned.get("status")

        if period_from and period_to and period_to < period_from:
            self.add_error("period_to", "Claim period end cannot be before start.")
        if period_to and submitted_date and submitted_date < period_to:
            self.add_error("submitted_date", "Submitted date cannot be before the claim period end.")
        for field_name in (
            "claimed_amount",
            "assessed_amount",
            "approved_amount",
            "retention_deducted",
            "backcharge_deducted",
            "amount_paid",
        ):
            value = cleaned.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, "Amount cannot be negative.")
        if claimed is not None and claimed <= 0:
            self.add_error("claimed_amount", "Claimed amount must be greater than zero.")
        if claimed is not None and assessed > claimed:
            self.add_error("assessed_amount", "Assessed amount cannot exceed claimed amount.")
        if approved > assessed:
            self.add_error("approved_amount", "Approved amount cannot exceed assessed amount.")
        if retention + backcharge > approved:
            self.add_error("retention_deducted", "Retention plus back-charge deductions cannot exceed approved amount.")
            self.add_error("backcharge_deducted", "Retention plus back-charge deductions cannot exceed approved amount.")
        net_approved = approved - retention - backcharge
        if paid > net_approved:
            self.add_error("amount_paid", "Paid amount cannot exceed net approved amount.")
        if status == SubcontractClaim.STATUS_PAID:
            if paid <= 0:
                self.add_error("amount_paid", "Paid claims must record a payment amount.")
            if not payment_date:
                self.add_error("payment_date", "Paid claims must record a payment date.")
            if not payment_reference:
                self.add_error("payment_reference", "Paid claims must record a payment reference.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.subcontract:
            instance.subcontract = self.subcontract
        if commit:
            instance.save()
        return instance


class SubcontractBackChargeForm(forms.ModelForm):
    class Meta:
        model = SubcontractBackCharge
        fields = [
            "date",
            "description",
            "amount",
            "recovered_from_claim",
            "status",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "amount": forms.NumberInput(attrs={"step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, subcontract=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.subcontract = subcontract
        if subcontract:
            self.fields["recovered_from_claim"].queryset = subcontract.claims.all()
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Back-charge amount must be greater than zero.")
        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.subcontract:
            instance.subcontract = self.subcontract
        if commit:
            instance.save()
        return instance


class SubcontractPerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = SubcontractPerformanceReview
        fields = [
            "review_date",
            "quality_score",
            "schedule_score",
            "safety_score",
            "commercial_score",
            "notes",
        ]
        widgets = {
            "review_date": forms.DateInput(attrs={"type": "date"}),
            "quality_score": forms.NumberInput(attrs={"min": "1", "max": "5"}),
            "schedule_score": forms.NumberInput(attrs={"min": "1", "max": "5"}),
            "safety_score": forms.NumberInput(attrs={"min": "1", "max": "5"}),
            "commercial_score": forms.NumberInput(attrs={"min": "1", "max": "5"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, subcontract=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.subcontract = subcontract
        self.user = user
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        for field_name in ("quality_score", "schedule_score", "safety_score", "commercial_score"):
            score = cleaned.get(field_name)
            if score is not None and not 1 <= score <= 5:
                self.add_error(field_name, "Score must be between 1 and 5.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.subcontract:
            instance.subcontract = self.subcontract
        if self.user:
            instance.reviewer = self.user
        if commit:
            instance.save()
        return instance
