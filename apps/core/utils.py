import os
import uuid
from django.utils.text import slugify


def upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"
    model_name = instance.__class__.__name__.lower()
    return os.path.join("uploads", model_name, new_name)


def generate_ref(prefix, model_class, field="ref_number"):
    count = model_class.objects.count() + 1
    return f"{prefix}-{count:04d}"
