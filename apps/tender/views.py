"""
Tender & Bid Library views.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from apps.projects.models import Project

from .forms import (
    BidEstimateForm,
    BidEstimateItemFormSet,
    CostRateForm,
    LessonsLearnedForm,
    TenderArchiveForm,
)
from .models import BidEstimate, BidEstimateItem, CostRate, LessonsLearned, TenderArchive


# ---------------------------------------------------------------------------
# Tender Archive
# ---------------------------------------------------------------------------


class TenderArchiveListView(LoginRequiredMixin, ListView):
    model = TenderArchive
    template_name = "tender/archive_list.html"
    context_object_name = "archives"
    paginate_by = 20

    def get_queryset(self):
        qs = TenderArchive.objects.select_related("project")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(project__name__icontains=q)
                | Q(searchable_tags__icontains=q)
                | Q(key_scope__icontains=q)
                | Q(project__project_type__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["breadcrumbs"] = [{"label": "Tender Library"}]
        return ctx


class TenderArchiveDetailView(LoginRequiredMixin, DetailView):
    model = TenderArchive
    template_name = "tender/archive_detail.html"
    context_object_name = "archive"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lessons"] = self.object.lessons_learned.all()
        ctx["cost_rates"] = self.object.cost_rates.filter(is_verified=True)
        ctx["breadcrumbs"] = [
            {"label": "Tender Library", "url": reverse_lazy("tender:archive-list")},
            {"label": str(self.object)},
        ]
        return ctx


class TenderArchiveCreateView(LoginRequiredMixin, CreateView):
    """Archive a closed project into the tender library."""

    model = TenderArchive
    form_class = TenderArchiveForm
    template_name = "tender/archive_form.html"
    success_url = reverse_lazy("tender:archive-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project_pk = self.request.GET.get("project")
        if project_pk:
            ctx["project"] = get_object_or_404(Project, pk=project_pk)
        return ctx

    def form_valid(self, form):
        project_pk = self.request.POST.get("project") or self.request.GET.get("project")
        project = get_object_or_404(Project, pk=project_pk)
        form.instance.project = project
        form.instance.archived_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, f"Project {project.project_id} archived to Tender Library.")
        return super().form_valid(form)


class TenderArchiveUpdateView(LoginRequiredMixin, UpdateView):
    model = TenderArchive
    form_class = TenderArchiveForm
    template_name = "tender/archive_form.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Archive updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.object.project
        return ctx


# ---------------------------------------------------------------------------
# Cost Rates
# ---------------------------------------------------------------------------


class CostRateListView(LoginRequiredMixin, ListView):
    model = CostRate
    template_name = "tender/rate_list.html"
    context_object_name = "rates"
    paginate_by = 40

    def get_queryset(self):
        qs = CostRate.objects.select_related("source_project")
        trade = self.request.GET.get("trade")
        region = self.request.GET.get("region")
        q = self.request.GET.get("q", "").strip()
        if trade:
            qs = qs.filter(trade=trade)
        if region:
            qs = qs.filter(region=region)
        if q:
            qs = qs.filter(Q(description__icontains=q) | Q(notes__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["trade_choices"] = CostRate.TRADE_CHOICES
        ctx["region_choices"] = CostRate.REGION_CHOICES
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_trade"] = self.request.GET.get("trade", "")
        ctx["selected_region"] = self.request.GET.get("region", "")
        ctx["breadcrumbs"] = [
            {"label": "Tender Library", "url": reverse_lazy("tender:archive-list")},
            {"label": "Cost Rates"},
        ]
        return ctx


class CostRateCreateView(LoginRequiredMixin, CreateView):
    model = CostRate
    form_class = CostRateForm
    template_name = "tender/rate_form.html"
    success_url = reverse_lazy("tender:rate-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Cost rate added to database.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [
            {"label": "Tender Library", "url": reverse_lazy("tender:archive-list")},
            {"label": "Cost Rates", "url": reverse_lazy("tender:rate-list")},
            {"label": "Add Rate"},
        ]
        return ctx


class CostRateUpdateView(LoginRequiredMixin, UpdateView):
    model = CostRate
    form_class = CostRateForm
    template_name = "tender/rate_form.html"
    success_url = reverse_lazy("tender:rate-list")

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Cost rate updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [
            {"label": "Tender Library", "url": reverse_lazy("tender:archive-list")},
            {"label": "Cost Rates", "url": reverse_lazy("tender:rate-list")},
            {"label": "Edit"},
        ]
        return ctx


# ---------------------------------------------------------------------------
# Bid Estimates
# ---------------------------------------------------------------------------


class BidEstimateListView(LoginRequiredMixin, ListView):
    model = BidEstimate
    template_name = "tender/estimate_list.html"
    context_object_name = "estimates"
    paginate_by = 20

    def get_queryset(self):
        qs = BidEstimate.objects.all()
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = BidEstimate.STATUS_CHOICES
        ctx["breadcrumbs"] = [
            {"label": "Tender Library", "url": reverse_lazy("tender:archive-list")},
            {"label": "Bid Estimates"},
        ]
        return ctx


class BidEstimateDetailView(LoginRequiredMixin, DetailView):
    model = BidEstimate
    template_name = "tender/estimate_detail.html"
    context_object_name = "estimate"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["items"] = self.object.items.select_related("rate_source").order_by("trade", "description")
        ctx["breadcrumbs"] = [
            {"label": "Bid Estimates", "url": reverse_lazy("tender:estimate-list")},
            {"label": str(self.object)},
        ]
        return ctx


class BidEstimateCreateView(LoginRequiredMixin, CreateView):
    model = BidEstimate
    form_class = BidEstimateForm
    template_name = "tender/estimate_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["item_formset"] = BidEstimateItemFormSet(self.request.POST)
        else:
            ctx["item_formset"] = BidEstimateItemFormSet()
        ctx["breadcrumbs"] = [
            {"label": "Bid Estimates", "url": reverse_lazy("tender:estimate-list")},
            {"label": "New Estimate"},
        ]
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        item_formset = ctx["item_formset"]
        if item_formset.is_valid():
            with transaction.atomic():
                form.instance.created_by = self.request.user
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()
                # Recalculate estimate total
                total = sum(i.amount for i in self.object.items.all())
                BidEstimate.objects.filter(pk=self.object.pk).update(estimate_total=total)
            messages.success(self.request, f"Bid estimate for {self.object.tender_reference} created.")
            return redirect(self.object.get_absolute_url())
        return self.form_invalid(form)


class BidEstimateUpdateView(LoginRequiredMixin, UpdateView):
    model = BidEstimate
    form_class = BidEstimateForm
    template_name = "tender/estimate_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["item_formset"] = BidEstimateItemFormSet(self.request.POST, instance=self.object)
        else:
            ctx["item_formset"] = BidEstimateItemFormSet(instance=self.object)
        ctx["breadcrumbs"] = [
            {"label": "Bid Estimates", "url": reverse_lazy("tender:estimate-list")},
            {"label": "Edit"},
        ]
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        item_formset = ctx["item_formset"]
        if item_formset.is_valid():
            with transaction.atomic():
                form.instance.updated_by = self.request.user
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()
                total = sum(i.amount for i in self.object.items.all())
                BidEstimate.objects.filter(pk=self.object.pk).update(estimate_total=total)
            messages.success(self.request, "Bid estimate updated.")
            return redirect(self.object.get_absolute_url())
        return self.form_invalid(form)


class BidEstimateCloneView(LoginRequiredMixin, View):
    def post(self, request, pk):
        original = get_object_or_404(BidEstimate, pk=pk)
        clone = BidEstimate.objects.create(
            tender_reference=f"COPY-{original.tender_reference}",
            title=f"Copy of {original.title}",
            client_name=original.client_name,
            funder=original.funder,
            location=original.location,
            margin_pct=original.margin_pct,
            cloned_from=original,
            notes=original.notes,
            created_by=request.user,
        )
        for item in original.items.all():
            BidEstimateItem.objects.create(
                estimate=clone,
                trade=item.trade,
                description=item.description,
                unit=item.unit,
                quantity=item.quantity,
                unit_rate=item.unit_rate,
                amount=item.amount,
                rate_source=item.rate_source,
                notes=item.notes,
            )
        BidEstimate.objects.filter(pk=clone.pk).update(estimate_total=original.estimate_total)
        messages.success(request, f"Estimate cloned as {clone.tender_reference}.")
        return redirect(clone.get_absolute_url())


# ---------------------------------------------------------------------------
# Lessons Learned
# ---------------------------------------------------------------------------


class LessonsLearnedListView(LoginRequiredMixin, ListView):
    model = LessonsLearned
    template_name = "tender/lessons_list.html"
    context_object_name = "lessons"
    paginate_by = 25

    def get_queryset(self):
        qs = LessonsLearned.objects.select_related("project")
        category = self.request.GET.get("category")
        q = self.request.GET.get("q", "").strip()
        if category:
            qs = qs.filter(category=category)
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(recommendation__icontains=q)
                | Q(what_went_wrong__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["category_choices"] = LessonsLearned.CATEGORY_CHOICES
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_category"] = self.request.GET.get("category", "")
        ctx["breadcrumbs"] = [
            {"label": "Tender Library", "url": reverse_lazy("tender:archive-list")},
            {"label": "Lessons Learned"},
        ]
        return ctx


class LessonsLearnedDetailView(LoginRequiredMixin, DetailView):
    model = LessonsLearned
    template_name = "tender/lessons_detail.html"
    context_object_name = "lesson"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [
            {"label": "Lessons Learned", "url": reverse_lazy("tender:lessons-list")},
            {"label": self.object.title},
        ]
        return ctx


class LessonsLearnedCreateView(LoginRequiredMixin, CreateView):
    model = LessonsLearned
    form_class = LessonsLearnedForm
    template_name = "tender/lessons_form.html"
    success_url = reverse_lazy("tender:lessons-list")

    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Lesson learned recorded.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [
            {"label": "Lessons Learned", "url": reverse_lazy("tender:lessons-list")},
            {"label": "Add Lesson"},
        ]
        return ctx


class LessonsLearnedUpdateView(LoginRequiredMixin, UpdateView):
    model = LessonsLearned
    form_class = LessonsLearnedForm
    template_name = "tender/lessons_form.html"
    success_url = reverse_lazy("tender:lessons-list")

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Lesson updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [
            {"label": "Lessons Learned", "url": reverse_lazy("tender:lessons-list")},
            {"label": "Edit"},
        ]
        return ctx
