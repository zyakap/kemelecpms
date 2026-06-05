import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.core.models import AuditLog
from apps.core.permissions import accessible_projects, can_manage_project

from .forms import (
    ClientForm,
    ContractForm,
    DelayEventForm,
    FunderForm,
    MilestoneForm,
    ProjectMembershipForm,
    ProjectForm,
    VariationForm,
)
from .models import (
    Client,
    Contract,
    DelayEvent,
    Funder,
    Milestone,
    Project,
    ProjectMembership,
    Variation,
)


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class StaffOrAdminMixin(UserPassesTestMixin):
    """Allow only staff members or system administrators."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_staff or getattr(user, "is_admin", False))


class SetAuditUserMixin:
    """Automatically populate created_by / updated_by from the logged-in user."""

    def form_valid(self, form):
        obj = form.save(commit=False)
        if not obj.pk:
            obj.created_by = self.request.user
        obj.updated_by = self.request.user
        obj.save()
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Client Views
# ---------------------------------------------------------------------------


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "projects/client_list.html"
    context_object_name = "clients"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(contact_person__icontains=q)
                | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class ClientCreateView(LoginRequiredMixin, SetAuditUserMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "projects/client_form.html"
    success_url = reverse_lazy("projects:client_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Add Client"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Client "{self.object.name}" created successfully.')
        return response


# ---------------------------------------------------------------------------
# Funder Views
# ---------------------------------------------------------------------------


class FunderListView(LoginRequiredMixin, ListView):
    model = Funder
    template_name = "projects/funder_list.html"
    context_object_name = "funders"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(contact_person__icontains=q)
                | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class FunderCreateView(LoginRequiredMixin, SetAuditUserMixin, CreateView):
    model = Funder
    form_class = FunderForm
    template_name = "projects/funder_form.html"
    success_url = reverse_lazy("projects:funder_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Add Funder"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Funder "{self.object.name}" created successfully.')
        return response


class FunderUpdateView(LoginRequiredMixin, SetAuditUserMixin, UpdateView):
    model = Funder
    form_class = FunderForm
    template_name = "projects/funder_form.html"
    success_url = reverse_lazy("projects:funder_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Funder "{self.object.name}" updated successfully.')
        return response


# ---------------------------------------------------------------------------
# Project Views
# ---------------------------------------------------------------------------


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            accessible_projects(self.request.user)
            .select_related("client", "project_manager", "site_supervisor")
        )
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        project_type = self.request.GET.get("type", "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(project_id__icontains=q)
                | Q(province__icontains=q)
                | Q(client__name__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if project_type:
            qs = qs.filter(project_type=project_type)
        return qs.distinct()

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            return self.export_csv()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_md or request.user.is_admin):
            messages.error(request, "You do not have permission to bulk update projects.")
            return redirect("projects:project_list")
        project_ids = request.POST.getlist("selected_projects")
        status = request.POST.get("bulk_status", "").strip()
        valid_statuses = {value for value, _ in Project.STATUS_CHOICES}
        if not project_ids or status not in valid_statuses:
            messages.warning(request, "Select projects and a valid status before applying a bulk action.")
            return redirect(f"{reverse('projects:project_list')}?{request.GET.urlencode()}")
        updated = accessible_projects(request.user).filter(pk__in=project_ids).update(status=status)
        messages.success(request, f"{updated} project(s) updated.")
        return redirect("projects:project_list")

    def export_csv(self):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="projects_export.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "Project ID",
                "Name",
                "Client",
                "Type",
                "Status",
                "Province",
                "District",
                "Project Manager",
                "Site Supervisor",
                "Start Date",
                "Target Completion",
                "Contract Value PGK",
            ]
        )
        for project in self.get_queryset():
            writer.writerow(
                [
                    project.project_id,
                    project.name,
                    project.client.name if project.client_id else "",
                    project.get_project_type_display(),
                    project.get_status_display(),
                    project.province,
                    project.district,
                    project.project_manager.get_full_name() if project.project_manager_id else "",
                    project.site_supervisor.get_full_name() if project.site_supervisor_id else "",
                    project.start_date or "",
                    project.target_completion_date or "",
                    project.contract_value,
                ]
            )
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["selected_type"] = self.request.GET.get("type", "")
        ctx["status_choices"] = Project.STATUS_CHOICES
        ctx["project_type_choices"] = Project.PROJECT_TYPE_CHOICES
        return ctx


class ProjectCreateView(LoginRequiredMixin, SetAuditUserMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "New Project"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Project "{self.object.name}" ({self.object.project_id}) created successfully.',
        )
        return response

    def get_success_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.object.pk})


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return (
            accessible_projects(self.request.user)
            .select_related(
                "client",
                "funder",
                "project_manager",
                "site_supervisor",
                "contract",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object

        # Contract
        try:
            ctx["contract"] = project.contract
        except Contract.DoesNotExist:
            ctx["contract"] = None

        # Milestones
        ctx["milestones"] = (
            project.milestones.all().order_by("target_date")
        )
        ctx["milestones_achieved"] = project.milestones.filter(is_achieved=True).count()
        ctx["milestones_total"] = project.milestones.count()

        # Variations
        ctx["variations"] = project.variations.all().order_by("ref_number")
        approved_variations = project.variations.filter(
            status=Variation.STATUS_APPROVED
        )
        approved_variation_total = sum(
            variation.signed_amount for variation in approved_variations
        )
        ctx["approved_variation_total"] = approved_variation_total
        ctx["variations_total"] = approved_variation_total

        # Delay events
        ctx["delay_events"] = project.delay_events.all().order_by("-date")
        ctx["total_delay_days"] = (
            project.delay_events.aggregate(total=Sum("impact_days"))["total"] or 0
        )
        ctx["open_issues"] = project.delay_events.count()

        # Computed contract value
        ctx["current_contract_value"] = project.contract_value
        ctx["can_manage_project"] = can_manage_project(self.request.user, project)
        ctx["memberships"] = project.memberships.select_related("user").order_by("role", "user__first_name")
        has_contract = ctx["contract"] is not None
        has_boq = project.boq_items.exists()
        has_wbs = project.wbs_activities.exists()
        has_programme = hasattr(project, "programme")
        has_baseline_programme = bool(has_programme and project.programme.is_baseline)
        has_dsr = project.daily_site_reports.exists()
        ctx["setup_steps"] = [
            {
                "label": "Contract",
                "complete": has_contract,
                "url": reverse("projects:contract_update" if has_contract else "projects:contract_create", kwargs={"project_pk": project.pk}),
            },
            {
                "label": "BOQ",
                "complete": has_boq,
                "url": reverse("budget:boq-list", kwargs={"project_pk": project.pk}),
            },
            {
                "label": "WBS",
                "complete": has_wbs,
                "url": reverse("schedule:wbs", kwargs={"project_pk": project.pk}),
            },
            {
                "label": "Baseline Programme",
                "complete": has_baseline_programme,
                "url": reverse("schedule:programme", kwargs={"project_pk": project.pk}),
            },
            {
                "label": "First DSR",
                "complete": has_dsr,
                "url": reverse("dsr:dsr_add"),
            },
        ]
        ctx["setup_complete_count"] = sum(1 for step in ctx["setup_steps"] if step["complete"])

        return ctx


class ProjectSetupView(LoginRequiredMixin, TemplateView):
    template_name = "projects/project_setup.html"

    def get_project(self):
        return get_object_or_404(accessible_projects(self.request.user), pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        has_contract = hasattr(project, "contract")
        boq_count = project.boq_items.count()
        wbs_count = project.wbs_activities.count()
        has_programme = hasattr(project, "programme")
        dsr_count = project.daily_site_reports.count()
        steps = [
            {
                "label": "Contract",
                "description": "Contract value, dates, retention, liquidated damages, and defects liability period.",
                "complete": has_contract,
                "url": reverse(
                    "projects:contract_update" if has_contract else "projects:contract_create",
                    kwargs={"project_pk": project.pk},
                ),
                "action": "Review" if has_contract else "Add contract",
            },
            {
                "label": "BOQ",
                "description": "Measured items and cost coding for claims and budget control.",
                "complete": boq_count > 0,
                "url": reverse("budget:boq-list", kwargs={"project_pk": project.pk}),
                "action": f"{boq_count} item(s)" if boq_count else "Build BOQ",
            },
            {
                "label": "WBS",
                "description": "Work breakdown for schedule, DSR, quality, and IPC evidence.",
                "complete": wbs_count > 0,
                "url": reverse("schedule:wbs", kwargs={"project_pk": project.pk}),
                "action": f"{wbs_count} node(s)" if wbs_count else "Create WBS",
            },
            {
                "label": "Baseline Programme",
                "description": "Approved baseline and current programme dates.",
                "complete": bool(has_programme and project.programme.is_baseline),
                "url": reverse("schedule:programme", kwargs={"project_pk": project.pk}),
                "action": "Open programme" if has_programme else "Create programme",
            },
            {
                "label": "Daily Site Reporting",
                "description": "First DSR confirms site mobilisation and field reporting is live.",
                "complete": dsr_count > 0,
                "url": reverse("dsr:dsr_add"),
                "action": f"{dsr_count} DSR(s)" if dsr_count else "Create first DSR",
            },
        ]
        complete_count = sum(1 for step in steps if step["complete"])
        ctx.update(
            {
                "project": project,
                "steps": steps,
                "complete_count": complete_count,
                "completion_percent": round(complete_count / len(steps) * 100),
                "breadcrumbs": [
                    {"label": "Projects", "url": reverse("projects:project_list")},
                    {"label": project.project_id, "url": project.get_absolute_url()},
                    {"label": "Setup"},
                ],
            }
        )
        return ctx


class ProjectMembershipCreateView(LoginRequiredMixin, CreateView):
    model = ProjectMembership
    form_class = ProjectMembershipForm
    template_name = "projects/membership_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(accessible_projects(request.user), pk=self.kwargs["project_pk"])
        if not can_manage_project(request.user, self.project):
            messages.error(request, "You do not have permission to manage project members.")
            return redirect(self.project.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"Add Member - {self.project.project_id}"
        return ctx

    def form_valid(self, form):
        form.instance.project = self.project
        form.instance.created_by = self.request.user
        messages.success(self.request, "Project member added.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.project.get_absolute_url()


class ProjectMembershipUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectMembership
    form_class = ProjectMembershipForm
    template_name = "projects/membership_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(accessible_projects(request.user), pk=self.kwargs["project_pk"])
        if not can_manage_project(request.user, self.project):
            messages.error(request, "You do not have permission to manage project members.")
            return redirect(self.project.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return ProjectMembership.objects.filter(project=self.project)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = "Edit Project Member"
        return ctx

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Project member updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.project.get_absolute_url()


class ProjectUpdateView(LoginRequiredMixin, SetAuditUserMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = f"Edit Project: {self.object.project_id}"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Project updated successfully.")
        return response

    def get_success_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.object.pk})


# ---------------------------------------------------------------------------
# Contract Views
# ---------------------------------------------------------------------------


class ContractCreateView(LoginRequiredMixin, SetAuditUserMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = "projects/contract_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"Add Contract – {self.project.project_id}"
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.project = self.project
        obj.created_by = self.request.user
        obj.updated_by = self.request.user
        obj.save()
        messages.success(
            self.request,
            f"Contract created for project {self.project.project_id}.",
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.project.pk})


class ContractUpdateView(LoginRequiredMixin, SetAuditUserMixin, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = "projects/contract_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(Contract, project=self.project)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"Edit Contract – {self.project.project_id}"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Contract updated successfully.")
        return response

    def get_success_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.project.pk})


# ---------------------------------------------------------------------------
# Variation Views
# ---------------------------------------------------------------------------


class VariationListView(LoginRequiredMixin, ListView):
    model = Variation
    template_name = "projects/variation_list.html"
    context_object_name = "variations"
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            accessible_projects(request.user),
            pk=self.kwargs["project_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Variation.objects.filter(project=self.project)
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("ref_number")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["status_choices"] = Variation.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["variation_total"] = sum(
            variation.signed_amount
            for variation in self.get_queryset().filter(status=Variation.STATUS_APPROVED)
        )
        return ctx


class VariationCreateView(LoginRequiredMixin, CreateView):
    model = Variation
    form_class = VariationForm
    template_name = "projects/variation_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            accessible_projects(request.user),
            pk=self.kwargs["project_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"New Variation – {self.project.project_id}"
        return ctx

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.project):
            messages.error(self.request, "You do not have permission to create variations for this project.")
            return redirect(self.get_success_url())
        obj = form.save(commit=False)
        obj.project = self.project
        obj.created_by = self.request.user
        obj.updated_by = self.request.user
        obj.save()
        messages.success(
            self.request,
            f"Variation {obj.ref_number} created for project {self.project.project_id}.",
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "projects:variation_list", kwargs={"project_pk": self.project.pk}
        )


class VariationUpdateView(LoginRequiredMixin, UpdateView):
    model = Variation
    form_class = VariationForm
    template_name = "projects/variation_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(
            accessible_projects(request.user),
            pk=self.kwargs["project_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Variation.objects.filter(project=self.project)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"Edit Variation {self.object.ref_number}"
        return ctx

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.project):
            messages.error(self.request, "You do not have permission to update variations for this project.")
            return redirect(self.get_success_url())
        old_status = self.object.status
        obj = form.save(commit=False)
        obj.updated_by = self.request.user
        obj.save()
        if old_status != obj.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                obj,
                changes=f"Variation status changed from {old_status} to {obj.status}.",
                request=self.request,
            )
        messages.success(self.request, f"Variation {obj.ref_number} updated successfully.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "projects:variation_list", kwargs={"project_pk": self.project.pk}
        )


# ---------------------------------------------------------------------------
# Milestone Views
# ---------------------------------------------------------------------------


class MilestoneListView(LoginRequiredMixin, ListView):
    model = Milestone
    template_name = "projects/milestone_list.html"
    context_object_name = "milestones"
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Milestone.objects.filter(project=self.project)
        milestone_type = self.request.GET.get("type", "").strip()
        achieved = self.request.GET.get("achieved", "").strip()
        if milestone_type:
            qs = qs.filter(milestone_type=milestone_type)
        if achieved == "yes":
            qs = qs.filter(is_achieved=True)
        elif achieved == "no":
            qs = qs.filter(is_achieved=False)
        return qs.order_by("target_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["milestone_type_choices"] = Milestone.MILESTONE_TYPE_CHOICES
        ctx["selected_type"] = self.request.GET.get("type", "")
        ctx["selected_achieved"] = self.request.GET.get("achieved", "")
        return ctx


class MilestoneCreateView(LoginRequiredMixin, CreateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = "projects/milestone_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"Add Milestone – {self.project.project_id}"
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.project = self.project
        obj.created_by = self.request.user
        obj.updated_by = self.request.user
        obj.save()
        messages.success(
            self.request,
            f'Milestone "{obj.name}" created for project {self.project.project_id}.',
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "projects:milestone_list", kwargs={"project_pk": self.project.pk}
        )


class MilestoneUpdateView(LoginRequiredMixin, UpdateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = "projects/milestone_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Milestone.objects.filter(project=self.project)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"Edit Milestone – {self.object.name}"
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.updated_by = self.request.user
        obj.save()
        messages.success(self.request, f'Milestone "{obj.name}" updated successfully.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "projects:milestone_list", kwargs={"project_pk": self.project.pk}
        )


# ---------------------------------------------------------------------------
# Project Closeout / Practical Completion
# ---------------------------------------------------------------------------


class ProjectCloseoutView(LoginRequiredMixin, View):
    """
    Change project status to Practical Completion and optionally archive
    to the Tender Library.
    """

    def post(self, request, pk):
        from .models import Project
        project = get_object_or_404(Project, pk=pk)

        action = request.POST.get("action", "practical_completion")

        if action == "practical_completion" and project.status not in (
            Project.STATUS_PRACTICAL_COMPLETION,
            Project.STATUS_DEFECTS_LIABILITY,
            Project.STATUS_CLOSED,
        ):
            project.status = Project.STATUS_PRACTICAL_COMPLETION
            project.actual_completion_date = request.POST.get("completion_date") or None
            project.updated_by = request.user
            project.save(update_fields=["status", "actual_completion_date", "updated_by"])
            messages.success(
                request,
                f"Project {project.project_id} marked as Practical Completion."
            )

        elif action == "close":
            project.status = Project.STATUS_CLOSED
            project.updated_by = request.user
            project.save(update_fields=["status", "updated_by"])
            messages.success(request, f"Project {project.project_id} closed.")

        elif action == "archive_to_library":
            # Redirect to tender archive creation form pre-populated with this project
            return redirect(f"/tender/library/new/?project={project.pk}")

        return redirect(project.get_absolute_url())
