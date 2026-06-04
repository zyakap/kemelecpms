from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import (
    ClientForm,
    ContractForm,
    DelayEventForm,
    FunderForm,
    MilestoneForm,
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
            super()
            .get_queryset()
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
            super()
            .get_queryset()
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
        ).aggregate(total=Sum("amount"))["total"] or 0
        ctx["approved_variation_total"] = approved_variations

        # Delay events
        ctx["delay_events"] = project.delay_events.all().order_by("-date")
        ctx["total_delay_days"] = (
            project.delay_events.aggregate(total=Sum("impact_days"))["total"] or 0
        )

        # Computed contract value
        ctx["current_contract_value"] = project.contract_value

        return ctx


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
        self.project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
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
        ctx["variation_total"] = (
            self.get_queryset()
            .filter(status=Variation.STATUS_APPROVED)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )
        return ctx


class VariationCreateView(LoginRequiredMixin, CreateView):
    model = Variation
    form_class = VariationForm
    template_name = "projects/variation_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"New Variation – {self.project.project_id}"
        return ctx

    def form_valid(self, form):
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
        self.project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Variation.objects.filter(project=self.project)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["form_title"] = f"Edit Variation {self.object.ref_number}"
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.updated_by = self.request.user
        obj.save()
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
