"""
Safety forms for kemelecpms.
"""

from django import forms
from django.utils import timezone

from .models import (
    HazardRisk,
    Incident,
    PPEIssue,
    SafetyInduction,
    PermitToWork,
    SafetyCorrectiveAction,
    SafetyObservation,
    SafetyTrainingRecord,
    SWMS,
    ToolboxAttendee,
    ToolboxTalk,
)


# ---------------------------------------------------------------------------
# Safety Induction
# ---------------------------------------------------------------------------


class SafetyInductionForm(forms.ModelForm):
    class Meta:
        model = SafetyInduction
        fields = [
            "project",
            "worker",
            "date",
            "topics_covered",
            "inducted_by",
            "expiry_date",
            "acknowledged",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "topics_covered": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        expiry = cleaned.get("expiry_date")
        if date and expiry and expiry <= date:
            self.add_error(
                "expiry_date", "Expiry date must be after the induction date."
            )
        return cleaned


# ---------------------------------------------------------------------------
# Toolbox Talk
# ---------------------------------------------------------------------------


class ToolboxTalkForm(forms.ModelForm):
    class Meta:
        model = ToolboxTalk
        fields = ["project", "date", "topic", "presenter", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


# ---------------------------------------------------------------------------
# Incident
# ---------------------------------------------------------------------------


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = [
            "project",
            "date",
            "time",
            "location",
            "incident_type",
            "description",
            "persons_involved",
            "body_part",
            "injury_nature",
            "treatment_given",
            "is_lti",
            "days_lost",
            "reported_by",
            "status",
            "corrective_action",
            "corrective_action_due",
            "corrective_action_person",
            "corrective_action_closed",
            "photo",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "persons_involved": forms.Textarea(attrs={"rows": 3}),
            "treatment_given": forms.Textarea(attrs={"rows": 3}),
            "corrective_action": forms.Textarea(attrs={"rows": 4}),
            "corrective_action_due": forms.DateInput(attrs={"type": "date"}),
            "corrective_action_closed": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        is_lti = cleaned.get("is_lti")
        days_lost = cleaned.get("days_lost")
        incident_type = cleaned.get("incident_type")

        if incident_type == Incident.TYPE_LTI:
            cleaned["is_lti"] = True

        if is_lti and (days_lost is None or days_lost < 1):
            self.add_error(
                "days_lost", "LTI incidents must record at least 1 day lost."
            )

        due = cleaned.get("corrective_action_due")
        closed = cleaned.get("corrective_action_closed")
        status = cleaned.get("status")
        corrective_action = (cleaned.get("corrective_action") or "").strip()
        corrective_person = cleaned.get("corrective_action_person")
        if due and closed and closed < due:
            self.add_error(
                "corrective_action_closed",
                "Closed date cannot be before the due date.",
            )
        if status == Incident.STATUS_INVESTIGATING and not corrective_action:
            self.add_error("corrective_action", "Corrective action is required while an incident is under investigation.")
        if status == Incident.STATUS_CLOSED:
            if not corrective_action:
                self.add_error("corrective_action", "Corrective action is required before closing an incident.")
            if not corrective_person:
                self.add_error("corrective_action_person", "Corrective action owner is required before closing an incident.")
            if not closed:
                cleaned["corrective_action_closed"] = timezone.now().date()
        return cleaned


# ---------------------------------------------------------------------------
# Hazard Risk
# ---------------------------------------------------------------------------


class HazardRiskForm(forms.ModelForm):
    class Meta:
        model = HazardRisk
        fields = [
            "project",
            "activity",
            "hazard_description",
            "likelihood",
            "consequence",
            "control_measure",
            "control_type",
            "reviewed_by",
            "reviewed_date",
        ]
        widgets = {
            "hazard_description": forms.Textarea(attrs={"rows": 3}),
            "control_measure": forms.Textarea(attrs={"rows": 3}),
            "reviewed_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        reviewed_by = cleaned.get("reviewed_by")
        reviewed_date = cleaned.get("reviewed_date")
        if reviewed_by and not reviewed_date:
            cleaned["reviewed_date"] = timezone.now().date()
        if reviewed_date and not reviewed_by:
            self.add_error("reviewed_by", "Reviewer is required when a reviewed date is recorded.")
        return cleaned


# ---------------------------------------------------------------------------
# SWMS
# ---------------------------------------------------------------------------


class SWMSForm(forms.ModelForm):
    class Meta:
        model = SWMS
        fields = [
            "project",
            "title",
            "activity",
            "version",
            "status",
            "document",
            "approved_by",
            "approved_date",
        ]
        widgets = {
            "approved_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        approved_by = cleaned.get("approved_by") or self.user
        approved_date = cleaned.get("approved_date")
        if status == SWMS.STATUS_APPROVED:
            if approved_by:
                cleaned["approved_by"] = approved_by
            if not approved_date:
                cleaned["approved_date"] = timezone.now().date()
                approved_date = cleaned["approved_date"]
            if not approved_by:
                self.add_error("approved_by", "An approver is required for approved SWMS.")
            if not approved_date:
                self.add_error(
                    "approved_date", "An approval date is required for approved SWMS."
                )
        return cleaned


# ---------------------------------------------------------------------------
# PPE Issue
# ---------------------------------------------------------------------------


class PPEIssueForm(forms.ModelForm):
    class Meta:
        model = PPEIssue
        fields = [
            "project",
            "worker",
            "ppe_type",
            "size",
            "quantity",
            "date_issued",
            "issued_by",
            "notes",
        ]
        widgets = {
            "date_issued": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is not None and qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return qty


class PermitToWorkForm(forms.ModelForm):
    class Meta:
        model = PermitToWork
        exclude = ("permit_number", "created_by", "updated_by", "created_at", "updated_at")
        widgets = {
            "valid_from": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "valid_to": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "approved_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "closed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "controls": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, projects=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if projects is not None:
            self.fields["project"].queryset = projects
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        valid_from = cleaned.get("valid_from")
        valid_to = cleaned.get("valid_to")
        status = cleaned.get("status")
        approved_by = cleaned.get("approved_by") or self.user
        closed_by = cleaned.get("closed_by") or self.user
        if valid_from and valid_to and valid_to <= valid_from:
            self.add_error("valid_to", "Permit valid-to time must be after valid-from time.")
        if status == PermitToWork.STATUS_APPROVED:
            if not cleaned.get("controls"):
                self.add_error("controls", "Controls must be recorded before a permit can be approved.")
            if approved_by:
                cleaned["approved_by"] = approved_by
            if not cleaned.get("approved_at"):
                cleaned["approved_at"] = timezone.now()
        if status == PermitToWork.STATUS_CLOSED:
            if cleaned.get("approved_at") is None and cleaned.get("status") != PermitToWork.STATUS_APPROVED:
                self.add_error("status", "Only approved permits can be closed.")
            if closed_by:
                cleaned["closed_by"] = closed_by
            if not cleaned.get("closed_at"):
                cleaned["closed_at"] = timezone.now()
        return cleaned


class SafetyTrainingRecordForm(forms.ModelForm):
    class Meta:
        model = SafetyTrainingRecord
        exclude = ("created_by", "updated_by", "created_at", "updated_at")
        widgets = {
            "completed_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, projects=None, **kwargs):
        super().__init__(*args, **kwargs)
        if projects is not None:
            self.fields["project"].queryset = projects
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        completed = cleaned.get("completed_date")
        expiry = cleaned.get("expiry_date")
        if completed and expiry and expiry <= completed:
            self.add_error("expiry_date", "Expiry date must be after completed date.")
        return cleaned


class SafetyObservationForm(forms.ModelForm):
    class Meta:
        model = SafetyObservation
        exclude = ("created_by", "updated_by", "created_at", "updated_at")
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "immediate_action": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, projects=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if projects is not None:
            self.fields["project"].queryset = projects
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("observation_type") == SafetyObservation.TYPE_UNSAFE and not cleaned.get("immediate_action"):
            self.add_error("immediate_action", "Immediate action is required for unsafe observations.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and not instance.observed_by_id:
            instance.observed_by = self.user
        if commit:
            instance.save()
        return instance


class SafetyCorrectiveActionForm(forms.ModelForm):
    class Meta:
        model = SafetyCorrectiveAction
        exclude = ("created_by", "updated_by", "created_at", "updated_at")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "close_out_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, projects=None, **kwargs):
        super().__init__(*args, **kwargs)
        if projects is not None:
            self.fields["project"].queryset = projects
            self.fields["incident"].queryset = Incident.objects.filter(project__in=projects)
            self.fields["observation"].queryset = SafetyObservation.objects.filter(project__in=projects)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        project = cleaned.get("project")
        incident = cleaned.get("incident")
        observation = cleaned.get("observation")
        if project and incident and incident.project_id != project.id:
            self.add_error("incident", "Incident must belong to the selected project.")
        if project and observation and observation.project_id != project.id:
            self.add_error("observation", "Observation must belong to the selected project.")
        if status == SafetyCorrectiveAction.STATUS_CLOSED:
            if not cleaned.get("close_out_notes"):
                self.add_error("close_out_notes", "Close-out notes are required before closing.")
            if not cleaned.get("close_out_evidence"):
                self.add_error("close_out_evidence", "Closure evidence is required before closing.")
            if not cleaned.get("closed_date"):
                cleaned["closed_date"] = timezone.now().date()
        return cleaned
