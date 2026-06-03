from django import forms

from .models import Task


def _apply_form_control(form):
    """Apply Bootstrap form-control class to all visible widgets."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        else:
            widget.attrs.setdefault("class", "form-control")


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "assigned_to",
            "project",
            "due_date",
            "priority",
            "status",
            "notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and not instance.assigned_by_id:
            instance.assigned_by = self.user
        if commit:
            instance.save()
        return instance


class TaskUpdateForm(TaskForm):
    """Task update form – includes status field and allows status changes."""

    class Meta(TaskForm.Meta):
        fields = TaskForm.Meta.fields + ["status"]
