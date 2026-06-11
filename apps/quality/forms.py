from django import forms
from django.utils import timezone

from .models import (
    Defect,
    ITP,
    ITPItem,
    InspectionChecklist,
    InspectionChecklistItem,
    InspectionRecord,
    MaterialTestResult,
    NCR,
)


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

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.user = user
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        if self.instance.pk and status in (ITP.STATUS_COMPLETE, ITP.STATUS_CLOSED):
            if self.instance.total_items == 0:
                self.add_error("status", "ITP cannot be completed or closed without inspection items.")
            elif self.instance.passed_items < self.instance.total_items:
                self.add_error("status", "All ITP items must pass before the ITP can be completed or closed.")
        return cleaned

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
            "hold_point_released_by",
            "hold_point_released_date",
            "witness_signed_by",
            "witness_signed_date",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "acceptance_criteria": forms.Textarea(attrs={"rows": 3}),
            "hold_point_released_date": forms.DateInput(attrs={"type": "date"}),
            "witness_signed_date": forms.DateInput(attrs={"type": "date"}),
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


class InspectionChecklistForm(forms.ModelForm):
    class Meta:
        model = InspectionChecklist
        fields = [
            "title",
            "location",
            "inspection_date",
            "inspected_by",
            "signed_off_by",
            "signed_off_date",
            "notes",
        ]
        widgets = {
            "inspection_date": forms.DateInput(attrs={"type": "date"}),
            "signed_off_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, itp=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.itp = itp
        self.user = user
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.itp:
            instance.itp = self.itp
        if self.user and not instance.inspected_by_id:
            instance.inspected_by = self.user
        if commit:
            instance.save()
        return instance


class InspectionChecklistItemForm(forms.ModelForm):
    class Meta:
        model = InspectionChecklistItem
        fields = ["description", "acceptance_criteria", "passed", "comments", "evidence"]
        widgets = {
            "comments": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, checklist=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.checklist = checklist
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.checklist:
            instance.checklist = self.checklist
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

    def clean(self):
        cleaned = super().clean()
        result = cleaned.get("result")
        notes = (cleaned.get("notes") or "").strip()
        if result in (InspectionRecord.RESULT_FAIL, InspectionRecord.RESULT_CONDITIONAL) and not notes:
            self.add_error("notes", "Notes are required for failed or conditional inspections.")
        return cleaned

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
            "root_cause",
            "corrective_action",
            "preventive_action",
            "status",
            "close_out_date",
            "close_out_notes",
            "closure_evidence",
            "itp_item",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "corrective_action_required": forms.Textarea(attrs={"rows": 3}),
            "response": forms.Textarea(attrs={"rows": 3}),
            "root_cause": forms.Textarea(attrs={"rows": 3}),
            "corrective_action": forms.Textarea(attrs={"rows": 3}),
            "preventive_action": forms.Textarea(attrs={"rows": 3}),
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

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        raised_date = cleaned.get("raised_date")
        due_date = cleaned.get("due_date")
        response = (cleaned.get("response") or "").strip()
        close_out_date = cleaned.get("close_out_date")
        close_out_notes = (cleaned.get("close_out_notes") or "").strip()
        root_cause = (cleaned.get("root_cause") or "").strip()
        corrective_action = (cleaned.get("corrective_action") or "").strip()
        preventive_action = (cleaned.get("preventive_action") or "").strip()

        if raised_date and due_date and due_date < raised_date:
            self.add_error("due_date", "Due date cannot be before the NCR raised date.")
        if status == NCR.STATUS_UNDER_REVIEW and not response:
            self.add_error("response", "A response is required before moving an NCR under review.")
        if status == NCR.STATUS_CLOSED:
            if not response:
                self.add_error("response", "A response is required before closing an NCR.")
            if not root_cause:
                self.add_error("root_cause", "Root cause is required before closing an NCR.")
            if not corrective_action:
                self.add_error("corrective_action", "Corrective action is required before closing an NCR.")
            if not preventive_action:
                self.add_error("preventive_action", "Preventive action is required before closing an NCR.")
            if not close_out_notes:
                self.add_error("close_out_notes", "Close-out notes are required before closing an NCR.")
            if not close_out_date:
                cleaned["close_out_date"] = timezone.now().date()
                close_out_date = cleaned["close_out_date"]
        if raised_date and close_out_date and close_out_date < raised_date:
            self.add_error("close_out_date", "Close-out date cannot be before the NCR raised date.")
        return cleaned

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

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.user = user
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        identified_date = cleaned.get("identified_date")
        target_date = cleaned.get("target_rectification_date")
        close_out_date = cleaned.get("close_out_date")
        photo_after = cleaned.get("photo_after")
        closed_by = cleaned.get("closed_by") or self.user

        if identified_date and target_date and target_date < identified_date:
            self.add_error(
                "target_rectification_date",
                "Target rectification date cannot be before the identified date.",
            )
        if status in (Defect.STATUS_RECTIFIED, Defect.STATUS_CLOSED) and not photo_after:
            self.add_error("photo_after", "After photo/evidence is required before a defect is rectified or closed.")
        if status == Defect.STATUS_CLOSED:
            if closed_by:
                cleaned["closed_by"] = closed_by
            if not close_out_date:
                cleaned["close_out_date"] = timezone.now().date()
                close_out_date = cleaned["close_out_date"]
            if not closed_by:
                self.add_error("closed_by", "Closed by is required before a defect can be closed.")
        if identified_date and close_out_date and close_out_date < identified_date:
            self.add_error("close_out_date", "Close-out date cannot be before the identified date.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance
