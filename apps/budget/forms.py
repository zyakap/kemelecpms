from django import forms

from .models import BoQItem, CostCode, CostEntry, Subcontract


class CostCodeForm(forms.ModelForm):
    class Meta:
        model = CostCode
        fields = [
            "code",
            "name",
            "category",
            "budget_amount",
            "is_contingency",
            "notes",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"placeholder": "e.g. 01.CIVIL.EARTHWORKS"}),
            "budget_amount": forms.NumberInput(attrs={"step": "0.01"}),
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
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance
