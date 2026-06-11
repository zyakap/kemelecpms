from django import forms
from django.utils import timezone

from .models import (
    Correspondence,
    DistributionContact,
    DocumentControlSettings,
    DocumentTransmittal,
    Drawing,
    DrawingRevision,
    ProjectDocument,
    ProjectDocumentRevision,
    RFI,
    Submittal,
)
from .services import validate_upload


def _apply_form_control(form):
    """Apply Bootstrap form-control class to all visible widgets."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        else:
            widget.attrs.setdefault("class", "form-control")


class UploadPolicyMixin:
    """Validates configured file fields against document control settings.

    Forms using this mixin must expose ``self.project`` (set in __init__)
    and list their file fields in ``upload_policy_fields``.
    """

    upload_policy_fields = ()

    def clean(self):
        cleaned = super().clean()
        for field_name in self.upload_policy_fields:
            uploaded = cleaned.get(field_name)
            # Only validate fresh uploads, not persisted FieldFiles.
            if uploaded and hasattr(uploaded, "content_type"):
                try:
                    validate_upload(uploaded, project=getattr(self, "project", None))
                except forms.ValidationError as exc:
                    self.add_error(field_name, exc)
        return cleaned


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


class DrawingForm(UploadPolicyMixin, forms.ModelForm):
    upload_policy_fields = ("file",)

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

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        revision_date = cleaned.get("current_revision_date")
        if status == Drawing.STATUS_IFC and not revision_date:
            self.add_error(
                "current_revision_date",
                "IFC drawings must record the current revision date.",
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class DrawingRevisionForm(UploadPolicyMixin, forms.ModelForm):
    upload_policy_fields = ("file",)

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
        self.project = drawing.project if drawing else None
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


class RFIForm(UploadPolicyMixin, forms.ModelForm):
    upload_policy_fields = ("photo",)

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

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        date_raised = cleaned.get("date_raised")
        response = (cleaned.get("response") or "").strip()
        response_date = cleaned.get("response_date")

        if status in (RFI.STATUS_RESPONDED, RFI.STATUS_CLOSED) and response and not response_date:
            cleaned["response_date"] = timezone.now().date()
            response_date = cleaned["response_date"]
        if status in (RFI.STATUS_RESPONDED, RFI.STATUS_CLOSED) and not response:
            self.add_error("response", "A response is required before this RFI can be responded or closed.")
        if status in (RFI.STATUS_RESPONDED, RFI.STATUS_CLOSED) and not response_date:
            self.add_error("response_date", "A response date is required before this RFI can be responded or closed.")
        if date_raised and response_date and response_date < date_raised:
            self.add_error("response_date", "Response date cannot be before the RFI raised date.")
        if status == RFI.STATUS_CLOSED and not response:
            self.add_error("status", "Only responded RFIs can be closed.")
        return cleaned

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


class SubmittalForm(UploadPolicyMixin, forms.ModelForm):
    upload_policy_fields = ("document",)

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

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        submitted_date = cleaned.get("submitted_date")
        review_notes = (cleaned.get("review_notes") or "").strip()
        reviewed_by = cleaned.get("reviewed_by") or self.user
        reviewed_date = cleaned.get("reviewed_date")
        review_statuses = {
            Submittal.STATUS_APPROVED,
            Submittal.STATUS_APPROVED_AS_NOTED,
            Submittal.STATUS_REVISE_RESUBMIT,
            Submittal.STATUS_REJECTED,
        }

        if status in review_statuses:
            if reviewed_by:
                cleaned["reviewed_by"] = reviewed_by
            if not reviewed_date:
                cleaned["reviewed_date"] = timezone.now().date()
                reviewed_date = cleaned["reviewed_date"]
            if not reviewed_by:
                self.add_error("reviewed_by", "A reviewer is required for reviewed submittals.")
            if not reviewed_date:
                self.add_error("reviewed_date", "A review date is required for reviewed submittals.")
            if status != Submittal.STATUS_APPROVED and not review_notes:
                self.add_error("review_notes", "Review notes are required unless the submittal is approved without comment.")
        if submitted_date and reviewed_date and reviewed_date < submitted_date:
            self.add_error("reviewed_date", "Review date cannot be before the submitted date.")
        return cleaned

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


class CorrespondenceForm(UploadPolicyMixin, forms.ModelForm):
    upload_policy_fields = ("document",)

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

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        action_due = cleaned.get("action_due_date")
        response_date = cleaned.get("response_date")
        action_required = cleaned.get("action_required")
        is_responded = cleaned.get("is_responded")

        if action_required and not action_due:
            self.add_error("action_due_date", "Action due date is required when action is required.")
        if date and action_due and action_due < date:
            self.add_error("action_due_date", "Action due date cannot be before the correspondence date.")
        if is_responded and not response_date:
            self.add_error("response_date", "Response date is required when correspondence is marked responded.")
        if date and response_date and response_date < date:
            self.add_error("response_date", "Response date cannot be before the correspondence date.")
        return cleaned

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


class ProjectDocumentForm(UploadPolicyMixin, forms.ModelForm):
    upload_policy_fields = ("file",)

    class Meta:
        model = ProjectDocument
        fields = [
            "title",
            "document_type",
            "file",
            "description",
            "version",
            "confidentiality",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.user = user
        if not self.instance.pk:
            from .services import get_document_settings

            self.fields["confidentiality"].initial = get_document_settings(
                project
            ).default_confidentiality
        _apply_form_control(self)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project is not None:
            # project can be None for company-wide templates
            instance.project = self.project
        if self.user:
            instance.uploaded_by = self.user
        if not instance.pk:
            from .services import get_document_settings

            if not get_document_settings(self.project).require_document_approval:
                instance.status = ProjectDocument.STATUS_APPROVED
        if commit:
            instance.save()
        return instance


class ProjectDocumentRevisionForm(UploadPolicyMixin, forms.ModelForm):
    upload_policy_fields = ("file",)

    class Meta:
        model = ProjectDocumentRevision
        fields = ["version", "file", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, document=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.document = document
        self.project = document.project if document else None
        self.user = user
        _apply_form_control(self)

    def clean_version(self):
        version = (self.cleaned_data.get("version") or "").strip()
        if self.document and version:
            if version == self.document.version:
                raise forms.ValidationError(
                    "This version already exists — use a new version identifier."
                )
            if self.document.revisions.filter(version=version).exists():
                raise forms.ValidationError(
                    "A revision with this version already exists for this document."
                )
        return version

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.document:
            instance.document = self.document
        if self.user:
            instance.uploaded_by = self.user
        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# Document Control Settings
# ---------------------------------------------------------------------------


class DocumentControlSettingsForm(forms.ModelForm):
    class Meta:
        model = DocumentControlSettings
        exclude = ["project", "created_by", "updated_by"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_control(self)

    def clean_allowed_file_extensions(self):
        raw = self.cleaned_data.get("allowed_file_extensions", "")
        cleaned = {
            ext.strip().lower().lstrip(".")
            for ext in raw.split(",")
            if ext.strip()
        }
        if not cleaned:
            raise forms.ValidationError("At least one file extension must be allowed.")
        return ",".join(sorted(cleaned))


class DistributionContactForm(forms.ModelForm):
    class Meta:
        model = DistributionContact
        fields = ["name", "organization", "email", "role", "is_active"]

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        _apply_form_control(self)
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
        return instance


class DocumentTransmittalForm(forms.ModelForm):
    class Meta:
        model = DocumentTransmittal
        fields = [
            "subject",
            "sent_date",
            "recipients",
            "drawings",
            "submittals",
            "documents",
            "status",
            "acknowledged_date",
            "notes",
        ]
        widgets = {
            "sent_date": forms.DateInput(attrs={"type": "date"}),
            "acknowledged_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        if project:
            self.fields["recipients"].queryset = project.distribution_contacts.filter(is_active=True)
            self.fields["drawings"].queryset = project.drawings.filter(status=Drawing.STATUS_IFC).order_by(
                "discipline", "drawing_number"
            )
            self.fields["submittals"].queryset = project.submittals.all()
            self.fields["documents"].queryset = project.project_documents.all()
        _apply_form_control(self)

    def clean(self):
        cleaned = super().clean()
        sent_date = cleaned.get("sent_date")
        status = cleaned.get("status")
        acknowledged_date = cleaned.get("acknowledged_date")
        recipients = cleaned.get("recipients")
        drawings = cleaned.get("drawings")
        submittals = cleaned.get("submittals")
        documents = cleaned.get("documents")
        has_recipients = bool(recipients)
        has_attachments = bool(drawings or submittals or documents)
        if status in (DocumentTransmittal.STATUS_SENT, DocumentTransmittal.STATUS_ACKNOWLEDGED):
            if not has_recipients:
                self.add_error("recipients", "Sent transmittals require at least one recipient.")
            if not has_attachments:
                self.add_error("drawings", "Sent transmittals require at least one drawing, submittal, or document.")
        if drawings and drawings.exclude(status=Drawing.STATUS_IFC).exists():
            self.add_error("drawings", "Only current IFC drawings can be transmitted.")
        if status == DocumentTransmittal.STATUS_ACKNOWLEDGED and not acknowledged_date:
            cleaned["acknowledged_date"] = timezone.now().date()
        if sent_date and acknowledged_date and acknowledged_date < sent_date:
            self.add_error("acknowledged_date", "Acknowledged date cannot be before sent date.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        if commit:
            instance.save()
            self.save_m2m()
        return instance
