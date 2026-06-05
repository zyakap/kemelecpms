from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.permissions import accessible_projects


def _count(qs):
    try:
        return qs.count()
    except Exception:
        return 0


def _first_items(qs, limit=6):
    try:
        return list(qs[:limit])
    except Exception:
        return []


def get_role_label(user):
    if not user or not user.is_authenticated:
        return ""
    return dict(User.ROLE_CHOICES).get(user.role, user.role)


def build_action_workspace(user, limit=6):
    """Build role-aware action queues for the home dashboard."""
    today = timezone.now().date()
    projects = accessible_projects(user)
    project_ids = list(projects.values_list("id", flat=True))

    from apps.documents.models import RFI, Submittal
    from apps.dsr.models import DailySiteReport
    from apps.budget.models import CostCode
    from apps.compliance.models import ComplianceCalendarEntry
    from apps.ipc.models import IPC
    from apps.notifications.models import Task
    from apps.procurement.models import MaterialRequisition, PurchaseOrder
    from apps.projects.models import Milestone, Variation
    from apps.quality.models import Defect, NCR
    from apps.safety.models import Incident, SafetyCorrectiveAction

    pending_dsrs = DailySiteReport.objects.filter(
        project_id__in=project_ids,
        status=DailySiteReport.STATUS_SUBMITTED,
    ).select_related("project", "prepared_by").order_by("-date")
    draft_dsrs = DailySiteReport.objects.filter(
        project_id__in=project_ids,
        prepared_by=user,
        status__in=[DailySiteReport.STATUS_DRAFT, DailySiteReport.STATUS_RETURNED],
    ).select_related("project").order_by("-date")

    pending_mrs = MaterialRequisition.objects.filter(
        project_id__in=project_ids,
        status=MaterialRequisition.STATUS_SUBMITTED,
    ).select_related("project", "requested_by").order_by("required_by_date")
    pending_pos = PurchaseOrder.objects.filter(
        project_id__in=project_ids,
        status=PurchaseOrder.STATUS_PENDING_APPROVAL,
    ).select_related("project", "supplier").order_by("expected_delivery_date", "-date")
    late_pos = PurchaseOrder.objects.filter(
        project_id__in=project_ids,
        expected_delivery_date__lt=today,
        status__in=[
            PurchaseOrder.STATUS_APPROVED,
            PurchaseOrder.STATUS_SENT,
            PurchaseOrder.STATUS_PARTIALLY_DELIVERED,
        ],
    ).select_related("project", "supplier").order_by("expected_delivery_date")

    ipc_queue = IPC.objects.filter(
        project_id__in=project_ids,
        status__in=[IPC.STATUS_INTERNAL_REVIEW, IPC.STATUS_SUBMITTED, IPC.STATUS_CERTIFIED],
    ).select_related("project").order_by("-claim_period_to")
    variation_queue = Variation.objects.filter(
        project_id__in=project_ids,
        status__in=[Variation.STATUS_SUBMITTED, Variation.STATUS_ASSESSED],
    ).select_related("project").order_by("-created_at")

    open_rfis = RFI.objects.filter(project_id__in=project_ids, status=RFI.STATUS_OPEN).select_related("project")
    open_submittals = Submittal.objects.filter(
        project_id__in=project_ids,
        status__in=[Submittal.STATUS_SUBMITTED, Submittal.STATUS_REVISE_RESUBMIT],
    ).select_related("project")
    open_ncrs = NCR.objects.filter(
        project_id__in=project_ids,
        status__in=[NCR.STATUS_OPEN, NCR.STATUS_UNDER_REVIEW],
    ).select_related("project").order_by("due_date")
    open_defects = Defect.objects.filter(
        project_id__in=project_ids,
        status__in=[Defect.STATUS_OPEN, Defect.STATUS_IN_PROGRESS],
    ).select_related("project").order_by("target_rectification_date")
    open_incidents = Incident.objects.filter(
        project_id__in=project_ids,
        status__in=[Incident.STATUS_OPEN, Incident.STATUS_INVESTIGATING],
    ).select_related("project").order_by("-date")
    corrective_actions = SafetyCorrectiveAction.objects.filter(
        project_id__in=project_ids,
        status__in=[SafetyCorrectiveAction.STATUS_OPEN, SafetyCorrectiveAction.STATUS_IN_PROGRESS],
    ).select_related("project", "assigned_to").order_by("due_date")

    tasks = Task.objects.filter(
        assigned_to=user,
        status__in=[Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS],
    ).select_related("project").order_by("due_date", "-priority")
    overdue_tasks = tasks.filter(due_date__lt=today)
    overdue_milestones = Milestone.objects.filter(
        project_id__in=project_ids,
        is_achieved=False,
        target_date__lt=today,
    ).select_related("project").order_by("target_date")
    compliance_due = ComplianceCalendarEntry.objects.filter(
        Q(project_id__in=project_ids) | Q(project__isnull=True),
        status__in=[ComplianceCalendarEntry.STATUS_PENDING, ComplianceCalendarEntry.STATUS_OVERDUE],
        due_date__lte=today + timezone.timedelta(days=14),
    ).select_related("project", "responsible").order_by("due_date")
    budget_overruns = [
        cost_code
        for cost_code in CostCode.objects.filter(project_id__in=project_ids).select_related("project").order_by("project__name", "code")
        if cost_code.forecast_rag_status == "RED"
    ]

    queues = [
        {
            "key": "approvals",
            "label": "Approvals",
            "icon": "bi-check2-circle",
            "count": _count(pending_dsrs) + _count(pending_mrs) + _count(pending_pos) + _count(ipc_queue) + _count(variation_queue),
            "items": [
                *[
                    {"title": f"DSR {item.dsr_number}", "meta": item.project.name, "url": item.get_absolute_url(), "tone": "primary"}
                    for item in _first_items(pending_dsrs, limit=2)
                ],
                *[
                    {"title": item.mr_number, "meta": item.project.name, "url": item.get_absolute_url(), "tone": "warning"}
                    for item in _first_items(pending_mrs, limit=2)
                ],
                *[
                    {"title": item.po_number, "meta": item.supplier.name, "url": item.get_absolute_url(), "tone": "warning"}
                    for item in _first_items(pending_pos, limit=2)
                ],
            ],
        },
        {
            "key": "site",
            "label": "Site Actions",
            "icon": "bi-clipboard2-check",
            "count": _count(draft_dsrs) + _count(tasks),
            "items": [
                *[
                    {"title": f"Complete DSR {item.dsr_number}", "meta": item.project.name, "url": item.get_absolute_url(), "tone": "secondary"}
                    for item in _first_items(draft_dsrs, limit=3)
                ],
                *[
                    {"title": item.title, "meta": item.project.name if item.project else "General", "url": reverse("notifications:task-list"), "tone": item.priority_colour}
                    for item in _first_items(tasks, limit=3)
                ],
            ],
        },
        {
            "key": "overdue",
            "label": "Overdue",
            "icon": "bi-exclamation-triangle",
            "count": _count(overdue_tasks) + _count(overdue_milestones) + _count(open_ncrs.filter(due_date__lt=today)) + _count(open_defects.filter(target_rectification_date__lt=today)),
            "items": [
                *[
                    {"title": item.title, "meta": item.due_date.strftime("%d %b %Y"), "url": reverse("notifications:task-list"), "tone": "danger"}
                    for item in _first_items(overdue_tasks, limit=2)
                ],
                *[
                    {"title": item.name, "meta": item.project.name, "url": item.project.get_absolute_url(), "tone": "danger"}
                    for item in _first_items(overdue_milestones, limit=2)
                ],
            ],
        },
        {
            "key": "commercial",
            "label": "Commercial",
            "icon": "bi-cash-stack",
            "count": _count(ipc_queue) + _count(variation_queue),
            "items": [
                *[
                    {"title": item.ipc_number, "meta": item.project.name, "url": item.get_absolute_url(), "tone": "success"}
                    for item in _first_items(ipc_queue, limit=3)
                ],
                *[
                    {"title": item.ref_number, "meta": item.project.name, "url": item.get_absolute_url(), "tone": "warning"}
                    for item in _first_items(variation_queue, limit=3)
                ],
            ],
        },
        {
            "key": "procurement",
            "label": "Procurement",
            "icon": "bi-truck",
            "count": _count(pending_pos) + _count(late_pos),
            "items": [
                *[
                    {"title": item.po_number, "meta": f"Due {item.expected_delivery_date:%d %b %Y}" if item.expected_delivery_date else item.supplier.name, "url": item.get_absolute_url(), "tone": "danger"}
                    for item in _first_items(late_pos, limit=3)
                ],
                *[
                    {"title": item.po_number, "meta": item.supplier.name, "url": item.get_absolute_url(), "tone": "warning"}
                    for item in _first_items(pending_pos, limit=3)
                ],
            ],
        },
        {
            "key": "budget",
            "label": "Budget Risk",
            "icon": "bi-graph-down-arrow",
            "count": len(budget_overruns),
            "items": [
                {
                    "title": item.code,
                    "meta": f"{item.project.name} · EFC {item.forecast_variance_percentage}%",
                    "url": reverse("budget:dashboard", kwargs={"project_pk": item.project_id}),
                    "tone": "danger",
                }
                for item in budget_overruns[:limit]
            ],
        },
        {
            "key": "compliance",
            "label": "HSEQ & Docs",
            "icon": "bi-shield-check",
            "count": _count(open_rfis) + _count(open_submittals) + _count(open_ncrs) + _count(open_defects) + _count(open_incidents) + _count(corrective_actions) + _count(compliance_due),
            "items": [
                *[
                    {"title": item.rfi_number, "meta": item.project.name, "url": item.get_absolute_url(), "tone": "primary"}
                    for item in _first_items(open_rfis, limit=2)
                ],
                *[
                    {"title": item.ncr_number, "meta": item.project.name, "url": item.get_absolute_url(), "tone": "danger"}
                    for item in _first_items(open_ncrs, limit=2)
                ],
                *[
                    {"title": item.description[:60], "meta": item.project.name, "url": reverse("safety:corrective_action_list"), "tone": "warning"}
                    for item in _first_items(corrective_actions, limit=2)
                ],
                *[
                    {
                        "title": item.title,
                        "meta": item.project.name if item.project else "Company-wide",
                        "url": item.get_absolute_url(),
                        "tone": "danger" if item.due_date < today else "warning",
                    }
                    for item in _first_items(compliance_due, limit=2)
                ],
            ],
        },
    ]

    queue_counts = {queue["key"]: queue["count"] for queue in queues}
    project_status_rows = projects.values("status").annotate(count=Count("id")).order_by("status")

    return {
        "role_label": get_role_label(user),
        "queues": queues,
        "queue_counts": queue_counts,
        "projects": projects.select_related("client", "project_manager", "site_supervisor").order_by("name"),
        "project_status_rows": project_status_rows,
        "my_tasks": tasks[:limit],
        "today": today,
    }


def build_global_context(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    from apps.notifications.models import Notification, Task

    projects = accessible_projects(user).order_by("name")
    current_project = None
    project_pk = request.resolver_match.kwargs.get("project_pk") if request.resolver_match else None
    project_pk = project_pk or (request.resolver_match.kwargs.get("pk") if request.resolver_match and "project" in request.path else None)
    if project_pk:
        current_project = projects.filter(pk=project_pk).first()

    task_count = Task.objects.filter(
        assigned_to=user,
        status__in=[Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS],
    ).count()
    notifications = Notification.objects.filter(recipient=user).order_by("-created_at")
    return {
        "global_projects": projects[:50],
        "current_project": current_project,
        "recent_notifications": notifications[:6],
        "unread_notifications_count": notifications.filter(is_read=False).count(),
        "my_open_task_count": task_count,
    }
