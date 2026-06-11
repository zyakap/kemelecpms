from django import forms
from django.utils import timezone

from .models import (
    Activity,
    LookAhead,
    LookAheadTask,
    Programme,
    ProgrammeRevision,
    ProgressEntry,
    WBSActivity,
)


class WBSActivityForm(forms.ModelForm):
    class Meta:
        model = WBSActivity
        fields = [
            "parent",
            "wbs_code",
            "name",
            "description",
            "level",
            "responsible",
            "cost_code",
        ]
        widgets = {
            "wbs_code": forms.TextInput(attrs={"placeholder": "e.g. 1.2.3"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            self.fields["parent"].queryset = WBSActivity.objects.filter(project=project)
            self.fields["cost_code"].queryset = project.cost_codes.all()
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


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = [
            "baseline_start",
            "baseline_end",
            "current_start",
            "current_end",
            "version",
            "is_baseline",
            "notes",
        ]
        widgets = {
            "baseline_start": forms.DateInput(attrs={"type": "date"}),
            "baseline_end": forms.DateInput(attrs={"type": "date"}),
            "current_start": forms.DateInput(attrs={"type": "date"}),
            "current_end": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        baseline_start = cleaned.get("baseline_start")
        baseline_end = cleaned.get("baseline_end")
        current_start = cleaned.get("current_start")
        current_end = cleaned.get("current_end")
        if baseline_start and baseline_end and baseline_end < baseline_start:
            raise forms.ValidationError("Baseline end date must be after baseline start date.")
        if current_start and current_end and current_end < current_start:
            raise forms.ValidationError("Current end date must be after current start date.")
        return cleaned


class ProgrammeRevisionForm(forms.ModelForm):
    class Meta:
        model = ProgrammeRevision
        fields = [
            "submitted_date",
            "reason",
            "revised_start",
            "revised_end",
            "eot_days",
            "delay_events",
            "causation_summary",
            "status",
            "approved_by",
            "approved_date",
            "document",
            "notes",
        ]
        widgets = {
            "submitted_date": forms.DateInput(attrs={"type": "date"}),
            "revised_start": forms.DateInput(attrs={"type": "date"}),
            "revised_end": forms.DateInput(attrs={"type": "date"}),
            "approved_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
            "causation_summary": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, programme=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.programme = programme
        self.user = user
        if programme:
            self.fields["delay_events"].queryset = programme.project.delay_events.all()
        for field in self.fields.values():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault("class", "form-control")
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        submitted_date = cleaned.get("submitted_date")
        revised_start = cleaned.get("revised_start")
        revised_end = cleaned.get("revised_end")
        status = cleaned.get("status")
        approved_by = cleaned.get("approved_by") or self.user
        approved_date = cleaned.get("approved_date")
        eot_days = cleaned.get("eot_days") or 0
        delay_events = cleaned.get("delay_events")
        causation_summary = (cleaned.get("causation_summary") or "").strip()

        if revised_start and revised_end and revised_end < revised_start:
            self.add_error("revised_end", "Revised end date cannot be before revised start date.")
        if submitted_date and approved_date and approved_date < submitted_date:
            self.add_error("approved_date", "Approved date cannot be before submitted date.")
        if eot_days > 0 and not delay_events:
            self.add_error("delay_events", "EOT revisions must be linked to one or more delay events.")
        if eot_days > 0 and not causation_summary:
            self.add_error("causation_summary", "EOT revisions must include a causation summary.")
        if status == ProgrammeRevision.STATUS_APPROVED:
            if approved_by:
                cleaned["approved_by"] = approved_by
            if not approved_date:
                cleaned["approved_date"] = timezone.now().date()
            if not approved_by:
                self.add_error("approved_by", "Approved programme revisions require an approver.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.programme:
            instance.programme = self.programme
        if commit:
            instance.save()
        return instance


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            "wbs_activity",
            "name",
            "description",
            "start_date",
            "end_date",
            "planned_percent",
            "actual_percent",
            "predecessor",
            "dependency_type",
            "is_critical",
            "responsible",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "planned_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "actual_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
        }

    def __init__(self, *args, programme=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.programme = programme
        if programme:
            self.fields["wbs_activity"].queryset = WBSActivity.objects.filter(
                project=programme.project
            )
            self.fields["predecessor"].queryset = Activity.objects.filter(programme=programme)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("End date must be on or after start date.")
        predecessor = cleaned.get("predecessor")
        dependency_type = cleaned.get("dependency_type")
        if predecessor and self.instance.pk and predecessor.pk == self.instance.pk:
            self.add_error("predecessor", "Activity cannot depend on itself.")
        if predecessor:
            seen = set()
            node = predecessor
            while node is not None:
                if node.pk in seen or (self.instance.pk and node.pk == self.instance.pk):
                    self.add_error("predecessor", "Activity dependency chain cannot contain a cycle.")
                    break
                seen.add(node.pk)
                node = node.predecessor
            if start and dependency_type == Activity.DEP_FS and start < predecessor.end_date:
                self.add_error("start_date", "Finish-to-start activity cannot start before predecessor finishes.")
            if start and dependency_type == Activity.DEP_SS and start < predecessor.start_date:
                self.add_error("start_date", "Start-to-start activity cannot start before predecessor starts.")
            if end and dependency_type == Activity.DEP_FF and end < predecessor.end_date:
                self.add_error("end_date", "Finish-to-finish activity cannot finish before predecessor finishes.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.programme:
            instance.programme = self.programme
        if commit:
            instance.save()
        return instance


class ProgressEntryForm(forms.ModelForm):
    class Meta:
        model = ProgressEntry
        fields = [
            "date",
            "percent_complete",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "percent_complete": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class LookAheadForm(forms.ModelForm):
    class Meta:
        model = LookAhead
        fields = [
            "period_start",
            "period_end",
            "notes",
        ]
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and end <= start:
            raise forms.ValidationError("Period end must be after period start.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class LookAheadTaskForm(forms.ModelForm):
    class Meta:
        model = LookAheadTask
        fields = [
            "activity",
            "description",
            "assigned_to",
            "planned_start",
            "planned_end",
            "actual_start",
            "actual_end",
            "is_completed",
        ]
        widgets = {
            "planned_start": forms.DateInput(attrs={"type": "date"}),
            "planned_end": forms.DateInput(attrs={"type": "date"}),
            "actual_start": forms.DateInput(attrs={"type": "date"}),
            "actual_end": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(),
        }

    def __init__(self, *args, look_ahead=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.look_ahead = look_ahead
        if look_ahead:
            self.fields["activity"].queryset = Activity.objects.filter(
                programme__project=look_ahead.project
            )
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.look_ahead:
            instance.look_ahead = self.look_ahead
        if commit:
            instance.save()
        return instance
