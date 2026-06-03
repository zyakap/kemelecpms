from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.projects.models import Project

from .forms import (
    AttendanceBulkForm,
    AttendanceRecordForm,
    CrewForm,
    CrewMemberForm,
    EquipmentAllocationForm,
    EquipmentForm,
    EquipmentUtilisationForm,
    SubcontractorCompanyForm,
    WorkerForm,
)
from .models import (
    AttendanceRecord,
    Crew,
    CrewMember,
    Equipment,
    EquipmentAllocation,
    EquipmentUtilisation,
    SubcontractorCompany,
    Worker,
)


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
# Worker views
# ---------------------------------------------------------------------------


class WorkerListView(LoginRequiredMixin, ListView):
    model = Worker
    template_name = "resources/worker_list.html"
    context_object_name = "workers"
    paginate_by = 40

    def get_queryset(self):
        qs = Worker.objects.select_related("project").order_by("last_name", "first_name")
        # Optional filters via query params
        project_pk = self.request.GET.get("project")
        classification = self.request.GET.get("classification")
        employment_type = self.request.GET.get("employment_type")
        is_active = self.request.GET.get("is_active")
        search = self.request.GET.get("q")

        if project_pk:
            qs = qs.filter(project_id=project_pk)
        if classification:
            qs = qs.filter(classification=classification)
        if employment_type:
            qs = qs.filter(employment_type=employment_type)
        if is_active in ("true", "1"):
            qs = qs.filter(is_active=True)
        elif is_active in ("false", "0"):
            qs = qs.filter(is_active=False)
        if search:
            qs = qs.filter(
                first_name__icontains=search
            ) | qs.filter(
                last_name__icontains=search
            ) | qs.filter(
                worker_id__icontains=search
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["classification_choices"] = Worker.CLASSIFICATION_CHOICES
        ctx["employment_choices"] = Worker.EMPLOYMENT_CHOICES
        ctx["projects"] = Project.objects.all()
        return ctx


class WorkerDetailView(LoginRequiredMixin, DetailView):
    model = Worker
    template_name = "resources/worker_detail.html"
    context_object_name = "worker"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        worker = self.get_object()
        ctx["crew_memberships"] = worker.crew_memberships.select_related("crew__project").order_by(
            "-date_joined"
        )
        ctx["recent_attendance"] = worker.attendance_records.order_by("-date")[:30]
        return ctx


class WorkerCreateView(LoginRequiredMixin, CreateView):
    model = Worker
    form_class = WorkerForm
    template_name = "resources/worker_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Worker registered successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:worker-list")


class WorkerUpdateView(LoginRequiredMixin, UpdateView):
    model = Worker
    form_class = WorkerForm
    template_name = "resources/worker_form.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Worker details updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:worker-detail", kwargs={"pk": self.object.pk})


# ---------------------------------------------------------------------------
# Attendance views
# ---------------------------------------------------------------------------


