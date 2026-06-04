"""
Celery tasks for Procurement workflow notifications.
"""

from celery import shared_task


@shared_task
def notify_po_pending_approval(po_id):
    """Notify PM/MD when a Purchase Order requires approval."""
    from apps.procurement.models import PurchaseOrder
    from apps.notifications.tasks import notify_users

    try:
        po = PurchaseOrder.objects.select_related("project", "created_by").get(pk=po_id)
    except PurchaseOrder.DoesNotExist:
        return

    project = po.project
    approvers = []
    pm = getattr(project, "project_manager", None)
    if pm:
        approvers.append(pm.pk)

    if approvers:
        notify_users.delay(
            user_ids=approvers,
            notification_type="APPROVAL_REQUIRED",
            title=f"PO Approval Required — {po.po_number}",
            message=(
                f"Purchase Order {po.po_number} for {project.name} totalling "
                f"K{po.total_amount:,.2f} requires your approval."
            ),
            link=f"/procurement/pos/{po.pk}/",
        )


@shared_task
def notify_mr_approved(mr_id):
    """Notify MR creator when their requisition is approved."""
    from apps.procurement.models import MaterialRequisition
    from apps.notifications.tasks import create_notification

    try:
        mr = MaterialRequisition.objects.select_related("created_by").get(pk=mr_id)
    except MaterialRequisition.DoesNotExist:
        return

    if mr.created_by:
        create_notification.delay(
            user_id=mr.created_by_id,
            notification_type="INFO",
            title=f"MR Approved — {mr.mr_number}",
            message=f"Your material requisition {mr.mr_number} has been approved.",
            link=f"/procurement/mrs/{mr.pk}/",
        )


@shared_task
def notify_grn_recorded(grn_id):
    """Notify procurement officer when goods are received against a PO."""
    from apps.procurement.models import GoodsReceivedNote
    from apps.notifications.tasks import create_notification

    try:
        grn = GoodsReceivedNote.objects.select_related("purchase_order__created_by").get(pk=grn_id)
    except GoodsReceivedNote.DoesNotExist:
        return

    po = grn.purchase_order
    if po.created_by:
        create_notification.delay(
            user_id=po.created_by_id,
            notification_type="INFO",
            title=f"GRN Recorded — {grn.grn_number}",
            message=f"Goods received note {grn.grn_number} has been recorded against PO {po.po_number}.",
            link=f"/procurement/grns/{grn.pk}/",
        )
