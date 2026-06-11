from django import forms
from django.utils import timezone

from .models import (
    Asset,
    BreakdownTicket,
    PreventiveMaintenanceSchedule,
    ServiceRecord,
    SparePart,
    WorkOrder,
)


def _style(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "form-check-input")
        else:
            field.widget.attrs.setdefault("class", "form-control")


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        exclude = ("project", "created_by", "updated_by", "created_at", "updated_at")
        widgets = {
            "installed_date": forms.DateInput(attrs={"type": "date"}),
            "last_service_date": forms.DateInput(attrs={"type": "date"}),
            "next_service_due": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        _style(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class PreventiveMaintenanceScheduleForm(forms.ModelForm):
    class Meta:
        model = PreventiveMaintenanceSchedule
        fields = ("title", "frequency", "next_due_date", "checklist", "is_active")
        widgets = {
            "next_due_date": forms.DateInput(attrs={"type": "date"}),
            "checklist": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, asset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset = asset
        _style(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.asset:
            instance.asset = self.asset
        if commit:
            instance.save()
        return instance


class WorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        exclude = ("project", "work_order_number", "created_by", "updated_by", "created_at", "updated_at")
        widgets = {
            "requested_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "responded_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "completed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "signed_off_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "completion_notes": forms.Textarea(attrs={"rows": 3}),
            "parts_used": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.user = user
        if project:
            self.fields["asset"].queryset = project.maintenance_assets.all()
        _style(self)

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        requested = cleaned.get("requested_date")
        due = cleaned.get("due_date")
        completed = cleaned.get("completed_at")
        signed_by = cleaned.get("signed_off_by") or self.user
        signed_at = cleaned.get("signed_off_at")
        if requested and due and due < requested:
            self.add_error("due_date", "Due date cannot be before requested date.")
        if status == WorkOrder.STATUS_COMPLETED and not completed:
            cleaned["completed_at"] = timezone.now()
        if status == WorkOrder.STATUS_SIGNED_OFF:
            if signed_by:
                cleaned["signed_off_by"] = signed_by
            if not completed:
                self.add_error("completed_at", "Work order must be completed before sign-off.")
            if not signed_at:
                cleaned["signed_off_at"] = timezone.now()
        for field_name in ("labour_hours", "cost"):
            value = cleaned.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, "Value cannot be negative.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if self.user and not instance.requested_by_id:
            instance.requested_by = self.user
        if commit:
            instance.save()
        return instance


class BreakdownTicketForm(forms.ModelForm):
    class Meta:
        model = BreakdownTicket
        fields = ("asset", "work_order", "reported_at", "restored_at", "cause", "operational_impact", "status")
        widgets = {
            "reported_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "restored_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "cause": forms.Textarea(attrs={"rows": 3}),
            "operational_impact": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields["asset"].queryset = project.maintenance_assets.all()
            self.fields["work_order"].queryset = project.maintenance_work_orders.all()
        _style(self)

    def clean(self):
        cleaned = super().clean()
        reported = cleaned.get("reported_at")
        restored = cleaned.get("restored_at")
        status = cleaned.get("status")
        if reported and restored and restored < reported:
            self.add_error("restored_at", "Restored time cannot be before reported time.")
        if status == BreakdownTicket.STATUS_RESOLVED and not restored:
            cleaned["restored_at"] = timezone.now()
        return cleaned


class ServiceRecordForm(forms.ModelForm):
    class Meta:
        model = ServiceRecord
        fields = ("work_order", "service_date", "technician", "work_performed", "downtime_hours", "cost", "document")
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date"}),
            "work_performed": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields["work_order"].queryset = project.maintenance_work_orders.all()
        _style(self)

    def clean(self):
        cleaned = super().clean()
        for field_name in ("downtime_hours", "cost"):
            value = cleaned.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, "Value cannot be negative.")
        return cleaned


class SparePartForm(forms.ModelForm):
    class Meta:
        model = SparePart
        exclude = ("project", "created_by", "updated_by", "created_at", "updated_at")

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            self.fields["asset"].queryset = project.maintenance_assets.all()
        _style(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance
