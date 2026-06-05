"""
Safety Management models for kemelecpms.

Covers: Safety Inductions, Toolbox Talks, Incidents, Hazard Risk Register,
SWMS (Safe Work Method Statements), and PPE Issue records.
"""

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# SafetyInduction
# ---------------------------------------------------------------------------


class SafetyInduction(TimeStampedModel):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="safety_inductions",
    )
    worker = models.ForeignKey(
        "resources.Worker",
        on_delete=models.PROTECT,
        related_name="inductions",
    )
    date = models.DateField()
    topics_covered = models.TextField(
        help_text="Describe topics / modules covered during induction."
    )
    inducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inductions_conducted",
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Induction Expiry Date",
        help_text="Leave blank if induction does not expire.",
    )
    acknowledged = models.BooleanField(
        default=False,
        help_text="Worker has signed/acknowledged the induction.",
    )

    class Meta:
        verbose_name = "Safety Induction"
        verbose_name_plural = "Safety Inductions"
        ordering = ["-date"]
        unique_together = [("project", "worker", "date")]

    def __str__(self):
        return f"{self.worker} inducted on {self.date} ({self.project})"

    def get_absolute_url(self):
        return reverse("safety:induction_list")

    @property
    def is_expired(self):
        if self.expiry_date is None:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()


# ---------------------------------------------------------------------------
# ToolboxTalk
# ---------------------------------------------------------------------------


class ToolboxTalk(TimeStampedModel):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="toolbox_talks",
    )
    date = models.DateField()
    topic = models.CharField(max_length=255)
    presenter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="toolbox_talks_presented",
    )
    notes = models.TextField(blank=True)
    attendee_count = models.IntegerField(
        default=0, verbose_name="Total Attendees"
    )

    class Meta:
        verbose_name = "Toolbox Talk"
        verbose_name_plural = "Toolbox Talks"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} – {self.topic} ({self.project})"

    def get_absolute_url(self):
        return reverse("safety:toolbox_list")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep attendee_count in sync with linked ToolboxAttendee records
        self.attendee_count = self.attendees.count()
        ToolboxTalk.objects.filter(pk=self.pk).update(
            attendee_count=self.attendee_count
        )


class ToolboxAttendee(TimeStampedModel):
    toolbox = models.ForeignKey(
        ToolboxTalk, on_delete=models.CASCADE, related_name="attendees"
    )
    worker = models.ForeignKey(
        "resources.Worker",
        on_delete=models.PROTECT,
        related_name="toolbox_attendances",
    )

    class Meta:
        verbose_name = "Toolbox Attendee"
        verbose_name_plural = "Toolbox Attendees"
        unique_together = [("toolbox", "worker")]

    def __str__(self):
        return f"{self.worker} – {self.toolbox.topic} ({self.toolbox.date})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update parent count whenever an attendee is added
        ToolboxTalk.objects.filter(pk=self.toolbox_id).update(
            attendee_count=ToolboxAttendee.objects.filter(
                toolbox_id=self.toolbox_id
            ).count()
        )


# ---------------------------------------------------------------------------
# Incident
# ---------------------------------------------------------------------------


class Incident(TimeStampedModel):
    TYPE_NEAR_MISS = "NEAR_MISS"
    TYPE_FIRST_AID = "FIRST_AID"
    TYPE_MEDICAL = "MEDICAL"
    TYPE_LTI = "LTI"
    TYPE_FATALITY = "FATALITY"
    TYPE_PROPERTY = "PROPERTY"
    TYPE_ENVIRONMENTAL = "ENVIRONMENTAL"

    INCIDENT_TYPE_CHOICES = [
        (TYPE_NEAR_MISS, "Near Miss"),
        (TYPE_FIRST_AID, "First Aid"),
        (TYPE_MEDICAL, "Medical Treatment"),
        (TYPE_LTI, "Lost Time Injury (LTI)"),
        (TYPE_FATALITY, "Fatality"),
        (TYPE_PROPERTY, "Property Damage"),
        (TYPE_ENVIRONMENTAL, "Environmental"),
    ]

    STATUS_OPEN = "OPEN"
    STATUS_INVESTIGATING = "UNDER_INVESTIGATION"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_INVESTIGATING, "Under Investigation"),
        (STATUS_CLOSED, "Closed"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="incidents",
    )
    incident_number = models.CharField(
        max_length=20, unique=True, editable=False, db_index=True
    )
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    incident_type = models.CharField(
        max_length=20, choices=INCIDENT_TYPE_CHOICES
    )
    description = models.TextField()
    persons_involved = models.TextField(
        help_text="Names and roles of persons involved."
    )
    body_part = models.CharField(max_length=100, blank=True)
    injury_nature = models.CharField(max_length=150, blank=True)
    treatment_given = models.TextField(blank=True)
    is_lti = models.BooleanField(
        default=False, verbose_name="Is Lost Time Injury?"
    )
    days_lost = models.IntegerField(
        default=0, verbose_name="Days Lost (LTI)"
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incidents_reported",
    )
    status = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    corrective_action = models.TextField(blank=True)
    corrective_action_due = models.DateField(null=True, blank=True)
    corrective_action_closed = models.DateField(null=True, blank=True)
    corrective_action_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="safety_corrective_actions",
    )
    photo = models.FileField(
        upload_to="incident_photos/", null=True, blank=True
    )

    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.incident_number} – {self.get_incident_type_display()} ({self.date})"

    def save(self, *args, **kwargs):
        if not self.incident_number:
            count = Incident.objects.count() + 1
            self.incident_number = f"INC-{count:04d}"
        # Auto-set is_lti based on incident_type
        if self.incident_type == self.TYPE_LTI:
            self.is_lti = True
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("safety:incident_detail", kwargs={"pk": self.pk})


