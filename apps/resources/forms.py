from django import forms

from .models import (
    AttendanceRecord,
    Crew,
    CrewMember,
    Equipment,
    EquipmentAllocation,
    EquipmentUtilisation,
    SubcontractorCompany,
    Worker,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _apply_form_control(form):
    """Apply Bootstrap form-control class to all fields."""
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(field.widget, forms.FileInput):
            field.widget.attrs.setdefault("class", "form-control")
        else:
            field.widget.attrs.setdefault("class", "form-control")


# ---------------------------------------------------------------------------
# Worker forms
# ---------------------------------------------------------------------------


class WorkerForm(forms.ModelForm):
    class Meta:
        model = Worker
        fields = [
            "first_name",
            "last_name",
            "gender",
            "nationality",
            "occupation",
            "trade",
            "classification",
            "employment_type",
            "nid_number",
            "tfn",
            "phone",
            "emergency_contact",
            "project",
            "is_active",
            "date_joined",
        ]
        widgets = {
            "date_joined": forms.DateInput(attrs={"type": "date"}),
            "emergency_contact": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)


# ---------------------------------------------------------------------------
# Crew forms
# ---------------------------------------------------------------------------


class CrewForm(forms.ModelForm):
    class Meta:
        model = Crew
        fields = ["name", "foreman", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            self.fields["foreman"].queryset = Worker.objects.filter(
                project=project, is_active=True
            )
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class CrewMemberForm(forms.ModelForm):
    class Meta:
        model = CrewMember
        fields = ["worker", "date_joined", "date_left"]
        widgets = {
            "date_joined": forms.DateInput(attrs={"type": "date"}),
            "date_left": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, crew=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.crew = crew
        if crew:
            # Only show active workers from the same project, not already in this crew
            existing = CrewMember.objects.filter(crew=crew).values_list("worker_id", flat=True)
            self.fields["worker"].queryset = Worker.objects.filter(
                project=crew.project, is_active=True
            ).exclude(pk__in=existing)
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.crew:
            instance.crew = self.crew
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# Attendance forms
# ---------------------------------------------------------------------------


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = [
            "worker",
            "crew",
            "date",
            "time_in",
            "time_out",
            "overtime_hours",
            "is_present",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time_in": forms.TimeInput(attrs={"type": "time"}),
            "time_out": forms.TimeInput(attrs={"type": "time"}),
            "overtime_hours": forms.NumberInput(attrs={"step": "0.25"}),
            "notes": forms.TextInput(),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            self.fields["worker"].queryset = Worker.objects.filter(
                project=project, is_active=True
            ).order_by("last_name", "first_name")
            self.fields["crew"].queryset = Crew.objects.filter(project=project)
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class AttendanceBulkForm(forms.Form):
    """
    Bulk attendance form: records presence/absence for multiple workers on a single date.
    Constructed dynamically with one row per active worker.
    """

    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            workers = Worker.objects.filter(project=project, is_active=True).order_by(
                "last_name", "first_name"
            )
            for worker in workers:
                self.fields[f"present_{worker.pk}"] = forms.BooleanField(
                    required=False,
                    initial=True,
                    label=worker.full_name,
                    widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
                )
                self.fields[f"overtime_{worker.pk}"] = forms.DecimalField(
                    required=False,
                    initial=0,
                    min_value=0,
                    label="OT Hours",
                    widget=forms.NumberInput(
                        attrs={"step": "0.25", "class": "form-control form-control-sm"}
                    ),
                )


# ---------------------------------------------------------------------------
# Equipment forms
# ---------------------------------------------------------------------------


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = [
            "description",
            "equipment_type",
            "ownership_type",
            "supplier",
            "model",
            "year",
            "registration_number",
            "is_active",
        ]
        widgets = {
            "year": forms.NumberInput(attrs={"min": 1950, "max": 2100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)


class EquipmentAllocationForm(forms.ModelForm):
    class Meta:
        model = EquipmentAllocation
        fields = [
            "equipment",
            "allocated_date",
            "return_date",
            "hire_rate_daily",
            "notes",
        ]
        widgets = {
            "allocated_date": forms.DateInput(attrs={"type": "date"}),
            "return_date": forms.DateInput(attrs={"type": "date"}),
            "hire_rate_daily": forms.NumberInput(attrs={"step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        # Only offer equipment that is currently not allocated (return_date is null)
        # or allow re-allocation after return. Show all active equipment.
        self.fields["equipment"].queryset = Equipment.objects.filter(is_active=True).order_by(
            "equipment_id"
        )
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        alloc = cleaned.get("allocated_date")
        ret = cleaned.get("return_date")
        if alloc and ret and ret < alloc:
            raise forms.ValidationError("Return date cannot be before allocation date.")
        equipment = cleaned.get("equipment")
        if equipment and alloc:
            # Warn if equipment has an open allocation on the same project
            overlap = EquipmentAllocation.objects.filter(
                equipment=equipment,
                return_date__isnull=True,
            )
            if self.project:
                overlap = overlap.exclude(project=self.project)
            if overlap.exists():
                raise forms.ValidationError(
                    f"{equipment} is currently allocated to another project. "
                    "Return it first before re-allocating."
                )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class EquipmentUtilisationForm(forms.ModelForm):
    class Meta:
        model = EquipmentUtilisation
        fields = [
            "date",
            "hours_worked",
            "hours_idle",
            "hours_breakdown",
            "fuel_litres",
            "operator",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "hours_worked": forms.NumberInput(attrs={"step": "0.5"}),
            "hours_idle": forms.NumberInput(attrs={"step": "0.5"}),
            "hours_breakdown": forms.NumberInput(attrs={"step": "0.5"}),
            "fuel_litres": forms.NumberInput(attrs={"step": "0.1"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, allocation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.allocation = allocation
        if allocation:
            self.fields["operator"].queryset = Worker.objects.filter(
                project=allocation.project, is_active=True
            ).order_by("last_name")
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.allocation:
            instance.allocation = self.allocation
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# Subcontractor Company form
# ---------------------------------------------------------------------------


class SubcontractorCompanyForm(forms.ModelForm):
    class Meta:
        model = SubcontractorCompany
        fields = [
            "company_name",
            "trade",
            "contact_person",
            "email",
            "phone",
            "address",
            "irc_tin",
            "is_prequalified",
            "is_blacklisted",
            "blacklist_reason",
            "performance_rating",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "blacklist_reason": forms.Textarea(attrs={"rows": 3}),
            "performance_rating": forms.NumberInput(attrs={"step": "0.1", "min": "1.0", "max": "5.0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        is_blacklisted = cleaned.get("is_blacklisted")
        blacklist_reason = cleaned.get("blacklist_reason", "").strip()
        if is_blacklisted and not blacklist_reason:
            raise forms.ValidationError(
                "Please provide a reason for blacklisting this subcontractor."
            )
        return cleaned
