import datetime

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import Client, Funder, Project

from .forms import ProjectDocumentForm
from .models import (
    DocumentAccessLog,
    DocumentControlSettings,
    DocumentTransmittal,
    ProjectDocument,
    RFI,
)
from .services import get_document_settings, next_number

User = get_user_model()


def make_pdf(name="test.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


class DocumentControlTestCase(TestCase):
    def setUp(self):
        self.doc_ctrl = User.objects.create_user(
            email="dc@example.com",
            password="pw",
            first_name="Dora",
            last_name="Controller",
            role=User.ROLE_DOC_CTRL,
        )
        self.supervisor = User.objects.create_user(
            email="super@example.com",
            password="pw",
            first_name="Sam",
            last_name="Supervisor",
            role=User.ROLE_SUPERVISOR,
        )
        self.png_client = Client.objects.create(
            name="PNG Works", client_type=Client.TYPE_GOVERNMENT
        )
        self.funder = Funder.objects.create(
            name="Internal", funder_type=Funder.TYPE_PRIVATE
        )
        self.project = Project.objects.create(
            name="Health Centre",
            project_type=Project.TYPE_BUILDING,
            status=Project.STATUS_ACTIVE,
            client=self.png_client,
            funder=self.funder,
            site_supervisor=self.supervisor,
        )


class SettingsResolutionTests(DocumentControlTestCase):
    def test_company_settings_created_on_first_use(self):
        settings = get_document_settings(self.project)
        self.assertIsNone(settings.project)
        self.assertEqual(settings.rfi_prefix, "RFI")

    def test_project_override_wins(self):
        DocumentControlSettings.objects.create(
            project=self.project, rfi_prefix="REQ", number_padding=5
        )
        settings = get_document_settings(self.project)
        self.assertEqual(settings.rfi_prefix, "REQ")
        self.assertEqual(settings.number_padding, 5)


class NumberingTests(DocumentControlTestCase):
    def _make_rfi(self, **extra):
        fields = {
            "project": self.project,
            "date_raised": timezone.now().date(),
            "subject": "Clarify detail",
            "question": "What is the cover to reinforcement?",
            "raised_by": self.doc_ctrl,
            "directed_to": "Architect",
        }
        fields.update(extra)
        return RFI.objects.create(**fields)

    def test_rfi_numbering_uses_settings_prefix_and_padding(self):
        DocumentControlSettings.objects.create(
            project=self.project, rfi_prefix="REQ", number_padding=6
        )
        rfi = self._make_rfi()
        self.assertEqual(rfi.rfi_number, "REQ-000001")

    def test_numbering_includes_project_code_when_configured(self):
        DocumentControlSettings.objects.create(
            project=self.project, include_project_code=True
        )
        rfi = self._make_rfi()
        self.assertEqual(rfi.rfi_number, f"RFI-{self.project.project_id}-0001")

    def test_deleting_a_record_does_not_reuse_its_number(self):
        first = self._make_rfi()
        second = self._make_rfi(subject="Second")
        self.assertEqual(second.rfi_number, "RFI-0002")
        first.delete()
        third = self._make_rfi(subject="Third")
        self.assertEqual(third.rfi_number, "RFI-0003")

    def test_next_number_helper(self):
        settings = get_document_settings(self.project)
        number = next_number(
            self.project, "DOC", ProjectDocument.objects.none(), "document_number",
            settings=settings,
        )
        self.assertEqual(number, "DOC-0001")


class RFIOverdueTests(DocumentControlTestCase):
    def test_overdue_uses_configured_window(self):
        DocumentControlSettings.objects.create(
            project=self.project, rfi_response_due_days=3
        )
        rfi = RFI.objects.create(
            project=self.project,
            date_raised=timezone.now().date() - datetime.timedelta(days=5),
            subject="Old question",
            question="?",
            raised_by=self.doc_ctrl,
            directed_to="Engineer",
        )
        self.assertTrue(rfi.is_overdue)
        DocumentControlSettings.objects.filter(project=self.project).update(
            rfi_response_due_days=10
        )
        self.assertFalse(rfi.is_overdue)


class UploadPolicyTests(DocumentControlTestCase):
    def test_disallowed_extension_rejected(self):
        DocumentControlSettings.objects.create(
            project=self.project, allowed_file_extensions="pdf"
        )
        form = ProjectDocumentForm(
            data={
                "title": "Method statement",
                "document_type": "Method Statement",
                "version": "1.0",
                "confidentiality": "INTERNAL",
            },
            files={
                "file": SimpleUploadedFile(
                    "macro.exe", b"MZ", content_type="application/octet-stream"
                )
            },
            project=self.project,
            user=self.doc_ctrl,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_oversize_upload_rejected(self):
        DocumentControlSettings.objects.create(
            project=self.project, max_upload_size_mb=1
        )
        big = SimpleUploadedFile(
            "big.pdf", b"0" * (1024 * 1024 + 1), content_type="application/pdf"
        )
        form = ProjectDocumentForm(
            data={
                "title": "Big drawing set",
                "document_type": "Drawings",
                "version": "1.0",
                "confidentiality": "INTERNAL",
            },
            files={"file": big},
            project=self.project,
            user=self.doc_ctrl,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)


class DocumentWorkflowTests(DocumentControlTestCase):
    def _make_document(self, status=ProjectDocument.STATUS_DRAFT):
        doc = ProjectDocument(
            project=self.project,
            title="QA Plan",
            document_type="Plan",
            uploaded_by=self.doc_ctrl,
            status=status,
        )
        doc.file.save("qa-plan.pdf", make_pdf(), save=True)
        return doc

    def test_document_gets_register_number(self):
        doc = self._make_document()
        self.assertEqual(doc.document_number, "DOC-0001")

    def test_approve_transition_sets_approver(self):
        doc = self._make_document()
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:projectdoc-action",
            kwargs={"project_pk": self.project.pk, "pk": doc.pk, "action": "approve"},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.status, ProjectDocument.STATUS_APPROVED)
        self.assertEqual(doc.approved_by, self.doc_ctrl)
        self.assertIsNotNone(doc.approved_at)

    def test_invalid_transition_rejected(self):
        doc = self._make_document(status=ProjectDocument.STATUS_ARCHIVED)
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:projectdoc-action",
            kwargs={"project_pk": self.project.pk, "pk": doc.pk, "action": "approve"},
        )
        self.client.post(url)
        doc.refresh_from_db()
        self.assertEqual(doc.status, ProjectDocument.STATUS_ARCHIVED)

    def test_supervisor_cannot_approve(self):
        doc = self._make_document()
        self.client.force_login(self.supervisor)
        url = reverse(
            "documents:projectdoc-action",
            kwargs={"project_pk": self.project.pk, "pk": doc.pk, "action": "approve"},
        )
        self.client.post(url)
        doc.refresh_from_db()
        self.assertEqual(doc.status, ProjectDocument.STATUS_DRAFT)

    def test_download_creates_access_log(self):
        doc = self._make_document()
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:projectdoc-download",
            kwargs={"project_pk": self.project.pk, "pk": doc.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            DocumentAccessLog.objects.filter(document=doc, user=self.doc_ctrl).count(),
            1,
        )

    def test_download_log_disabled_by_settings(self):
        DocumentControlSettings.objects.create(
            project=self.project, log_document_access=False
        )
        doc = self._make_document()
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:projectdoc-download",
            kwargs={"project_pk": self.project.pk, "pk": doc.pk},
        )
        self.client.get(url)
        self.assertEqual(DocumentAccessLog.objects.filter(document=doc).count(), 0)


