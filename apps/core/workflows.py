from django.core.exceptions import ValidationError

from apps.core.models import AuditLog


WORKFLOW_TRANSITIONS = {
    "dsr": {
        "DRAFT": {"SUBMITTED"},
        "SUBMITTED": {"APPROVED", "RETURNED"},
        "RETURNED": {"DRAFT", "SUBMITTED"},
        "APPROVED": set(),
    },
    "mr": {
        "DRAFT": {"SUBMITTED"},
        "SUBMITTED": {"APPROVED", "REJECTED"},
        "APPROVED": {"ORDERED", "CLOSED"},
        "ORDERED": {"DELIVERED", "CLOSED"},
        "DELIVERED": {"CLOSED"},
        "REJECTED": set(),
        "CLOSED": set(),
    },
    "po": {
        "DRAFT": {"PENDING_APPROVAL"},
        "PENDING_APPROVAL": {"APPROVED", "CANCELLED"},
        "APPROVED": {"SENT", "CANCELLED"},
        "SENT": {"PARTIALLY_DELIVERED", "DELIVERED", "CANCELLED"},
        "PARTIALLY_DELIVERED": {"DELIVERED", "CANCELLED"},
        "DELIVERED": set(),
        "CANCELLED": set(),
    },
    "ipc": {
        "DRAFT": {"INTERNAL_REVIEW", "SUBMITTED"},
        "INTERNAL_REVIEW": {"DRAFT", "SUBMITTED"},
        "SUBMITTED": {"CERTIFIED", "DISPUTED"},
        "CERTIFIED": {"PAID", "DISPUTED"},
        "DISPUTED": {"CERTIFIED", "PAID"},
        "PAID": set(),
    },
    "variation": {
        "INSTRUCTED": {"SUBMITTED", "REJECTED"},
        "SUBMITTED": {"ASSESSED", "REJECTED"},
        "ASSESSED": {"APPROVED", "REJECTED"},
        "APPROVED": set(),
        "REJECTED": set(),
    },
    "rfi": {
        "OPEN": {"RESPONDED"},
        "RESPONDED": {"CLOSED", "OPEN"},
        "CLOSED": set(),
    },
    "submittal": {
        "SUBMITTED": {"APPROVED", "APPROVED_AS_NOTED", "REVISE_RESUBMIT", "REJECTED"},
        "REVISE_RESUBMIT": {"SUBMITTED"},
        "APPROVED": set(),
        "APPROVED_AS_NOTED": set(),
        "REJECTED": set(),
    },
    "incident": {
        "OPEN": {"UNDER_INVESTIGATION", "CLOSED"},
        "UNDER_INVESTIGATION": {"CLOSED", "OPEN"},
        "CLOSED": set(),
    },
    "ncr": {
        "OPEN": {"UNDER_REVIEW", "CLOSED"},
        "UNDER_REVIEW": {"CLOSED", "OPEN"},
        "CLOSED": set(),
    },
    "defect": {
        "OPEN": {"IN_PROGRESS", "RECTIFIED"},
        "IN_PROGRESS": {"RECTIFIED"},
        "RECTIFIED": {"CLOSED"},
        "CLOSED": set(),
    },
}


def assert_transition(workflow_key, current_status, next_status):
    allowed = WORKFLOW_TRANSITIONS.get(workflow_key, {}).get(current_status)
    if allowed is None:
        raise ValidationError(f"Unknown workflow status: {workflow_key}.{current_status}")
    if next_status not in allowed:
        raise ValidationError(f"Cannot move {workflow_key} from {current_status} to {next_status}.")


def transition(instance, workflow_key, next_status, *, user=None, request=None, save=True):
    current_status = instance.status
    assert_transition(workflow_key, current_status, next_status)
    instance.status = next_status
    if user is not None and hasattr(instance, "updated_by"):
        instance.updated_by = user
    if save:
        update_fields = ["status"]
        if user is not None and hasattr(instance, "updated_by"):
            update_fields.append("updated_by")
        update_fields.append("updated_at")
        instance.save(update_fields=update_fields)
    if user is not None:
        AuditLog.log(
            user,
            AuditLog.ACTION_UPDATE,
            instance,
            changes=f"{workflow_key} status changed from {current_status} to {next_status}.",
            request=request,
        )
    return instance
