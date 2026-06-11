from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# DocumentControlSettings
# ---------------------------------------------------------------------------


class DocumentControlSettings(TimeStampedModel):
    """Configurable document-control policy.

    One company-wide record (``project=None``) holds the defaults; a project
    may carry its own override record. Use
    :func:`apps.documents.services.get_document_settings` to resolve the
    effective settings for any project.
    """

    CONFIDENTIALITY_PUBLIC = "PUBLIC"
    CONFIDENTIALITY_INTERNAL = "INTERNAL"
    CONFIDENTIALITY_CONFIDENTIAL = "CONFIDENTIAL"
    CONFIDENTIALITY_CHOICES = [
        (CONFIDENTIALITY_PUBLIC, "Public"),
        (CONFIDENTIALITY_INTERNAL, "Internal"),
        (CONFIDENTIALITY_CONFIDENTIAL, "Confidential"),
    ]

    project = models.OneToOneField(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="document_control_settings",
        help_text="Leave blank for the company-wide default settings.",
    )

    # Reference numbering
    rfi_prefix = models.CharField(max_length=10, default="RFI")
    submittal_prefix = models.CharField(max_length=10, default="SUB")
    correspondence_prefix = models.CharField(max_length=10, default="CORR")
    transmittal_prefix = models.CharField(max_length=10, default="TRN")
    document_prefix = models.CharField(max_length=10, default="DOC")
    number_padding = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(2), MaxValueValidator(8)],
        help_text="Digits in the numeric part of references, e.g. 4 → RFI-0001.",
    )
    include_project_code = models.BooleanField(
        default=False,
        help_text="Include the project code in references, e.g. RFI-KC001-0001.",
    )

    # Review / response policy
    rfi_response_due_days = models.PositiveSmallIntegerField(
        default=7, help_text="Days before an unanswered RFI is flagged overdue."
    )
    submittal_review_due_days = models.PositiveSmallIntegerField(
        default=14, help_text="Days before an unreviewed submittal is flagged overdue."
    )
    correspondence_action_due_days = models.PositiveSmallIntegerField(
        default=7,
        help_text="Default days allowed for correspondence requiring action.",
    )

    # Controlled document workflow
    require_document_approval = models.BooleanField(
        default=True,
        help_text="New controlled documents and revisions must pass review before issue.",
    )
    require_transmittal_acknowledgement = models.BooleanField(
        default=True,
        help_text="Sent transmittals must be acknowledged by the recipient.",
    )
    auto_supersede_on_new_revision = models.BooleanField(
        default=True,
        help_text="Uploading a new revision automatically supersedes the previous one.",
    )

    # Upload policy
    allowed_file_extensions = models.CharField(
        max_length=255,
        default="pdf,doc,docx,xls,xlsx,csv,dwg,dxf,jpg,jpeg,png,zip",
        help_text="Comma-separated list of permitted file extensions.",
    )
    max_upload_size_mb = models.PositiveSmallIntegerField(
        default=50, help_text="Maximum upload size in megabytes."
    )
    default_confidentiality = models.CharField(
        max_length=15,
        choices=CONFIDENTIALITY_CHOICES,
        default=CONFIDENTIALITY_INTERNAL,
    )
    log_document_access = models.BooleanField(
        default=True,
        help_text="Record an access log entry each time a controlled document is downloaded.",
    )

    class Meta:
        verbose_name = "Document Control Settings"
        verbose_name_plural = "Document Control Settings"

    def __str__(self):
        scope = self.project.project_id if self.project else "Company default"
        return f"Document control settings ({scope})"

    @property
    def allowed_extension_list(self):
        return {
            ext.strip().lower().lstrip(".")
            for ext in self.allowed_file_extensions.split(",")
            if ext.strip()
        }

    def get_absolute_url(self):
        if self.project_id:
            return reverse(
                "documents:project-settings", kwargs={"project_pk": self.project_id}
            )
        return reverse("documents:company-settings")


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


