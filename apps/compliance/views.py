"""
Compliance & Funder Reporting views.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from apps.projects.models import Project

from .forms import ComplianceCalendarEntryForm, IRCTaxInvoiceForm, OTMLTCSReportForm
from .models import ComplianceCalendarEntry, IRCTaxInvoice, OTMLTCSReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_project(view):
    return get_object_or_404(Project, pk=view.kwargs["project_pk"])


# ---------------------------------------------------------------------------
# OTML TCS Reports
# ---------------------------------------------------------------------------


class TCSReportListView(LoginRequiredMixin, ListView):
    model = OTMLTCSReport
    template_name = "compliance/tcs_list.html"
    context_object_name = "reports"

    def get_queryset(self):
        return OTMLTCSReport.objects.filter(project_id=self.kwargs["project_pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = _get_project(self)
        ctx["breadcrumbs"] = [
            {"label": "Projects", "url": "/projects/"},
            {"label": ctx["project"].name, "url": ctx["project"].get_absolute_url()},
            {"label": "TCS Reports"},
        ]
        return ctx


class TCSReportCreateView(LoginRequiredMixin, CreateView):
    model = OTMLTCSReport
    form_class = OTMLTCSReportForm
    template_name = "compliance/tcs_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = _get_project(self)
        ctx["breadcrumbs"] = [
            {"label": "Projects", "url": "/projects/"},
            {"label": ctx["project"].name, "url": ctx["project"].get_absolute_url()},
            {"label": "TCS Reports", "url": reverse_lazy("compliance:tcs-list", kwargs={"project_pk": ctx["project"].pk})},
            {"label": "New Report"},
        ]
        return ctx

    def form_valid(self, form):
        project = _get_project(self)
        form.instance.project = project
        form.instance.created_by = self.request.user
        messages.success(self.request, "TCS report created.")
        return super().form_valid(form)


class TCSReportDetailView(LoginRequiredMixin, DetailView):
    model = OTMLTCSReport
    template_name = "compliance/tcs_detail.html"
    context_object_name = "report"

    def get_queryset(self):
        return OTMLTCSReport.objects.filter(project_id=self.kwargs["project_pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = _get_project(self)
        ctx["breadcrumbs"] = [
            {"label": "Projects", "url": "/projects/"},
            {"label": ctx["project"].name, "url": ctx["project"].get_absolute_url()},
            {"label": "TCS Reports", "url": reverse_lazy("compliance:tcs-list", kwargs={"project_pk": ctx["project"].pk})},
            {"label": self.object.report_number},
        ]
        return ctx


class TCSReportUpdateView(LoginRequiredMixin, UpdateView):
    model = OTMLTCSReport
    form_class = OTMLTCSReportForm
    template_name = "compliance/tcs_form.html"

    def get_queryset(self):
        return OTMLTCSReport.objects.filter(project_id=self.kwargs["project_pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = _get_project(self)
        return ctx

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "TCS report updated.")
        return super().form_valid(form)


class TCSReportSubmitView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        report = get_object_or_404(OTMLTCSReport, pk=pk, project_id=project_pk)
        if report.status == OTMLTCSReport.STATUS_DRAFT:
            report.status = OTMLTCSReport.STATUS_SUBMITTED
            report.submission_date = timezone.now().date()
            report.submitted_by = request.user
            report.save(update_fields=["status", "submission_date", "submitted_by"])
            messages.success(request, f"TCS report {report.report_number} marked as submitted.")
        from django.shortcuts import redirect
        return redirect(report.get_absolute_url())


# ---------------------------------------------------------------------------
# IRC Tax Invoices
# ---------------------------------------------------------------------------


class TaxInvoiceListView(LoginRequiredMixin, ListView):
    model = IRCTaxInvoice
    template_name = "compliance/invoice_list.html"
    context_object_name = "invoices"

    def get_queryset(self):
        return IRCTaxInvoice.objects.filter(project_id=self.kwargs["project_pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = _get_project(self)
        ctx["breadcrumbs"] = [
            {"label": "Projects", "url": "/projects/"},
            {"label": ctx["project"].name, "url": ctx["project"].get_absolute_url()},
            {"label": "Tax Invoices"},
        ]
        return ctx


class TaxInvoiceCreateView(LoginRequiredMixin, CreateView):
    model = IRCTaxInvoice
    form_class = IRCTaxInvoiceForm
    template_name = "compliance/invoice_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = _get_project(self)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = _get_project(self)
        return ctx

    def form_valid(self, form):
        project = _get_project(self)
        form.instance.project = project
        form.instance.created_by = self.request.user
        # Pre-fill client details from project if not provided
        if not form.instance.client_name and project.client:
            form.instance.client_name = project.client.name
        messages.success(self.request, "Tax invoice created.")
        return super().form_valid(form)


class TaxInvoiceDetailView(LoginRequiredMixin, DetailView):
    model = IRCTaxInvoice
    template_name = "compliance/invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return IRCTaxInvoice.objects.filter(project_id=self.kwargs["project_pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = _get_project(self)
        ctx["breadcrumbs"] = [
            {"label": "Projects", "url": "/projects/"},
            {"label": ctx["project"].name, "url": ctx["project"].get_absolute_url()},
            {"label": "Tax Invoices", "url": reverse_lazy("compliance:invoice-list", kwargs={"project_pk": ctx["project"].pk})},
            {"label": self.object.invoice_number},
        ]
        return ctx


class TaxInvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = IRCTaxInvoice
    form_class = IRCTaxInvoiceForm
    template_name = "compliance/invoice_form.html"

    def get_queryset(self):
        return IRCTaxInvoice.objects.filter(project_id=self.kwargs["project_pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = _get_project(self)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = _get_project(self)
        return ctx

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Tax invoice updated.")
        return super().form_valid(form)


class TaxInvoicePDFView(LoginRequiredMixin, DetailView):
    """Generate IRC-compliant tax invoice as PDF using WeasyPrint."""

    model = IRCTaxInvoice
    template_name = "pdf/tax_invoice.html"

    def get_queryset(self):
        return IRCTaxInvoice.objects.filter(project_id=self.kwargs["project_pk"])

    def render_to_response(self, context, **response_kwargs):
        try:
            from weasyprint import HTML
            from django.template.loader import render_to_string
            import tempfile, os

            html_string = render_to_string(self.template_name, context, request=self.request)
            html = HTML(string=html_string, base_url=self.request.build_absolute_uri("/"))
            pdf_bytes = html.write_pdf()

            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            filename = f"TaxInvoice_{self.object.invoice_number}.pdf"
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response
        except ImportError:
            messages.error(self.request, "WeasyPrint is not available in this environment.")
            from django.shortcuts import redirect
            return redirect(self.object.get_absolute_url())


# ---------------------------------------------------------------------------
# Compliance Calendar
# ---------------------------------------------------------------------------


class ComplianceCalendarView(LoginRequiredMixin, ListView):
    model = ComplianceCalendarEntry
    template_name = "compliance/calendar.html"
    context_object_name = "entries"

    def get_queryset(self):
        qs = ComplianceCalendarEntry.objects.select_related("project", "responsible")
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        # Auto-flag overdue items
        ComplianceCalendarEntry.objects.filter(
            status=ComplianceCalendarEntry.STATUS_PENDING,
            due_date__lt=today,
        ).update(status=ComplianceCalendarEntry.STATUS_OVERDUE)
        ctx["projects"] = Project.objects.filter(status__in=["ACTIVE", "MOBILISATION"])
        ctx["today"] = today
        ctx["breadcrumbs"] = [{"label": "Compliance Calendar"}]
        return ctx


class CalendarEntryCreateView(LoginRequiredMixin, CreateView):
    model = ComplianceCalendarEntry
    form_class = ComplianceCalendarEntryForm
    template_name = "compliance/calendar_form.html"
    success_url = reverse_lazy("compliance:calendar")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Compliance item added to calendar.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [
            {"label": "Compliance Calendar", "url": reverse_lazy("compliance:calendar")},
            {"label": "Add Item"},
        ]
        return ctx


class CalendarEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = ComplianceCalendarEntry
    form_class = ComplianceCalendarEntryForm
    template_name = "compliance/calendar_form.html"
    success_url = reverse_lazy("compliance:calendar")

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Compliance item updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [
            {"label": "Compliance Calendar", "url": reverse_lazy("compliance:calendar")},
            {"label": "Edit"},
        ]
        return ctx


class CalendarEntryDetailView(LoginRequiredMixin, DetailView):
    model = ComplianceCalendarEntry
    template_name = "compliance/calendar_detail.html"
    context_object_name = "entry"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [
            {"label": "Compliance Calendar", "url": reverse_lazy("compliance:calendar")},
            {"label": self.object.title},
        ]
        return ctx
