from django import forms

from .models import ComplianceCalendarEntry, IRCTaxInvoice, OTMLTCSReport


class OTMLTCSReportForm(forms.ModelForm):
    class Meta:
        model = OTMLTCSReport
        fields = [
            "period_type",
            "period_from",
            "period_to",
            "total_tcs_budget",
            "expenditure_this_period",
            "expenditure_to_date",
            "overall_progress_pct",
            "narrative",
            "issues_risks",
            "local_labour_pct",
            "expat_labour_pct",
            "local_materials_pct",
            "attachment",
        ]
        widgets = {
            "period_from": forms.DateInput(attrs={"type": "date"}),
            "period_to": forms.DateInput(attrs={"type": "date"}),
            "narrative": forms.Textarea(attrs={"rows": 4}),
            "issues_risks": forms.Textarea(attrs={"rows": 3}),
        }


class IRCTaxInvoiceForm(forms.ModelForm):
    class Meta:
        model = IRCTaxInvoice
        fields = [
            "ipc",
            "invoice_date",
            "kemele_tinpng",
            "kemele_gst_number",
            "client_name",
            "client_address",
            "client_tinpng",
            "subtotal",
            "gst_rate",
            "description",
            "payment_terms",
            "notes",
        ]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "client_address": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields["ipc"].queryset = self.fields["ipc"].queryset.filter(project=project)
            self.fields["ipc"].required = False


class ComplianceCalendarEntryForm(forms.ModelForm):
    class Meta:
        model = ComplianceCalendarEntry
        fields = [
            "project",
            "title",
            "category",
            "description",
            "due_date",
            "reminder_days",
            "responsible",
            "status",
            "completed_date",
            "completion_notes",
            "attachment",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "completed_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "completion_notes": forms.Textarea(attrs={"rows": 3}),
        }