class Drawing(TimeStampedModel):
    DISCIPLINE_ARCHITECTURAL = "ARCHITECTURAL"
    DISCIPLINE_STRUCTURAL = "STRUCTURAL"
    DISCIPLINE_CIVIL = "CIVIL"
    DISCIPLINE_ELECTRICAL = "ELECTRICAL"
    DISCIPLINE_MECHANICAL = "MECHANICAL"
    DISCIPLINE_PLUMBING = "PLUMBING"
    DISCIPLINE_OTHER = "OTHER"

    DISCIPLINE_CHOICES = [
        (DISCIPLINE_ARCHITECTURAL, "Architectural"),
        (DISCIPLINE_STRUCTURAL, "Structural"),
        (DISCIPLINE_CIVIL, "Civil"),
        (DISCIPLINE_ELECTRICAL, "Electrical"),
        (DISCIPLINE_MECHANICAL, "Mechanical"),
        (DISCIPLINE_PLUMBING, "Plumbing / Hydraulics"),
        (DISCIPLINE_OTHER, "Other"),
    ]

    STATUS_IFC = "IFC"
    STATUS_FOR_REVIEW = "FOR_REVIEW"
    STATUS_SUPERSEDED = "SUPERSEDED"
    STATUS_FOR_INFO = "FOR_INFO"

    STATUS_CHOICES = [
        (STATUS_IFC, "Issued for Construction"),
        (STATUS_FOR_REVIEW, "Issued for Review"),
        (STATUS_SUPERSEDED, "Superseded"),
        (STATUS_FOR_INFO, "Issued for Information"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="drawings",
    )
    drawing_number = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    discipline = models.CharField(
        max_length=20,
        choices=DISCIPLINE_CHOICES,
        default=DISCIPLINE_OTHER,
    )
    scale = models.CharField(max_length=50, blank=True)
    current_revision = models.CharField(
        max_length=10,
        help_text='Current revision identifier, e.g. "A", "B", "C0".',
    )
    current_revision_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_FOR_REVIEW,
    )
    file = models.FileField(upload_to="drawings/")
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Drawing"
        verbose_name_plural = "Drawings"
        ordering = ["project", "discipline", "drawing_number"]
        unique_together = [("project", "drawing_number")]

    def __str__(self):
        return f"{self.drawing_number} Rev {self.current_revision} – {self.title}"

    def get_absolute_url(self):
        return reverse(
            "documents:drawing-detail",
            kwargs={"project_pk": self.project_id, "pk": self.pk},
        )


# ---------------------------------------------------------------------------
# DrawingRevision
# ---------------------------------------------------------------------------


class DrawingRevision(TimeStampedModel):
    drawing = models.ForeignKey(
        Drawing,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision = models.CharField(max_length=10)
    date = models.DateField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_drawing_revisions",
    )
    file = models.FileField(upload_to="drawings/revisions/")
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Drawing Revision"
        verbose_name_plural = "Drawing Revisions"
        ordering = ["drawing", "-date"]
        unique_together = [("drawing", "revision")]

    def __str__(self):
        return f"{self.drawing.drawing_number} Rev {self.revision} ({self.date})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep the parent drawing's current revision in sync
        Drawing.objects.filter(pk=self.drawing_id).update(
            current_revision=self.revision,
            current_revision_date=self.date,
            file=self.file,
        )


# ---------------------------------------------------------------------------
# RFI – Request for Information
# ---------------------------------------------------------------------------


