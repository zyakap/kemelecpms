from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.template.loader import get_template
from django.test import TestCase

from apps.core.permissions import accessible_projects, can_approve_financial_action
from apps.core.serializers import DSRDetailSerializer, ProjectListSerializer
from apps.core.workflows import assert_transition
from apps.accounts.models import UserProfile
from apps.projects.models import Client, Funder, Project, ProjectMembership


class CriticalSmokeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.pm = User.objects.create_user(
            email="pm@example.com",
            password="pw",
            first_name="Pat",
            last_name="Manager",
            role=User.ROLE_PM,
        )
        self.finance = User.objects.create_user(
            email="finance@example.com",
            password="pw",
            first_name="Fran",
            last_name="Finance",
            role=User.ROLE_FINANCE,
        )
        UserProfile.objects.create(user=self.finance, financial_approval_threshold=Decimal("1000.00"))
        self.client = Client.objects.create(name="PNG Works", client_type=Client.TYPE_GOVERNMENT)
        self.funder = Funder.objects.create(name="Internal", funder_type=Funder.TYPE_PRIVATE)
        self.project = Project.objects.create(
            name="Hospital Maintenance",
            project_type=Project.TYPE_BUILDING,
            status=Project.STATUS_ACTIVE,
            client=self.client,
            funder=self.funder,
            project_manager=self.pm,
        )

    def test_critical_serializers_expose_expected_fields(self):
        self.assertIn("contract_value", ProjectListSerializer.Meta.fields)
        self.assertIn("activities", DSRDetailSerializer.Meta.fields)
        self.assertIn("photos", DSRDetailSerializer.Meta.fields)

    def test_high_risk_templates_load(self):
        for template_name in [
            "projects/project_detail.html",
            "dsr/dsr_detail.html",
            "procurement/grn_detail.html",
            "procurement/invoice_list.html",
            "ipc/ipc_detail.html",
            "documents/latest_ifc_list.html",
            "safety/safety_dashboard.html",
            "maintenance/dashboard.html",
        ]:
            self.assertIsNotNone(get_template(template_name))

    def test_project_membership_grants_object_access(self):
        ProjectMembership.objects.create(
            project=self.project,
            user=self.finance,
            role=ProjectMembership.ROLE_FINANCE,
            can_edit=True,
        )
        self.assertTrue(accessible_projects(self.finance).filter(pk=self.project.pk).exists())

    def test_financial_threshold_blocks_excess_amount(self):
        self.assertTrue(can_approve_financial_action(self.finance, self.project, Decimal("999.99")))
        self.assertFalse(can_approve_financial_action(self.finance, self.project, Decimal("1000.01")))

    def test_workflow_transition_guard_rejects_invalid_move(self):
        assert_transition("ipc", "SUBMITTED", "CERTIFIED")
        with self.assertRaises(ValidationError):
            assert_transition("ipc", "DRAFT", "PAID")
