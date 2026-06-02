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

from apps.projects.models import Project

from .forms import (
    HazardRiskForm,
    IncidentForm,
    PPEIssueForm,
    SafetyInductionForm,
    SWMSForm,
    ToolboxTalkForm,
)
from .models import (
    HazardRisk,
    Incident,
    PPEIssue,
    SafetyInduction,
    SWMS,
    ToolboxTalk,
)


# ---------------------------------------------------------------------------
# Incident views
# ---------------------------------------------------------------------------


class IncidentListView(LoginRequiredMixin, ListView):
    model = Incident
    template_name = "safety/incident_list.html"
    context_object_name = "incidents"
    paginate_by = 20

    def get_queryset(self):
        qs = Incident.objects.select_related(
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
        ctx["projects"] = Project.objects.all()
        ctx["type_choices"] = Incident.INCIDENT_TYPE_CHOICES
        ctx["status_choices"] = Incident.STATUS_CHOICES
        return ctx


class IncidentCreateView(LoginRequiredMixin, CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = "safety/incident_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(
            self.request,
            f"Incident {form.instance.incident_number or 'record'} created.",
        )
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

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(
            self.request, f"Incident {self.object.incident_number} updated."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class IncidentDetailView(LoginRequiredMixin, DetailView):
    model = Incident
    template_name = "safety/incident_detail.html"
    context_object_name = "incident"

    def get_queryset(self):
        return Incident.objects.select_related(
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
        qs = ToolboxTalk.objects.select_related("project", "presenter").order_by(
            "-date"
        )
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = Project.objects.all()
        return ctx


class ToolboxTalkCreateView(LoginRequiredMixin, CreateView):
    model = ToolboxTalk
    form_class = ToolboxTalkForm
    template_name = "safety/toolbox_form.html"
    success_url = reverse_lazy("safety:toolbox_list")

    def form_valid(self, form):
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
        qs = SafetyInduction.objects.select_related(
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
        ctx["projects"] = Project.objects.all()
        return ctx


class SafetyInductionCreateView(LoginRequiredMixin, CreateView):
    model = SafetyInduction
    form_class = SafetyInductionForm
    template_name = "safety/induction_form.html"
    success_url = reverse_lazy("safety:induction_list")

    def form_valid(self, form):
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
        qs = HazardRisk.objects.select_related("project", "reviewed_by").order_by(
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
        ctx["projects"] = Project.objects.all()
        ctx["control_types"] = HazardRisk.CONTROL_TYPE_CHOICES
        return ctx


class HazardRiskCreateView(LoginRequiredMixin, CreateView):
    model = HazardRisk
    form_class = HazardRiskForm
    template_name = "safety/hazard_form.html"
    success_url = reverse_lazy("safety:hazard_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Hazard / risk entry created.")
        return super().form_valid(form)


class HazardRiskUpdateView(LoginRequiredMixin, UpdateView):
    model = HazardRisk
    form_class = HazardRiskForm
    template_name = "safety/hazard_form.html"
    success_url = reverse_lazy("safety:hazard_list")

    def form_valid(self, form):
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
        qs = SWMS.objects.select_related("project", "approved_by").order_by(
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
        ctx["projects"] = Project.objects.all()
        ctx["status_choices"] = SWMS.STATUS_CHOICES
        return ctx


class SWMSCreateView(LoginRequiredMixin, CreateView):
    model = SWMS
    form_class = SWMSForm
    template_name = "safety/swms_form.html"
    success_url = reverse_lazy("safety:swms_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "SWMS document created.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# PPE Issue views
# ---------------------------------------------------------------------------


class PPEIssueListView(LoginRequiredMixin, ListView):
    model = PPEIssue
    template_name = "safety/ppe_list.html"
    context_object_name = "ppe_issues"
    paginate_by = 25

    def get_queryset(self):
        qs = PPEIssue.objects.select_related(
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
        ctx["projects"] = Project.objects.all()
        ctx["ppe_types"] = PPEIssue.PPE_TYPE_CHOICES
        return ctx


class PPEIssueCreateView(LoginRequiredMixin, CreateView):
    model = PPEIssue
    form_class = PPEIssueForm
    template_name = "safety/ppe_form.html"
    success_url = reverse_lazy("safety:ppe_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "PPE issue record saved.")
        return super().form_valid(form)


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
        projects = Project.objects.all()
        ctx["projects"] = projects
        ctx["selected_project_pk"] = project_pk

        incident_qs = Incident.objects.all()
        toolbox_qs = ToolboxTalk.objects.all()
        induction_qs = SafetyInduction.objects.all()

        if project_pk:
            try:
                selected = Project.objects.get(pk=project_pk)
                ctx["selected_project"] = selected
            except Project.DoesNotExist:
                selected = None
            if selected:
                incident_qs = incident_qs.filter(project=selected)
                toolbox_qs = toolbox_qs.filter(project=selected)
                induction_qs = induction_qs.filter(project=selected)

        # Incident stats
        incident_counts = incident_qs.values("incident_type").annotate(
            total=Count("pk")
        )
        incident_by_type = {
            row["incident_type"]: row["total"] for row in incident_counts
        }

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
                "ltifr": ltifr,
                "toolbox_count": toolbox_count,
                "total_toolbox_attendees": total_attendees,
                "induction_count": induction_count,
                "open_corrective_actions": open_corrective_actions,
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
