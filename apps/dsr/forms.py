"""
DSR forms for kemelecpms.
"""

from django import forms
from django.forms import inlineformset_factory

from .models import (
    DailySiteReport,
    DSRActivity,
    DSREquipment,
    DSRIssue,
    DSRLabour,
    DSRMaterialDelivery,
    DSRMaterialUsage,
    DSRPhoto,
    DSRVisitor,
    WEATHER_CHOICES,
)


# ---------------------------------------------------------------------------
# DSR Header form
# ---------------------------------------------------------------------------


class DSRForm(forms.ModelForm):
    class Meta:
        model = DailySiteReport
        fields = [
            "project",
            "date",
            "weather_am",
            "weather_pm",
            "prepared_by",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        project = cleaned.get("project")
        date = cleaned.get("date")
        # On create, enforce unique_together at form level for a clearer error
        if project and date:
            qs = DailySiteReport.objects.filter(project=project, date=date)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"A Daily Site Report already exists for {project} on {date}."
                )
        return cleaned


# ---------------------------------------------------------------------------
# DSR Activity form and formset
# ---------------------------------------------------------------------------


class DSRActivityForm(forms.ModelForm):
    class Meta:
        model = DSRActivity
        fields = [
            "wbs_activity",
            "description",
            "location_on_site",
            "status",
            "quantity_achieved",
            "unit",
            "percent_complete",
            "constraints",
            "crew",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "location_on_site": forms.TextInput(attrs={"class": "form-control"}),
            "constraints": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_percent_complete(self):
        pct = self.cleaned_data.get("percent_complete")
        if pct is not None and (pct < 0 or pct > 100):
            raise forms.ValidationError("Percentage must be between 0 and 100.")
        return pct


DSRActivityFormSet = inlineformset_factory(
    DailySiteReport,
    DSRActivity,
    form=DSRActivityForm,
    extra=2,
    min_num=0,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# DSR Labour form and formset
# ---------------------------------------------------------------------------


class DSRLabourForm(forms.ModelForm):
    class Meta:
        model = DSRLabour
        fields = ["classification", "nationality", "count"]

    def clean_count(self):
        count = self.cleaned_data.get("count")
        if count is not None and count < 0:
            raise forms.ValidationError("Count cannot be negative.")
        return count


DSRLabourFormSet = inlineformset_factory(
    DailySiteReport,
    DSRLabour,
    form=DSRLabourForm,
    extra=3,
    min_num=0,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# DSR Visitor form and formset
# ---------------------------------------------------------------------------


class DSRVisitorForm(forms.ModelForm):
    class Meta:
        model = DSRVisitor
        fields = ["name", "organization", "purpose", "time_in", "time_out"]
        widgets = {
            "time_in": forms.TimeInput(attrs={"type": "time"}),
            "time_out": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        time_in = cleaned.get("time_in")
        time_out = cleaned.get("time_out")
        if time_in and time_out and time_out <= time_in:
            self.add_error("time_out", "Time-out must be after time-in.")
        return cleaned


DSRVisitorFormSet = inlineformset_factory(
    DailySiteReport,
    DSRVisitor,
    form=DSRVisitorForm,
    extra=1,
    min_num=0,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# DSR Equipment form and formset
# ---------------------------------------------------------------------------


class DSREquipmentForm(forms.ModelForm):
    class Meta:
        model = DSREquipment
        fields = [
            "equipment",
            "hours_worked",
            "hours_idle",
            "hours_breakdown",
            "notes",
        ]

    def clean(self):
        cleaned = super().clean()
        worked = cleaned.get("hours_worked") or 0
        idle = cleaned.get("hours_idle") or 0
        breakdown = cleaned.get("hours_breakdown") or 0
        total = worked + idle + breakdown
        if total > 24:
            raise forms.ValidationError(
                "Total hours (worked + idle + breakdown) cannot exceed 24 hours."
            )
        return cleaned


DSREquipmentFormSet = inlineformset_factory(
    DailySiteReport,
    DSREquipment,
    form=DSREquipmentForm,
    extra=1,
    min_num=0,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# DSR Material Usage form and formset
# ---------------------------------------------------------------------------


class DSRMaterialUsageForm(forms.ModelForm):
    class Meta:
        model = DSRMaterialUsage
        fields = ["material", "quantity_used", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_quantity_used(self):
        qty = self.cleaned_data.get("quantity_used")
        if qty is not None and qty <= 0:
            raise forms.ValidationError("Quantity must be positive.")
        return qty


DSRMaterialUsageFormSet = inlineformset_factory(
    DailySiteReport,
    DSRMaterialUsage,
    form=DSRMaterialUsageForm,
    extra=2,
    min_num=0,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# DSR Photo form
# ---------------------------------------------------------------------------


class DSRPhotoForm(forms.ModelForm):
    class Meta:
        model = DSRPhoto
        fields = ["photo", "caption", "tag", "gps_lat", "gps_lng"]
        widgets = {
            "caption": forms.TextInput(attrs={"placeholder": "Brief description of photo"}),
        }


# ---------------------------------------------------------------------------
# DSR Issue form
# ---------------------------------------------------------------------------


class DSRIssueForm(forms.ModelForm):
    class Meta:
        model = DSRIssue
        fields = [
            "issue_type",
            "description",
            "raised_by",
            "date",
            "action_required",
            "resolved",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "action_required": forms.Textarea(attrs={"rows": 3}),
        }


DSRIssueFormSet = inlineformset_factory(
    DailySiteReport,
    DSRIssue,
    form=DSRIssueForm,
    extra=1,
    min_num=0,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# DSR Return form (enter return reason)
# ---------------------------------------------------------------------------


class DSRReturnForm(forms.Form):
    return_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Return Reason",
        help_text="Explain what needs to be corrected before re-submission.",
    )
