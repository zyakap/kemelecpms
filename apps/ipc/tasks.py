"""
Celery tasks for IPC workflow notifications.
"""

from celery import shared_task


@shared_task
def notify_ipc_submitted(ipc_id):
    """Notify Finance and MD when an IPC is submitted for internal review."""
    from apps.ipc.models import IPC
    from apps.notifications.tasks import notify_users
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        ipc = IPC.objects.select_related("project").get(pk=ipc_id)
    except IPC.DoesNotExist:
        return

    # Notify Finance role and MD role users
    finance_md_users = User.objects.filter(
        role__in=["FINANCE", "MANAGING_DIRECTOR"],
        is_active=True,
    ).values_list("pk", flat=True)

    notify_users.delay(
        user_ids=list(finance_md_users),
        notification_type="APPROVAL_REQUIRED",
        title=f"IPC Submitted — {ipc.ipc_number}",
        message=(
            f"Interim Payment Claim {ipc.ipc_number} for project {ipc.project.name} "
            f"(period {ipc.claim_period_from} to {ipc.claim_period_to}) is ready for review."
        ),
        link=f"/ipc/{ipc.pk}/",
    )


@shared_task
def notify_payment_received(ipc_id):
    """Notify PM when a payment is recorded against an IPC."""
    from apps.ipc.models import IPC
    from apps.notifications.tasks import create_notification

    try:
        ipc = IPC.objects.select_related("project").get(pk=ipc_id)
    except IPC.DoesNotExist:
        return

    project = ipc.project
    pm = getattr(project, "project_manager", None)
    if pm:
        create_notification.delay(
            user_id=pm.pk,
            notification_type="INFO",
            title=f"Payment Received — {ipc.ipc_number}",
            message=f"A payment has been recorded against IPC {ipc.ipc_number} for {project.name}.",
            link=f"/ipc/{ipc.pk}/",
        )
