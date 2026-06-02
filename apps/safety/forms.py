"""
Safety forms for kemelecpms.
"""

from django import forms

from .models import (
    HazardRisk,
    Incident,
    PPEIssue,
    SafetyInduction,
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
        if due and closed and closed < due:
            self.add_error(
                "corrective_action_closed",
                "Closed date cannot be before the due date.",
            )
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

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        approved_by = cleaned.get("approved_by")
        approved_date = cleaned.get("approved_date")
        if status == SWMS.STATUS_APPROVED:
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