class TransmittalAcknowledgeTests(DocumentControlTestCase):
    def test_sent_transmittal_can_be_acknowledged(self):
        transmittal = DocumentTransmittal.objects.create(
            project=self.project,
            subject="IFC issue",
            sent_date=timezone.now().date(),
            status=DocumentTransmittal.STATUS_SENT,
            sent_by=self.doc_ctrl,
        )
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:transmittal-acknowledge",
            kwargs={"project_pk": self.project.pk, "pk": transmittal.pk},
        )
        self.client.post(url)
        transmittal.refresh_from_db()
        self.assertEqual(transmittal.status, DocumentTransmittal.STATUS_ACKNOWLEDGED)
        self.assertIsNotNone(transmittal.acknowledged_date)

    def test_draft_transmittal_cannot_be_acknowledged(self):
        transmittal = DocumentTransmittal.objects.create(
            project=self.project,
            subject="Draft pack",
            sent_date=timezone.now().date(),
            status=DocumentTransmittal.STATUS_DRAFT,
        )
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:transmittal-acknowledge",
            kwargs={"project_pk": self.project.pk, "pk": transmittal.pk},
        )
        self.client.post(url)
        transmittal.refresh_from_db()
        self.assertEqual(transmittal.status, DocumentTransmittal.STATUS_DRAFT)


