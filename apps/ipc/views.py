from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from apps.core.utils import queue_task
from apps.core.permissions import (
    accessible_projects,
    can_approve_financial_action,
    can_certify_ipc,
    can_manage_ipc,
    can_record_payment,
    can_submit_ipc,
)
from apps.projects.models import Project

from .forms import CertificationForm, IPCForm, PaymentForm, RetentionReleaseForm
from .models import Certification, IPC, IPCLineItem, Payment, RetentionRelease


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class ProjectMixin(LoginRequiredMixin):
    """Resolves the current project from the ``project_pk`` URL kwarg."""

    def get_project(self):
        if not hasattr(self, "_project"):
            self._project = get_object_or_404(
                accessible_projects(self.request.user),
                pk=self.kwargs["project_pk"],
            )
        return self._project

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.get_project()
        return ctx


# ---------------------------------------------------------------------------
# IPC views
# ---------------------------------------------------------------------------


class IPCListView(ProjectMixin, ListView):
    model = IPC
    template_name = "ipc/ipc_list.html"
    context_object_name = "ipcs"

    def get_queryset(self):
        return IPC.objects.filter(project=self.get_project()).order_by("ipc_number")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = IPC.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        # Ledger totals
        ipcs = self.get_queryset()
        total_claimed = sum(ipc.total_claimed for ipc in ipcs)
        total_certified = sum(ipc.amount_certified for ipc in ipcs)
        total_paid = sum(ipc.amount_paid for ipc in ipcs)
        ctx["total_claimed"] = total_claimed
        ctx["total_certified"] = total_certified
        ctx["total_paid"] = total_paid
        ctx["total_outstanding"] = total_certified - total_paid
        return ctx


class IPCCreateView(ProjectMixin, CreateView):
    """Create an IPC and auto-populate BoQ line items from current progress."""

    model = IPC
    form_class = IPCForm
    template_name = "ipc/ipc_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        project = self.get_project()
        if not can_manage_ipc(self.request.user, project):
            messages.error(self.request, "You do not have permission to create IPCs for this project.")
            return redirect(reverse_lazy("ipc:ipc-list", kwargs={"project_pk": project.pk}))
        with transaction.atomic():
            ipc = form.save(commit=False)
            ipc.project = project
            ipc.created_by = self.request.user
            ipc.save()
            self._populate_line_items(ipc, project)
        messages.success(self.request, f"{ipc.ipc_number} created with BoQ line items.")
        return redirect(
            reverse_lazy("ipc:ipc-detail", kwargs={"project_pk": project.pk, "pk": ipc.pk})
        )

    def _populate_line_items(self, ipc: IPC, project: Project) -> None:
        """
        For each BoQ item in the project, calculate the cumulative % claimed in
        all previous certified/paid IPCs and populate this IPC's line items.
        """
        from apps.budget.models import BoQItem

        boq_items = BoQItem.objects.filter(project=project).order_by("item_number")
        previous_ipcs = IPC.objects.filter(
            project=project,
            status__in=[
                IPC.STATUS_CERTIFIED,
                IPC.STATUS_DISPUTED,
                IPC.STATUS_PAID,
                IPC.STATUS_SUBMITTED,
                IPC.STATUS_INTERNAL_REVIEW,
            ],
        ).exclude(pk=ipc.pk)

        line_items_to_create = []
        for boq_item in boq_items:
            prev_percent = Decimal("0.00")
            for prev_ipc in previous_ipcs:
                try:
                    prev_line = prev_ipc.line_items.get(boq_item=boq_item)
                    prev_percent += prev_line.cumulative_percent
                except IPCLineItem.DoesNotExist:
                    pass
            prev_percent = min(prev_percent, Decimal("100.00"))
            line_items_to_create.append(
                IPCLineItem(
                    ipc=ipc,
                    boq_item=boq_item,
                    boq_description=boq_item.description[:500],
                    boq_quantity=boq_item.quantity,
                    unit_rate=boq_item.unit_rate,
                    previous_percent=prev_percent,
                    current_percent=Decimal("0.00"),
                    created_by=self.request.user,
                )
            )
        IPCLineItem.objects.bulk_create(line_items_to_create)


