from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.projects.models import Client, Funder, Project

from .models import NCR

User = get_user_model()


class NCRWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="pw",
            first_name="Ada",
            last_name="Admin",
            role=User.ROLE_ADMIN,
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
        self.ncr = NCR.objects.create(
            project=self.project,
            description="Honeycombing in column C3.",
            location="Block A, Grid C3",
            trade_responsible="Concrete subcontractor",
            raised_by=self.admin,
            raised_date=timezone.now().date(),
            corrective_action_required="Break out and recast to spec.",
        )

    def _url(self, name):
        return reverse(
            f"quality:{name}",
            kwargs={"project_pk": self.project.pk, "pk": self.ncr.pk},
        )

    def test_start_review(self):
        self.client.force_login(self.admin)
        response = self.client.post(self._url("ncr-start-review"))
        self.assertEqual(response.status_code, 302)
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.status, NCR.STATUS_UNDER_REVIEW)
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="NCR", object_id=str(self.ncr.pk)
            ).exists()
        )

    def test_close_requires_root_cause_and_corrective_action(self):
        self.client.force_login(self.admin)
        self.client.post(self._url("ncr-close"))
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.status, NCR.STATUS_OPEN)

        self.ncr.root_cause = "Poor vibration during pour."
        self.ncr.corrective_action = "Column broken out and recast; cube tests passed."
        self.ncr.save(update_fields=["root_cause", "corrective_action"])
        self.client.post(self._url("ncr-close"))
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.status, NCR.STATUS_CLOSED)
        self.assertIsNotNone(self.ncr.close_out_date)

    def test_closed_ncr_cannot_be_reopened_via_review(self):
        self.ncr.status = NCR.STATUS_CLOSED
        self.ncr.save(update_fields=["status"])
        self.client.force_login(self.admin)
        self.client.post(self._url("ncr-start-review"))
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.status, NCR.STATUS_CLOSED)
