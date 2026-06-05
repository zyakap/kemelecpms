"""
Safety views for kemelecpms.

All views require authentication.

Covers:
  - Incident list / create / update / detail
  - ToolboxTalk list / create
  - SafetyInduction list / create
  - HazardRisk list / create / update
  - SWMS list / create
  - PPEIssue list / create
  - SafetyDashboardView: LTIFR, incident counts, man-hours
"""

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.core.permissions import accessible_projects, can_manage_safety
from apps.core.models import AuditLog
from apps.projects.models import Project

from .forms import (
    HazardRiskForm,
    IncidentForm,
    PPEIssueForm,
    PermitToWorkForm,
    SafetyInductionForm,
    SafetyCorrectiveActionForm,
    SafetyObservationForm,
    SafetyTrainingRecordForm,
    SWMSForm,
    ToolboxTalkForm,
)
from .models import (
    HazardRisk,
    Incident,
    PPEIssue,
    PermitToWork,
    SafetyInduction,
    SafetyCorrectiveAction,
    SafetyObservation,
    SafetyTrainingRecord,
    SWMS,
    ToolboxTalk,
)


# ---------------------------------------------------------------------------
# Incident views
# ---------------------------------------------------------------------------


class AccessibleProjectFormMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if "project" in form.fields:
            form.fields["project"].queryset = accessible_projects(self.request.user)
        return form


class IncidentListView(LoginRequiredMixin, ListView):
    model = Incident
    template_name = "safety/incident_list.html"
    context_object_name = "incidents"
    paginate_by = 20

    def get_queryset(self):
        qs = Incident.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related(
            "project", "reported_by"
        ).order_by("-date", "-incident_number")

        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)

        incident_type = self.request.GET.get("type")
        if incident_type:
            qs = qs.filter(incident_type=incident_type)

        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        lti = self.request.GET.get("lti")
        if lti:
            qs = qs.filter(is_lti=True)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        ctx["type_choices"] = Incident.INCIDENT_TYPE_CHOICES
        ctx["status_choices"] = Incident.STATUS_CHOICES
        return ctx


class IncidentCreateView(AccessibleProjectFormMixin, LoginRequiredMixin, CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = "safety/incident_form.html"

    def form_valid(self, form):
        if not accessible_projects(self.request.user).filter(pk=form.instance.project_id).exists():
            messages.error(self.request, "You do not have access to report incidents for this project.")
            return redirect("safety:incident_list")
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, f"Incident {self.object.incident_number} created."
        )
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class IncidentUpdateView(LoginRequiredMixin, UpdateView):
    model = Incident
    form_class = IncidentForm
    template_name = "safety/incident_form.html"

    def get_queryset(self):
        return Incident.objects.filter(project__in=accessible_projects(self.request.user))

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to update this incident.")
            return redirect(form.instance.get_absolute_url())
        old_status = self.object.status
        form.instance.updated_by = self.request.user
        messages.success(
            self.request, f"Incident {self.object.incident_number} updated."
        )
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"Incident status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class IncidentDetailView(LoginRequiredMixin, DetailView):
    model = Incident
    template_name = "safety/incident_detail.html"
    context_object_name = "incident"

    def get_queryset(self):
        return Incident.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related(
            "project",
            "reported_by",
            "corrective_action_person",
        )


# ---------------------------------------------------------------------------
# Toolbox Talk views
# ---------------------------------------------------------------------------


class ToolboxTalkListView(LoginRequiredMixin, ListView):
    model = ToolboxTalk
    template_name = "safety/toolbox_list.html"
    context_object_name = "talks"
    paginate_by = 20

    def get_queryset(self):
        qs = ToolboxTalk.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related("project", "presenter").order_by(
            "-date"
        )
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        return ctx


