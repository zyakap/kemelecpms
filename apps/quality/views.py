from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.core.permissions import accessible_projects, can_manage_quality
from apps.core.models import AuditLog
from apps.core.workflows import assert_transition
from apps.projects.models import Project

from .forms import (
    DefectForm,
    InspectionChecklistForm,
    InspectionChecklistItemForm,
    InspectionRecordForm,
    ITPForm,
    ITPItemForm,
    MaterialTestResultForm,
    NCRForm,
)
from .models import (
    Defect,
    ITP,
    InspectionChecklist,
    InspectionChecklistItem,
    InspectionRecord,
    ITPItem,
    MaterialTestResult,
    NCR,
)


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
# ITP views
# ---------------------------------------------------------------------------


class ITPListView(ProjectMixin, ListView):
    model = ITP
    template_name = "quality/itp_list.html"
    context_object_name = "itps"

    def get_queryset(self):
        return (
            ITP.objects.filter(project=self.get_project())
            .order_by("title")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = ITP.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class ITPCreateView(ProjectMixin, CreateView):
    model = ITP
    form_class = ITPForm
    template_name = "quality/itp_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create ITPs for this project.")
            return redirect(reverse_lazy("quality:itp-list", kwargs={"project_pk": self.get_project().pk}))
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "ITP created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("quality:itp-list", kwargs={"project_pk": self.get_project().pk})


class ITPDetailView(ProjectMixin, DetailView):
    model = ITP
    template_name = "quality/itp_detail.html"
    context_object_name = "itp"

    def get_queryset(self):
        return ITP.objects.filter(project=self.get_project()).prefetch_related(
            "items__inspection_records"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        itp = self.object
        ctx["items"] = itp.items.order_by("sequence").prefetch_related("inspection_records")
        ctx["itp_item_form"] = ITPItemForm(itp=itp)
        ctx["checklists"] = itp.checklists.prefetch_related("items").order_by("-inspection_date")
        return ctx


# ---------------------------------------------------------------------------
# Inspection Record views
# ---------------------------------------------------------------------------


class InspectionRecordCreateView(LoginRequiredMixin, CreateView):
    """Create an inspection record for a specific ITP item."""

    model = InspectionRecord
    form_class = InspectionRecordForm
    template_name = "quality/inspectionrecord_form.html"

    def get_itp_item(self):
        if not hasattr(self, "_itp_item"):
            self._itp_item = get_object_or_404(
                ITPItem,
                pk=self.kwargs["itp_item_pk"],
                itp__project__in=accessible_projects(self.request.user),
            )
        return self._itp_item

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["itp_item"] = self.get_itp_item()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["itp_item"] = self.get_itp_item()
        ctx["itp"] = self.get_itp_item().itp
        ctx["project"] = self.get_itp_item().itp.project
        return ctx

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_itp_item().itp.project):
            messages.error(self.request, "You do not have permission to record inspections for this project.")
            return redirect(
                reverse_lazy(
                    "quality:itp-detail",
                    kwargs={
                        "project_pk": self.get_itp_item().itp.project_id,
                        "pk": self.get_itp_item().itp_id,
                    },
                )
            )
        form.instance.itp_item = self.get_itp_item()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Inspection record saved.")
        return super().form_valid(form)

    def get_success_url(self):
        itp = self.get_itp_item().itp
        return reverse_lazy(
            "quality:itp-detail",
            kwargs={"project_pk": itp.project_id, "pk": itp.pk},
        )


class InspectionChecklistCreateView(ProjectMixin, CreateView):
    model = InspectionChecklist
    form_class = InspectionChecklistForm
    template_name = "quality/checklist_form.html"

    def get_itp(self):
        if not hasattr(self, "_itp"):
            self._itp = get_object_or_404(ITP, pk=self.kwargs["itp_pk"], project=self.get_project())
        return self._itp

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["itp"] = self.get_itp()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["itp"] = self.get_itp()
        return ctx

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create inspection checklists for this project.")
            return redirect(self.get_success_url())
        form.instance.itp = self.get_itp()
        form.instance.inspected_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Inspection checklist created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("quality:itp-detail", kwargs={"project_pk": self.get_project().pk, "pk": self.get_itp().pk})


