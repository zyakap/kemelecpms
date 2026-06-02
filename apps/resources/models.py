from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class Worker(TimeStampedModel):
    """
    Represents an individual worker (direct, day-labour, or subcontractor).
    Worker IDs are auto-generated in the format WRK-0001.
    """

    GENDER_MALE = "M"
    GENDER_FEMALE = "F"
    GENDER_OTHER = "OTHER"
    GENDER_CHOICES = [
        (GENDER_MALE, "Male"),
        (GENDER_FEMALE, "Female"),
        (GENDER_OTHER, "Other"),
    ]

    NATIONALITY_PNG = "PNG"
    NATIONALITY_EXPAT = "EXPAT"
    NATIONALITY_OTHER = "OTHER"
    NATIONALITY_CHOICES = [
        (NATIONALITY_PNG, "PNG National"),
        (NATIONALITY_EXPAT, "Expatriate"),
        (NATIONALITY_OTHER, "Other"),
    ]

    CLASSIFICATION_UNSKILLED = "UNSKILLED"
    CLASSIFICATION_SEMI = "SEMI_SKILLED"
    CLASSIFICATION_SKILLED = "SKILLED"
    CLASSIFICATION_SUPERVISOR = "SUPERVISOR"
    CLASSIFICATION_PROFESSIONAL = "PROFESSIONAL"
    CLASSIFICATION_CHOICES = [
        (CLASSIFICATION_UNSKILLED, "Unskilled"),
        (CLASSIFICATION_SEMI, "Semi-Skilled"),
        (CLASSIFICATION_SKILLED, "Skilled"),
        (CLASSIFICATION_SUPERVISOR, "Supervisor"),
        (CLASSIFICATION_PROFESSIONAL, "Professional"),
    ]

    EMPLOYMENT_DIRECT = "DIRECT"
    EMPLOYMENT_DAY_LABOUR = "DAY_LABOUR"
    EMPLOYMENT_SUBCONTRACTOR = "SUBCONTRACTOR"
    EMPLOYMENT_CHOICES = [
        (EMPLOYMENT_DIRECT, "Direct Employee"),
        (EMPLOYMENT_DAY_LABOUR, "Day Labour"),
        (EMPLOYMENT_SUBCONTRACTOR, "Subcontractor"),
    ]

    worker_id = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
        help_text="Auto-generated worker ID, e.g. WRK-0001",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=5, choices=GENDER_CHOICES, default=GENDER_MALE)
    nationality = models.CharField(
        max_length=10,
        choices=NATIONALITY_CHOICES,
        default=NATIONALITY_PNG,
    )
    occupation = models.CharField(max_length=150)
    trade = models.CharField(max_length=150, blank=True)
    classification = models.CharField(
        max_length=15,
        choices=CLASSIFICATION_CHOICES,
        default=CLASSIFICATION_UNSKILLED,
    )
    employment_type = models.CharField(
        max_length=15,
        choices=EMPLOYMENT_CHOICES,
        default=EMPLOYMENT_DIRECT,
    )
    nid_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="National ID Number",
    )
    tfn = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Tax File Number",
    )
    phone = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workers",
        help_text="Current primary project assignment.",
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateField()

    class Meta:
        verbose_name = "Worker"
        verbose_name_plural = "Workers"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.worker_id} – {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if not self.worker_id:
            self.worker_id = self._generate_worker_id()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_worker_id(cls):
        last = cls.objects.order_by("worker_id").last()
        if last and last.worker_id.startswith("WRK-"):
            try:
                seq = int(last.worker_id.split("-")[1]) + 1
            except (IndexError, ValueError):
                seq = 1
        else:
            seq = 1
        return f"WRK-{seq:04d}"


class Crew(TimeStampedModel):
    """A named crew of workers assigned to a project."""

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="crews",
    )
    name = models.CharField(max_length=150)
    foreman = models.ForeignKey(
        Worker,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="led_crews",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Crew"
        verbose_name_plural = "Crews"
        ordering = ["project", "name"]
        unique_together = [("project", "name")]

    def __str__(self):
        return f"{self.name} ({self.project})"

    @property
    def active_member_count(self):
        return self.crew_members.filter(date_left__isnull=True).count()


class CrewMember(TimeStampedModel):
    """Junction between Crew and Worker with date range."""

    crew = models.ForeignKey(
        Crew,
        on_delete=models.CASCADE,
        related_name="crew_members",
    )
    worker = models.ForeignKey(
        Worker,
        on_delete=models.CASCADE,
        related_name="crew_memberships",
    )
    date_joined = models.DateField()
    date_left = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Crew Member"
        verbose_name_plural = "Crew Members"
        ordering = ["crew", "date_joined"]
        unique_together = [("crew", "worker")]

    def __str__(self):
        return f"{self.worker.full_name} → {self.crew.name}"

    @property
    def is_current(self):
        return self.date_left is None


class AttendanceRecord(TimeStampedModel):
    """Daily attendance record for a single worker on a project."""

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    worker = models.ForeignKey(
        Worker,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    crew = models.ForeignKey(
        Crew,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_records",
    )
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    overtime_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    is_present = models.BooleanField(default=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_records_recorded",
    )
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        ordering = ["-date", "worker__last_name"]
        unique_together = [("project", "worker", "date")]

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.worker.full_name} – {self.date} [{status}]"

    @property
    def hours_worked(self):
        if self.time_in and self.time_out:
            from datetime import datetime, date as date_type
            dt_in = datetime.combine(date_type.today(), self.time_in)
            dt_out = datetime.combine(date_type.today(), self.time_out)
            delta = dt_out - dt_in
            if delta.total_seconds() > 0:
                return round(delta.total_seconds() / 3600, 2)
        return 0.0


class Equipment(TimeStampedModel):
    """
    A piece of plant or equipment. Can be company-owned or hired.
    Equipment IDs are auto-generated in the format EQP-0001.
    """

    OWNERSHIP_OWNED = "OWNED"
    OWNERSHIP_HIRED = "HIRED"
    OWNERSHIP_CHOICES = [
        (OWNERSHIP_OWNED, "Owned"),
        (OWNERSHIP_HIRED, "Hired"),
    ]

    equipment_id = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
        help_text="Auto-generated equipment ID, e.g. EQP-0001",
    )
    description = models.CharField(max_length=255)
    equipment_type = models.CharField(max_length=100)
    ownership_type = models.CharField(
        max_length=6,
        choices=OWNERSHIP_CHOICES,
        default=OWNERSHIP_OWNED,
    )
    supplier = models.CharField(max_length=200, blank=True)
    model = models.CharField(max_length=100, blank=True)
    year = models.IntegerField(null=True, blank=True)
    registration_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"
        ordering = ["equipment_id"]

    def __str__(self):
        return f"{self.equipment_id} – {self.description}"

    def save(self, *args, **kwargs):
        if not self.equipment_id:
            self.equipment_id = self._generate_equipment_id()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_equipment_id(cls):
        last = cls.objects.order_by("equipment_id").last()
        if last and last.equipment_id.startswith("EQP-"):
            try:
                seq = int(last.equipment_id.split("-")[1]) + 1
            except (IndexError, ValueError):
                seq = 1
        else:
            seq = 1
        return f"EQP-{seq:04d}"


