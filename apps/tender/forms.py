from django import forms
from django.forms import inlineformset_factory

from .models import BidEstimate, BidEstimateItem, CostRate, LessonsLearned, TenderArchive, TenderDocument


class TenderArchiveForm(forms.ModelForm):
    class Meta:
        model = TenderArchive
        fields = [
            "original_contract_value",
            "final_contract_value",
            "total_cost",
            "margin_pct",
            "planned_duration_days",
            "actual_duration_days",
            "executive_summary",
            "key_scope",
            "unique_challenges",
            "searchable_tags",
        ]
        widgets = {
            "executive_summary": forms.Textarea(attrs={"rows": 4}),
            "key_scope": forms.Textarea(attrs={"rows": 4}),
            "unique_challenges": forms.Textarea(attrs={"rows": 3}),
        }


class CostRateForm(forms.ModelForm):
    class Meta:
        model = CostRate
        fields = [
            "trade",
            "region",
            "year",
            "description",
            "unit",
            "unit_rate",
            "notes",
            "is_verified",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class BidEstimateForm(forms.ModelForm):
    class Meta:
        model = BidEstimate
        fields = [
            "tender_reference",
            "title",
            "client_name",
            "funder",
            "location",
            "tender_due_date",
            "margin_pct",
            "bid_amount",
            "cloned_from",
            "notes",
        ]
        widgets = {
            "tender_due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class BidEstimateItemForm(forms.ModelForm):
    class Meta:
        model = BidEstimateItem
        fields = ["trade", "description", "unit", "quantity", "unit_rate", "rate_source", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rate_source"].queryset = CostRate.objects.filter(is_verified=True)
        self.fields["rate_source"].required = False


BidEstimateItemFormSet = inlineformset_factory(
    BidEstimate,
    BidEstimateItem,
    form=BidEstimateItemForm,
    extra=3,
    can_delete=True,
)


class TenderDocumentForm(forms.ModelForm):
    class Meta:
        model = TenderDocument
        fields = [
            "title",
            "doc_type",
            "trade_category",
            "description",
            "document",
            "version",
            "is_current",
            "tags",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class LessonsLearnedForm(forms.ModelForm):
    class Meta:
        model = LessonsLearned
        fields = [
            "project",
            "category",
            "title",
            "what_went_well",
            "what_went_wrong",
            "recommendation",
        ]
        widgets = {
            "what_went_well": forms.Textarea(attrs={"rows": 4}),
            "what_went_wrong": forms.Textarea(attrs={"rows": 4}),
            "recommendation": forms.Textarea(attrs={"rows": 4}),
        }
