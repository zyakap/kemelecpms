import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

app = Celery("kemelecpms")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    # Daily at 7am Port Moresby time — compliance reminders
    "daily-compliance-reminders": {
        "task": "apps.notifications.tasks.send_overdue_compliance_reminders",
        "schedule": crontab(hour=7, minute=0),
    },
}
