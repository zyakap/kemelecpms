from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


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
            count = RFI.objects.filter(project=self.project).count() + 1
            self.rfi_number = f"RFI-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "documents:rfi-detail",
            kwargs={"project_pk": self.project_id, "pk": self.pk},
        )

    @property
    def is_overdue(self):
        """True if open (no response) and raised more than 7 days ago."""
        if self.status != self.STATUS_OPEN:
            return False
        from django.utils import timezone
        import datetime
        return (timezone.now().date() - self.date_raised) > datetime.timedelta(days=7)


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
            count = Submittal.objects.filter(project=self.project).count() + 1
            self.submittal_number = f"SUB-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "documents:submittal-list",
            kwargs={"project_pk": self.project_id},
        )


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
            count = Correspondence.objects.filter(project=self.project).count() + 1
            self.reference_number = f"CORR-{count:04d}"
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
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="project_documents",
        help_text="Leave blank for company-wide templates.",
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

    class Meta:
        verbose_name = "Project Document"
        verbose_name_plural = "Project Documents"
        ordering = ["-created_at"]

    def __str__(self):
        scope = self.project.project_id if self.project else "Company"
        return f"[{scope}] {self.title} v{self.version}"

    def get_absolute_url(self):
        if self.project:
            return reverse(
                "documents:projectdoc-list",
                kwargs={"project_pk": self.project_id},
            )
        return reverse("documents:projectdoc-templates")


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
        return reverse("documents:distribution-list", kwargs={"project_pk": self.project_id})


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
            count = DocumentTransmittal.objects.filter(project=self.project).count() + 1
            self.transmittal_number = f"TRN-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "documents:transmittal-detail",
            kwargs={"project_pk": self.project_id, "pk": self.pk},
        )