class RFI(TimeStampedModel):
    STATUS_OPEN = "OPEN"
    STATUS_RESPONDED = "RESPONDED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_RESPONDED, "Responded"),
        (STATUS_CLOSED, "Closed"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="rfis",
    )
    rfi_number = models.CharField(max_length=20, editable=False, db_index=True)
    date_raised = models.DateField()
    subject = models.CharField(max_length=255)
    question = models.TextField()
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="raised_rfis",
    )
    directed_to = models.CharField(max_length=200)
    drawing = models.ForeignKey(
        Drawing,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rfis",
    )
    photo = models.FileField(
        upload_to="rfi_attachments/",
        null=True,
        blank=True,
    )
    response = models.TextField(blank=True)
    response_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    schedule_impact_days = models.IntegerField(
        default=0,
        verbose_name="Schedule Impact (days)",
    )
    cost_impact = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Cost Impact (PGK)",
    )

    class Meta:
        verbose_name = "RFI"
        verbose_name_plural = "RFIs"
        ordering = ["project", "-date_raised"]
        unique_together = [("project", "rfi_number")]

    def __str__(self):
        return f"{self.rfi_number} – {self.subject}"

    def save(self, *args, **kwargs):
        if not self.rfi_number:
            from .services import get_document_settings, next_number

            doc_settings = get_document_settings(self.project)
            self.rfi_number = next_number(
                self.project,
                doc_settings.rfi_prefix,
                RFI.objects.filter(project=self.project),
                "rfi_number",
                settings=doc_settings,
            )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "documents:rfi-detail",
            kwargs={"project_pk": self.project_id, "pk": self.pk},
        )

    @property
    def is_overdue(self):
        """True if open (no response) past the configured response window."""
        if self.status != self.STATUS_OPEN:
            return False
        import datetime

        from django.utils import timezone

        from .services import get_document_settings

        due_days = get_document_settings(self.project).rfi_response_due_days
        return (timezone.now().date() - self.date_raised) > datetime.timedelta(days=due_days)


# ---------------------------------------------------------------------------
# Submittal
# ---------------------------------------------------------------------------


class Submittal(TimeStampedModel):
    TYPE_MATERIAL = "MATERIAL"
    TYPE_SHOP_DRAWING = "SHOP_DRAWING"
    TYPE_METHOD_STATEMENT = "METHOD_STATEMENT"
    TYPE_SAMPLE = "SAMPLE"
    TYPE_CERTIFICATE = "CERTIFICATE"

    SUBMITTAL_TYPE_CHOICES = [
        (TYPE_MATERIAL, "Material Submittal"),
        (TYPE_SHOP_DRAWING, "Shop Drawing"),
        (TYPE_METHOD_STATEMENT, "Method Statement"),
        (TYPE_SAMPLE, "Sample"),
        (TYPE_CERTIFICATE, "Certificate"),
    ]

    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_APPROVED_AS_NOTED = "APPROVED_AS_NOTED"
    STATUS_REVISE_RESUBMIT = "REVISE_RESUBMIT"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_APPROVED_AS_NOTED, "Approved As Noted"),
        (STATUS_REVISE_RESUBMIT, "Revise & Resubmit"),
        (STATUS_REJECTED, "Rejected"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="submittals",
    )
    submittal_number = models.CharField(max_length=20, editable=False, db_index=True)
    submittal_type = models.CharField(
        max_length=20,
        choices=SUBMITTAL_TYPE_CHOICES,
        default=TYPE_MATERIAL,
    )
    title = models.CharField(max_length=255)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_submittals",
    )
    submitted_date = models.DateField()
    document = models.FileField(upload_to="submittals/")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
    )
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_submittals",
    )
    reviewed_date = models.DateField(null=True, blank=True)
    revision = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Submittal"
        verbose_name_plural = "Submittals"
        ordering = ["project", "-submitted_date"]
        unique_together = [("project", "submittal_number")]

    def __str__(self):
        return f"{self.submittal_number} Rev{self.revision} – {self.title}"

    def save(self, *args, **kwargs):
        if not self.submittal_number:
            from .services import get_document_settings, next_number

            doc_settings = get_document_settings(self.project)
            self.submittal_number = next_number(
                self.project,
                doc_settings.submittal_prefix,
                Submittal.objects.filter(project=self.project),
                "submittal_number",
                settings=doc_settings,
            )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "documents:submittal-list",
            kwargs={"project_pk": self.project_id},
        )

    @property
    def is_review_overdue(self):
        """True if still awaiting review past the configured review window."""
        if self.status != self.STATUS_SUBMITTED:
            return False
        import datetime

        from django.utils import timezone

        from .services import get_document_settings

        due_days = get_document_settings(self.project).submittal_review_due_days
        return (timezone.now().date() - self.submitted_date) > datetime.timedelta(days=due_days)