class SettingsViewPermissionTests(DocumentControlTestCase):
    def test_doc_controller_can_open_company_settings(self):
        self.client.force_login(self.doc_ctrl)
        response = self.client.get(reverse("documents:company-settings"))
        self.assertEqual(response.status_code, 200)

    def test_supervisor_cannot_open_company_settings(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("documents:company-settings"))
        self.assertEqual(response.status_code, 403)

    def test_project_settings_save_creates_override(self):
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:project-settings", kwargs={"project_pk": self.project.pk}
        )
        company = get_document_settings(None)
        response = self.client.post(
            url,
            data={
                "rfi_prefix": "REQ",
                "submittal_prefix": company.submittal_prefix,
                "correspondence_prefix": company.correspondence_prefix,
                "transmittal_prefix": company.transmittal_prefix,
                "document_prefix": company.document_prefix,
                "number_padding": company.number_padding,
                "rfi_response_due_days": company.rfi_response_due_days,
                "submittal_review_due_days": company.submittal_review_due_days,
                "correspondence_action_due_days": company.correspondence_action_due_days,
                "require_document_approval": "on",
                "require_transmittal_acknowledgement": "on",
                "auto_supersede_on_new_revision": "on",
                "allowed_file_extensions": company.allowed_file_extensions,
                "max_upload_size_mb": company.max_upload_size_mb,
                "default_confidentiality": company.default_confidentiality,
                "log_document_access": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            get_document_settings(self.project).rfi_prefix, "REQ"
        )

    def test_reset_removes_override(self):
        DocumentControlSettings.objects.create(project=self.project, rfi_prefix="REQ")
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:project-settings-reset",
            kwargs={"project_pk": self.project.pk},
        )
        self.client.post(url)
        self.assertFalse(
            DocumentControlSettings.objects.filter(project=self.project).exists()
        )
        self.assertEqual(get_document_settings(self.project).rfi_prefix, "RFI")


class RevisionWorkflowTests(DocumentControlTestCase):
    def test_new_revision_supersedes_and_requires_review(self):
        doc = ProjectDocument(
            project=self.project,
            title="QA Plan",
            document_type="Plan",
            uploaded_by=self.doc_ctrl,
            status=ProjectDocument.STATUS_APPROVED,
        )
        doc.file.save("qa-plan.pdf", make_pdf(), save=True)
        self.client.force_login(self.doc_ctrl)
        url = reverse(
            "documents:projectdoc-revision-create",
            kwargs={"project_pk": self.project.pk, "pk": doc.pk},
        )
        response = self.client.post(
            url,
            data={"version": "2.0", "notes": "Updated scope", "file": make_pdf("v2.pdf")},
        )
        self.assertEqual(response.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.version, "2.0")
        self.assertEqual(doc.status, ProjectDocument.STATUS_FOR_REVIEW)
        self.assertIsNone(doc.approved_by)
