import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.core.permissions import accessible_projects, can_manage_project

from .forms import (
    ActivityForm,
    LookAheadForm,
    LookAheadTaskForm,
    ProgressEntryForm,
    ProgrammeForm,
    ProgrammeRevisionForm,
    WBSActivityForm,
)
from .models import (
    Activity,
    LookAhead,
    LookAheadTask,
    Programme,
    ProgrammeRevision,
    ProgressEntry,
    WBSActivity,
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


class ProgrammeMixin(ProjectMixin):
    """Additionally resolves the Programme for the current project."""

    def get_programme(self):
        if not hasattr(self, "_programme"):
            self._programme = get_object_or_404(Programme, project=self.get_project())
        return self._programme

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx["programme"] = self.get_programme()
        except Exception:
            ctx["programme"] = None
        return ctx


# ---------------------------------------------------------------------------
# WBS Views
# ---------------------------------------------------------------------------


class WBSView(ProjectMixin, TemplateView):
    """
    Tree view of WBS activities for a project.
    Renders only top-level (parentless) nodes; children are nested in template.
    """

    template_name = "schedule/wbs.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        # Top-level nodes (no parent)
        ctx["root_nodes"] = (
            WBSActivity.objects.filter(project=project, parent__isnull=True)
            .select_related("responsible", "cost_code")
            .prefetch_related("children__children")
            .order_by("wbs_code")
        )
        return ctx


class WBSActivityCreateView(ProjectMixin, CreateView):
    model = WBSActivity
    form_class = WBSActivityForm
    template_name = "schedule/wbs_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create WBS activities for this project.")
            return redirect(self.get_success_url())
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "WBS activity created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("schedule:wbs", kwargs={"project_pk": self.get_project().pk})


