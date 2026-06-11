"""
Celery tasks for DSR workflow notifications.
"""

from celery import shared_task


@shared_task
def notify_dsr_submitted(dsr_id):
    """Notify project manager when a DSR is submitted for approval."""
    from apps.core.utils import safe_task_delay
    from apps.dsr.models import DailySiteReport
    from apps.notifications.tasks import notify_users

    try:
        dsr = DailySiteReport.objects.select_related("project", "prepared_by").get(pk=dsr_id)
    except DailySiteReport.DoesNotExist:
        return

    project = dsr.project
    # Notify PM (project manager assigned to project)
    pm = getattr(project, "project_manager", None)
    if pm:
        safe_task_delay(
            notify_users,
            user_ids=[pm.pk],
            notification_type="APPROVAL_REQUIRED",
            title=f"DSR Submitted — {dsr.dsr_number}",
            message=(
                f"{dsr.prepared_by.get_full_name() or dsr.prepared_by.email} has submitted "
                f"DSR {dsr.dsr_number} for {project.name} ({dsr.date}) for your approval."
            ),
            link=f"/dsr/{dsr.pk}/",
            category="dsr",
        )


@shared_task
def notify_dsr_approved(dsr_id):
    """Notify DSR preparer when their report is approved."""
    from apps.core.utils import safe_task_delay
    from apps.dsr.models import DailySiteReport
    from apps.notifications.tasks import create_notification

    try:
        dsr = DailySiteReport.objects.select_related("project", "prepared_by").get(pk=dsr_id)
    except DailySiteReport.DoesNotExist:
        return

    safe_task_delay(
        create_notification,
        user_id=dsr.prepared_by_id,
        notification_type="INFO",
        title=f"DSR Approved — {dsr.dsr_number}",
        message=f"Your DSR {dsr.dsr_number} for {dsr.project.name} ({dsr.date}) has been approved.",
        link=f"/dsr/{dsr.pk}/",
        category="dsr",
    )


@shared_task
def notify_dsr_returned(dsr_id):
    """Notify DSR preparer when report is returned for revision."""
    from apps.core.utils import safe_task_delay
    from apps.dsr.models import DailySiteReport
    from apps.notifications.tasks import create_notification

    try:
        dsr = DailySiteReport.objects.select_related("project", "prepared_by").get(pk=dsr_id)
    except DailySiteReport.DoesNotExist:
        return

    safe_task_delay(
        create_notification,
        user_id=dsr.prepared_by_id,
        notification_type="ALERT",
        title=f"DSR Returned — {dsr.dsr_number}",
        message=f"DSR {dsr.dsr_number} for {dsr.project.name} has been returned for revision. Please review and resubmit.",
        link=f"/dsr/{dsr.pk}/",
        category="dsr",
    )
