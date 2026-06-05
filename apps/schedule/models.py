from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class WBSActivity(TimeStampedModel):
    """
    Work Breakdown Structure node.
    Level 0 = Phase, 1 = Work Package, 2 = Activity.
    Supports unlimited nesting via parent FK but conventional use is 3 levels.
    """

    LEVEL_PHASE = 0
    LEVEL_WORK_PACKAGE = 1
    LEVEL_ACTIVITY = 2

    LEVEL_CHOICES = [
        (LEVEL_PHASE, "Phase"),
        (LEVEL_WORK_PACKAGE, "Work Package"),
        (LEVEL_ACTIVITY, "Activity"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="wbs_activities",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    wbs_code = models.CharField(
        max_length=30,
        help_text='Hierarchical WBS code, e.g. "1.2.3"',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="wbs_activities",
    )
    cost_code = models.ForeignKey(
        "budget.CostCode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="wbs_activities",
    )
    level = models.IntegerField(choices=LEVEL_CHOICES, default=LEVEL_ACTIVITY)

    class Meta:
        verbose_name = "WBS Activity"
        verbose_name_plural = "WBS Activities"
        ordering = ["wbs_code"]
        unique_together = [("project", "wbs_code")]

    def __str__(self):
        return f"{self.wbs_code} – {self.name}"

    def get_ancestors(self):
        """Return list of ancestor nodes from root to direct parent."""
        ancestors = []
        node = self.parent
        while node is not None:
            ancestors.insert(0, node)
            node = node.parent
        return ancestors

    def get_descendants(self):
        """Return a flat queryset of all descendant WBSActivity objects."""
        result = []
        for child in self.children.all():
            result.append(child)
            result.extend(child.get_descendants())
        return result


class Programme(TimeStampedModel):
    """Master programme (schedule) for a project. One active programme per project."""

    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="programme",
    )
    baseline_start = models.DateField()
    baseline_end = models.DateField()
    current_start = models.DateField()
    current_end = models.DateField()
    version = models.IntegerField(default=1)
    is_baseline = models.BooleanField(
        default=False,
        help_text="Set to True once the baseline has been formally approved.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Programme"
        verbose_name_plural = "Programmes"

    def __str__(self):
        return f"Programme v{self.version} – {self.project}"

    @property
    def duration_days(self):
        if self.current_start and self.current_end:
            return (self.current_end - self.current_start).days
        return 0

    @property
    def baseline_duration_days(self):
        if self.baseline_start and self.baseline_end:
            return (self.baseline_end - self.baseline_start).days
        return 0

    def recalculate_critical_path(self):
        """Mark the longest predecessor chain ending at the latest activity finish as critical."""
        activities = list(self.activities.select_related("predecessor"))
        Activity.objects.filter(programme=self).update(is_critical=False)
        if not activities:
            return []

        by_id = {activity.pk: activity for activity in activities}
        latest_finish = max(activity.end_date for activity in activities)
        candidates = [activity for activity in activities if activity.end_date == latest_finish]
        current = max(candidates, key=lambda activity: activity.duration)
        critical_ids = []
        seen = set()

        while current and current.pk not in seen:
            critical_ids.append(current.pk)
            seen.add(current.pk)
            current = by_id.get(current.predecessor_id)

        Activity.objects.filter(pk__in=critical_ids).update(is_critical=True)
        return critical_ids


class ProgrammeRevision(TimeStampedModel):
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    programme = models.ForeignKey(
        Programme,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision_number = models.CharField(max_length=30, editable=False, db_index=True)
    submitted_date = models.DateField()
    reason = models.TextField()
    revised_start = models.DateField()
    revised_end = models.DateField()
    eot_days = models.PositiveIntegerField(default=0, verbose_name="EOT Days")
    delay_events = models.ManyToManyField(
        "projects.DelayEvent",
        blank=True,
        related_name="programme_revisions",
        help_text="Delay events supporting the programme revision or EOT claim.",
    )
    causation_summary = models.TextField(
        blank=True,
        help_text="Explain delay causation, entitlement, mitigation, and concurrency assessment.",
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_programme_revisions",
    )
    approved_date = models.DateField(null=True, blank=True)
    document = models.FileField(upload_to="programme_revisions/", null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Programme Revision"
        verbose_name_plural = "Programme Revisions"
        ordering = ["programme", "-submitted_date", "-revision_number"]
        unique_together = [("programme", "revision_number")]

    def __str__(self):
        return f"{self.revision_number} - {self.programme.project}"

    def save(self, *args, **kwargs):
        if not self.revision_number:
            count = ProgrammeRevision.objects.filter(programme=self.programme).count() + 1
            self.revision_number = f"PRG-REV-{count:03d}"
        super().save(*args, **kwargs)
        if self.status == self.STATUS_APPROVED:
            Programme.objects.filter(pk=self.programme_id).update(
                current_start=self.revised_start,
                current_end=self.revised_end,
                version=models.F("version") + 1,
            )


class Activity(TimeStampedModel):
    """
    An individual schedule activity within a Programme.
    Tracks planned vs actual progress and supports FS/SS/FF dependencies.
    """

    DEP_FS = "FS"
    DEP_SS = "SS"
    DEP_FF = "FF"

    DEPENDENCY_CHOICES = [
        (DEP_FS, "Finish-to-Start"),
        (DEP_SS, "Start-to-Start"),
        (DEP_FF, "Finish-to-Finish"),
    ]

    programme = models.ForeignKey(
        Programme,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    wbs_activity = models.ForeignKey(
        WBSActivity,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="schedule_activities",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    duration = models.IntegerField(
        default=0,
        help_text="Duration in calendar days (auto-calculated or manually overridden).",
    )
    planned_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    actual_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    predecessor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="successors",
    )
    dependency_type = models.CharField(
        max_length=2,
        choices=DEPENDENCY_CHOICES,
        default=DEP_FS,
    )
    is_critical = models.BooleanField(default=False)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="schedule_activities",
    )

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"
        ordering = ["start_date", "name"]

    def __str__(self):
        return f"{self.name} ({self.programme.project})"

    def save(self, *args, **kwargs):
        # Auto-calculate duration from dates if not manually set
        if self.start_date and self.end_date:
            delta = (self.end_date - self.start_date).days
            if delta >= 0:
                self.duration = delta
        super().save(*args, **kwargs)

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Activity end date must be on or after start date.")
        if self.predecessor_id and self.pk and self.predecessor_id == self.pk:
            raise ValidationError("Activity cannot depend on itself.")
        seen = set()
        predecessor = self.predecessor
        while predecessor is not None:
            if predecessor.pk in seen or (self.pk and predecessor.pk == self.pk):
                raise ValidationError("Activity dependency chain cannot contain a cycle.")
            seen.add(predecessor.pk)
            predecessor = predecessor.predecessor
        if self.predecessor:
            if self.dependency_type == self.DEP_FS and self.start_date < self.predecessor.end_date:
                raise ValidationError("Finish-to-start activity cannot start before predecessor finishes.")
            if self.dependency_type == self.DEP_SS and self.start_date < self.predecessor.start_date:
                raise ValidationError("Start-to-start activity cannot start before predecessor starts.")
            if self.dependency_type == self.DEP_FF and self.end_date < self.predecessor.end_date:
                raise ValidationError("Finish-to-finish activity cannot finish before predecessor finishes.")

    @property
    def spi(self) -> Decimal:
        """Schedule Performance Index: actual % / planned %. >1 = ahead; <1 = behind."""
        if self.planned_percent and self.planned_percent > 0:
            return (self.actual_percent / self.planned_percent).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @property
    def is_on_schedule(self) -> bool:
        """True when actual progress is at or ahead of planned progress."""
        return self.actual_percent >= self.planned_percent


class ProgressEntry(TimeStampedModel):
    """Point-in-time progress snapshot for an Activity."""

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="progress_entries",
    )
    date = models.DateField()
    percent_complete = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="progress_entries_recorded",
    )
    notes = models.TextField(blank=True)
    # Store DSR id without a DB-level FK to break the schedule↔dsr circular dependency.
    # Use get_dsr() to retrieve the related DSR object.
    dsr_id = models.PositiveIntegerField(null=True, blank=True)

    def get_dsr(self):
        if self.dsr_id is None:
            return None
        from apps.dsr.models import DailySiteReport
        return DailySiteReport.objects.filter(pk=self.dsr_id).first()

    class Meta:
        verbose_name = "Progress Entry"
        verbose_name_plural = "Progress Entries"
        ordering = ["-date"]
        unique_together = [("activity", "date")]

    def __str__(self):
        return f"{self.activity.name} – {self.date} – {self.percent_complete}%"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the parent activity's actual_percent to the latest value
        latest = (
            ProgressEntry.objects.filter(activity=self.activity)
            .order_by("-date")
            .first()
        )
        if latest:
            Activity.objects.filter(pk=self.activity_id).update(
                actual_percent=latest.percent_complete
            )


class LookAhead(TimeStampedModel):
    """A 2–6 week look-ahead planning document for a project."""

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="look_aheads",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="look_aheads_created",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Look-Ahead Plan"
        verbose_name_plural = "Look-Ahead Plans"
        ordering = ["-period_start"]

    def __str__(self):
        return f"Look-Ahead {self.period_start} → {self.period_end} ({self.project})"

    @property
    def completion_rate(self) -> Decimal:
        """Percentage of tasks completed."""
        total = self.tasks.count()
        if total == 0:
            return Decimal("0.00")
        done = self.tasks.filter(is_completed=True).count()
        return Decimal(str(round(done / total * 100, 2)))


class LookAheadTask(TimeStampedModel):
    """An individual task within a LookAhead plan."""

    look_ahead = models.ForeignKey(
        LookAhead,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    activity = models.ForeignKey(
        Activity,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="look_ahead_tasks",
    )
    description = models.CharField(max_length=500)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="look_ahead_tasks",
    )
    planned_start = models.DateField()
    planned_end = models.DateField()
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Look-Ahead Task"
        verbose_name_plural = "Look-Ahead Tasks"
        ordering = ["planned_start", "description"]

    def __str__(self):
        status = "Done" if self.is_completed else "Pending"
        return f"{self.description[:60]} [{status}]"