class WBSActivityUpdateView(ProjectMixin, UpdateView):
    model = WBSActivity
    form_class = WBSActivityForm
    template_name = "schedule/wbs_form.html"

    def get_queryset(self):
        return WBSActivity.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update WBS activities for this project.")
            return redirect(self.get_success_url())
        form.instance.updated_by = self.request.user
        messages.success(self.request, "WBS activity updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("schedule:wbs", kwargs={"project_pk": self.get_project().pk})


# ---------------------------------------------------------------------------
# Programme views
# ---------------------------------------------------------------------------


class ProgrammeView(ProjectMixin, TemplateView):
    """
    Main programme view; also exposes Gantt JSON at ?format=json.
    Returns activity data structured for a frontend Gantt chart library
    (e.g. dhtmlxGantt / frappe-gantt).
    """

    template_name = "schedule/programme.html"

    def _gantt_data(self, project):
        try:
            programme = Programme.objects.get(project=project)
        except Programme.DoesNotExist:
            return {"data": [], "links": []}

        activities = (
            Activity.objects.filter(programme=programme)
            .select_related("predecessor", "wbs_activity", "responsible")
            .order_by("start_date")
        )

        data = []
        links = []
        for act in activities:
            data.append(
                {
                    "id": act.pk,
                    "text": act.name,
                    "start_date": act.start_date.strftime("%Y-%m-%d"),
                    "end_date": act.end_date.strftime("%Y-%m-%d"),
                    "duration": act.duration,
                    "progress": float(act.actual_percent) / 100,
                    "planned_percent": float(act.planned_percent),
                    "actual_percent": float(act.actual_percent),
                    "is_critical": act.is_critical,
                    "responsible": str(act.responsible) if act.responsible else "",
                    "wbs": str(act.wbs_activity) if act.wbs_activity else "",
                    "spi": float(act.spi),
                    "on_schedule": act.is_on_schedule,
                }
            )
            if act.predecessor_id:
                dep_map = {Activity.DEP_FS: 0, Activity.DEP_SS: 1, Activity.DEP_FF: 3}
                links.append(
                    {
                        "id": f"link_{act.pk}",
                        "source": act.predecessor_id,
                        "target": act.pk,
                        "type": dep_map.get(act.dependency_type, 0),
                    }
                )

        return {"data": data, "links": links}

    def get(self, request, *args, **kwargs):
        if request.GET.get("format") == "json":
            return JsonResponse(self._gantt_data(self.get_project()))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        try:
            ctx["programme"] = Programme.objects.get(project=project)
        except Programme.DoesNotExist:
            ctx["programme"] = None
        if ctx["programme"]:
            ctx["programme_revisions"] = ctx["programme"].revisions.select_related(
                "approved_by"
            ).order_by("-submitted_date")
        else:
            ctx["programme_revisions"] = []
        ctx["gantt_data_json"] = json.dumps(self._gantt_data(project))
        return ctx


class ProgrammeCreateView(ProjectMixin, CreateView):
    model = Programme
    form_class = ProgrammeForm
    template_name = "schedule/programme_form.html"

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create programmes for this project.")
            return redirect(reverse_lazy("schedule:programme", kwargs={"project_pk": self.get_project().pk}))
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Programme created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("schedule:programme", kwargs={"project_pk": self.get_project().pk})


class ProgrammeUpdateView(ProjectMixin, UpdateView):
    model = Programme
    form_class = ProgrammeForm
    template_name = "schedule/programme_form.html"

    def get_object(self, queryset=None):
        return get_object_or_404(Programme, project=self.get_project())

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update programmes for this project.")
            return redirect(self.get_success_url())
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Programme updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("schedule:programme", kwargs={"project_pk": self.get_project().pk})


class ProgrammeRevisionCreateView(ProgrammeMixin, CreateView):
    model = ProgrammeRevision
    form_class = ProgrammeRevisionForm
    template_name = "schedule/programme_revision_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["programme"] = self.get_programme()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        programme = self.get_programme()
        if not can_manage_project(self.request.user, programme.project):
            messages.error(self.request, "You do not have permission to submit programme revisions for this project.")
            return redirect(self.get_success_url())
        form.instance.programme = programme
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        if self.object.status == ProgrammeRevision.STATUS_APPROVED:
            programme.recalculate_critical_path()
        messages.success(self.request, "Programme revision recorded.")
        return response

    def get_success_url(self):
        return reverse_lazy("schedule:programme", kwargs={"project_pk": self.get_project().pk})


class ProgrammeRevisionUpdateView(ProgrammeMixin, UpdateView):
    model = ProgrammeRevision
    form_class = ProgrammeRevisionForm
    template_name = "schedule/programme_revision_form.html"

    def get_queryset(self):
        return ProgrammeRevision.objects.filter(programme=self.get_programme())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["programme"] = self.get_programme()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        programme = self.get_programme()
        if not can_manage_project(self.request.user, programme.project):
            messages.error(self.request, "You do not have permission to update programme revisions for this project.")
            return redirect(self.get_success_url())
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        if self.object.status == ProgrammeRevision.STATUS_APPROVED:
            programme.recalculate_critical_path()
        messages.success(self.request, "Programme revision updated.")
        return response

    def get_success_url(self):
        return reverse_lazy("schedule:programme", kwargs={"project_pk": self.get_project().pk})


class CriticalPathRecalculateView(ProgrammeMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        programme = self.get_programme()
        if not can_manage_project(request.user, programme.project):
            messages.error(request, "You do not have permission to recalculate the critical path for this project.")
            return redirect("schedule:programme", project_pk=programme.project_id)
        count = len(programme.recalculate_critical_path())
        messages.success(request, f"Critical path recalculated across {count} activities.")
        return redirect("schedule:programme", project_pk=programme.project_id)


# ---------------------------------------------------------------------------
# Activity views
# ---------------------------------------------------------------------------


class ActivityListView(ProgrammeMixin, ListView):
    model = Activity
    template_name = "schedule/activity_list.html"
    context_object_name = "activities"

    def get_queryset(self):
        try:
            programme = self.get_programme()
            qs = Activity.objects.filter(programme=programme).select_related(
                "wbs_activity", "responsible", "predecessor"
            )
            if self.request.GET.get("critical"):
                qs = qs.filter(is_critical=True)
            return qs
        except Exception:
            return Activity.objects.none()


class ActivityCreateView(ProgrammeMixin, CreateView):
    model = Activity
    form_class = ActivityForm
    template_name = "schedule/activity_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs["programme"] = self.get_programme()
        except Exception:
            kwargs["programme"] = None
        return kwargs

    def form_valid(self, form):
        programme = self.get_programme()
        if not can_manage_project(self.request.user, programme.project):
            messages.error(self.request, "You do not have permission to create activities for this project.")
            return redirect(self.get_success_url())
        form.instance.programme = programme
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        programme.recalculate_critical_path()
        messages.success(self.request, "Activity created successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("schedule:activity-list", kwargs={"project_pk": self.get_project().pk})


class ActivityUpdateView(ProgrammeMixin, UpdateView):
    model = Activity
    form_class = ActivityForm
    template_name = "schedule/activity_form.html"

    def get_queryset(self):
        try:
            return Activity.objects.filter(programme=self.get_programme())
        except Exception:
            return Activity.objects.none()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs["programme"] = self.get_programme()
        except Exception:
            kwargs["programme"] = None
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update activities for this project.")
            return redirect(self.get_success_url())
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        self.get_programme().recalculate_critical_path()
        messages.success(self.request, "Activity updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("schedule:activity-list", kwargs={"project_pk": self.get_project().pk})


# ---------------------------------------------------------------------------
# Progress Entry views
# ---------------------------------------------------------------------------


class ProgressEntryCreateView(LoginRequiredMixin, CreateView):
    model = ProgressEntry
    form_class = ProgressEntryForm
    template_name = "schedule/progress_form.html"

    def get_activity(self):
        if not hasattr(self, "_activity"):
            self._activity = get_object_or_404(
                Activity,
                pk=self.kwargs["activity_pk"],
                programme__project__in=accessible_projects(self.request.user),
            )
        return self._activity

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["activity"] = self.get_activity()
        ctx["project"] = self.get_activity().programme.project
        return ctx

    def form_valid(self, form):
        activity = self.get_activity()
        if not can_manage_project(self.request.user, activity.programme.project):
            messages.error(self.request, "You do not have permission to record progress for this project.")
            return redirect(self.get_success_url())
        form.instance.activity = activity
        form.instance.recorded_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Progress recorded successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        activity = self.get_activity()
        return reverse_lazy(
            "schedule:activity-list",
            kwargs={"project_pk": activity.programme.project_id},
        )


# ---------------------------------------------------------------------------
# Look-Ahead views
# ---------------------------------------------------------------------------


class LookAheadListView(ProjectMixin, ListView):
    model = LookAhead
    template_name = "schedule/lookahead_list.html"
    context_object_name = "look_aheads"

    def get_queryset(self):
        return LookAhead.objects.filter(project=self.get_project()).select_related("created_by")


class LookAheadCreateView(ProjectMixin, CreateView):
    model = LookAhead
    form_class = LookAheadForm
    template_name = "schedule/lookahead_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create look-ahead plans for this project.")
            return redirect(self.get_success_url())
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        form.instance.created_by_id = self.request.user.pk  # explicit for non-TS field
        messages.success(self.request, "Look-Ahead plan created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("schedule:lookahead-list", kwargs={"project_pk": self.get_project().pk})


class LookAheadDetailView(ProjectMixin, DetailView):
    model = LookAhead
    template_name = "schedule/lookahead_detail.html"
    context_object_name = "look_ahead"

    def get_queryset(self):
        return LookAhead.objects.filter(project=self.get_project()).prefetch_related(
            "tasks__activity", "tasks__assigned_to"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["task_form"] = LookAheadTaskForm(look_ahead=self.get_object())
        return ctx

    def post(self, request, *args, **kwargs):
        """Inline task creation from the detail page."""
        look_ahead = self.get_object()
        form = LookAheadTaskForm(request.POST, look_ahead=look_ahead)
        if form.is_valid():
            if not can_manage_project(request.user, look_ahead.project):
                messages.error(request, "You do not have permission to add look-ahead tasks for this project.")
                return redirect("schedule:lookahead-detail", project_pk=self.get_project().pk, pk=look_ahead.pk)
            task = form.save(commit=False)
            task.look_ahead = look_ahead
            task.created_by = request.user
            task.save()
            messages.success(request, "Task added to look-ahead.")
        else:
            messages.error(request, "Please correct the errors below.")
        return redirect("schedule:lookahead-detail", project_pk=self.get_project().pk, pk=look_ahead.pk)


# ---------------------------------------------------------------------------
# S-Curve Data view
# ---------------------------------------------------------------------------


class SCurveDataView(ProjectMixin, View):
    """
    Returns JSON with cumulative planned vs actual percentage progress over time.
    Intended to feed a frontend chart (e.g. Chart.js).

    Response shape:
    {
        "labels": ["2025-01-01", ...],
        "planned": [0.0, 5.2, ...],
        "actual":  [0.0, 3.8, ...]
    }
    """

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        try:
            programme = Programme.objects.get(project=project)
        except Programme.DoesNotExist:
            return JsonResponse({"labels": [], "planned": [], "actual": []})

        activities = list(
            Activity.objects.filter(programme=programme).order_by("start_date")
        )

        if not activities:
            return JsonResponse({"labels": [], "planned": [], "actual": []})

        # Collect all relevant dates (activity start and end dates)
        date_set = set()
        for act in activities:
            date_set.add(act.start_date)
            date_set.add(act.end_date)
        sorted_dates = sorted(date_set)

        # For each date, compute weighted cumulative planned and actual %
        # Weight each activity equally (simple average approach)
        n = len(activities)
        labels = []
        planned_series = []
        actual_series = []

        for d in sorted_dates:
            cum_planned = Decimal("0.00")
            cum_actual = Decimal("0.00")
            for act in activities:
                if act.start_date <= d:
                    if act.end_date <= d:
                        # Fully within range: use full planned/actual
                        cum_planned += act.planned_percent
                        cum_actual += act.actual_percent
                    else:
                        # Partially within range: interpolate planned linearly
                        total_days = max((act.end_date - act.start_date).days, 1)
                        elapsed = (d - act.start_date).days
                        fraction = Decimal(str(elapsed / total_days))
                        cum_planned += act.planned_percent * fraction
                        cum_actual += act.actual_percent * fraction

            labels.append(str(d))
            planned_series.append(round(float(cum_planned / n), 2))
            actual_series.append(round(float(cum_actual / n), 2))

        return JsonResponse(
            {
                "labels": labels,
                "planned": planned_series,
                "actual": actual_series,
            }
        )