# ---------------------------------------------------------------------------
# HazardRisk
# ---------------------------------------------------------------------------


class HazardRisk(TimeStampedModel):
    LIKELIHOOD_CHOICES = [(i, str(i)) for i in range(1, 6)]
    CONSEQUENCE_CHOICES = [(i, str(i)) for i in range(1, 6)]

    CONTROL_ELIMINATE = "ELIMINATE"
    CONTROL_SUBSTITUTE = "SUBSTITUTE"
    CONTROL_ISOLATE = "ISOLATE"
    CONTROL_ENGINEERING = "ENGINEERING"
    CONTROL_ADMINISTRATIVE = "ADMINISTRATIVE"
    CONTROL_PPE = "PPE"

    CONTROL_TYPE_CHOICES = [
        (CONTROL_ELIMINATE, "Eliminate"),
        (CONTROL_SUBSTITUTE, "Substitute"),
        (CONTROL_ISOLATE, "Isolate"),
        (CONTROL_ENGINEERING, "Engineering Controls"),
        (CONTROL_ADMINISTRATIVE, "Administrative Controls"),
        (CONTROL_PPE, "PPE"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="hazard_risks",
    )
    activity = models.CharField(max_length=255)
    hazard_description = models.TextField()
    likelihood = models.IntegerField(choices=LIKELIHOOD_CHOICES)
    consequence = models.IntegerField(choices=CONSEQUENCE_CHOICES)
    control_measure = models.TextField()
    control_type = models.CharField(
        max_length=20, choices=CONTROL_TYPE_CHOICES, default=CONTROL_ADMINISTRATIVE
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hazards_reviewed",
    )
    reviewed_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Hazard / Risk"
        verbose_name_plural = "Hazard / Risk Register"
        ordering = ["-likelihood", "-consequence"]

    def __str__(self):
        return (
            f"{self.activity} – {self.hazard_description[:60]} "
            f"[Risk: {self.risk_level}]"
        )

    def get_absolute_url(self):
        return reverse("safety:hazard_list")

    @property
    def risk_level(self):
        """Numeric risk score: likelihood × consequence."""
        return self.likelihood * self.consequence

    @property
    def risk_category(self):
        """Categorise risk score into LOW / MEDIUM / HIGH."""
        score = self.risk_level
        if score < 6:
            return "LOW"
        if score < 15:
            return "MEDIUM"
        return "HIGH"

    @property
    def risk_category_display(self):
        return self.risk_category.title()


# ---------------------------------------------------------------------------
# SWMS (Safe Work Method Statement)
# ---------------------------------------------------------------------------


class SWMS(TimeStampedModel):
    STATUS_DRAFT = "DRAFT"
    STATUS_APPROVED = "APPROVED"
    STATUS_ARCHIVED = "ARCHIVED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="swms",
    )
    title = models.CharField(max_length=255)
    activity = models.CharField(max_length=255)
    version = models.IntegerField(default=1)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    document = models.FileField(upload_to="swms/")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="swms_approved",
    )
    approved_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "SWMS"
        verbose_name_plural = "SWMS Documents"
        ordering = ["project", "title", "-version"]

    def __str__(self):
        return f"{self.title} v{self.version} ({self.project})"

    def get_absolute_url(self):
        return reverse("safety:swms_list")


# ---------------------------------------------------------------------------
# PPEIssue
# ---------------------------------------------------------------------------


