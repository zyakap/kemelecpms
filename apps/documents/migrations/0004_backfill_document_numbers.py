"""Backfill document numbers and status for pre-existing project documents.

Documents created before the controlled-document workflow existed are
treated as already issued: they get a register number and APPROVED status.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    ProjectDocument = apps.get_model("documents", "ProjectDocument")

    by_scope = {}
    for doc in ProjectDocument.objects.order_by("created_at", "pk"):
        seq = by_scope.get(doc.project_id, 0) + 1
        by_scope[doc.project_id] = seq
        updates = []
        if not doc.document_number:
            doc.document_number = f"DOC-{seq:04d}"
            updates.append("document_number")
        if doc.status == "DRAFT":
            doc.status = "APPROVED"
            updates.append("status")
        if updates:
            doc.save(update_fields=updates)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_projectdocument_approved_at_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
