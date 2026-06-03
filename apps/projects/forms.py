from django import forms

from .models import (
    Client,
    Contract,
    DelayEvent,
    Funder,
    Milestone,
    Project,
    Variation,
)


# ---------------------------------------------------------------------------
# Shared widget helper
# ---------------------------------------------------------------------------

def _text(placeholder="", **extra):
    attrs = {"class": "form-control"}
    if placeholder:
        attrs["placeholder"] = placeholder
    attrs.update(extra)
    return forms.TextInput(attrs=attrs)


def _date():
    return forms.DateInput(attrs={"class": "form-control", "type": "date"})


def _select():
    return forms.Select(attrs={"class": "form-select"})


def _textarea(rows=4, placeholder=""):
    attrs = {"class": "form-control", "rows": rows}
    if placeholder:
        attrs["placeholder"] = placeholder
    return forms.Textarea(attrs=attrs)


def _number():
    return forms.NumberInput(attrs={"class": "form-control"})


def _file():
    return forms.ClearableFileInput(attrs={"class": "form-control"})


# ---------------------------------------------------------------------------
# Client Form
# ---------------------------------------------------------------------------


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = (
            "name",
            "client_type",
            "contact_person",
            "email",
            "phone",
            "address",
        )
        widgets = {
            "name": _text("e.g. Department of Works & Implementation"),
            "client_type": _select(),
            "contact_person": _text("Full name"),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": _text("+675 ..."),
            "address": _textarea(rows=3),
        }


# ---------------------------------------------------------------------------
# Funder Form
# ---------------------------------------------------------------------------


class FunderForm(forms.ModelForm):
    class Meta:
        model = Funder
        fields = (
            "name",
            "funder_type",
            "contact_person",
            "email",
            "phone",
        )
        widgets = {
            "name": _text("e.g. Asian Development Bank"),
            "funder_type": _select(),
            "contact_person": _text("Full name"),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": _text("+675 ..."),
        }


# ---------------------------------------------------------------------------
# Project Form
# ---------------------------------------------------------------------------


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ("project_id", "created_by", "updated_by", "created_at", "updated_at")
        widgets = {
            "name": _text("Project name"),
            "description": _textarea(rows=4, placeholder="Brief description of the project scope"),
            "project_type": _select(),
            "status": _select(),
            "province": _text("e.g. Western Highlands"),
            "district": _text("e.g. Hagen Central"),
            "site_address": _textarea(rows=3, placeholder="Physical site address"),
            "gps_lat": _number(),
            "gps_lng": _number(),
            "project_manager": _select(),
            "site_supervisor": _select(),
            "client": _select(),
            "funder": _select(),
            "thumbnail": _file(),
            "start_date": _date(),
            "target_completion_date": _date(),
            "actual_completion_date": _date(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make optional fields explicitly optional
        for field_name in (
            "description",
            "province",
            "district",
            "site_address",
            "gps_lat",
            "gps_lng",
            "site_supervisor",
            "funder",
            "thumbnail",
            "start_date",
            "target_completion_date",
            "actual_completion_date",
        ):
            if field_name in self.fields:
                self.fields[field_name].required = False


# ---------------------------------------------------------------------------
# Contract Form
# ---------------------------------------------------------------------------


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        exclude = ("project", "created_by", "updated_by", "created_at", "updated_at")
        widgets = {
            "contract_number": _text("e.g. DoW-2024-001"),
            "contract_type": _select(),
            "original_value": _number(),
            "start_date": _date(),
            "original_completion_date": _date(),
            "revised_completion_date": _date(),
            "liquidated_damages_rate": _number(),
            "dlp_months": _number(),
            "retention_percentage": _number(),
            "retention_cap_percentage": _number(),
            "payment_terms_days": _number(),
            "letter_of_award": _file(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["revised_completion_date"].required = False
        self.fields["liquidated_damages_rate"].required = False
        self.fields["letter_of_award"].required = False


# ---------------------------------------------------------------------------
# Variation Form
# ---------------------------------------------------------------------------


class VariationForm(forms.ModelForm):
    class Meta:
        model = Variation
        exclude = (
            "project",
            "ref_number",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        widgets = {
            "description": _textarea(rows=4, placeholder="Describe the scope of the variation"),
            "date_instructed": _date(),
            "status": _select(),
            "variation_type": _select(),
            "amount": _number(),
            "supporting_document": _file(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supporting_document"].required = False


# ---------------------------------------------------------------------------
# Milestone Form
# ---------------------------------------------------------------------------


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        exclude = (
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        widgets = {
            "name": _text("e.g. Practical Completion"),
            "milestone_type": _select(),
            "target_date": _date(),
            "actual_date": _date(),
            "is_achieved": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": _textarea(rows=3),
            "evidence": _file(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["actual_date"].required = False
        self.fields["description"].required = False
        self.fields["evidence"].required = False


# ---------------------------------------------------------------------------
# Delay Event Form
# ---------------------------------------------------------------------------


class DelayEventForm(forms.ModelForm):
    class Meta:
        model = DelayEvent
        exclude = (
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        widgets = {
            "date": _date(),
            "description": _textarea(rows=4, placeholder="Describe the delay event and its impact"),
            "delay_type": _select(),
            "responsible_party": _select(),
            "impact_days": _number(),
            "linked_milestone": _select(),
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        self.fields["linked_milestone"].required = False
        if project is not None:
            self.fields["linked_milestone"].queryset = Milestone.objects.filter(
                project=project
            )
        else:
            self.fields["linked_milestone"].queryset = Milestone.objects.none()