class InspectionChecklistItemCreateView(ProjectMixin, CreateView):
    model = InspectionChecklistItem
    form_class = InspectionChecklistItemForm
    template_name = "quality/checklist_item_form.html"

    def get_checklist(self):
        if not hasattr(self, "_checklist"):
            self._checklist = get_object_or_404(
                InspectionChecklist,
                pk=self.kwargs["checklist_pk"],
                itp__project=self.get_project(),
            )
        return self._checklist

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["checklist"] = self.get_checklist()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["checklist"] = self.get_checklist()
        ctx["itp"] = self.get_checklist().itp
        return ctx

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to add checklist items for this project.")
            return redirect(self.get_success_url())
        form.instance.checklist = self.get_checklist()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Checklist item added.")
        return super().form_valid(form)

    def get_success_url(self):
        checklist = self.get_checklist()
        return reverse_lazy("quality:itp-detail", kwargs={"project_pk": self.get_project().pk, "pk": checklist.itp_id})


# ---------------------------------------------------------------------------
# NCR views
# ---------------------------------------------------------------------------


class NCRListView(ProjectMixin, ListView):
    model = NCR
    template_name = "quality/ncr_list.html"
    context_object_name = "ncrs"
    paginate_by = 25

    def get_queryset(self):
        qs = NCR.objects.filter(project=self.get_project()).select_related(
            "raised_by", "responsible_person"
        )
        status = self.request.GET.get("status")
        severity = self.request.GET.get("severity")
        if status:
            qs = qs.filter(status=status)
        if severity:
            qs = qs.filter(severity=severity)
        return qs.order_by("-raised_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = NCR.STATUS_CHOICES
        ctx["severity_choices"] = NCR.SEVERITY_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["selected_severity"] = self.request.GET.get("severity", "")
        return ctx


class NCRCreateView(ProjectMixin, CreateView):
    model = NCR
    form_class = NCRForm
    template_name = "quality/ncr_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to raise NCRs for this project.")
            return redirect(reverse_lazy("quality:ncr-list", kwargs={"project_pk": self.get_project().pk}))
        form.instance.project = self.get_project()
        form.instance.raised_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "NCR raised successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("quality:ncr-list", kwargs={"project_pk": self.get_project().pk})


class NCRUpdateView(ProjectMixin, UpdateView):
    model = NCR
    form_class = NCRForm
    template_name = "quality/ncr_form.html"

    def get_queryset(self):
        return NCR.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update NCRs for this project.")
            return redirect(
                reverse_lazy("quality:ncr-detail", kwargs={"project_pk": self.get_project().pk, "pk": self.object.pk})
            )
        old_status = self.object.status
        new_status = form.instance.status
        if old_status != new_status:
            try:
                assert_transition("ncr", old_status, new_status)
            except ValidationError as exc:
                form.add_error("status", exc.messages[0])
                return self.form_invalid(form)
        form.instance.updated_by = self.request.user
        messages.success(self.request, "NCR updated successfully.")
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"NCR status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        return response

    def get_success_url(self):
        return reverse_lazy(
            "quality:ncr-detail",
            kwargs={"project_pk": self.get_project().pk, "pk": self.object.pk},
        )


class NCRStartReviewView(ProjectMixin, View):
    """POST-only: move an open NCR to Under Review."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        ncr = get_object_or_404(NCR, pk=kwargs["pk"], project=self.get_project())
        if not can_manage_quality(request.user, ncr.project):
            messages.error(request, "You do not have permission to update this NCR.")
            return redirect(ncr.get_absolute_url())
        old_status = ncr.status
        try:
            assert_transition("ncr", old_status, NCR.STATUS_UNDER_REVIEW)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect(ncr.get_absolute_url())
        ncr.status = NCR.STATUS_UNDER_REVIEW
        ncr.updated_by = request.user
        ncr.save(update_fields=["status", "updated_by", "updated_at"])
        AuditLog.log(
            request.user,
            AuditLog.ACTION_UPDATE,
            ncr,
            changes=f"NCR status changed from {old_status} to {NCR.STATUS_UNDER_REVIEW}.",
            request=request,
        )
        messages.success(request, f"{ncr.ncr_number} is now under review.")
        return redirect(ncr.get_absolute_url())


class NCRCloseView(ProjectMixin, View):
    """POST-only: close an NCR once root cause and corrective action are recorded."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        ncr = get_object_or_404(NCR, pk=kwargs["pk"], project=self.get_project())
        if not can_manage_quality(request.user, ncr.project):
            messages.error(request, "You do not have permission to close this NCR.")
            return redirect(ncr.get_absolute_url())
        old_status = ncr.status
        try:
            assert_transition("ncr", old_status, NCR.STATUS_CLOSED)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect(ncr.get_absolute_url())
        missing = []
        if not ncr.root_cause.strip():
            missing.append("root cause")
        if not ncr.corrective_action.strip():
            missing.append("corrective action taken")
        if missing:
            messages.error(
                request,
                f"Please record the {' and '.join(missing)} (edit the NCR) before closing it.",
            )
            return redirect(ncr.get_absolute_url())
        ncr.status = NCR.STATUS_CLOSED
        if not ncr.close_out_date:
            ncr.close_out_date = timezone.now().date()
        ncr.updated_by = request.user
        ncr.save(update_fields=["status", "close_out_date", "updated_by", "updated_at"])
        AuditLog.log(
            request.user,
            AuditLog.ACTION_UPDATE,
            ncr,
            changes=f"NCR status changed from {old_status} to {NCR.STATUS_CLOSED}.",
            request=request,
        )
        messages.success(request, f"{ncr.ncr_number} closed.")
        return redirect(ncr.get_absolute_url())


