from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.projects.models import Project

from .forms import BoQItemForm, CostCodeForm, CostEntryForm, SubcontractForm
from .models import BoQItem, CostCode, CostEntry, Subcontract


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class ProjectMixin(LoginRequiredMixin):
    """Injects the current project (from URL kwarg ``project_pk``) into context."""

    def get_project(self):
        if not hasattr(self, "_project"):
            self._project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return self._project

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.get_project()
        return ctx


# ---------------------------------------------------------------------------
# Budget Dashboard
# ---------------------------------------------------------------------------


class BudgetDashboardView(ProjectMixin, TemplateView):
    """High-level budget vs actual table with RAG status per cost code."""

    template_name = "budget/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        cost_codes = CostCode.objects.filter(project=project).order_by("code")

        rows = []
        total_budget = Decimal("0.00")
        total_committed = Decimal("0.00")
        total_actual = Decimal("0.00")

        for cc in cost_codes:
            committed = cc.total_committed
            actual = cc.total_actual
            spent = cc.total_spent
            total_budget += cc.budget_amount
            total_committed += committed
            total_actual += actual
            rows.append(
                {
                    "cost_code": cc,
                    "budget": cc.budget_amount,
                    "committed": committed,
                    "actual": actual,
                    "spent": spent,
                    "variance": cc.variance,
                    "variance_pct": cc.variance_percentage,
                    "rag": cc.rag_status,
                }
            )

        total_spent = total_committed + total_actual
        ctx.update(
            {
                "rows": rows,
                "total_budget": total_budget,
                "total_committed": total_committed,
                "total_actual": total_actual,
                "total_spent": total_spent,
                "total_variance": total_budget - total_spent,
            }
        )
        return ctx


# ---------------------------------------------------------------------------
# Cost Code views
# ---------------------------------------------------------------------------


class CostCodeListView(ProjectMixin, ListView):
    model = CostCode
    template_name = "budget/costcode_list.html"
    context_object_name = "cost_codes"

    def get_queryset(self):
        return CostCode.objects.filter(project=self.get_project()).order_by("code")


class CostCodeCreateView(ProjectMixin, CreateView):
    model = CostCode
    form_class = CostCodeForm
    template_name = "budget/costcode_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Cost code created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("budget:costcode-list", kwargs={"project_pk": self.get_project().pk})


class CostCodeUpdateView(ProjectMixin, UpdateView):
    model = CostCode
    form_class = CostCodeForm
    template_name = "budget/costcode_form.html"

    def get_queryset(self):
        return CostCode.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Cost code updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("budget:costcode-list", kwargs={"project_pk": self.get_project().pk})


# ---------------------------------------------------------------------------
# BoQ views
# ---------------------------------------------------------------------------


class BoQListView(ProjectMixin, ListView):
    model = BoQItem
    template_name = "budget/boq_list.html"
    context_object_name = "boq_items"

    def get_queryset(self):
        qs = BoQItem.objects.filter(project=self.get_project()).select_related("cost_code")
        trade = self.request.GET.get("trade")
        if trade:
            qs = qs.filter(trade_section=trade)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["trade_choices"] = CostCode.CATEGORY_CHOICES
        ctx["selected_trade"] = self.request.GET.get("trade", "")
        total = sum(item.amount for item in ctx["boq_items"])
        ctx["total_amount"] = total
        return ctx


class BoQItemCreateView(ProjectMixin, CreateView):
    model = BoQItem
    form_class = BoQItemForm
    template_name = "budget/boq_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "BoQ item added successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("budget:boq-list", kwargs={"project_pk": self.get_project().pk})


class BoQItemUpdateView(ProjectMixin, UpdateView):
    model = BoQItem
    form_class = BoQItemForm
    template_name = "budget/boq_form.html"

    def get_queryset(self):
        return BoQItem.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "BoQ item updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("budget:boq-list", kwargs={"project_pk": self.get_project().pk})


# ---------------------------------------------------------------------------
# Cost Entry views
# ---------------------------------------------------------------------------


class CostEntryListView(ProjectMixin, ListView):
    model = CostEntry
    template_name = "budget/costentry_list.html"
    context_object_name = "cost_entries"
    paginate_by = 30

    def get_queryset(self):
        qs = CostEntry.objects.filter(project=self.get_project()).select_related("cost_code", "boq_item")
        entry_type = self.request.GET.get("type")
        cost_code = self.request.GET.get("cost_code")
        if entry_type:
            qs = qs.filter(entry_type=entry_type)
        if cost_code:
            qs = qs.filter(cost_code_id=cost_code)
        return qs.order_by("-date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        ctx["cost_codes"] = CostCode.objects.filter(project=project)
        ctx["entry_type_choices"] = CostEntry.ENTRY_TYPE_CHOICES
        ctx["selected_type"] = self.request.GET.get("type", "")
        ctx["selected_cost_code"] = self.request.GET.get("cost_code", "")
        return ctx


class CostEntryCreateView(ProjectMixin, CreateView):
    model = CostEntry
    form_class = CostEntryForm
    template_name = "budget/costentry_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Cost entry recorded successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("budget:costentry-list", kwargs={"project_pk": self.get_project().pk})


class CostEntryUpdateView(ProjectMixin, UpdateView):
    model = CostEntry
    form_class = CostEntryForm
    template_name = "budget/costentry_form.html"

    def get_queryset(self):
        return CostEntry.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Cost entry updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("budget:costentry-list", kwargs={"project_pk": self.get_project().pk})


# ---------------------------------------------------------------------------
# Subcontract views
# ---------------------------------------------------------------------------


class SubcontractListView(ProjectMixin, ListView):
    model = Subcontract
    template_name = "budget/subcontract_list.html"
    context_object_name = "subcontracts"

    def get_queryset(self):
        qs = Subcontract.objects.filter(project=self.get_project())
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Subcontract.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class SubcontractCreateView(ProjectMixin, CreateView):
    model = Subcontract
    form_class = SubcontractForm
    template_name = "budget/subcontract_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Subcontract created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("budget:subcontract-list", kwargs={"project_pk": self.get_project().pk})


class SubcontractUpdateView(ProjectMixin, UpdateView):
    model = Subcontract
    form_class = SubcontractForm
    template_name = "budget/subcontract_form.html"

    def get_queryset(self):
        return Subcontract.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Subcontract updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("budget:subcontract-list", kwargs={"project_pk": self.get_project().pk})
