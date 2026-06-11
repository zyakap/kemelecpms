import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.projects.models import Client, Funder, Project

from .models import Incident

User = get_user_model()


class IncidentWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="pw",
            first_name="Ada",
            last_name="Admin",
            role=User.ROLE_ADMIN,
        )
        self.supervisor = User.objects.create_user(
            email="super@example.com",
            password="pw",
            first_name="Sam",
            last_name="Supervisor",
            role=User.ROLE_SUPERVISOR,
        )
        png_client = Client.objects.create(
            name="PNG Works", client_type=Client.TYPE_GOVERNMENT
        )
        funder = Funder.objects.create(name="Internal", funder_type=Funder.TYPE_PRIVATE)
        self.project = Project.objects.create(
            name="Health Centre",
            project_type=Project.TYPE_BUILDING,
            status=Project.STATUS_ACTIVE,
            client=png_client,
            funder=funder,
        )
        self.incident = Incident.objects.create(
            project=self.project,
            date=timezone.now().date(),
            time=datetime.time(10, 30),
            location="Block A slab",
            incident_type=Incident.TYPE_FIRST_AID,
            description="Minor cut while stripping formwork.",
            persons_involved="J. Kila (carpenter)",
            reported_by=self.admin,
        )

    def test_start_investigation(self):
        self.client.force_login(self.admin)
        url = reverse("safety:incident_investigate", kwargs={"pk": self.incident.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.STATUS_INVESTIGATING)
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="Incident", object_id=str(self.incident.pk)
            ).exists()
        )

    def test_close_requires_corrective_action(self):
        self.client.force_login(self.admin)
        url = reverse("safety:incident_close", kwargs={"pk": self.incident.pk})
        self.client.post(url)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.STATUS_OPEN)

        self.incident.corrective_action = "Toolbox talk delivered; gloves mandated."
        self.incident.save(update_fields=["corrective_action"])
        self.client.post(url)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.STATUS_CLOSED)
        self.assertIsNotNone(self.incident.corrective_action_closed)

    def test_closed_incident_cannot_be_reinvestigated(self):
        self.incident.status = Incident.STATUS_CLOSED
        self.incident.save(update_fields=["status"])
        self.client.force_login(self.admin)
        url = reverse("safety:incident_investigate", kwargs={"pk": self.incident.pk})
        self.client.post(url)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.STATUS_CLOSED)