# ---------------------------------------------------------------------------
# Correspondence
# ---------------------------------------------------------------------------


class Correspondence(TimeStampedModel):
    DIRECTION_INCOMING = "INCOMING"
    DIRECTION_OUTGOING = "OUTGOING"

    DIRECTION_CHOICES = [
        (DIRECTION_INCOMING, "Incoming"),
        (DIRECTION_OUTGOING, "Outgoing"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="correspondences",
    )
    reference_number = models.CharField(max_length=20, editable=False, db_index=True)
    date = models.DateField()
    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        default=DIRECTION_INCOMING,
    )
    subject = models.CharField(max_length=255)
    sender = models.CharField(max_length=200)
    recipient = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    document = models.FileField(upload_to="correspondence/")
    action_required = models.BooleanField(default=False)
    action_due_date = models.DateField(null=True, blank=True)
    response_date = models.DateField(null=True, blank=True)
    is_responded = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Correspondence"
        verbose_name_plural = "Correspondence"
        ordering = ["project", "-date"]
        unique_together = [("project", "reference_number")]

    def __str__(self):
        return f"{self.reference_number} – {self.subject}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            from .services import get_document_settings, next_number

            doc_settings = get_document_settings(self.project)
            self.reference_number = next_number(
                self.project,
                doc_settings.correspondence_prefix,
                Correspondence.objects.filter(project=self.project),
                "reference_number",
                settings=doc_settings,
            )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "documents:correspondence-list",
            kwargs={"project_pk": self.project_id},
        )

    @property
    def is_action_overdue(self):
        if not self.action_required or self.is_responded or not self.action_due_date:
            return False
        from django.utils import timezone
        return self.action_due_date < timezone.now().date()


# ---------------------------------------------------------------------------
# ProjectDocument
# ---------------------------------------------------------------------------


