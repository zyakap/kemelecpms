"""
Compliance & Funder Reporting views.
"""

import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from apps.core.permissions import accessible_projects
from apps.projects.models import Project

from .forms import (
    AuthorityPermitForm,
    ComplianceCalendarEntryForm,
    ComplianceCalendarTemplateForm,
    FunderReportPackForm,
    IRCTaxInvoiceForm,
    LocalContentRecordForm,
    OTMLTCSReportForm,
    PublicProcurementRecordForm,
    TaxInvoiceVoidForm,
)
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_project(view):
    return get_object_or_404(accessible_projects(view.request.user), pk=view.kwargs["project_pk"])


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
        _get_project(self)
        return IRCTaxInvoice.objects.filter(project_id=self.kwargs["project_pk"])

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            return self.export_csv()
        return super().get(request, *args, **kwargs)

    def export_csv(self):
        project = _get_project(self)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="tax_invoices_{project.project_id}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Invoice", "Sequence", "Date", "Client", "TINPNG", "Subtotal", "GST", "Total", "Status", "Payment Date", "Payment Reference"])
        for invoice in self.get_queryset():
            writer.writerow([
                invoice.invoice_number,
                invoice.sequence_number,
                invoice.invoice_date,
                invoice.client_name,
                invoice.client_tinpng,
                invoice.subtotal,
                invoice.gst_amount,
                invoice.total_amount,
                invoice.get_status_display(),
                invoice.payment_date or "",
                invoice.payment_reference,
            ])
        return response

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


class TaxInvoiceVoidView(LoginRequiredMixin, View):
    def post(self, request, project_pk, pk):
        invoice = get_object_or_404(
            IRCTaxInvoice,
            pk=pk,
            project=_get_project(self),
        )
        form = TaxInvoiceVoidForm(request.POST)
        if form.is_valid() and invoice.status != IRCTaxInvoice.STATUS_VOID:
            invoice.void(user=request.user, reason=form.cleaned_data["reason"])
            messages.success(request, f"Invoice {invoice.invoice_number} voided.")
        else:
            messages.error(request, "Void reason is required.")
        return redirect(invoice.get_absolute_url())


class ProjectComplianceMixin(LoginRequiredMixin):
    model = None
    form_class = None
    template_name = "compliance/register_form.html"
    context_object_name = "records"
    page_title = "Compliance Register"
    list_url_name = ""
    create_url_name = ""

    def dispatch(self, request, *args, **kwargs):
        self.project = _get_project(self)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(project=self.project)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["page_title"] = self.page_title
        ctx["list_url_name"] = self.list_url_name
        ctx["create_url_name"] = self.create_url_name
        ctx["breadcrumbs"] = [
            {"label": "Projects", "url": reverse("projects:project_list")},
            {"label": self.project.project_id, "url": self.project.get_absolute_url()},
            {"label": self.page_title},
        ]
        return ctx


