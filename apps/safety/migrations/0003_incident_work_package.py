import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("safety", "0002_safetyobservation_safetycorrectiveaction_and_more"),
        ("projects", "0003_workpackage_workpackageprogress"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="work_package",
            field=models.ForeignKey(
                blank=True,
                help_text="Work package where this incident occurred.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="incidents",
                to="projects.workpackage",
            ),
        ),
    ]
