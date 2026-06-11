import logging
import os
import uuid
from django.db import transaction
from django.utils.text import slugify

logger = logging.getLogger(__name__)


def safe_task_delay(task, *args, **kwargs):
    """
    Dispatch a Celery task, falling back to a synchronous call if the
    broker is unavailable. Never raises — a broker outage must not break
    the calling request.
    """
    try:
        task.delay(*args, **kwargs)
    except Exception:
        try:
            task.run(*args, **kwargs)
        except Exception:
            logger.exception(
                "Failed to dispatch task %s", getattr(task, "name", repr(task))
            )


def queue_task(task, *args, **kwargs):
    """
    Queue a Celery task once the current transaction commits (immediately
    when not inside an atomic block), using safe_task_delay so a broker
    outage degrades to a synchronous call instead of an error.
    """
    transaction.on_commit(lambda: safe_task_delay(task, *args, **kwargs))


def upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"
    model_name = instance.__class__.__name__.lower()
    return os.path.join("uploads", model_name, new_name)


def generate_ref(prefix, model_class, field="ref_number"):
    count = model_class.objects.count() + 1
    return f"{prefix}-{count:04d}"
