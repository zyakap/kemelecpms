from .models import Notification


def send_notification(recipient, notification_type, title, message, link=""):
    Notification.objects.create(
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
