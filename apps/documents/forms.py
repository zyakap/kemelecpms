from django import forms

from .models import Correspondence, Drawing, DrawingRevision, ProjectDocument, RFI, Submittal


def _apply_form_control(form):
    """Apply Bootstrap form-control class to all visible widgets."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        else:
            widget.attrs.setdefault("class", "form-control")


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


class DrawingForm(forms.ModelForm):
    class Meta:
        model = Drawing
        fields = [
            "drawing_number",
            "title",
            "discipline",
            "scale",
            "current_revision",
            "current_revision_date",
            "status",
            "file",
            "notes",
        ]
        widgets = {
            "current_revision_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
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


class DrawingRevisionForm(forms.ModelForm):
    class Meta:
        model = DrawingRevision
        fields = ["revision", "date", "file", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, drawing=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.drawing = drawing
        self.user = user
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.drawing:
            instance.drawing = self.drawing
        if self.user:
            instance.uploaded_by = self.user
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# RFI
# ---------------------------------------------------------------------------


class RFIForm(forms.ModelForm):
    class Meta:
        model = RFI
        fields = [
            "date_raised",
            "subject",
            "question",
            "directed_to",
            "drawing",
            "photo",
            "response",
            "response_date",
            "status",
            "schedule_impact_days",
            "cost_impact",
        ]
        widgets = {
            "date_raised": forms.DateInput(attrs={"type": "date"}),
            "response_date": forms.DateInput(attrs={"type": "date"}),
            "question": forms.Textarea(attrs={"rows": 4}),
            "response": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.user = user
        if project:
            self.fields["drawing"].queryset = Drawing.objects.filter(project=project).order_by(
                "drawing_number"
            )
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if self.user and not instance.raised_by_id:
            instance.raised_by = self.user
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# Submittal
# ---------------------------------------------------------------------------


class SubmittalForm(forms.ModelForm):
    class Meta:
        model = Submittal
        fields = [
            "submittal_type",
            "title",
            "submitted_date",
            "document",
            "status",
            "review_notes",
            "reviewed_by",
            "reviewed_date",
            "revision",
        ]
        widgets = {
            "submitted_date": forms.DateInput(attrs={"type": "date"}),
            "reviewed_date": forms.DateInput(attrs={"type": "date"}),
            "review_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.user = user
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if self.user and not instance.submitted_by_id:
            instance.submitted_by = self.user
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# Correspondence
# ---------------------------------------------------------------------------


class CorrespondenceForm(forms.ModelForm):
    class Meta:
        model = Correspondence
        fields = [
            "date",
            "direction",
            "subject",
            "sender",
            "recipient",
            "summary",
            "document",
            "action_required",
            "action_due_date",
            "response_date",
            "is_responded",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "action_due_date": forms.DateInput(attrs={"type": "date"}),
            "response_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        _apply_form_control(self)
        # Checkboxes need different class
        self.fields["action_required"].widget.attrs["class"] = "form-check-input"
        self.fields["is_responded"].widget.attrs["class"] = "form-check-input"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# ProjectDocument
# ---------------------------------------------------------------------------


class ProjectDocumentForm(forms.ModelForm):
    class Meta:
        model = ProjectDocument
        fields = [
            "title",
            "document_type",
            "file",
            "description",
            "version",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.user = user
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project is not None:
            # project can be None for company-wide templates
            instance.project = self.project
        if self.user:
            instance.uploaded_by = self.user
        if commit:
            instance.save()
        return instance
