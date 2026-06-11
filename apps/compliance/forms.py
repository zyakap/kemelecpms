from django import forms

from .models import (
    AuthorityPermit,
    ComplianceCalendarEntry,
    ComplianceCalendarTemplate,
    FunderReportPack,
    IRCTaxInvoice,
    LocalContentRecord,
    OTMLTCSReport,
    PublicProcurementRecord,
)


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
            "status",
            "description",
            "payment_terms",
            "payment_date",
            "payment_reference",
            "notes",
        ]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "client_address": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields["ipc"].queryset = self.fields["ipc"].queryset.filter(project=project)
            self.fields["ipc"].required = False


class TaxInvoiceVoidForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Void reason")


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


class PublicProcurementRecordForm(forms.ModelForm):
    class Meta:
        model = PublicProcurementRecord
        fields = [
            "tender_number",
            "procurement_method",
            "procuring_entity",
            "approval_reference",
            "approval_history",
            "evaluation_summary",
            "probity_notes",
            "bid_evaluation_file",
            "award_notice_file",
            "approval_file",
            "status",
        ]
        widgets = {
            "approval_history": forms.Textarea(attrs={"rows": 4}),
            "evaluation_summary": forms.Textarea(attrs={"rows": 3}),
            "probity_notes": forms.Textarea(attrs={"rows": 3}),
        }


class LocalContentRecordForm(forms.ModelForm):
    class Meta:
        model = LocalContentRecord
        fields = [
            "period_from",
            "period_to",
            "png_labour_count",
            "expat_labour_count",
            "local_supplier_spend",
            "total_supplier_spend",
            "local_subcontractor_spend",
            "total_subcontractor_spend",
            "png_material_spend",
            "total_material_spend",
            "notes",
            "evidence_file",
        ]
        widgets = {
            "period_from": forms.DateInput(attrs={"type": "date"}),
            "period_to": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class AuthorityPermitForm(forms.ModelForm):
    class Meta:
        model = AuthorityPermit
        fields = [
            "authority",
            "permit_type",
            "reference_number",
            "status",
            "submission_date",
            "approval_date",
            "inspection_date",
            "expiry_date",
            "responsible",
            "conditions",
            "certificate_file",
        ]
        widgets = {
            "submission_date": forms.DateInput(attrs={"type": "date"}),
            "approval_date": forms.DateInput(attrs={"type": "date"}),
            "inspection_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "conditions": forms.Textarea(attrs={"rows": 3}),
        }


class FunderReportPackForm(forms.ModelForm):
    class Meta:
        model = FunderReportPack
        fields = [
            "funder_type",
            "pack_type",
            "period_from",
            "period_to",
            "status",
            "narrative",
            "pack_file",
            "submitted_date",
        ]
        widgets = {
            "period_from": forms.DateInput(attrs={"type": "date"}),
            "period_to": forms.DateInput(attrs={"type": "date"}),
            "submitted_date": forms.DateInput(attrs={"type": "date"}),
            "narrative": forms.Textarea(attrs={"rows": 4}),
        }


class ComplianceCalendarTemplateForm(forms.ModelForm):
    class Meta:
        model = ComplianceCalendarTemplate
        fields = [
            "name",
            "category",
            "frequency",
            "default_reminder_days",
            "description",
            "applies_to_government",
            "applies_to_private",
            "applies_to_maintenance",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
