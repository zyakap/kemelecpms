from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# ITP – Inspection and Test Plan
# ---------------------------------------------------------------------------


class ITP(TimeStampedModel):
    STATUS_NOT_STARTED = "NOT_STARTED"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETE = "COMPLETE"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, "Not Started"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETE, "Complete"),
        (STATUS_CLOSED, "Closed"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="itps",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    trade_section = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_STARTED,
    )

    class Meta:
        verbose_name = "ITP"
        verbose_name_plural = "ITPs"
        ordering = ["project", "title"]

    def __str__(self):
        return f"{self.project.project_id} – {self.title}"

    def get_absolute_url(self):
        return reverse("quality:itp-detail", kwargs={"pk": self.pk})

    @property
    def total_items(self):
        return self.items.count()

    @property
    def passed_items(self):
        return self.items.filter(status=ITPItem.STATUS_PASSED).count()

    @property
    def completion_percentage(self):
        total = self.total_items
        if total == 0:
            return 0
        return round(self.passed_items / total * 100, 1)


# ---------------------------------------------------------------------------
# ITP Item
# ---------------------------------------------------------------------------


class ITPItem(TimeStampedModel):
    INSPECTION_HOLD = "HOLD"
    INSPECTION_WITNESS = "WITNESS"
    INSPECTION_REVIEW = "REVIEW"

    INSPECTION_TYPE_CHOICES = [
        (INSPECTION_HOLD, "Hold Point"),
        (INSPECTION_WITNESS, "Witness Point"),
        (INSPECTION_REVIEW, "Review"),
    ]

    RESPONSIBLE_CONTRACTOR = "CONTRACTOR"
    RESPONSIBLE_CONSULTANT = "CONSULTANT"
    RESPONSIBLE_CLIENT = "CLIENT"

    RESPONSIBLE_PARTY_CHOICES = [
        (RESPONSIBLE_CONTRACTOR, "Contractor"),
        (RESPONSIBLE_CONSULTANT, "Consultant"),
        (RESPONSIBLE_CLIENT, "Client"),
    ]

    STATUS_PENDING = "PENDING"
    STATUS_PASSED = "PASSED"
    STATUS_FAILED = "FAILED"
    STATUS_CONDITIONAL = "CONDITIONAL"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PASSED, "Passed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CONDITIONAL, "Conditional"),
    ]

    itp = models.ForeignKey(
        ITP,
        on_delete=models.CASCADE,
        related_name="items",
    )
    sequence = models.IntegerField(default=1)
    description = models.TextField()
    inspection_type = models.CharField(
        max_length=10,
        choices=INSPECTION_TYPE_CHOICES,
        default=INSPECTION_WITNESS,
    )
    responsible_party = models.CharField(
        max_length=15,
        choices=RESPONSIBLE_PARTY_CHOICES,
        default=RESPONSIBLE_CONTRACTOR,
    )
    acceptance_criteria = models.TextField()
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    class Meta:
        verbose_name = "ITP Item"
        verbose_name_plural = "ITP Items"
        ordering = ["itp", "sequence"]
        unique_together = [("itp", "sequence")]

    def __str__(self):
        return f"{self.itp} – Item {self.sequence}"

    def get_absolute_url(self):
        return reverse("quality:itp-detail", kwargs={"pk": self.itp.pk})


# ---------------------------------------------------------------------------
# Inspection Record
# ---------------------------------------------------------------------------


class InspectionRecord(TimeStampedModel):
    RESULT_PASS = "PASS"
    RESULT_FAIL = "FAIL"
    RESULT_CONDITIONAL = "CONDITIONAL_PASS"

    RESULT_CHOICES = [
        (RESULT_PASS, "Pass"),
        (RESULT_FAIL, "Fail"),
        (RESULT_CONDITIONAL, "Conditional Pass"),
    ]

    itp_item = models.ForeignKey(
        ITPItem,
        on_delete=models.CASCADE,
        related_name="inspection_records",
    )
    date = models.DateField()
    inspector_name = models.CharField(max_length=150)
    inspector_org = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=255)
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
    )
    notes = models.TextField(blank=True)
    document = models.FileField(
        upload_to="inspections/",
        null=True,
        blank=True,
    )
    signed_off_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="signed_off_inspections",
    )

    class Meta:
        verbose_name = "Inspection Record"
        verbose_name_plural = "Inspection Records"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.itp_item} – {self.date} – {self.get_result_display()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Sync ITPItem status based on latest inspection result
        if self.result == self.RESULT_PASS:
            ITPItem.objects.filter(pk=self.itp_item_id).update(status=ITPItem.STATUS_PASSED)
        elif self.result == self.RESULT_FAIL:
            ITPItem.objects.filter(pk=self.itp_item_id).update(status=ITPItem.STATUS_FAILED)
        elif self.result == self.RESULT_CONDITIONAL:
            ITPItem.objects.filter(pk=self.itp_item_id).update(status=ITPItem.STATUS_CONDITIONAL)


# ---------------------------------------------------------------------------
# NCR – Non-Conformance Report
# ---------------------------------------------------------------------------


class NCR(TimeStampedModel):
    SEVERITY_MINOR = "MINOR"
    SEVERITY_MAJOR = "MAJOR"
    SEVERITY_CRITICAL = "CRITICAL"

    SEVERITY_CHOICES = [
        (SEVERITY_MINOR, "Minor"),
        (SEVERITY_MAJOR, "Major"),
        (SEVERITY_CRITICAL, "Critical"),
    ]

    STATUS_OPEN = "OPEN"
    STATUS_UNDER_REVIEW = "UNDER_REVIEW"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_CLOSED, "Closed"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ncrs",
    )
    ncr_number = models.CharField(max_length=20, editable=False, db_index=True)
    description = models.TextField()
    location = models.CharField(max_length=255)
    trade_responsible = models.CharField(max_length=150)
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_MINOR,
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="raised_ncrs",
    )
    raised_date = models.DateField()
    corrective_action_required = models.TextField()
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quality_ncr_responsible",
    )
    due_date = models.DateField(null=True, blank=True)
    response = models.TextField(blank=True)
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    close_out_date = models.DateField(null=True, blank=True)
    close_out_notes = models.TextField(blank=True)
    itp_item = models.ForeignKey(
        ITPItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ncrs",
        help_text="Linked ITP item if triggered by a failed inspection.",
    )

    class Meta:
        verbose_name = "NCR"
        verbose_name_plural = "NCRs"
        ordering = ["project", "-raised_date"]
        unique_together = [("project", "ncr_number")]

    def __str__(self):
        return f"{self.ncr_number} – {self.project.project_id}"

    def save(self, *args, **kwargs):
        if not self.ncr_number:
            count = NCR.objects.filter(project=self.project).count() + 1
            self.ncr_number = f"NCR-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("quality:ncr-detail", kwargs={"pk": self.pk})

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.status == self.STATUS_CLOSED or not self.due_date:
            return False
        return self.due_date < timezone.now().date()