class AttendanceView(ProjectMixin, ListView):
    """
    Lists attendance records for a project, filtered by date.
    Defaults to today if no date param provided.
    """

    model = AttendanceRecord
    template_name = "resources/attendance_list.html"
    context_object_name = "records"

    def get_date(self):
        date_str = self.request.GET.get("date")
        if date_str:
            from datetime import date
            try:
                year, month, day = date_str.split("-")
                return date(int(year), int(month), int(day))
            except (ValueError, AttributeError):
                pass
        return timezone.localdate()

    def get_queryset(self):
        return AttendanceRecord.objects.filter(
            project=self.get_project(),
            date=self.get_date(),
        ).select_related("worker", "crew", "recorded_by").order_by(
            "worker__last_name", "worker__first_name"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["selected_date"] = self.get_date()
        present_count = self.get_queryset().filter(is_present=True).count()
        absent_count = self.get_queryset().filter(is_present=False).count()
        ctx["present_count"] = present_count
        ctx["absent_count"] = absent_count
        return ctx


class AttendanceBulkCreateView(ProjectMixin, FormView):
    """
    Enter attendance (present/absent + overtime) for all active project workers on a given date.
    On POST, creates or updates AttendanceRecord for each worker.
    """

    template_name = "resources/attendance_bulk.html"
    form_class = AttendanceBulkForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        ctx["workers"] = Worker.objects.filter(project=project, is_active=True).order_by(
            "last_name", "first_name"
        )
        return ctx

    def form_valid(self, form):
        project = self.get_project()
        date = form.cleaned_data["date"]
        workers = Worker.objects.filter(project=project, is_active=True)

        created = 0
        updated = 0
        for worker in workers:
            is_present = form.cleaned_data.get(f"present_{worker.pk}", False)
            overtime = form.cleaned_data.get(f"overtime_{worker.pk}") or 0

            record, was_created = AttendanceRecord.objects.update_or_create(
                project=project,
                worker=worker,
                date=date,
                defaults={
                    "is_present": is_present,
                    "overtime_hours": overtime,
                    "recorded_by": self.request.user,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        messages.success(
            self.request,
            f"Attendance saved: {created} new, {updated} updated for {date}.",
        )
        return redirect(
            reverse_lazy("resources:attendance", kwargs={"project_pk": project.pk})
            + f"?date={date}"
        )


class AttendanceCreateView(ProjectMixin, CreateView):
    model = AttendanceRecord
    form_class = AttendanceRecordForm
    template_name = "resources/attendance_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.recorded_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Attendance record saved.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:attendance", kwargs={"project_pk": self.get_project().pk})


# ---------------------------------------------------------------------------
# Equipment views
# ---------------------------------------------------------------------------


class EquipmentListView(LoginRequiredMixin, ListView):
    model = Equipment
    template_name = "resources/equipment_list.html"
    context_object_name = "equipment_list"
    paginate_by = 30

    def get_queryset(self):
        qs = Equipment.objects.prefetch_related("allocations__project")
        ownership = self.request.GET.get("ownership")
        eq_type = self.request.GET.get("type")
        is_active = self.request.GET.get("is_active")
        search = self.request.GET.get("q")
        if ownership:
            qs = qs.filter(ownership_type=ownership)
        if eq_type:
            qs = qs.filter(equipment_type__icontains=eq_type)
        if is_active in ("true", "1"):
            qs = qs.filter(is_active=True)
        elif is_active in ("false", "0"):
            qs = qs.filter(is_active=False)
        if search:
            qs = qs.filter(description__icontains=search) | qs.filter(
                equipment_id__icontains=search
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ownership_choices"] = Equipment.OWNERSHIP_CHOICES
        return ctx


class EquipmentCreateView(LoginRequiredMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = "resources/equipment_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Equipment record created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:equipment-list")


class EquipmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = "resources/equipment_form.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Equipment record updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:equipment-list")


# ---------------------------------------------------------------------------
# Equipment Allocation views
# ---------------------------------------------------------------------------


class EquipmentAllocationCreateView(ProjectMixin, CreateView):
    model = EquipmentAllocation
    form_class = EquipmentAllocationForm
    template_name = "resources/equipment_allocation_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Equipment allocated to project successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:equipment-list")


# ---------------------------------------------------------------------------
# Equipment Utilisation views
# ---------------------------------------------------------------------------


class EquipmentUtilisationCreateView(LoginRequiredMixin, CreateView):
    model = EquipmentUtilisation
    form_class = EquipmentUtilisationForm
    template_name = "resources/equipment_utilisation_form.html"

    def get_allocation(self):
        if not hasattr(self, "_allocation"):
            self._allocation = get_object_or_404(
                EquipmentAllocation, pk=self.kwargs["allocation_pk"]
            )
        return self._allocation

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["allocation"] = self.get_allocation()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["allocation"] = self.get_allocation()
        return ctx

    def form_valid(self, form):
        form.instance.allocation = self.get_allocation()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Utilisation record saved.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:equipment-list")


# ---------------------------------------------------------------------------
# Crew views
# ---------------------------------------------------------------------------


class CrewListView(ProjectMixin, ListView):
    model = Crew
    template_name = "resources/crew_list.html"
    context_object_name = "crews"

    def get_queryset(self):
        return Crew.objects.filter(project=self.get_project()).select_related(
            "foreman"
        ).prefetch_related("crew_members__worker")


class CrewCreateView(ProjectMixin, CreateView):
    model = Crew
    form_class = CrewForm
    template_name = "resources/crew_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Crew created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:crew-list", kwargs={"project_pk": self.get_project().pk})


class CrewDetailView(ProjectMixin, DetailView):
    model = Crew
    template_name = "resources/crew_detail.html"
    context_object_name = "crew"

    def get_queryset(self):
        return Crew.objects.filter(project=self.get_project()).prefetch_related(
            "crew_members__worker"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["member_form"] = CrewMemberForm(crew=self.get_object())
        return ctx

    def post(self, request, *args, **kwargs):
        crew = self.get_object()
        form = CrewMemberForm(request.POST, crew=crew)
        if form.is_valid():
            member = form.save(commit=False)
            member.crew = crew
            member.created_by = request.user
            member.save()
            messages.success(request, "Worker added to crew.")
        else:
            messages.error(request, "Could not add worker. Please check the form.")
        return redirect(
            "resources:crew-detail",
            project_pk=self.get_project().pk,
            pk=crew.pk,
        )


class CrewUpdateView(ProjectMixin, UpdateView):
    model = Crew
    form_class = CrewForm
    template_name = "resources/crew_form.html"

    def get_queryset(self):
        return Crew.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Crew updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "resources:crew-detail",
            kwargs={"project_pk": self.get_project().pk, "pk": self.object.pk},
        )


# ---------------------------------------------------------------------------
# Subcontractor Company views
# ---------------------------------------------------------------------------


class SubcontractorListView(LoginRequiredMixin, ListView):
    model = SubcontractorCompany
    template_name = "resources/subcontractor_list.html"
    context_object_name = "subcontractors"
    paginate_by = 30

    def get_queryset(self):
        qs = SubcontractorCompany.objects.all()
        is_prequalified = self.request.GET.get("prequalified")
        is_blacklisted = self.request.GET.get("blacklisted")
        trade = self.request.GET.get("trade")
        search = self.request.GET.get("q")
        if is_prequalified in ("true", "1"):
            qs = qs.filter(is_prequalified=True)
        if is_blacklisted in ("true", "1"):
            qs = qs.filter(is_blacklisted=True)
        if trade:
            qs = qs.filter(trade__icontains=trade)
        if search:
            qs = qs.filter(company_name__icontains=search) | qs.filter(
                contact_person__icontains=search
            )
        return qs


class SubcontractorCreateView(LoginRequiredMixin, CreateView):
    model = SubcontractorCompany
    form_class = SubcontractorCompanyForm
    template_name = "resources/subcontractor_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Subcontractor company registered.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:subcontractor-list")


class SubcontractorUpdateView(LoginRequiredMixin, UpdateView):
    model = SubcontractorCompany
    form_class = SubcontractorCompanyForm
    template_name = "resources/subcontractor_form.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Subcontractor details updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("resources:subcontractor-list")