class IPCDetailView(ProjectMixin, DetailView):
    model = IPC
    template_name = "ipc/ipc_detail.html"
    context_object_name = "ipc"

    def get_queryset(self):
        return IPC.objects.filter(project=self.get_project()).prefetch_related(
            "line_items__boq_item", "payments"
        ).select_related("certification")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ipc = self.object
        ctx["line_items"] = ipc.line_items.order_by("boq_item__item_number")
        ctx["has_certification"] = hasattr(ipc, "certification") and ipc.certification is not None
        try:
            ctx["certification"] = ipc.certification
        except Certification.DoesNotExist:
            ctx["certification"] = None
        ctx["payments"] = ipc.payments.order_by("-payment_date")
        ctx["can_submit"] = (
            ipc.status in (IPC.STATUS_DRAFT, IPC.STATUS_INTERNAL_REVIEW)
            and can_submit_ipc(self.request.user, ipc)
        )
        ctx["can_certify"] = (
            ipc.status == IPC.STATUS_SUBMITTED
            and ctx["certification"] is None
            and can_certify_ipc(self.request.user, ipc)
        )
        ctx["can_pay"] = (
            ipc.status in (IPC.STATUS_CERTIFIED, IPC.STATUS_DISPUTED)
            and can_record_payment(self.request.user, ipc)
        )
        return ctx


# ---------------------------------------------------------------------------
# IPCSubmitView
# ---------------------------------------------------------------------------


class IPCSubmitView(LoginRequiredMixin, View):
    """POST: transition an IPC from Draft/Internal Review to Submitted."""

    http_method_names = ["post"]

    def post(self, request, project_pk, pk):
        project = get_object_or_404(accessible_projects(request.user), pk=project_pk)
        ipc = get_object_or_404(IPC, pk=pk, project=project)
        if not can_submit_ipc(request.user, ipc):
            messages.error(request, "You do not have permission to submit this IPC.")
            return redirect(
                reverse_lazy("ipc:ipc-detail", kwargs={"project_pk": project_pk, "pk": pk})
            )
        if ipc.status not in (IPC.STATUS_DRAFT, IPC.STATUS_INTERNAL_REVIEW):
            messages.error(request, "Only Draft or Internal Review IPCs can be submitted.")
            return redirect(
                reverse_lazy("ipc:ipc-detail", kwargs={"project_pk": project_pk, "pk": pk})
            )
        from django.utils import timezone
        from apps.core.models import AuditLog
        ipc.status = IPC.STATUS_SUBMITTED
        ipc.submitted_date = ipc.submitted_date or timezone.now().date()
        ipc.updated_by = request.user
        ipc.save(update_fields=["status", "submitted_date", "updated_by", "updated_at"])
        AuditLog.log(request.user, AuditLog.ACTION_SUBMIT, ipc, request=request)
        from .tasks import notify_ipc_submitted
        queue_task(notify_ipc_submitted, ipc.pk)
        messages.success(request, f"{ipc.ipc_number} submitted successfully.")
        return redirect(
            reverse_lazy("ipc:ipc-detail", kwargs={"project_pk": project_pk, "pk": pk})
        )


# ---------------------------------------------------------------------------
# Certification views
# ---------------------------------------------------------------------------


class CertificationCreateView(ProjectMixin, CreateView):
    model = Certification
    form_class = CertificationForm
    template_name = "ipc/certification_form.html"

    def get_ipc(self):
        if not hasattr(self, "_ipc"):
            self._ipc = get_object_or_404(
                IPC,
                pk=self.kwargs["ipc_pk"],
                project=self.get_project(),
                status=IPC.STATUS_SUBMITTED,
            )
        return self._ipc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ipc"] = self.get_ipc()
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ipc"] = self.get_ipc()
        return kwargs

    def form_valid(self, form):
        ipc = self.get_ipc()
        if not can_certify_ipc(self.request.user, ipc):
            messages.error(self.request, "You do not have permission to certify IPCs.")
            return redirect(
                reverse_lazy("ipc:ipc-detail", kwargs={"project_pk": ipc.project_id, "pk": ipc.pk})
            )
        if not can_approve_financial_action(self.request.user, ipc.project, form.instance.amount_certified):
            messages.error(self.request, "Your financial approval threshold is below this certified amount.")
            return redirect(
                reverse_lazy("ipc:ipc-detail", kwargs={"project_pk": ipc.project_id, "pk": ipc.pk})
            )
        form.instance.ipc = ipc
        form.instance.created_by = self.request.user
        from apps.core.models import AuditLog
        AuditLog.log(self.request.user, AuditLog.ACTION_APPROVE, ipc, changes="Certification recorded.", request=self.request)
        messages.success(self.request, f"Certification recorded for {ipc.ipc_number}.")
        return super().form_valid(form)

    def get_success_url(self):
        ipc = self.get_ipc()
        return reverse_lazy(
            "ipc:ipc-detail", kwargs={"project_pk": ipc.project_id, "pk": ipc.pk}
        )


# ---------------------------------------------------------------------------
# Payment views
# ---------------------------------------------------------------------------


