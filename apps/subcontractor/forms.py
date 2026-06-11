from django import forms

from apps.budget.models import SubcontractorDocument


class SubcontractorDocumentForm(forms.ModelForm):
    class Meta:
        model = SubcontractorDocument
        fields = ["title", "doc_type", "revision", "description", "file"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Reinforcement Shop Drawing — Level 2"}),
            "doc_type": forms.Select(attrs={"class": "form-select"}),
            "revision": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. A, B, 01"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Brief description or notes"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class DocumentReviewForm(forms.ModelForm):
    class Meta:
        model = SubcontractorDocument
        fields = ["status", "review_notes"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "review_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Review comments…"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only allow actionable statuses when reviewing
        self.fields["status"].choices = [
            (SubcontractorDocument.STATUS_UNDER_REVIEW, "Under Review"),
            (SubcontractorDocument.STATUS_APPROVED, "Approved"),
            (SubcontractorDocument.STATUS_REJECTED, "Rejected / Revise & Resubmit"),
        ]
