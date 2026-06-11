import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dsr", "0003_dsractivity_ipc_line_item_and_more"),
        ("projects", "0003_workpackage_workpackageprogress"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailysitereport",
            name="work_package",
            field=models.ForeignKey(
                blank=True,
                help_text="Work package this DSR belongs to (subcontractor or Kemele scope).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="dsrs",
                to="projects.workpackage",
            ),
        ),
    ]
