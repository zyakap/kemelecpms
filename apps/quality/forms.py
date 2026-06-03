from django import forms

from .models import Defect, ITP, ITPItem, InspectionRecord, MaterialTestResult, NCR


def _apply_form_control(form):
    """Apply Bootstrap form-control class to all widgets."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(widget, forms.FileInput):
            widget.attrs.setdefault("class", "form-control")
        else:
            widget.attrs.setdefault("class", "form-control")


class ITPForm(forms.ModelForm):
    class Meta:
        model = ITP
        fields = ["title", "description", "trade_section", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
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


class ITPItemForm(forms.ModelForm):
    class Meta:
        model = ITPItem
        fields = [
            "sequence",
            "description",
            "inspection_type",
            "responsible_party",
            "acceptance_criteria",
            "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "acceptance_criteria": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, itp=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.itp = itp
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.itp:
            instance.itp = self.itp
        if commit:
            instance.save()
        return instance


class InspectionRecordForm(forms.ModelForm):
    class Meta:
        model = InspectionRecord
        fields = [
            "date",
            "inspector_name",
            "inspector_org",
            "location",
            "result",
            "notes",
            "document",
            "signed_off_by",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, itp_item=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.itp_item = itp_item
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.itp_item:
            instance.itp_item = self.itp_item
        if commit:
            instance.save()
        return instance


class NCRForm(forms.ModelForm):
    class Meta:
        model = NCR
        fields = [
            "description",
            "location",
            "trade_responsible",
            "severity",
            "raised_date",
            "corrective_action_required",
            "responsible_person",
            "due_date",
            "response",
            "status",
            "close_out_date",
            "close_out_notes",
            "itp_item",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "corrective_action_required": forms.Textarea(attrs={"rows": 3}),
            "response": forms.Textarea(attrs={"rows": 3}),
            "close_out_notes": forms.Textarea(attrs={"rows": 3}),
            "raised_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "close_out_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            # Restrict itp_item choices to this project's ITPs
            self.fields["itp_item"].queryset = ITPItem.objects.filter(
                itp__project=project
            ).select_related("itp")
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class MaterialTestResultForm(forms.ModelForm):
    class Meta:
        model = MaterialTestResult
        fields = [
            "test_type",
            "test_date",
            "location",
            "sample_reference",
            "specified_value",
            "actual_value",
            "passed",
            "lab_certificate",
            "ncr",
            "notes",
        ]
        widgets = {
            "test_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            self.fields["ncr"].queryset = NCR.objects.filter(project=project)
        _apply_form_control(self)
        self.fields["passed"].widget.attrs["class"] = "form-check-input"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class DefectForm(forms.ModelForm):
    class Meta:
        model = Defect
        fields = [
            "description",
            "location",
            "trade",
            "identified_date",
            "severity",
            "phase",
            "responsible_party",
            "target_rectification_date",
            "photo_before",
            "photo_after",
            "status",
            "close_out_date",
            "closed_by",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "identified_date": forms.DateInput(attrs={"type": "date"}),
            "target_rectification_date": forms.DateInput(attrs={"type": "date"}),
            "close_out_date": forms.DateInput(attrs={"type": "date"}),
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
