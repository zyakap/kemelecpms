"""
Celery tasks for notification dispatch.
"""

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email(self, recipient_email, subject, body):
    """Send an email notification. Retries up to 3 times on failure."""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def create_notification(user_id, notification_type, title, message, link=""):
    """Create an in-app notification for a user."""
    from apps.notifications.models import Notification
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        notif = Notification.objects.create(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
        )
        # Also send email if user has email notifications enabled
        if user.email:
            send_notification_email.delay(
                recipient_email=user.email,
                subject=f"[Kemele CPMS] {title}",
                body=f"{message}\n\nView: {settings.SITE_URL}{link}" if link else message,
            )
        return notif.pk
    except User.DoesNotExist:
        return None


@shared_task
def notify_users(user_ids, notification_type, title, message, link=""):
    """Dispatch notifications to multiple users."""
    for user_id in user_ids:
        create_notification.delay(user_id, notification_type, title, message, link)


@shared_task
def send_overdue_compliance_reminders():
    """Daily task: remind responsible persons about upcoming/overdue compliance items."""
    from django.utils import timezone
    from apps.compliance.models import ComplianceCalendarEntry

    today = timezone.now().date()

    # Find entries due within reminder_days
    entries = ComplianceCalendarEntry.objects.filter(
        status=ComplianceCalendarEntry.STATUS_PENDING,
        responsible__isnull=False,
    ).select_related("responsible")

    for entry in entries:
        days_until_due = (entry.due_date - today).days
        if 0 <= days_until_due <= entry.reminder_days:
            create_notification.delay(
                user_id=entry.responsible_id,
                notification_type="REMINDER",
                title=f"Compliance Due: {entry.title}",
                message=(
                    f"Compliance item '{entry.title}' is due on {entry.due_date}. "
                    f"{'Today!' if days_until_due == 0 else f'{days_until_due} day(s) remaining.'}"
                ),
                link=f"/compliance/calendar/{entry.pk}/",
            )
        elif days_until_due < 0:
            # Auto-mark overdue
            entry.status = ComplianceCalendarEntry.STATUS_OVERDUE
            entry.save(update_fields=["status"])
            create_notification.delay(
                user_id=entry.responsible_id,
                notification_type="ALERT",
                title=f"OVERDUE: {entry.title}",
                message=f"Compliance item '{entry.title}' was due on {entry.due_date} and is now overdue.",
                link=f"/compliance/calendar/{entry.pk}/",
            )


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def send_sms_notification(self, mobile_number, message):
    """
    Send an SMS notification via a configured HTTP gateway.

    Set SMS_GATEWAY_URL, SMS_API_KEY, and SMS_FROM_NUMBER in settings/env
    to enable. Compatible with Digicel PNG Business SMS API and most
    generic HTTP SMS gateways.
    """
    import requests as req

    gateway_url = getattr(settings, "SMS_GATEWAY_URL", "")
    api_key = getattr(settings, "SMS_API_KEY", "")
    if not gateway_url or not api_key:
        return  # SMS not configured — skip silently

    from_number = getattr(settings, "SMS_FROM_NUMBER", "KEMELE")
    try:
        resp = req.post(
            gateway_url,
            json={
                "to": mobile_number,
                "from": from_number,
                "message": message,
                "api_key": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def sms_notify_users(user_ids, message):
    """Send an SMS to a list of user IDs (uses their phone field)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    for user in User.objects.filter(pk__in=user_ids).exclude(phone=""):
        send_sms_notification.delay(user.phone, message)
