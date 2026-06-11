import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("budget", "0004_subcontract_user_subcontractordocument"),
        ("projects", "0002_projectmembership"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkPackage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(help_text="e.g. 'Duplexes 1–30 (Kemele)'", max_length=255)),
                ("contractor_type", models.CharField(
                    choices=[("principal", "Kemele Construction (Principal)"), ("subcontractor", "Subcontractor")],
                    default="principal",
                    max_length=20,
                )),
                ("description", models.TextField(blank=True)),
                ("scope_quantity", models.DecimalField(blank=True, decimal_places=2, help_text="Quantity of deliverable units (e.g. 30 duplexes).", max_digits=10, null=True)),
                ("scope_unit", models.CharField(blank=True, help_text="Unit of scope (e.g. duplexes, km, m²).", max_length=50)),
                ("contract_value", models.DecimalField(decimal_places=2, default=0, help_text="Value of this work package for weighting purposes.", max_digits=14)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("current_progress_pct", models.DecimalField(decimal_places=2, default=0, help_text="Latest reported progress % (auto-updated from progress entries).", max_digits=5)),
                ("is_active", models.BooleanField(default=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_packages", to="projects.project")),
                ("subcontract", models.OneToOneField(
                    blank=True,
                    help_text="Leave blank for Kemele's own work package.",
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="work_package",
                    to="budget.subcontract",
                )),
            ],
            options={
                "verbose_name": "Work Package",
                "verbose_name_plural": "Work Packages",
                "ordering": ["contractor_type", "name"],
            },
        ),
        migrations.CreateModel(
            name="WorkPackageProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("date", models.DateField()),
                ("percent_complete", models.DecimalField(decimal_places=2, help_text="Overall % completion of this work package.", max_digits=5)),
                ("narrative", models.TextField(blank=True, help_text="What was achieved in this period.")),
                ("recorded_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="work_package_progress_entries",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("work_package", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="progress_entries",
                    to="projects.workpackage",
                )),
            ],
            options={
                "verbose_name": "Work Package Progress Entry",
                "verbose_name_plural": "Work Package Progress Entries",
                "ordering": ["-date"],
                "unique_together": {("work_package", "date")},
            },
        ),
    ]
