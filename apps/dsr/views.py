"""
DSR views for kemelecpms.

All views require authentication.

Covers:
  - DSRListView            — list DSRs, filterable by project / date / status
  - DSRCreateView          — create new DSR (validates one-per-project-per-day)
  - DSRDetailView          — full DSR with all related sections
  - DSRUpdateView          — edit DSR (only while status == DRAFT or RETURNED)
  - DSRSubmitView          — POST: submit for approval
  - DSRApproveView         — POST: PM approves and locks DSR
  - DSRReturnView          — POST: return with reason
  - DSRPhotoUploadView     — AJAX photo upload
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from apps.core.permissions import accessible_projects, can_approve_dsr, can_submit_dsr
from apps.core.utils import queue_task
from apps.ipc.models import IPCLineItem
from apps.procurement.models import StockLedger
from apps.schedule.models import Activity
from apps.schedule.models import ProgressEntry

from .forms import (
    DSRActivityFormSet,
    DSREquipmentFormSet,
    DSRForm,
    DSRIssueForm,
    DSRIssueFormSet,
    DSRLabourFormSet,
    DSRMaterialUsageFormSet,
    DSRPhotoForm,
    DSRPhotoFormSet,
    DSRReturnForm,
    DSRVisitorFormSet,
)
from .models import (
    DailySiteReport,
    DSRIssue,
    DSRPhoto,
)


# ---------------------------------------------------------------------------
# DSR List
# ---------------------------------------------------------------------------


class DSRListView(LoginRequiredMixin, ListView):
    model = DailySiteReport
    template_name = "dsr/dsr_list.html"
    context_object_name = "dsrs"
    paginate_by = 25

    def get_queryset(self):
        qs = DailySiteReport.objects.select_related(
            "project", "prepared_by"
        ).filter(project__in=accessible_projects(self.request.user)).order_by("-date", "-dsr_number")

        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)

        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        date_from = self.request.GET.get("date_from")
        if date_from:
            qs = qs.filter(date__gte=date_from)

        date_to = self.request.GET.get("date_to")
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        ctx["status_choices"] = DailySiteReport.STATUS_CHOICES
        ctx["selected_project"] = self.request.GET.get("project", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


# ---------------------------------------------------------------------------
# DSR Create
# ---------------------------------------------------------------------------


class DSRCreateView(LoginRequiredMixin, CreateView):
    model = DailySiteReport
    form_class = DSRForm
    template_name = "dsr/dsr_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        return kwargs

    def _selected_project(self):
        project_id = self.request.POST.get("project") if self.request.POST else None
        if project_id:
            return accessible_projects(self.request.user).filter(pk=project_id).first()
        return None

    def _scope_formsets(self, formsets, project):
        if not project:
            return
        for formset in formsets:
            for child_form in formset.forms:
                fields = child_form.fields
                if "wbs_activity" in fields:
                    fields["wbs_activity"].queryset = project.wbs_activities.all()
                if "schedule_activity" in fields:
                    fields["schedule_activity"].queryset = Activity.objects.filter(programme__project=project)
                if "ipc_line_item" in fields:
                    fields["ipc_line_item"].queryset = IPCLineItem.objects.filter(ipc__project=project)
                if "material" in fields:
                    fields["material"].queryset = fields["material"].queryset.all()
                if "stock_ledger_entry" in fields:
                    fields["stock_ledger_entry"].queryset = project.stock_ledger_entries.all()
                if "rfi" in fields:
                    fields["rfi"].queryset = project.rfis.all()
                if "ncr" in fields:
                    fields["ncr"].queryset = project.ncrs.all()
                if "incident" in fields:
                    fields["incident"].queryset = project.incidents.all()
                if "delay_event" in fields:
                    fields["delay_event"].queryset = project.delay_events.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.request.POST if self.request.POST else None
        files = self.request.FILES if self.request.FILES else None
        ctx["activity_formset"] = DSRActivityFormSet(post, prefix="activities")
        ctx["labour_formset"] = DSRLabourFormSet(post, prefix="labour")
        ctx["visitor_formset"] = DSRVisitorFormSet(post, prefix="visitors")
        ctx["equipment_formset"] = DSREquipmentFormSet(post, prefix="equipment")
        ctx["material_usage_formset"] = DSRMaterialUsageFormSet(post, prefix="mat_usage")
        ctx["photo_formset"] = DSRPhotoFormSet(post, files, prefix="photos")
        ctx["issue_formset"] = DSRIssueFormSet(post, prefix="issues")
        self._scope_formsets(
            [
                ctx["activity_formset"],
                ctx["labour_formset"],
                ctx["visitor_formset"],
                ctx["equipment_formset"],
                ctx["material_usage_formset"],
                ctx["photo_formset"],
                ctx["issue_formset"],
            ],
            self._selected_project(),
        )
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formsets = [
            ctx["activity_formset"],
            ctx["labour_formset"],
            ctx["visitor_formset"],
            ctx["equipment_formset"],
            ctx["material_usage_formset"],
            ctx["photo_formset"],
            ctx["issue_formset"],
        ]
        if not all(fs.is_valid() for fs in formsets):
            return self.form_invalid(form)
        if not accessible_projects(self.request.user).filter(pk=form.instance.project_id).exists():
            messages.error(self.request, "You do not have access to create a DSR for this project.")
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            user = self.request.user
            if getattr(user, "is_subcontractor", False):
                try:
                    form.instance.work_package = user.subcontract.work_package
                except Exception:
                    pass
            self.object = form.save()
            for fs in formsets:
                fs.instance = self.object
                fs.save()

        messages.success(
            self.request, f"DSR {self.object.dsr_number} created successfully."
        )
        return redirect(self.object.get_absolute_url())


# ---------------------------------------------------------------------------
# DSR Detail
# ---------------------------------------------------------------------------


class DSRDetailView(LoginRequiredMixin, DetailView):
    model = DailySiteReport
    template_name = "dsr/dsr_detail.html"
    context_object_name = "dsr"

    def get_queryset(self):
        return DailySiteReport.objects.select_related(
            "project",
            "prepared_by",
            "approved_by",
        ).filter(project__in=accessible_projects(self.request.user)).prefetch_related(
            "activities__wbs_activity",
            "activities__schedule_activity",
            "activities__ipc_line_item__boq_item",
            "activities__crew",
            "labour_records",
            "visitors",
            "equipment_records__equipment",
            "material_deliveries__grn",
            "material_usages__material",
            "material_usages__stock_ledger_entry",
            "photos",
            "issues__raised_by",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dsr = self.object
        ctx["can_edit"] = dsr.can_edit
        ctx["can_submit"] = (
            dsr.status == DailySiteReport.STATUS_DRAFT
            and not dsr.is_locked
            and can_submit_dsr(self.request.user, dsr)
        )
        ctx["can_approve"] = (
            dsr.status == DailySiteReport.STATUS_SUBMITTED
            and can_approve_dsr(self.request.user, dsr)
        )
        ctx["can_return"] = ctx["can_approve"]
        ctx["photo_form"] = DSRPhotoForm(project=dsr.project)
        ctx["issue_form"] = DSRIssueForm(initial={"raised_by": self.request.user, "date": dsr.date})
        return ctx


# ---------------------------------------------------------------------------
# DSR Update
# ---------------------------------------------------------------------------


class DSRUpdateView(LoginRequiredMixin, UpdateView):
    model = DailySiteReport
    form_class = DSRForm
    template_name = "dsr/dsr_form.html"

    def get_queryset(self):
        return DailySiteReport.objects.filter(project__in=accessible_projects(self.request.user))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        return kwargs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        return obj

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.can_edit:
            messages.error(
                request, "This DSR is locked or has been submitted/approved and cannot be edited."
            )
            return redirect(obj.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.request.POST if self.request.POST else None
        files = self.request.FILES if self.request.FILES else None
        ctx["activity_formset"] = DSRActivityFormSet(
            post, instance=self.object, prefix="activities"
        )
        ctx["labour_formset"] = DSRLabourFormSet(
            post, instance=self.object, prefix="labour"
        )
        ctx["visitor_formset"] = DSRVisitorFormSet(
            post, instance=self.object, prefix="visitors"
        )
        ctx["equipment_formset"] = DSREquipmentFormSet(
            post, instance=self.object, prefix="equipment"
        )
        ctx["material_usage_formset"] = DSRMaterialUsageFormSet(
            post, instance=self.object, prefix="mat_usage"
        )
        ctx["photo_formset"] = DSRPhotoFormSet(
            post, files, instance=self.object, prefix="photos"
        )
        ctx["issue_formset"] = DSRIssueFormSet(
            post, instance=self.object, prefix="issues"
        )
        DSRCreateView._scope_formsets(
            self,
            [
                ctx["activity_formset"],
                ctx["labour_formset"],
                ctx["visitor_formset"],
                ctx["equipment_formset"],
                ctx["material_usage_formset"],
                ctx["photo_formset"],
                ctx["issue_formset"],
            ],
            self.object.project,
        )
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formsets = [
            ctx["activity_formset"],
            ctx["labour_formset"],
            ctx["visitor_formset"],
            ctx["equipment_formset"],
            ctx["material_usage_formset"],
            ctx["photo_formset"],
            ctx["issue_formset"],
        ]
        if not all(fs.is_valid() for fs in formsets):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            for fs in formsets:
                fs.instance = self.object
                fs.save()

        messages.success(self.request, f"DSR {self.object.dsr_number} updated.")
        return redirect(self.object.get_absolute_url())


# ---------------------------------------------------------------------------
# DSR Submit
# ---------------------------------------------------------------------------


class DSRSubmitView(LoginRequiredMixin, View):
    """POST-only: submit a draft DSR for approval."""

    def post(self, request, pk):
        dsr = get_object_or_404(
            DailySiteReport,
            pk=pk,
            project__in=accessible_projects(request.user),
        )
        if not can_submit_dsr(request.user, dsr):
            messages.error(request, "You do not have permission to submit this DSR.")
            return redirect(dsr.get_absolute_url())
        if dsr.status != DailySiteReport.STATUS_DRAFT:
            messages.error(request, "Only draft DSRs can be submitted.")
            return redirect(dsr.get_absolute_url())
        if dsr.is_locked:
            messages.error(request, "This DSR is locked.")
            return redirect(dsr.get_absolute_url())
        dsr.status = DailySiteReport.STATUS_SUBMITTED
        dsr.updated_by = request.user
        dsr.save(update_fields=["status", "updated_by", "updated_at"])
        from apps.core.models import AuditLog
        AuditLog.log(request.user, AuditLog.ACTION_SUBMIT, dsr, request=request)
        from .tasks import notify_dsr_submitted
        queue_task(notify_dsr_submitted, dsr.pk)
        messages.success(request, f"{dsr.dsr_number} submitted for approval.")
        return redirect(dsr.get_absolute_url())


# ---------------------------------------------------------------------------
# DSR Approve
# ---------------------------------------------------------------------------


class DSRApproveView(LoginRequiredMixin, View):
    """POST-only: approve and lock a submitted DSR."""

    def _sync_schedule_progress(self, dsr, user):
        for activity in dsr.activities.filter(schedule_activity__isnull=False):
            ProgressEntry.objects.update_or_create(
                activity=activity.schedule_activity,
                date=dsr.date,
                defaults={
                    "percent_complete": activity.percent_complete,
                    "recorded_by": user,
                    "notes": f"Progress recorded from {dsr.dsr_number}: {activity.description}",
                    "dsr_id": dsr.pk,
                    "created_by": user,
                    "updated_by": user,
                },
            )

    def _sync_material_usage(self, dsr, user):
        for usage in dsr.material_usages.filter(stock_ledger_entry__isnull=True):
            ledger = StockLedger.objects.create(
                project=dsr.project,
                material=usage.material,
                date=dsr.date,
                transaction_type=StockLedger.TYPE_ISSUE,
                quantity=usage.quantity_used,
                reference=dsr.dsr_number,
                recorded_by=user,
                notes=usage.notes or f"Issued to works from {dsr.dsr_number}",
                created_by=user,
                updated_by=user,
            )
            usage.stock_ledger_entry = ledger
            usage.updated_by = user
            usage.save(update_fields=["stock_ledger_entry", "updated_by", "updated_at"])

    def post(self, request, pk):
        dsr = get_object_or_404(
            DailySiteReport,
            pk=pk,
            project__in=accessible_projects(request.user),
        )
        if not can_approve_dsr(request.user, dsr):
            messages.error(request, "You do not have permission to approve this DSR.")
            return redirect(dsr.get_absolute_url())
        if dsr.status != DailySiteReport.STATUS_SUBMITTED:
            messages.error(request, "Only submitted DSRs can be approved.")
            return redirect(dsr.get_absolute_url())
        with transaction.atomic():
            dsr.status = DailySiteReport.STATUS_APPROVED
            dsr.approved_by = request.user
            dsr.approved_at = timezone.now()
            dsr.is_locked = True
            dsr.updated_by = request.user
            dsr.save(
                update_fields=[
                    "status",
                    "approved_by",
                    "approved_at",
                    "is_locked",
                    "updated_by",
                    "updated_at",
                ]
            )
            self._sync_schedule_progress(dsr, request.user)
            self._sync_material_usage(dsr, request.user)
            from apps.core.models import AuditLog
            AuditLog.log(request.user, AuditLog.ACTION_APPROVE, dsr, request=request)
            from .tasks import notify_dsr_approved
            queue_task(notify_dsr_approved, dsr.pk)
        messages.success(request, f"{dsr.dsr_number} approved and locked.")
        return redirect(dsr.get_absolute_url())


# ---------------------------------------------------------------------------
# DSR Return
# ---------------------------------------------------------------------------


class DSRReturnView(LoginRequiredMixin, FormView):
    """Return a submitted DSR to the preparer with a reason."""

    form_class = DSRReturnForm
    template_name = "dsr/dsr_return.html"

    def get_dsr(self):
        return get_object_or_404(
            DailySiteReport,
            pk=self.kwargs["pk"],
            project__in=accessible_projects(self.request.user),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dsr"] = self.get_dsr()
        return ctx

    def form_valid(self, form):
        dsr = self.get_dsr()
        if dsr.status != DailySiteReport.STATUS_SUBMITTED:
            messages.error(self.request, "Only submitted DSRs can be returned.")
            return redirect(dsr.get_absolute_url())
        dsr.status = DailySiteReport.STATUS_RETURNED
        dsr.return_reason = form.cleaned_data["return_reason"]
        dsr.updated_by = self.request.user
        dsr.save(update_fields=["status", "return_reason", "updated_by", "updated_at"])
        from .tasks import notify_dsr_returned
        queue_task(notify_dsr_returned, dsr.pk)
        messages.warning(
            self.request, f"{dsr.dsr_number} has been returned for revision."
        )
        return redirect(dsr.get_absolute_url())


# ---------------------------------------------------------------------------
# DSR Photo Upload (AJAX)
# ---------------------------------------------------------------------------


class DSRPhotoUploadView(LoginRequiredMixin, View):
    """
    AJAX endpoint: POST a photo to attach to a DSR.
    Expects multipart/form-data with 'photo', 'caption', 'tag'.
    Returns JSON with photo id and URL on success.
    """

    def post(self, request, pk):
        dsr = get_object_or_404(
            DailySiteReport,
            pk=pk,
            project__in=accessible_projects(request.user),
        )
        if dsr.is_locked:
            return JsonResponse(
                {"success": False, "error": "DSR is locked."}, status=403
            )
        form = DSRPhotoForm(request.POST, request.FILES, project=dsr.project)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.dsr = dsr
            photo.created_by = request.user
            photo.save()
            return JsonResponse(
                {
                    "success": True,
                    "id": photo.pk,
                    "url": photo.photo.url,
                    "caption": photo.caption,
                    "tag": photo.get_tag_display(),
                }
            )
        return JsonResponse(
            {"success": False, "errors": form.errors}, status=400
        )


# ---------------------------------------------------------------------------
# PDF view
# ---------------------------------------------------------------------------


class DSRPDFView(LoginRequiredMixin, DetailView):
    """Render a DSR as a print-ready PDF using WeasyPrint."""

    template_name = "pdf/dsr.html"
    model = DailySiteReport
    context_object_name = "dsr"

    def get_queryset(self):
        return DailySiteReport.objects.filter(
            project__in=accessible_projects(self.request.user)
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dsr = self.object
        ctx["activities"] = dsr.activities.all()
        ctx["labour_entries"] = dsr.labour_records.all()
        ctx["equipment_entries"] = dsr.equipment_records.select_related("equipment").all()
        ctx["material_deliveries"] = dsr.material_deliveries.all()
        ctx["material_usages"] = dsr.material_usages.select_related(
            "material", "stock_ledger_entry"
        ).all()
        ctx["photos"] = dsr.photos.all()
        ctx["issues"] = dsr.issues.all()
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
            response["Content-Disposition"] = f'inline; filename="DSR_{self.object.dsr_number}.pdf"'
            return response
        except ImportError:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(self.request, "PDF generation requires WeasyPrint.")
            return redirect(self.object.get_absolute_url())
