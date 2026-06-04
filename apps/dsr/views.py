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

from apps.projects.models import Project

from .forms import (
    DSRActivityFormSet,
    DSREquipmentFormSet,
    DSRForm,
    DSRIssueForm,
    DSRIssueFormSet,
    DSRLabourFormSet,
    DSRMaterialUsageFormSet,
    DSRPhotoForm,
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
        ).order_by("-date", "-dsr_number")

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
        ctx["projects"] = Project.objects.all()
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.request.POST if self.request.POST else None
        ctx["activity_formset"] = DSRActivityFormSet(post, prefix="activities")
        ctx["labour_formset"] = DSRLabourFormSet(post, prefix="labour")
        ctx["visitor_formset"] = DSRVisitorFormSet(post, prefix="visitors")
        ctx["equipment_formset"] = DSREquipmentFormSet(post, prefix="equipment")
        ctx["material_usage_formset"] = DSRMaterialUsageFormSet(post, prefix="mat_usage")
        ctx["issue_formset"] = DSRIssueFormSet(post, prefix="issues")
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formsets = [
            ctx["activity_formset"],
            ctx["labour_formset"],
            ctx["visitor_formset"],
            ctx["equipment_formset"],
            ctx["material_usage_formset"],
            ctx["issue_formset"],
        ]
        if not all(fs.is_valid() for fs in formsets):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
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
        ).prefetch_related(
            "activities__wbs_activity",
            "activities__crew",
            "labour_records",
            "visitors",
            "equipment_records__equipment",
            "material_deliveries__grn",
            "material_usages__material",
            "photos",
            "issues__raised_by",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dsr = self.object
        ctx["can_edit"] = dsr.can_edit
        ctx["can_submit"] = dsr.status == DailySiteReport.STATUS_DRAFT and not dsr.is_locked
        ctx["can_approve"] = dsr.status == DailySiteReport.STATUS_SUBMITTED
        ctx["can_return"] = dsr.status == DailySiteReport.STATUS_SUBMITTED
        ctx["photo_form"] = DSRPhotoForm()
        ctx["issue_form"] = DSRIssueForm(initial={"raised_by": self.request.user, "date": dsr.date})
        return ctx


# ---------------------------------------------------------------------------
# DSR Update
# ---------------------------------------------------------------------------


class DSRUpdateView(LoginRequiredMixin, UpdateView):
    model = DailySiteReport
    form_class = DSRForm
    template_name = "dsr/dsr_form.html"

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
        ctx["issue_formset"] = DSRIssueFormSet(
            post, instance=self.object, prefix="issues"
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
        dsr = get_object_or_404(DailySiteReport, pk=pk)
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
        messages.success(request, f"{dsr.dsr_number} submitted for approval.")
        return redirect(dsr.get_absolute_url())


# ---------------------------------------------------------------------------
# DSR Approve
# ---------------------------------------------------------------------------


class DSRApproveView(LoginRequiredMixin, View):
    """POST-only: approve and lock a submitted DSR."""

    def post(self, request, pk):
        dsr = get_object_or_404(DailySiteReport, pk=pk)
        if dsr.status != DailySiteReport.STATUS_SUBMITTED:
            messages.error(request, "Only submitted DSRs can be approved.")
            return redirect(dsr.get_absolute_url())
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
        from apps.core.models import AuditLog
        AuditLog.log(request.user, AuditLog.ACTION_APPROVE, dsr, request=request)
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
        return get_object_or_404(DailySiteReport, pk=self.kwargs["pk"])

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
        dsr = get_object_or_404(DailySiteReport, pk=pk)
        if dsr.is_locked:
            return JsonResponse(
                {"success": False, "error": "DSR is locked."}, status=403
            )
        form = DSRPhotoForm(request.POST, request.FILES)
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dsr = self.object
        ctx["activities"] = dsr.activities.all()
        ctx["labour_entries"] = dsr.labour_entries.select_related("worker").all()
        ctx["equipment_entries"] = dsr.equipment_entries.select_related("equipment").all()
        ctx["material_deliveries"] = dsr.material_deliveries.all()
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