class PPEIssue(TimeStampedModel):
    PPE_HELMET = "HELMET"
    PPE_VEST = "VEST"
    PPE_BOOTS = "BOOTS"
    PPE_GLOVES = "GLOVES"
    PPE_GLASSES = "GLASSES"
    PPE_HARNESS = "HARNESS"
    PPE_OTHER = "OTHER"

    PPE_TYPE_CHOICES = [
        (PPE_HELMET, "Safety Helmet"),
        (PPE_VEST, "High-Visibility Vest"),
        (PPE_BOOTS, "Safety Boots"),
        (PPE_GLOVES, "Gloves"),
        (PPE_GLASSES, "Safety Glasses / Goggles"),
        (PPE_HARNESS, "Safety Harness"),
        (PPE_OTHER, "Other"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="ppe_issues",
    )
    worker = models.ForeignKey(
        "resources.Worker",
        on_delete=models.PROTECT,
        related_name="ppe_issues",
    )
    ppe_type = models.CharField(max_length=10, choices=PPE_TYPE_CHOICES)
    size = models.CharField(max_length=20, blank=True)
    quantity = models.IntegerField(default=1)
    date_issued = models.DateField()
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ppe_issued",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "PPE Issue Record"
        verbose_name_plural = "PPE Issue Records"
        ordering = ["-date_issued"]

    def __str__(self):
        return (
            f"{self.get_ppe_type_display()} issued to {self.worker} on {self.date_issued}"
        )

    def get_absolute_url(self):
        return reverse("safety:ppe_list")


class PermitToWork(TimeStampedModel):
    TYPE_HOT_WORK = "HOT_WORK"
    TYPE_WORK_AT_HEIGHT = "WORK_AT_HEIGHT"
    TYPE_CONFINED_SPACE = "CONFINED_SPACE"
    TYPE_EXCAVATION = "EXCAVATION"
    TYPE_ELECTRICAL = "ELECTRICAL"
    TYPE_LIFTING = "LIFTING"
    TYPE_OTHER = "OTHER"

    PERMIT_TYPE_CHOICES = [
        (TYPE_HOT_WORK, "Hot Work"),
        (TYPE_WORK_AT_HEIGHT, "Work at Height"),
        (TYPE_CONFINED_SPACE, "Confined Space"),
        (TYPE_EXCAVATION, "Excavation"),
        (TYPE_ELECTRICAL, "Electrical Isolation"),
        (TYPE_LIFTING, "Lifting Operations"),
        (TYPE_OTHER, "Other"),
    ]

    STATUS_DRAFT = "DRAFT"
    STATUS_APPROVED = "APPROVED"
    STATUS_CLOSED = "CLOSED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="permits_to_work")
    permit_number = models.CharField(max_length=30, editable=False, db_index=True)
    permit_type = models.CharField(max_length=25, choices=PERMIT_TYPE_CHOICES)
    work_area = models.CharField(max_length=255)
    description = models.TextField()
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="permits_requested")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="permits_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="permits_closed")
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    controls = models.TextField(blank=True)

    class Meta:
        ordering = ["-valid_from", "-permit_number"]
        unique_together = [("project", "permit_number")]

    def __str__(self):
        return f"{self.permit_number} - {self.get_permit_type_display()}"

    def save(self, *args, **kwargs):
        if not self.permit_number:
            count = PermitToWork.objects.filter(project=self.project).count() + 1
            self.permit_number = f"PTW-{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("safety:permit_list")


class SafetyTrainingRecord(TimeStampedModel):
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="safety_training_records")
    worker = models.ForeignKey("resources.Worker", on_delete=models.PROTECT, related_name="safety_training_records")
    course_name = models.CharField(max_length=200)
    provider = models.CharField(max_length=200, blank=True)
    certificate_number = models.CharField(max_length=100, blank=True)
    completed_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    evidence = models.FileField(upload_to="safety_training/", null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["worker", "course_name", "-completed_date"]

    def __str__(self):
        return f"{self.worker} - {self.course_name}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return bool(self.expiry_date and self.expiry_date < timezone.now().date())

    def get_absolute_url(self):
        return reverse("safety:training_list")


class SafetyObservation(TimeStampedModel):
    TYPE_SAFE = "SAFE"
    TYPE_UNSAFE = "UNSAFE"
    TYPE_CHOICES = [
        (TYPE_SAFE, "Safe Act / Condition"),
        (TYPE_UNSAFE, "Unsafe Act / Condition"),
    ]

    STATUS_OPEN = "OPEN"
    STATUS_CLOSED = "CLOSED"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="safety_observations")
    date = models.DateField()
    observation_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    location = models.CharField(max_length=255)
    description = models.TextField()
    observed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="safety_observations")
    immediate_action = models.TextField(blank=True)
    photo = models.FileField(upload_to="safety_observations/", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_observation_type_display()} - {self.location}"

    def get_absolute_url(self):
        return reverse("safety:observation_list")


class SafetyCorrectiveAction(TimeStampedModel):
    STATUS_OPEN = "OPEN"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_CLOSED = "CLOSED"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_CLOSED, "Closed"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="safety_corrective_action_records")
    incident = models.ForeignKey(Incident, null=True, blank=True, on_delete=models.SET_NULL, related_name="corrective_actions")
    observation = models.ForeignKey(SafetyObservation, null=True, blank=True, on_delete=models.SET_NULL, related_name="corrective_actions")
    description = models.TextField()
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_safety_corrective_actions")
    due_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_OPEN)
    close_out_notes = models.TextField(blank=True)
    close_out_evidence = models.FileField(upload_to="safety_corrective_actions/", null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_date"]

    def __str__(self):
        return f"Safety CA - {self.description[:60]}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status != self.STATUS_CLOSED and self.due_date < timezone.now().date()

    def get_absolute_url(self):
        return reverse("safety:corrective_action_list")
