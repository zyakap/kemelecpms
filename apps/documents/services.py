"""Document control services: settings resolution, controlled numbering,
and upload validation.

Every numbered register in the documents app (RFIs, submittals,
correspondence, transmittals, controlled documents) derives its reference
format from :class:`~apps.documents.models.DocumentControlSettings`, which
can be configured company-wide and overridden per project.
"""
import os
import re

from django.core.exceptions import ValidationError


def get_document_settings(project=None):
    """Return the effective DocumentControlSettings for a project.

    Falls back to the company-wide record (project=None), creating it with
    defaults on first use.
    """
    from .models import DocumentControlSettings

    if project is not None:
        override = DocumentControlSettings.objects.filter(project=project).first()
        if override:
            return override
    company, _ = DocumentControlSettings.objects.get_or_create(project=None)
    return company


def build_number(project, prefix, sequence, settings=None):
    settings = settings or get_document_settings(project)
    seq = str(sequence).zfill(settings.number_padding)
    if settings.include_project_code and project is not None:
        code = getattr(project, "project_id", None) or project.pk
        return f"{prefix}-{code}-{seq}"
    return f"{prefix}-{seq}"


def next_number(project, prefix, queryset, field, settings=None):
    """Compute the next reference number for a register.

    Scans existing numbers for the highest numeric suffix rather than using
    ``count() + 1`` so deletions can never produce duplicate references.
    """
    settings = settings or get_document_settings(project)
    highest = 0
    for value in queryset.values_list(field, flat=True):
        match = re.search(r"(\d+)$", value or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return build_number(project, prefix, highest + 1, settings=settings)


def validate_upload(uploaded_file, project=None, settings=None):
    """Validate an uploaded file against document control settings."""
    if not uploaded_file:
        return uploaded_file
    settings = settings or get_document_settings(project)

    allowed = settings.allowed_extension_list
    ext = os.path.splitext(uploaded_file.name)[1].lstrip(".").lower()
    if allowed and ext not in allowed:
        raise ValidationError(
            f"File type '.{ext}' is not permitted. Allowed types: "
            f"{', '.join(sorted(allowed))}."
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    size = getattr(uploaded_file, "size", 0) or 0
    if max_bytes and size > max_bytes:
        raise ValidationError(
            f"File is {size / (1024 * 1024):.1f} MB which exceeds the "
            f"{settings.max_upload_size_mb} MB limit set by document control."
        )
    return uploaded_file