# ---------------------------------------------------------------------------
# MaterialTestResult
# ---------------------------------------------------------------------------


class MaterialTestResult(TimeStampedModel):
    TEST_CONCRETE = "CONCRETE_STRENGTH"
    TEST_SOIL = "SOIL_COMPACTION"
    TEST_WELD = "WELD"
    TEST_OTHER = "OTHER"

    TEST_TYPE_CHOICES = [
        (TEST_CONCRETE, "Concrete Strength"),
        (TEST_SOIL, "Soil Compaction"),
        (TEST_WELD, "Weld Test"),
        (TEST_OTHER, "Other"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="material_tests",
    )
    test_type = models.CharField(
        max_length=20,
        choices=TEST_TYPE_CHOICES,
        default=TEST_OTHER,
    )
    test_date = models.DateField()
    location = models.CharField(max_length=255)
    sample_reference = models.CharField(max_length=100)
    specified_value = models.CharField(
        max_length=100,
        help_text="Specified/required value with units, e.g. '25 MPa'",
    )
    actual_value = models.CharField(
        max_length=100,
        help_text="Actual measured value with units, e.g. '27.4 MPa'",
    )
    passed = models.BooleanField(default=True)
    lab_certificate = models.FileField(
        upload_to="test_certs/",
        null=True,
        blank=True,
    )
    ncr = models.ForeignKey(
        NCR,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="material_tests",
        help_text="Auto-linked NCR if test failed.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Material Test Result"
        verbose_name_plural = "Material Test Results"
        ordering = ["-test_date"]

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"{self.get_test_type_display()} – {self.sample_reference} [{status}] ({self.test_date})"


# ---------------------------------------------------------------------------
# Defect
# ---------------------------------------------------------------------------


class Defect(TimeStampedModel):
    SEVERITY_MINOR = "MINOR"
    SEVERITY_MAJOR = "MAJOR"
    SEVERITY_CRITICAL = "CRITICAL"

    SEVERITY_CHOICES = [
        (SEVERITY_MINOR, "Minor"),
        (SEVERITY_MAJOR, "Major"),
        (SEVERITY_CRITICAL, "Critical"),
    ]

    PHASE_CONSTRUCTION = "CONSTRUCTION"
    PHASE_DLP = "DLP"

    PHASE_CHOICES = [
        (PHASE_CONSTRUCTION, "Construction"),
        (PHASE_DLP, "Defects Liability Period"),
    ]

    STATUS_OPEN = "OPEN"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_RECTIFIED = "RECTIFIED"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RECTIFIED, "Rectified"),
        (STATUS_CLOSED, "Closed"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="defects",
    )
    defect_number = models.CharField(max_length=20, editable=False, db_index=True)
    description = models.TextField()
    location = models.CharField(max_length=255)
    trade = models.CharField(max_length=100)
    identified_date = models.DateField()
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_MINOR,
    )
    phase = models.CharField(
        max_length=15,
        choices=PHASE_CHOICES,
        default=PHASE_CONSTRUCTION,
    )
    responsible_party = models.CharField(max_length=150)
    target_rectification_date = models.DateField(null=True, blank=True)
    photo_before = models.FileField(
        upload_to="defect_photos/",
        null=True,
        blank=True,
    )
    photo_after = models.FileField(
        upload_to="defect_photos/",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    close_out_date = models.DateField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_defects",
    )

    class Meta:
        verbose_name = "Defect"
        verbose_name_plural = "Defects"
        ordering = ["project", "-identified_date"]
        unique_together = [("project", "defect_number")]

    def __str__(self):
        return f"{self.defect_number} – {self.project.project_id}"

    def save(self, *args, **kwargs):
        if not self.defect_number:
            count = Defect.objects.filter(project=self.project).count() + 1
            self.defect_number = f"DEF-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("quality:defect-list", kwargs={"project_pk": self.project.pk})

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.status in (self.STATUS_RECTIFIED, self.STATUS_CLOSED):
            return False
        if not self.target_rectification_date:
            return False
        return self.target_rectification_date < timezone.now().date()
