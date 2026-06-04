import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import RedirectView, TemplateView


# ---------------------------------------------------------------------------
# Home redirect
# ---------------------------------------------------------------------------


class HomeRedirectView(RedirectView):
    """Redirect authenticated users to the portfolio dashboard, others to login."""

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return "/dashboard/portfolio/"
        return "/accounts/login/"


# ---------------------------------------------------------------------------
# Portfolio Dashboard
# ---------------------------------------------------------------------------


class PortfolioDashboardView(LoginRequiredMixin, TemplateView):
    """
    Company-wide portfolio overview.

    Shows all projects the user has access to, with aggregated financials,
    recent notifications, upcoming milestones and open incidents.
    """

    template_name = "dashboard/portfolio.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Lazy imports to avoid circular dependency at module load time
        from apps.dsr.models import DailySiteReport
        from apps.notifications.models import Notification
        from apps.projects.models import Milestone, Project
        from apps.safety.models import Incident

        user = self.request.user
        today = timezone.now().date()

        # Determine project scope based on user role
        if user.is_superuser or getattr(user, "is_admin", False) or getattr(user, "is_md", False):
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(
                Q(project_manager=user) | Q(site_supervisor=user)
            )

        projects = projects.select_related("client", "project_manager").order_by("status", "name")

        # Aggregate contract value (sum of original contract values)
        total_contract_value = (
            projects.aggregate(total=Sum("contract__original_value"))["total"] or 0
        )

        # Project counts by status
        status_counts = {
            row["status"]: row["count"]
            for row in projects.values("status").annotate(count=Count("id"))
        }

        # Budget aggregates across all accessible projects
        from apps.budget.models import CostCode, CostEntry

        project_ids = list(projects.values_list("id", flat=True))

        total_budget = (
            CostCode.objects.filter(project_id__in=project_ids)
            .aggregate(total=Sum("budget_amount"))["total"] or 0
        )
        total_billed = (
            CostEntry.objects.filter(project_id__in=project_ids, entry_type="ACTUAL")
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        total_committed = (
            CostEntry.objects.filter(project_id__in=project_ids, entry_type="COMMITTED")
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        total_spent = total_billed + total_committed
        total_outstanding = total_budget - total_spent

        # Budget RAG
        if total_budget > 0:
            spend_pct = total_spent / total_budget * 100
            if spend_pct > 100:
                budget_rag = "RED"
            elif spend_pct >= 80:
                budget_rag = "AMBER"
            else:
                budget_rag = "GREEN"
        else:
            budget_rag = "GREEN"

        # Upcoming milestones (next 30 days)
        upcoming_milestones = (
            Milestone.objects.filter(
                project__in=projects,
                is_achieved=False,
                target_date__gte=today,
                target_date__lte=today + timezone.timedelta(days=30),
            )
            .select_related("project")
            .order_by("target_date")
        )

        # Recent unread notifications for this user
        notifications = (
            Notification.objects.filter(recipient=user, is_read=False)
            .order_by("-created_at")[:10]
        )
        unread_notification_count = notifications.count()

        # Recent DSRs pending approval (for PMs: prepared by others on their projects)
        recent_dsrs = (
            DailySiteReport.objects.filter(project__in=projects)
            .select_related("project", "prepared_by")
            .order_by("-date")[:10]
        )

        # Open incidents across all accessible projects
        open_incidents = Incident.objects.filter(
            project__in=projects,
            status__in=["OPEN", "UNDER_INVESTIGATION"],
        ).count()

        # Build per-project RAG indicators for the project table
        project_rows = []
        for project in projects:
            try:
                contract_val = project.contract.original_value
            except Exception:
                contract_val = 0

            cc_budget = (
                CostCode.objects.filter(project=project)
                .aggregate(total=Sum("budget_amount"))["total"] or 0
            )
            proj_spent = (
                CostEntry.objects.filter(project=project)
                .aggregate(total=Sum("amount"))["total"] or 0
            )
            if cc_budget > 0:
                proj_spend_pct = proj_spent / cc_budget * 100
                proj_budget_rag = (
                    "RED" if proj_spend_pct > 100 else "AMBER" if proj_spend_pct >= 80 else "GREEN"
                )
            else:
                proj_budget_rag = "GREEN"

            project_rows.append(
                {
                    "project": project,
                    "contract_value": contract_val,
                    "budget_rag": proj_budget_rag,
                }
            )

        ctx.update(
            {
                "project_rows": project_rows,
                "total_contract_value": total_contract_value,
                "total_budget": total_budget,
                "total_billed": total_billed,
                "total_outstanding": total_outstanding,
                "budget_rag": budget_rag,
                "project_count": projects.count(),
                "active_count": status_counts.get("ACTIVE", 0),
                "status_counts": status_counts,
                "upcoming_milestones": upcoming_milestones,
                "notifications": notifications,
                "unread_notification_count": unread_notification_count,
                "recent_dsrs": recent_dsrs,
                "open_incidents": open_incidents,
            }
        )
        return ctx


# ---------------------------------------------------------------------------
# Project Dashboard
# ---------------------------------------------------------------------------


class ProjectDashboardView(LoginRequiredMixin, TemplateView):
    """
    Single-project overview dashboard.

    Summarises budget, schedule, DSRs, open RFIs, NCRs and incidents.
    """

    template_name = "dashboard/project_dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Lazy imports to avoid circular dependency at module load time
        from apps.budget.models import CostCode, CostEntry
        from apps.documents.models import RFI
        from apps.dsr.models import DailySiteReport
        from apps.projects.models import Milestone, Project
        from apps.quality.models import Defect, NCR
        from apps.safety.models import Incident

        project = get_object_or_404(Project, pk=self.kwargs["pk"])
        today = timezone.now().date()

        # ---- Budget summary ----
        cost_codes = CostCode.objects.filter(project=project)
        total_budget = cost_codes.aggregate(total=Sum("budget_amount"))["total"] or 0
        total_committed = (
            CostEntry.objects.filter(project=project, entry_type="COMMITTED")
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        total_actual = (
            CostEntry.objects.filter(project=project, entry_type="ACTUAL")
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        total_spent = total_committed + total_actual
        budget_remaining = total_budget - total_spent
        budget_pct = round((total_spent / total_budget * 100) if total_budget else 0, 1)

        if budget_pct > 100:
            budget_rag = "RED"
        elif budget_pct >= 80:
            budget_rag = "AMBER"
        else:
            budget_rag = "GREEN"

        # ---- Schedule summary ----
        # Planned % = milestones achieved vs total milestones
        # Actual % = derived from DSR progress entries if available
        all_milestones = Milestone.objects.filter(project=project)
        total_milestones = all_milestones.count()
        achieved_milestones = all_milestones.filter(is_achieved=True).count()
        planned_pct = round(achieved_milestones / total_milestones * 100, 1) if total_milestones else 0

        # Try to get latest overall % complete from schedule progress entries
        try:
            from apps.schedule.models import ProgressEntry
            latest_progress = (
                ProgressEntry.objects.filter(activity__programme__project=project)
                .order_by("-date")
                .values("actual_percent")
                .first()
            )
            actual_schedule_pct = latest_progress["actual_percent"] if latest_progress else planned_pct
        except Exception:
            actual_schedule_pct = planned_pct

        if actual_schedule_pct >= planned_pct:
            schedule_rag = "GREEN"
        elif planned_pct - actual_schedule_pct <= 10:
            schedule_rag = "AMBER"
        else:
            schedule_rag = "RED"

        # ---- Recent DSRs ----
        recent_dsrs = (
            DailySiteReport.objects.filter(project=project)
            .select_related("prepared_by")
            .order_by("-date")[:5]
        )

        # ---- Open items ----
        open_rfis = RFI.objects.filter(
            project=project, status__in=[RFI.STATUS_OPEN, RFI.STATUS_RESPONDED]
        ).count()
        open_ncrs = NCR.objects.filter(
            project=project, status__in=[NCR.STATUS_OPEN, NCR.STATUS_UNDER_REVIEW]
        ).count()
        open_defects = Defect.objects.filter(
            project=project, status__in=[Defect.STATUS_OPEN, Defect.STATUS_IN_PROGRESS]
        ).count()
        open_incidents = Incident.objects.filter(
            project=project, status__in=["OPEN", "UNDER_INVESTIGATION"]
        ).count()

        # ---- Upcoming milestones ----
        upcoming_milestones = (
            Milestone.objects.filter(
                project=project,
                is_achieved=False,
                target_date__gte=today,
            )
            .order_by("target_date")[:5]
        )

        # ---- Safety RAG (LTI or fatality incidents in last 30 days → RED) ----
        recent_serious_incident = Incident.objects.filter(
            project=project,
            date__gte=today - timezone.timedelta(days=30),
            incident_type__in=["LTI", "FATALITY"],
        ).exists()
        safety_rag = "RED" if recent_serious_incident else "GREEN"

        ctx.update(
            {
                "project": project,
                # Budget
                "total_budget": total_budget,
                "total_committed": total_committed,
                "total_actual": total_actual,
                "total_spent": total_spent,
                "budget_remaining": budget_remaining,
                "budget_pct": budget_pct,
                "budget_rag": budget_rag,
                # Schedule
                "planned_pct": planned_pct,
                "actual_schedule_pct": actual_schedule_pct,
                "schedule_rag": schedule_rag,
                "total_milestones": total_milestones,
                "achieved_milestones": achieved_milestones,
                # Safety
                "safety_rag": safety_rag,
                "open_incidents": open_incidents,
                # Documents / Quality
                "open_rfis": open_rfis,
                "open_ncrs": open_ncrs,
                "open_defects": open_defects,
                "open_issues": open_rfis + open_ncrs + open_defects + open_incidents,
                # Lists
                "upcoming_milestones": upcoming_milestones,
                "recent_dsrs": recent_dsrs,
            }
        )
        return ctx


# ---------------------------------------------------------------------------
# S-Curve Data (JSON endpoint for Chart.js)
# ---------------------------------------------------------------------------


class SCurveDataView(LoginRequiredMixin, View):
    """
    Return monthly cumulative planned vs actual spend as JSON.
    Used by Chart.js to render the S-curve on the project dashboard.
    """

    def get(self, request, project_pk):
        from apps.budget.models import CostEntry
        from apps.projects.models import Project
        project = get_object_or_404(Project, pk=project_pk)

        # Actual spend grouped by month
        actuals = (
            CostEntry.objects.filter(project=project)
            .values("date__year", "date__month")
            .annotate(total=Sum("amount"))
            .order_by("date__year", "date__month")
        )

        labels = []
        actual_data = []
        cumulative = 0
        for entry in actuals:
            from datetime import date
            d = date(entry["date__year"], entry["date__month"], 1)
            labels.append(d.strftime("%b %Y"))
            cumulative += float(entry["total"] or 0)
            actual_data.append(round(cumulative, 2))

        return JsonResponse({
            "labels": labels,
            "datasets": [
                {
                    "label": "Cumulative Spend (K)",
                    "data": actual_data,
                    "borderColor": "#2980B9",
                    "backgroundColor": "rgba(41,128,185,0.1)",
                    "fill": True,
                    "tension": 0.3,
                },
            ],
        })


# ---------------------------------------------------------------------------
# Financial Analytics View
# ---------------------------------------------------------------------------


class FinancialAnalyticsView(LoginRequiredMixin, TemplateView):
    """Portfolio-level financial analytics for the MD."""

    template_name = "dashboard/financial_analytics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.budget.models import CostCode, CostEntry
        from apps.ipc.models import IPC, Payment
        from apps.projects.models import Project

        projects = Project.objects.filter(
            status__in=["ACTIVE", "MOBILISATION", "PRACTICAL_COMPLETION"]
        ).select_related("client", "project_manager")

        rows = []
        total_cv = 0
        total_budget = 0
        total_spent = 0
        total_claimed = 0
        total_paid = 0

        for project in projects:
            try:
                cv = float(project.contract_value or 0)
            except Exception:
                cv = 0
            budget = float(
                CostCode.objects.filter(project=project)
                .aggregate(total=Sum("budget_amount"))["total"] or 0
            )
            spent = float(
                CostEntry.objects.filter(project=project)
                .aggregate(total=Sum("amount"))["total"] or 0
            )
            claimed = float(
                IPC.objects.filter(project=project, status__in=["SUBMITTED", "CERTIFIED", "PAID"])
                .count()
            )  # count of submitted IPCs (use for tracking)
            paid = float(
                Payment.objects.filter(ipc__project=project)
                .aggregate(total=Sum("amount"))["total"] or 0
            )
            outstanding = max(0, float(cv) * 0.8 - paid)  # approximate from contract value

            if budget > 0:
                pct = spent / budget * 100
                rag = "RED" if pct > 100 else "AMBER" if pct >= 80 else "GREEN"
            else:
                pct = 0
                rag = "GREEN"

            total_cv += cv
            total_budget += budget
            total_spent += spent
            total_paid += paid

            rows.append({
                "project": project,
                "contract_value": cv,
                "budget": budget,
                "spent": spent,
                "remaining": budget - spent,
                "pct": round(pct, 1),
                "rag": rag,
                "paid": paid,
                "outstanding": outstanding,
            })

        ctx.update({
            "rows": rows,
            "total_cv": total_cv,
            "total_budget": total_budget,
            "total_spent": total_spent,
            "total_remaining": total_budget - total_spent,
            "total_paid": total_paid,
            "breadcrumbs": [{"label": "Financial Analytics"}],
        })
        return ctx


# ---------------------------------------------------------------------------
# Safety Analytics View
# ---------------------------------------------------------------------------


class SafetyAnalyticsView(LoginRequiredMixin, TemplateView):
    """Portfolio-level safety statistics."""

    template_name = "dashboard/safety_analytics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.resources.models import AttendanceRecord
        from apps.safety.models import Incident, ToolboxTalk
        from apps.projects.models import Project

        today = timezone.now().date()
        ytd_start = today.replace(month=1, day=1)

        projects = Project.objects.filter(status__in=["ACTIVE", "MOBILISATION"])

        ytd_incidents = Incident.objects.filter(
            project__in=projects,
            date__gte=ytd_start,
        )
        ltis = ytd_incidents.filter(incident_type="LTI")
        fatalities = ytd_incidents.filter(incident_type="FATALITY")
        near_misses = ytd_incidents.filter(incident_type="NEAR_MISS")

        # Man-hours YTD (attendance records × 8 hrs per day as approximation)
        attendance_count = AttendanceRecord.objects.filter(
            project__in=projects,
            date__gte=ytd_start,
            is_present=True,
        ).count()
        man_hours_ytd = attendance_count * 8

        # LTIFR = LTIs per million man-hours
        ltifr = round((ltis.count() / man_hours_ytd * 1_000_000), 2) if man_hours_ytd else 0

        per_project = []
        for project in projects:
            p_incidents = Incident.objects.filter(project=project, date__gte=ytd_start)
            per_project.append({
                "project": project,
                "total": p_incidents.count(),
                "lti": p_incidents.filter(incident_type="LTI").count(),
                "near_miss": p_incidents.filter(incident_type="NEAR_MISS").count(),
                "open": p_incidents.filter(status__in=["OPEN", "UNDER_INVESTIGATION"]).count(),
                "toolbox_talks": ToolboxTalk.objects.filter(
                    project=project, date__gte=ytd_start
                ).count(),
            })

        ctx.update({
            "ytd_start": ytd_start,
            "total_incidents": ytd_incidents.count(),
            "ltis": ltis.count(),
            "fatalities": fatalities.count(),
            "near_misses": near_misses.count(),
            "man_hours_ytd": man_hours_ytd,
            "ltifr": ltifr,
            "per_project": per_project,
            "open_incidents": ytd_incidents.filter(status__in=["OPEN", "UNDER_INVESTIGATION"]).count(),
            "breadcrumbs": [{"label": "Safety Analytics"}],
        })
        return ctx