class EquipmentAllocation(TimeStampedModel):
    """Tracks which project a piece of equipment is allocated to and when."""

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="equipment_allocations",
    )
    allocated_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    hire_rate_daily = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Daily hire rate (PGK). Applicable only when equipment is hired.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Equipment Allocation"
        verbose_name_plural = "Equipment Allocations"
        ordering = ["-allocated_date"]

    def __str__(self):
        return f"{self.equipment} → {self.project} (from {self.allocated_date})"

    @property
    def is_current(self):
        return self.return_date is None

    @property
    def total_hire_cost(self):
        """Calculate total hire cost based on days allocated and daily rate."""
        if not self.hire_rate_daily:
            return Decimal("0.00")
        end = self.return_date
        if end is None:
            from django.utils import timezone
            end = timezone.localdate()
        days = (end - self.allocated_date).days
        return (Decimal(str(days)) * self.hire_rate_daily).quantize(Decimal("0.01"))


class EquipmentUtilisation(TimeStampedModel):
    """Daily utilisation record for an equipment allocation."""

    allocation = models.ForeignKey(
        EquipmentAllocation,
        on_delete=models.CASCADE,
        related_name="utilisation_records",
    )
    date = models.DateField()
    hours_worked = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    hours_idle = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    hours_breakdown = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    fuel_litres = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    operator = models.ForeignKey(
        Worker,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="equipment_operations",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Equipment Utilisation"
        verbose_name_plural = "Equipment Utilisation Records"
        ordering = ["-date"]
        unique_together = [("allocation", "date")]

    def __str__(self):
        return f"{self.allocation.equipment} – {self.date} ({self.hours_worked}h worked)"

    @property
    def total_hours(self):
        return self.hours_worked + self.hours_idle + self.hours_breakdown

    @property
    def utilisation_rate(self):
        """Percentage of total hours spent working (0–100)."""
        total = self.total_hours
        if total == 0:
            return Decimal("0.00")
        return (self.hours_worked / total * 100).quantize(Decimal("0.01"))


class SubcontractorCompany(TimeStampedModel):
    """
    A subcontractor company in the vendor/supplier register.
    Used for prequalification tracking and performance management.
    """

    company_name = models.CharField(max_length=255)
    trade = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    irc_tin = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="IRC TIN",
        help_text="Internal Revenue Commission Tax Identification Number",
    )
    is_prequalified = models.BooleanField(default=False)
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)
    performance_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("1.0")), MaxValueValidator(Decimal("5.0"))],
        help_text="Overall performance rating from 1.0 (poor) to 5.0 (excellent).",
    )

    class Meta:
        verbose_name = "Subcontractor Company"
        verbose_name_plural = "Subcontractor Companies"
        ordering = ["company_name"]

    def __str__(self):
        flags = []
        if self.is_prequalified:
            flags.append("PQ")
        if self.is_blacklisted:
            flags.append("BL")
        suffix = f" [{'/'.join(flags)}]" if flags else ""
        return f"{self.company_name}{suffix}"

    @property
    def status_display(self):
        if self.is_blacklisted:
            return "Blacklisted"
        if self.is_prequalified:
            return "Prequalified"
        return "Registered"