class ProjectDocument(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_FOR_REVIEW = "FOR_REVIEW"
    STATUS_APPROVED = "APPROVED"
    STATUS_SUPERSEDED = "SUPERSEDED"
    STATUS_ARCHIVED = "ARCHIVED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_FOR_REVIEW, "For Review"),
        (STATUS_APPROVED, "Approved / Issued"),
        (STATUS_SUPERSEDED, "Superseded"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    # Permitted controlled-document status transitions.
    STATUS_TRANSITIONS = {
        STATUS_DRAFT: {STATUS_FOR_REVIEW, STATUS_APPROVED, STATUS_ARCHIVED},
        STATUS_FOR_REVIEW: {STATUS_APPROVED, STATUS_DRAFT, STATUS_ARCHIVED},
        STATUS_APPROVED: {STATUS_SUPERSEDED, STATUS_ARCHIVED},
        STATUS_SUPERSEDED: {STATUS_ARCHIVED},
        STATUS_ARCHIVED: set(),
    }

    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="project_documents",
        help_text="Leave blank for company-wide templates.",
    )
    document_number = models.CharField(
        max_length=40, blank=True, editable=False, db_index=True
    )
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=100)
    file = models.FileField(upload_to="project_docs/")
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_project_documents",
    )
    version = models.CharField(max_length=20, default="1.0")
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    confidentiality = models.CharField(
        max_length=15,
        choices=DocumentControlSettings.CONFIDENTIALITY_CHOICES,
        default=DocumentControlSettings.CONFIDENTIALITY_INTERNAL,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_project_documents",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Project Document"
        verbose_name_plural = "Project Documents"
        ordering = ["-created_at"]

    def __str__(self):
        scope = self.project.project_id if self.project else "Company"
        return f"[{scope}] {self.document_number or '(unnumbered)'} {self.title} v{self.version}"

    def save(self, *args, **kwargs):
        if not self.document_number:
            from .services import get_document_settings, next_number

            doc_settings = get_document_settings(self.project)
            self.document_number = next_number(
                self.project,
                doc_settings.document_prefix,
                ProjectDocument.objects.filter(project=self.project),
                "document_number",
                settings=doc_settings,
            )
        super().save(*args, **kwargs)

    def can_transition_to(self, new_status):
        return new_status in self.STATUS_TRANSITIONS.get(self.status, set())

    @property
    def is_editable(self):
        return self.status in (self.STATUS_DRAFT, self.STATUS_FOR_REVIEW)

    def get_absolute_url(self):
        if self.project:
            return reverse(
                "documents:projectdoc-detail",
                kwargs={"project_pk": self.project_id, "pk": self.pk},
            )
        return reverse("documents:projectdoc-templates")


class ProjectDocumentRevision(TimeStampedModel):
    """A superseding revision of a controlled project document."""

    document = models.ForeignKey(
        ProjectDocument,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    version = models.CharField(max_length=20)
    file = models.FileField(upload_to="project_docs/revisions/")
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_project_document_revisions",
    )

    class Meta:
        verbose_name = "Document Revision"
        verbose_name_plural = "Document Revisions"
        ordering = ["-created_at"]
        unique_together = [("document", "version")]

    def __str__(self):
        return f"{self.document.document_number} v{self.version}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep the parent document in sync with the latest revision.
        from .services import get_document_settings

        doc_settings = get_document_settings(self.document.project)
        update_fields = {"version": self.version, "file": self.file}
        if doc_settings.auto_supersede_on_new_revision:
            update_fields["status"] = (
                ProjectDocument.STATUS_FOR_REVIEW
                if doc_settings.require_document_approval
                else ProjectDocument.STATUS_APPROVED
            )
            update_fields["approved_by"] = None
            update_fields["approved_at"] = None
        ProjectDocument.objects.filter(pk=self.document_id).update(**update_fields)


class DocumentAccessLog(models.Model):
    """Audit trail of controlled-document downloads."""

    ACTION_DOWNLOAD = "DOWNLOAD"
    ACTION_VIEW = "VIEW"
    ACTION_CHOICES = [
        (ACTION_DOWNLOAD, "Download"),
        (ACTION_VIEW, "View"),
    ]

    document = models.ForeignKey(
        ProjectDocument,
        on_delete=models.CASCADE,
        related_name="access_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="document_access_logs",
    )
    action = models.CharField(
        max_length=10, choices=ACTION_CHOICES, default=ACTION_DOWNLOAD
    )
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Document Access Log"
        verbose_name_plural = "Document Access Logs"
        ordering = ["-accessed_at"]

    def __str__(self):
        return f"{self.user} {self.action} {self.document} at {self.accessed_at}"


class DistributionContact(TimeStampedModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="distribution_contacts")
    name = models.CharField(max_length=150)
    organization = models.CharField(max_length=200)
    email = models.EmailField()
    role = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["organization", "name"]
        unique_together = [("project", "email")]

    def __str__(self):
        return f"{self.name} - {self.organization}"

    def get_absolute_url(self):
        return reverse("documents:distribution-contact-list", kwargs={"project_pk": self.project_id})


class DocumentTransmittal(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_SENT = "SENT"
    STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="transmittals")
    transmittal_number = models.CharField(max_length=30, editable=False, db_index=True)
    subject = models.CharField(max_length=255)
    sent_date = models.DateField()
    recipients = models.ManyToManyField(DistributionContact, blank=True, related_name="transmittals")
    drawings = models.ManyToManyField(Drawing, blank=True, related_name="transmittals")
    submittals = models.ManyToManyField(Submittal, blank=True, related_name="transmittals")
    documents = models.ManyToManyField(ProjectDocument, blank=True, related_name="transmittals")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="document_transmittals_sent",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    acknowledged_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-sent_date", "-transmittal_number"]
        unique_together = [("project", "transmittal_number")]

    def __str__(self):
        return f"{self.transmittal_number} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.transmittal_number:
            from .services import get_document_settings, next_number

            doc_settings = get_document_settings(self.project)
            self.transmittal_number = next_number(
                self.project,
                doc_settings.transmittal_prefix,
                DocumentTransmittal.objects.filter(project=self.project),
                "transmittal_number",
                settings=doc_settings,
            )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "documents:transmittal-detail",
            kwargs={"project_pk": self.project_id, "pk": self.pk},
        )