class ProjectComplianceCreateMixin(ProjectComplianceMixin, CreateView):
    template_name = "compliance/register_form.html"

    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.created_by = self.request.user
        messages.success(self.request, f"{self.page_title} record saved.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(self.list_url_name, kwargs={"project_pk": self.project.pk})


class ProjectComplianceUpdateMixin(ProjectComplianceMixin, UpdateView):
    template_name = "compliance/register_form.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f"{self.page_title} record updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(self.list_url_name, kwargs={"project_pk": self.project.pk})


class PublicProcurementListView(ProjectComplianceMixin, ListView):
    model = PublicProcurementRecord
    template_name = "compliance/public_procurement_list.html"
    page_title = "Public Procurement Evidence"
    list_url_name = "compliance:public-procurement-list"
    create_url_name = "compliance:public-procurement-create"


class PublicProcurementCreateView(ProjectComplianceCreateMixin):
    model = PublicProcurementRecord
    form_class = PublicProcurementRecordForm
    page_title = "Public Procurement Evidence"
    list_url_name = "compliance:public-procurement-list"


class PublicProcurementUpdateView(ProjectComplianceUpdateMixin):
    model = PublicProcurementRecord
    form_class = PublicProcurementRecordForm
    page_title = "Public Procurement Evidence"
    list_url_name = "compliance:public-procurement-list"


class LocalContentListView(ProjectComplianceMixin, ListView):
    model = LocalContentRecord
    template_name = "compliance/local_content_list.html"
    page_title = "National Participation / Local Content"
    list_url_name = "compliance:local-content-list"
    create_url_name = "compliance:local-content-create"


class LocalContentCreateView(ProjectComplianceCreateMixin):
    model = LocalContentRecord
    form_class = LocalContentRecordForm
    page_title = "National Participation / Local Content"
    list_url_name = "compliance:local-content-list"


class LocalContentUpdateView(ProjectComplianceUpdateMixin):
    model = LocalContentRecord
    form_class = LocalContentRecordForm
    page_title = "National Participation / Local Content"
    list_url_name = "compliance:local-content-list"


class AuthorityPermitListView(ProjectComplianceMixin, ListView):
    model = AuthorityPermit
    template_name = "compliance/authority_permit_list.html"
    page_title = "Authority Permits & Certificates"
    list_url_name = "compliance:authority-permit-list"
    create_url_name = "compliance:authority-permit-create"


class AuthorityPermitCreateView(ProjectComplianceCreateMixin):
    model = AuthorityPermit
    form_class = AuthorityPermitForm
    page_title = "Authority Permits & Certificates"
    list_url_name = "compliance:authority-permit-list"


class AuthorityPermitUpdateView(ProjectComplianceUpdateMixin):
    model = AuthorityPermit
    form_class = AuthorityPermitForm
    page_title = "Authority Permits & Certificates"
    list_url_name = "compliance:authority-permit-list"


class FunderReportPackListView(ProjectComplianceMixin, ListView):
    model = FunderReportPack
    template_name = "compliance/funder_pack_list.html"
    page_title = "Funder Reporting Packs"
    list_url_name = "compliance:funder-pack-list"
    create_url_name = "compliance:funder-pack-create"


class FunderReportPackCreateView(ProjectComplianceCreateMixin):
    model = FunderReportPack
    form_class = FunderReportPackForm
    page_title = "Funder Reporting Packs"
    list_url_name = "compliance:funder-pack-list"


class FunderReportPackUpdateView(ProjectComplianceUpdateMixin):
    model = FunderReportPack
    form_class = FunderReportPackForm
    page_title = "Funder Reporting Packs"
    list_url_name = "compliance:funder-pack-list"


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


class ComplianceCalendarTemplateListView(LoginRequiredMixin, ListView):
    model = ComplianceCalendarTemplate
    template_name = "compliance/calendar_template_list.html"
    context_object_name = "templates"

    def get_queryset(self):
        qs = ComplianceCalendarTemplate.objects.all()
        if self.request.GET.get("active") == "1":
            qs = qs.filter(is_active=True)
        return qs


class ComplianceCalendarTemplateCreateView(LoginRequiredMixin, CreateView):
    model = ComplianceCalendarTemplate
    form_class = ComplianceCalendarTemplateForm
    template_name = "compliance/calendar_template_form.html"
    success_url = reverse_lazy("compliance:calendar-template-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Compliance calendar template saved.")
        return super().form_valid(form)


class ComplianceCalendarTemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = ComplianceCalendarTemplate
    form_class = ComplianceCalendarTemplateForm
    template_name = "compliance/calendar_template_form.html"
    success_url = reverse_lazy("compliance:calendar-template-list")

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Compliance calendar template updated.")
        return super().form_valid(form)


class ProjectMapView(LoginRequiredMixin, TemplateView):
    template_name = "compliance/project_map.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        projects = accessible_projects(self.request.user).exclude(gps_lat__isnull=True).exclude(gps_lng__isnull=True)
        province = self.request.GET.get("province")
        if province:
            projects = projects.filter(province__iexact=province)
        ctx["projects"] = projects.select_related("client").order_by("province", "district", "name")
        ctx["province"] = province or ""
        ctx["provinces"] = (
            accessible_projects(self.request.user)
            .exclude(province="")
            .values_list("province", flat=True)
            .distinct()
            .order_by("province")
        )
        return ctx