class PaymentCreateView(ProjectMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = "ipc/payment_form.html"

    def get_ipc(self):
        if not hasattr(self, "_ipc"):
            self._ipc = get_object_or_404(
                IPC,
                pk=self.kwargs["ipc_pk"],
                project=self.get_project(),
                status__in=[IPC.STATUS_CERTIFIED, IPC.STATUS_DISPUTED],
            )
        return self._ipc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ipc"] = self.get_ipc()
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ipc"] = self.get_ipc()
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["received_by"].initial = self.request.user
        form.fields["received_by"].disabled = True
        return form

    def form_valid(self, form):
        ipc = self.get_ipc()
        if not can_record_payment(self.request.user, ipc):
            messages.error(self.request, "You do not have permission to record IPC payments.")
            return redirect(
                reverse_lazy("ipc:ipc-detail", kwargs={"project_pk": ipc.project_id, "pk": ipc.pk})
            )
        if not can_approve_financial_action(self.request.user, ipc.project, form.instance.amount):
            messages.error(self.request, "Your financial approval threshold is below this payment amount.")
            return redirect(
                reverse_lazy("ipc:ipc-detail", kwargs={"project_pk": ipc.project_id, "pk": ipc.pk})
            )
        form.instance.ipc = ipc
        form.instance.received_by = self.request.user
        form.instance.created_by = self.request.user
        from apps.core.models import AuditLog
        AuditLog.log(self.request.user, AuditLog.ACTION_UPDATE, ipc, changes="Payment recorded.", request=self.request)
        response = super().form_valid(form)
        from .tasks import notify_payment_received
        queue_task(notify_payment_received, ipc.pk)
        messages.success(self.request, "Payment recorded.")
        return response

    def get_success_url(self):
        ipc = self.get_ipc()
        return reverse_lazy(
            "ipc:ipc-detail", kwargs={"project_pk": ipc.project_id, "pk": ipc.pk}
        )


# ---------------------------------------------------------------------------
# IPC Ledger View
# ---------------------------------------------------------------------------


class IPCLedgerView(ProjectMixin, TemplateView):
    """
    Summary ledger showing for each IPC:
      claimed → certified → paid → outstanding per project.
    """

    template_name = "ipc/ipc_ledger.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        ipcs = (
            IPC.objects.filter(project=project)
            .prefetch_related("line_items", "payments")
            .select_related("certification")
            .order_by("ipc_number")
        )

        rows = []
        cumulative_claimed = Decimal("0.00")
        cumulative_certified = Decimal("0.00")
        cumulative_paid = Decimal("0.00")

        for ipc in ipcs:
            claimed = ipc.total_claimed
            certified = ipc.amount_certified
            paid = ipc.amount_paid
            outstanding = certified - paid
            cumulative_claimed += claimed
            cumulative_certified += certified
            cumulative_paid += paid
            rows.append(
                {
                    "ipc": ipc,
                    "claimed": claimed,
                    "certified": certified,
                    "paid": paid,
                    "outstanding": outstanding,
                }
            )

        # Retention releases
        retention_releases = RetentionRelease.objects.filter(project=project).order_by(
            "release_date"
        )
        total_retention_released = (
            retention_releases.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )

        ctx.update(
            {
                "rows": rows,
                "cumulative_claimed": cumulative_claimed,
                "cumulative_certified": cumulative_certified,
                "cumulative_paid": cumulative_paid,
                "cumulative_outstanding": cumulative_certified - cumulative_paid,
                "retention_releases": retention_releases,
                "total_retention_released": total_retention_released,
            }
        )
        return ctx


# ---------------------------------------------------------------------------
# PDF views
# ---------------------------------------------------------------------------


class IPCPDFView(ProjectMixin, DetailView):
    """Render an IPC as a print-ready PDF using WeasyPrint."""

    template_name = "pdf/ipc.html"

    def get_queryset(self):
        return IPC.objects.filter(project=self.get_project())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.get_project()
        ctx["line_items"] = IPCLineItem.objects.filter(ipc=self.object).select_related("boq_item")
        ctx["certifications"] = Certification.objects.filter(ipc=self.object)
        ctx["payments"] = Payment.objects.filter(ipc=self.object)
        return ctx

    def render_to_response(self, context, **response_kwargs):
        from django.http import HttpResponse
        try:
            from weasyprint import HTML
            from django.template.loader import render_to_string
            html_string = render_to_string(self.template_name, context, request=self.request)
            html = HTML(string=html_string, base_url=self.request.build_absolute_uri("/"))
            pdf_bytes = html.write_pdf()
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="IPC_{self.object.ipc_number}.pdf"'
            return response
        except ImportError:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(self.request, "PDF generation requires WeasyPrint.")
            return redirect(self.object.get_absolute_url())
