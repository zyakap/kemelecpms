from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.projects.models import Project

from .forms import (
    DefectForm,
    InspectionRecordForm,
    ITPForm,
    ITPItemForm,
    MaterialTestResultForm,
    NCRForm,
)
from .models import Defect, ITP, InspectionRecord, ITPItem, MaterialTestResult, NCR


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class ProjectMixin(LoginRequiredMixin):
    """Resolves the current project from the ``project_pk`` URL kwarg."""

    def get_project(self):
        if not hasattr(self, "_project"):
            self._project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
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
            self._itp_item = get_object_or_404(ITPItem, pk=self.kwargs["itp_item_pk"])
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
        form.instance.updated_by = self.request.user
        messages.success(self.request, "NCR updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "quality:ncr-detail",
            kwargs={"project_pk": self.get_project().pk, "pk": self.object.pk},
        )


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
        return kwargs

    def form_valid(self, form):
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
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Defect updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("quality:defect-list", kwargs={"project_pk": self.get_project().pk})
