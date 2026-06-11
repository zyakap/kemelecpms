from .models import Notification

# Maps a notification category to the UserProfile preference flag that
# controls it. Categories not listed here are always delivered.
CATEGORY_PREFERENCE_FIELDS = {
    "dsr": "notif_dsr",
    "budget": "notif_budget",
    "safety": "notif_safety",
    "milestone": "notif_milestone",
    "ipc": "notif_ipc",
}


def _wants_notification(recipient, category):
    if not category:
        return True
    field = CATEGORY_PREFERENCE_FIELDS.get(category)
    if not field:
        return True
    profile = getattr(recipient, "profile", None)
    if profile is None:
        return True
    return getattr(profile, field, True)


def send_notification(recipient, notification_type, title, message, link="", category=None):
    if not _wants_notification(recipient, category):
        return None
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


def notify_approval_required(approver, title, link):
    send_notification(
        approver,
        Notification.APPROVAL_REQUIRED,
        f"Approval Required: {title}",
        f"Please review and approve: {title}",
        link,
    )


def notify_overdue(user, title, link):
    send_notification(
        user,
        Notification.OVERDUE,
        f"Overdue: {title}",
        f"This item is overdue: {title}",
        link,
    )


def notify_milestone_due(user, milestone_name, link):
    send_notification(
        user,
        Notification.MILESTONE_DUE,
        f"Milestone Due: {milestone_name}",
        f"A milestone is due soon: {milestone_name}",
        link,
    )


def notify_submission(recipient, title, link):
    send_notification(
        recipient,
        Notification.SUBMISSION,
        f"New Submission: {title}",
        f"A new submission requires your attention: {title}",
        link,
    )


def notify_payment(recipient, title, link):
    send_notification(
        recipient,
        Notification.PAYMENT,
        f"Payment Update: {title}",
        f"A payment event has occurred: {title}",
        link,
    )