class ToolboxTalkCreateView(AccessibleProjectFormMixin, LoginRequiredMixin, CreateView):
    model = ToolboxTalk
    form_class = ToolboxTalkForm
    template_name = "safety/toolbox_form.html"
    success_url = reverse_lazy("safety:toolbox_list")

    def form_valid(self, form):
        if not accessible_projects(self.request.user).filter(pk=form.instance.project_id).exists():
            messages.error(self.request, "You do not have access to record toolbox talks for this project.")
            return redirect("safety:toolbox_list")
        form.instance.created_by = self.request.user
        messages.success(self.request, "Toolbox talk recorded.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Safety Induction views
# ---------------------------------------------------------------------------


class SafetyInductionListView(LoginRequiredMixin, ListView):
    model = SafetyInduction
    template_name = "safety/induction_list.html"
    context_object_name = "inductions"
    paginate_by = 25

    def get_queryset(self):
        qs = SafetyInduction.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related(
            "project", "worker", "inducted_by"
        ).order_by("-date")
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        worker_pk = self.request.GET.get("worker")
        if worker_pk:
            qs = qs.filter(worker_id=worker_pk)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        return ctx


class SafetyInductionCreateView(AccessibleProjectFormMixin, LoginRequiredMixin, CreateView):
    model = SafetyInduction
    form_class = SafetyInductionForm
    template_name = "safety/induction_form.html"
    success_url = reverse_lazy("safety:induction_list")

    def form_valid(self, form):
        if not accessible_projects(self.request.user).filter(pk=form.instance.project_id).exists():
            messages.error(self.request, "You do not have access to create inductions for this project.")
            return redirect("safety:induction_list")
        form.instance.created_by = self.request.user
        messages.success(self.request, "Induction record created.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Hazard Risk Register views
# ---------------------------------------------------------------------------


class HazardRiskListView(LoginRequiredMixin, ListView):
    model = HazardRisk
    template_name = "safety/hazard_list.html"
    context_object_name = "hazards"
    paginate_by = 25

    def get_queryset(self):
        qs = HazardRisk.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related("project", "reviewed_by").order_by(
            "-likelihood", "-consequence"
        )
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        control = self.request.GET.get("control")
        if control:
            qs = qs.filter(control_type=control)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        ctx["control_types"] = HazardRisk.CONTROL_TYPE_CHOICES
        return ctx


class HazardRiskCreateView(AccessibleProjectFormMixin, LoginRequiredMixin, CreateView):
    model = HazardRisk
    form_class = HazardRiskForm
    template_name = "safety/hazard_form.html"
    success_url = reverse_lazy("safety:hazard_list")

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to create hazard/risk records for this project.")
            return redirect("safety:hazard_list")
        form.instance.created_by = self.request.user
        messages.success(self.request, "Hazard / risk entry created.")
        return super().form_valid(form)


class HazardRiskUpdateView(LoginRequiredMixin, UpdateView):
    model = HazardRisk
    form_class = HazardRiskForm
    template_name = "safety/hazard_form.html"
    success_url = reverse_lazy("safety:hazard_list")

    def get_queryset(self):
        return HazardRisk.objects.filter(project__in=accessible_projects(self.request.user))

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to update hazard/risk records for this project.")
            return redirect("safety:hazard_list")
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Hazard / risk entry updated.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# SWMS views
# ---------------------------------------------------------------------------


class SWMSListView(LoginRequiredMixin, ListView):
    model = SWMS
    template_name = "safety/swms_list.html"
    context_object_name = "swms_list"
    paginate_by = 20

    def get_queryset(self):
        qs = SWMS.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related("project", "approved_by").order_by(
            "project", "title", "-version"
        )
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        ctx["status_choices"] = SWMS.STATUS_CHOICES
        return ctx


class SWMSCreateView(AccessibleProjectFormMixin, LoginRequiredMixin, CreateView):
    model = SWMS
    form_class = SWMSForm
    template_name = "safety/swms_form.html"
    success_url = reverse_lazy("safety:swms_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to create SWMS documents for this project.")
            return redirect("safety:swms_list")
        form.instance.created_by = self.request.user
        messages.success(self.request, "SWMS document created.")
        return super().form_valid(form)


class SWMSUpdateView(LoginRequiredMixin, UpdateView):
    model = SWMS
    form_class = SWMSForm
    template_name = "safety/swms_form.html"
    success_url = reverse_lazy("safety:swms_list")

    def get_queryset(self):
        return SWMS.objects.filter(project__in=accessible_projects(self.request.user))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to update SWMS documents for this project.")
            return redirect("safety:swms_list")
        old_status = self.object.status
        form.instance.updated_by = self.request.user
        messages.success(self.request, "SWMS document updated.")
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"SWMS status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        return response


# ---------------------------------------------------------------------------
# PPE Issue views
# ---------------------------------------------------------------------------


class PPEIssueListView(LoginRequiredMixin, ListView):
    model = PPEIssue
    template_name = "safety/ppe_list.html"
    context_object_name = "ppe_issues"
    paginate_by = 25

    def get_queryset(self):
        qs = PPEIssue.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related(
            "project", "worker", "issued_by"
        ).order_by("-date_issued")
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        ppe_type = self.request.GET.get("type")
        if ppe_type:
            qs = qs.filter(ppe_type=ppe_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        ctx["ppe_types"] = PPEIssue.PPE_TYPE_CHOICES
        return ctx


class PPEIssueCreateView(AccessibleProjectFormMixin, LoginRequiredMixin, CreateView):
    model = PPEIssue
    form_class = PPEIssueForm
    template_name = "safety/ppe_form.html"
    success_url = reverse_lazy("safety:ppe_list")

    def form_valid(self, form):
        if not accessible_projects(self.request.user).filter(pk=form.instance.project_id).exists():
            messages.error(self.request, "You do not have access to issue PPE for this project.")
            return redirect("safety:ppe_list")
        form.instance.created_by = self.request.user
        messages.success(self.request, "PPE issue record saved.")
        return super().form_valid(form)


class PermitToWorkListView(LoginRequiredMixin, ListView):
    model = PermitToWork
    template_name = "safety/permit_list.html"
    context_object_name = "permits"
    paginate_by = 25

    def get_queryset(self):
        qs = PermitToWork.objects.filter(project__in=accessible_projects(self.request.user)).select_related(
            "project", "requested_by", "approved_by", "closed_by"
        )
        project_pk = self.request.GET.get("project")
        status = self.request.GET.get("status")
        permit_type = self.request.GET.get("type")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        if status:
            qs = qs.filter(status=status)
        if permit_type:
            qs = qs.filter(permit_type=permit_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        ctx["status_choices"] = PermitToWork.STATUS_CHOICES
        ctx["permit_types"] = PermitToWork.PERMIT_TYPE_CHOICES
        return ctx


class PermitToWorkCreateView(LoginRequiredMixin, CreateView):
    model = PermitToWork
    form_class = PermitToWorkForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("safety:permit_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to create permits for this project.")
            return redirect("safety:permit_list")
        form.instance.requested_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Permit to work created.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Permit to Work"
        ctx["cancel_url"] = reverse_lazy("safety:permit_list")
        return ctx


class PermitToWorkUpdateView(LoginRequiredMixin, UpdateView):
    model = PermitToWork
    form_class = PermitToWorkForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("safety:permit_list")

    def get_queryset(self):
        return PermitToWork.objects.filter(project__in=accessible_projects(self.request.user))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to update permits for this project.")
            return redirect("safety:permit_list")
        old_status = self.object.status
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"Permit status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        messages.success(self.request, "Permit to work updated.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Permit {self.object.permit_number}"
        ctx["cancel_url"] = reverse_lazy("safety:permit_list")
        return ctx


class SafetyTrainingRecordListView(LoginRequiredMixin, ListView):
    model = SafetyTrainingRecord
    template_name = "safety/training_list.html"
    context_object_name = "training_records"
    paginate_by = 25

    def get_queryset(self):
        qs = SafetyTrainingRecord.objects.filter(project__in=accessible_projects(self.request.user)).select_related(
            "project", "worker"
        )
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        if self.request.GET.get("expired"):
            qs = qs.filter(expiry_date__lt=date.today())
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        return ctx


class SafetyTrainingRecordCreateView(LoginRequiredMixin, CreateView):
    model = SafetyTrainingRecord
    form_class = SafetyTrainingRecordForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("safety:training_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to create training records for this project.")
            return redirect("safety:training_list")
        form.instance.created_by = self.request.user
        messages.success(self.request, "Safety training record saved.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Safety Training / Certification"
        ctx["cancel_url"] = reverse_lazy("safety:training_list")
        return ctx


class SafetyTrainingRecordUpdateView(LoginRequiredMixin, UpdateView):
    model = SafetyTrainingRecord
    form_class = SafetyTrainingRecordForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("safety:training_list")

    def get_queryset(self):
        return SafetyTrainingRecord.objects.filter(project__in=accessible_projects(self.request.user))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to update training records for this project.")
            return redirect("safety:training_list")
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Safety training record updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Safety Training / Certification"
        ctx["cancel_url"] = reverse_lazy("safety:training_list")
        return ctx


class SafetyObservationListView(LoginRequiredMixin, ListView):
    model = SafetyObservation
    template_name = "safety/observation_list.html"
    context_object_name = "observations"
    paginate_by = 25

    def get_queryset(self):
        qs = SafetyObservation.objects.filter(project__in=accessible_projects(self.request.user)).select_related(
            "project", "observed_by"
        )
        project_pk = self.request.GET.get("project")
        status = self.request.GET.get("status")
        observation_type = self.request.GET.get("type")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        if status:
            qs = qs.filter(status=status)
        if observation_type:
            qs = qs.filter(observation_type=observation_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        ctx["status_choices"] = SafetyObservation.STATUS_CHOICES
        ctx["type_choices"] = SafetyObservation.TYPE_CHOICES
        return ctx


class SafetyObservationCreateView(LoginRequiredMixin, CreateView):
    model = SafetyObservation
    form_class = SafetyObservationForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("safety:observation_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not accessible_projects(self.request.user).filter(pk=form.instance.project_id).exists():
            messages.error(self.request, "You do not have access to this project.")
            return redirect("safety:observation_list")
        form.instance.observed_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Safety observation recorded.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Safety Observation"
        ctx["cancel_url"] = reverse_lazy("safety:observation_list")
        return ctx


class SafetyObservationUpdateView(LoginRequiredMixin, UpdateView):
    model = SafetyObservation
    form_class = SafetyObservationForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("safety:observation_list")

    def get_queryset(self):
        return SafetyObservation.objects.filter(project__in=accessible_projects(self.request.user))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to update safety observations for this project.")
            return redirect("safety:observation_list")
        old_status = self.object.status
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"Safety observation status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        messages.success(self.request, "Safety observation updated.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Safety Observation"
        ctx["cancel_url"] = reverse_lazy("safety:observation_list")
        return ctx


class SafetyCorrectiveActionListView(LoginRequiredMixin, ListView):
    model = SafetyCorrectiveAction
    template_name = "safety/corrective_action_list.html"
    context_object_name = "actions"
    paginate_by = 25

    def get_queryset(self):
        qs = SafetyCorrectiveAction.objects.filter(project__in=accessible_projects(self.request.user)).select_related(
            "project", "assigned_to", "incident", "observation"
        )
        project_pk = self.request.GET.get("project")
        status = self.request.GET.get("status")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        if status:
            qs = qs.filter(status=status)
        if self.request.GET.get("overdue"):
            qs = qs.exclude(status=SafetyCorrectiveAction.STATUS_CLOSED).filter(due_date__lt=date.today())
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = accessible_projects(self.request.user)
        ctx["status_choices"] = SafetyCorrectiveAction.STATUS_CHOICES
        return ctx


class SafetyCorrectiveActionCreateView(LoginRequiredMixin, CreateView):
    model = SafetyCorrectiveAction
    form_class = SafetyCorrectiveActionForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("safety:corrective_action_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to create corrective actions for this project.")
            return redirect("safety:corrective_action_list")
        form.instance.created_by = self.request.user
        messages.success(self.request, "Safety corrective action saved.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Safety Corrective Action"
        ctx["cancel_url"] = reverse_lazy("safety:corrective_action_list")
        return ctx


class SafetyCorrectiveActionUpdateView(LoginRequiredMixin, UpdateView):
    model = SafetyCorrectiveAction
    form_class = SafetyCorrectiveActionForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("safety:corrective_action_list")

    def get_queryset(self):
        return SafetyCorrectiveAction.objects.filter(project__in=accessible_projects(self.request.user))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["projects"] = accessible_projects(self.request.user)
        return kwargs

    def form_valid(self, form):
        if not can_manage_safety(self.request.user, form.instance.project):
            messages.error(self.request, "You do not have permission to update corrective actions for this project.")
            return redirect("safety:corrective_action_list")
        old_status = self.object.status
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"Safety corrective action status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        messages.success(self.request, "Safety corrective action updated.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Safety Corrective Action"
        ctx["cancel_url"] = reverse_lazy("safety:corrective_action_list")
        return ctx


# ---------------------------------------------------------------------------
# Safety Dashboard
# ---------------------------------------------------------------------------


class SafetyDashboardView(LoginRequiredMixin, TemplateView):
    """
    Aggregate safety statistics across all active projects (or a selected one).

    Key metrics:
      - Incident counts by type
      - LTI count and total days lost
      - LTIFR = (LTIs × 1,000,000) / man-hours worked
      - Toolbox talk count
      - Induction count
      - Open corrective actions
    """

    template_name = "safety/safety_dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        project_pk = self.request.GET.get("project")
        projects = accessible_projects(self.request.user)
        ctx["projects"] = projects
        ctx["selected_project_pk"] = project_pk

        incident_qs = Incident.objects.filter(project__in=projects)
        toolbox_qs = ToolboxTalk.objects.filter(project__in=projects)
        induction_qs = SafetyInduction.objects.filter(project__in=projects)
        permit_qs = PermitToWork.objects.filter(project__in=projects)
        training_qs = SafetyTrainingRecord.objects.filter(project__in=projects)
        observation_qs = SafetyObservation.objects.filter(project__in=projects)
        action_qs = SafetyCorrectiveAction.objects.filter(project__in=projects)

        if project_pk:
            try:
                selected = projects.get(pk=project_pk)
                ctx["selected_project"] = selected
            except Project.DoesNotExist:
                selected = None
            if selected:
                incident_qs = incident_qs.filter(project=selected)
                toolbox_qs = toolbox_qs.filter(project=selected)
                induction_qs = induction_qs.filter(project=selected)
                permit_qs = permit_qs.filter(project=selected)
                training_qs = training_qs.filter(project=selected)
                observation_qs = observation_qs.filter(project=selected)
                action_qs = action_qs.filter(project=selected)

        # Incident stats
        incident_by_type = incident_qs.values("incident_type").annotate(count=Count("pk")).order_by("incident_type")

        lti_stats = incident_qs.filter(is_lti=True).aggregate(
            lti_count=Count("pk"),
            days_lost=Sum("days_lost"),
        )
        lti_count = lti_stats["lti_count"] or 0
        days_lost = lti_stats["days_lost"] or 0

        total_incidents = incident_qs.count()
        open_incidents = incident_qs.filter(
            status__in=[Incident.STATUS_OPEN, Incident.STATUS_INVESTIGATING]
        ).count()

        # Open corrective actions
        open_corrective_actions = incident_qs.filter(
            corrective_action_closed__isnull=True,
            corrective_action__gt="",
        ).exclude(status=Incident.STATUS_CLOSED).count()
        open_action_records = action_qs.exclude(status=SafetyCorrectiveAction.STATUS_CLOSED)

        # Man-hours: derive from DSR labour records if available,
        # else estimate from toolbox attendee counts × 8 hrs as a fallback.
        # Attempt to use DSRLabour records for accuracy.
        man_hours = self._compute_man_hours(project_pk)

        # LTIFR = (LTIs × 1,000,000) / man_hours_worked
        if man_hours > 0:
            ltifr = round((lti_count * 1_000_000) / man_hours, 2)
        else:
            ltifr = None

        # Toolbox talks
        toolbox_count = toolbox_qs.count()
        total_attendees = toolbox_qs.aggregate(
            total=Sum("attendee_count")
        )["total"] or 0

        # Inductions
        induction_count = induction_qs.count()

        ctx.update(
            {
                "total_incidents": total_incidents,
                "open_incidents": open_incidents,
                "incident_by_type": incident_by_type,
                "lti_count": lti_count,
                "days_lost": days_lost,
                "man_hours": man_hours,
                "total_man_hours": man_hours,
                "ltifr": ltifr,
                "toolbox_count": toolbox_count,
                "total_toolbox_attendees": total_attendees,
                "induction_count": induction_count,
                "open_corrective_actions": open_corrective_actions,
                "open_action_records": open_action_records.count(),
                "overdue_actions": open_action_records.filter(due_date__lt=date.today()).count(),
                "open_permits": permit_qs.filter(status=PermitToWork.STATUS_APPROVED).count(),
                "expired_training": sum(1 for record in training_qs if record.is_expired),
                "open_observations": observation_qs.filter(status=SafetyObservation.STATUS_OPEN).count(),
                "recent_incidents": incident_qs.select_related("project").order_by("-date", "-time")[:10],
                "recent_actions": action_qs.select_related("project", "assigned_to").order_by("status", "due_date")[:10],
                "incident_type_choices": Incident.INCIDENT_TYPE_CHOICES,
            }
        )
        return ctx

    def _compute_man_hours(self, project_pk):
        """
        Derive total man-hours from DSRLabour records (count × 10 hrs/day).
        Falls back gracefully to 0 if DSR app has no data.
        """
        try:
            from apps.dsr.models import DSRLabour, DailySiteReport

            qs = DSRLabour.objects.all()
            if project_pk:
                qs = qs.filter(dsr__project_id=project_pk)
            total_person_days = qs.aggregate(
                total=Sum("count")
            )["total"] or 0
            # Assume 10-hour shifts typical for construction sites
            return total_person_days * 10
        except Exception:
            return 0