class NCRDetailView(ProjectMixin, DetailView):
    model = NCR
    template_name = "quality/ncr_detail.html"
    context_object_name = "ncr"

    def get_queryset(self):
        return NCR.objects.filter(project=self.get_project()).select_related(
            "raised_by", "responsible_person", "itp_item__itp"
        )


# ---------------------------------------------------------------------------
# Material Test Result views
# ---------------------------------------------------------------------------


class MaterialTestListView(ProjectMixin, ListView):
    model = MaterialTestResult
    template_name = "quality/materialtest_list.html"
    context_object_name = "tests"
    paginate_by = 25

    def get_queryset(self):
        qs = MaterialTestResult.objects.filter(project=self.get_project())
        test_type = self.request.GET.get("test_type")
        passed = self.request.GET.get("passed")
        if test_type:
            qs = qs.filter(test_type=test_type)
        if passed in ("true", "false"):
            qs = qs.filter(passed=(passed == "true"))
        return qs.order_by("-test_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["test_type_choices"] = MaterialTestResult.TEST_TYPE_CHOICES
        ctx["selected_test_type"] = self.request.GET.get("test_type", "")
        ctx["selected_passed"] = self.request.GET.get("passed", "")
        return ctx


class MaterialTestCreateView(ProjectMixin, CreateView):
    model = MaterialTestResult
    form_class = MaterialTestResultForm
    template_name = "quality/materialtest_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to record material tests for this project.")
            return redirect(reverse_lazy("quality:materialtest-list", kwargs={"project_pk": self.get_project().pk}))
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Material test result recorded.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "quality:materialtest-list", kwargs={"project_pk": self.get_project().pk}
        )


# ---------------------------------------------------------------------------
# Defect views
# ---------------------------------------------------------------------------


class DefectListView(ProjectMixin, ListView):
    model = Defect
    template_name = "quality/defect_list.html"
    context_object_name = "defects"
    paginate_by = 25

    def get_queryset(self):
        qs = Defect.objects.filter(project=self.get_project())
        status = self.request.GET.get("status")
        severity = self.request.GET.get("severity")
        phase = self.request.GET.get("phase")
        if status:
            qs = qs.filter(status=status)
        if severity:
            qs = qs.filter(severity=severity)
        if phase:
            qs = qs.filter(phase=phase)
        return qs.order_by("-identified_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Defect.STATUS_CHOICES
        ctx["severity_choices"] = Defect.SEVERITY_CHOICES
        ctx["phase_choices"] = Defect.PHASE_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["selected_severity"] = self.request.GET.get("severity", "")
        ctx["selected_phase"] = self.request.GET.get("phase", "")
        return ctx


class DefectCreateView(ProjectMixin, CreateView):
    model = Defect
    form_class = DefectForm
    template_name = "quality/defect_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to log defects for this project.")
            return redirect(reverse_lazy("quality:defect-list", kwargs={"project_pk": self.get_project().pk}))
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Defect logged successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("quality:defect-list", kwargs={"project_pk": self.get_project().pk})


class DefectUpdateView(ProjectMixin, UpdateView):
    model = Defect
    form_class = DefectForm
    template_name = "quality/defect_form.html"

    def get_queryset(self):
        return Defect.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_quality(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update defects for this project.")
            return redirect(reverse_lazy("quality:defect-list", kwargs={"project_pk": self.get_project().pk}))
        old_status = self.object.status
        new_status = form.instance.status
        if old_status != new_status:
            try:
                assert_transition("defect", old_status, new_status)
            except ValidationError as exc:
                form.add_error("status", exc.messages[0])
                return self.form_invalid(form)
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Defect updated successfully.")
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"Defect status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        return response

    def get_success_url(self):
        return reverse_lazy("quality:defect-list", kwargs={"project_pk": self.get_project().pk})
