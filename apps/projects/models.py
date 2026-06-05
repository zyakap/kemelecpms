from django.conf import settings
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.core.models import TimeStampedModel
from apps.core.utils import generate_ref, upload_to


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class Client(TimeStampedModel):
    TYPE_GOVERNMENT = "GOVERNMENT"
    TYPE_PRIVATE = "PRIVATE"
    TYPE_NGO = "NGO"
    TYPE_OTHER = "OTHER"

    CLIENT_TYPE_CHOICES = [
        (TYPE_GOVERNMENT, "Government"),
        (TYPE_PRIVATE, "Private"),
        (TYPE_NGO, "NGO / Aid Organisation"),
        (TYPE_OTHER, "Other"),
    ]

    name = models.CharField(max_length=255)
    client_type = models.CharField(
        max_length=20, choices=CLIENT_TYPE_CHOICES, default=TYPE_GOVERNMENT
    )
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("projects:client_list")


# ---------------------------------------------------------------------------
# Funder
# ---------------------------------------------------------------------------


class Funder(TimeStampedModel):
    TYPE_OTML_TCS = "OTML_TCS"
    TYPE_ADB = "ADB"
    TYPE_WORLD_BANK = "WORLD_BANK"
    TYPE_DFAT = "DFAT"
    TYPE_PRIVATE = "PRIVATE"
    TYPE_OTHER = "OTHER"

    FUNDER_TYPE_CHOICES = [
        (TYPE_OTML_TCS, "OTML / TCS"),
        (TYPE_ADB, "ADB (Asian Development Bank)"),
        (TYPE_WORLD_BANK, "World Bank"),
        (TYPE_DFAT, "DFAT (Australia Aid)"),
        (TYPE_PRIVATE, "Private"),
        (TYPE_OTHER, "Other"),
    ]

    name = models.CharField(max_length=255)
    funder_type = models.CharField(
        max_length=20, choices=FUNDER_TYPE_CHOICES, default=TYPE_OTHER
    )
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "Funder"
        verbose_name_plural = "Funders"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("projects:funder_list")


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class Project(TimeStampedModel):
    # Project type
    TYPE_BUILDING = "BUILDING"
    TYPE_CIVIL = "CIVIL"
    TYPE_ELECTRICAL = "ELECTRICAL"
    TYPE_EPC = "EPC"
    TYPE_MIXED = "MIXED"

    PROJECT_TYPE_CHOICES = [
        (TYPE_BUILDING, "Building / Structural"),
        (TYPE_CIVIL, "Civil Works"),
        (TYPE_ELECTRICAL, "Electrical"),
        (TYPE_EPC, "EPC (Engineering, Procurement & Construction)"),
        (TYPE_MIXED, "Mixed / Multi-discipline"),
    ]

    # Status
    STATUS_TENDERING = "TENDERING"
    STATUS_AWARDED = "AWARDED"
    STATUS_MOBILISATION = "MOBILISATION"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_PRACTICAL_COMPLETION = "PRACTICAL_COMPLETION"
    STATUS_DEFECTS_LIABILITY = "DEFECTS_LIABILITY"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_TENDERING, "Tendering"),
        (STATUS_AWARDED, "Awarded"),
        (STATUS_MOBILISATION, "Mobilisation"),
        (STATUS_ACTIVE, "Active / Under Construction"),
        (STATUS_PRACTICAL_COMPLETION, "Practical Completion"),
        (STATUS_DEFECTS_LIABILITY, "Defects Liability Period"),
        (STATUS_CLOSED, "Closed"),
    ]

    project_id = models.CharField(
        max_length=20, unique=True, editable=False, db_index=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    project_type = models.CharField(
        max_length=20, choices=PROJECT_TYPE_CHOICES, default=TYPE_BUILDING
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STATUS_TENDERING
    )

    # Location
    province = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    site_address = models.TextField(blank=True)
    gps_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        verbose_name="GPS Latitude"
    )
    gps_lng = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        verbose_name="GPS Longitude"
    )

    # Key personnel
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_projects",
        limit_choices_to={"role": "project_manager"},
    )
    site_supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="supervised_projects",
        limit_choices_to={"role": "site_supervisor"},
    )

    # Client / Funder
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="projects"
    )
    funder = models.ForeignKey(
        Funder, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="projects"
    )

    # Media
    thumbnail = models.ImageField(
        upload_to="projects/thumbnails/", null=True, blank=True
    )

    # Dates
    start_date = models.DateField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project_id} – {self.name}"

    def save(self, *args, **kwargs):
        if not self.project_id:
            self.project_id = generate_ref("PROJ", Project)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.pk})

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def is_complete(self):
        return self.status in (
            self.STATUS_PRACTICAL_COMPLETION,
            self.STATUS_DEFECTS_LIABILITY,
            self.STATUS_CLOSED,
        )

    @property
    def contract_value(self):
        """Return current contract value including approved variations."""
        try:
            base = self.contract.original_value or 0
        except Contract.DoesNotExist:
            return 0
        approved_variations = self.variations.filter(
            status=Variation.STATUS_APPROVED
        )
        variation_total = sum(
            variation.signed_amount for variation in approved_variations
        )
        return base + variation_total


class ProjectMembership(TimeStampedModel):
    ROLE_PM = "project_manager"
    ROLE_SUPERVISOR = "site_supervisor"
    ROLE_PROCUREMENT = "procurement"
    ROLE_FINANCE = "finance"
    ROLE_DOC_CTRL = "document_control"
    ROLE_QAQC = "quality"
    ROLE_HSE = "safety"
    ROLE_CLIENT = "client"
    ROLE_AUDITOR = "auditor"
    ROLE_VIEWER = "viewer"

    ROLE_CHOICES = [
        (ROLE_PM, "Project Manager"),
        (ROLE_SUPERVISOR, "Site Supervisor"),
        (ROLE_PROCUREMENT, "Procurement"),
        (ROLE_FINANCE, "Finance"),
        (ROLE_DOC_CTRL, "Document Control"),
        (ROLE_QAQC, "Quality"),
        (ROLE_HSE, "Safety"),
        (ROLE_CLIENT, "Client / Funder"),
        (ROLE_AUDITOR, "Auditor"),
        (ROLE_VIEWER, "Viewer"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_VIEWER)
    can_edit = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["project", "role", "user__first_name", "user__last_name"]
        unique_together = [("project", "user")]

    def __str__(self):
        return f"{self.user} - {self.project} ({self.get_role_display()})"


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


class Contract(TimeStampedModel):
    TYPE_LUMP_SUM = "LUMP_SUM"
    TYPE_SCHEDULE_OF_RATES = "SCHEDULE_OF_RATES"
    TYPE_COST_PLUS = "COST_PLUS"
    TYPE_EPC = "EPC"
    TYPE_DESIGN_BUILD = "DESIGN_BUILD"

    CONTRACT_TYPE_CHOICES = [
        (TYPE_LUMP_SUM, "Lump Sum"),
        (TYPE_SCHEDULE_OF_RATES, "Schedule of Rates"),
        (TYPE_COST_PLUS, "Cost Plus"),
        (TYPE_EPC, "EPC"),
        (TYPE_DESIGN_BUILD, "Design & Build"),
    ]

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="contract"
    )
    contract_number = models.CharField(max_length=100, blank=True)
    contract_type = models.CharField(
        max_length=30, choices=CONTRACT_TYPE_CHOICES, default=TYPE_LUMP_SUM
    )
    original_value = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name="Original Contract Value (PGK)"
    )
    start_date = models.DateField()
    original_completion_date = models.DateField()
    revised_completion_date = models.DateField(null=True, blank=True)
    liquidated_damages_rate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Liquidated Damages Rate (PGK/day)"
    )
    dlp_months = models.PositiveIntegerField(
        default=12, verbose_name="Defects Liability Period (months)"
    )
    retention_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        verbose_name="Retention Percentage (%)"
    )
    retention_cap_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        verbose_name="Retention Cap (%)"
    )
    payment_terms_days = models.PositiveIntegerField(
        default=30, verbose_name="Payment Terms (days)"
    )
    letter_of_award = models.FileField(
        upload_to="contracts/loa/", null=True, blank=True,
        verbose_name="Letter of Award"
    )

    class Meta:
        verbose_name = "Contract"
        verbose_name_plural = "Contracts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Contract: {self.contract_number or self.project.project_id}"

    def get_absolute_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.project.pk})

    @property
    def current_completion_date(self):
        return self.revised_completion_date or self.original_completion_date


# ---------------------------------------------------------------------------
# Variation
# ---------------------------------------------------------------------------


class Variation(TimeStampedModel):
    STATUS_INSTRUCTED = "INSTRUCTED"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_ASSESSED = "ASSESSED"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_INSTRUCTED, "Instructed"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_ASSESSED, "Assessed"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    TYPE_ADD = "ADD"
    TYPE_OMIT = "OMIT"

    VARIATION_TYPE_CHOICES = [
        (TYPE_ADD, "Addition"),
        (TYPE_OMIT, "Omission"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="variations"
    )
    ref_number = models.CharField(max_length=30, editable=False)
    description = models.TextField()
    date_instructed = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_INSTRUCTED
    )
    variation_type = models.CharField(
        max_length=10, choices=VARIATION_TYPE_CHOICES, default=TYPE_ADD
    )
    amount = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name="Amount (PGK)"
    )
    supporting_document = models.FileField(
        upload_to="variations/documents/", null=True, blank=True
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Variation"
        verbose_name_plural = "Variations"
        ordering = ["project", "ref_number"]
        unique_together = [("project", "ref_number")]

    def __str__(self):
        return f"{self.ref_number} – {self.project.project_id}"

    def save(self, *args, **kwargs):
        if not self.ref_number:
            count = Variation.objects.filter(project=self.project).count() + 1
            self.ref_number = f"VO-{count:03d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("projects:variation_list", kwargs={"project_pk": self.project.pk})

    @property
    def signed_amount(self):
        """Return positive or negative value based on variation type."""
        if self.variation_type == self.TYPE_OMIT:
            return -abs(self.amount)
        return abs(self.amount)


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------


class Milestone(TimeStampedModel):
    TYPE_CONTRACTUAL = "CONTRACTUAL"
    TYPE_INTERNAL = "INTERNAL"
    TYPE_FUNDER = "FUNDER"

    MILESTONE_TYPE_CHOICES = [
        (TYPE_CONTRACTUAL, "Contractual"),
        (TYPE_INTERNAL, "Internal"),
        (TYPE_FUNDER, "Funder / External"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="milestones"
    )
    name = models.CharField(max_length=255)
    milestone_type = models.CharField(
        max_length=20, choices=MILESTONE_TYPE_CHOICES, default=TYPE_CONTRACTUAL
    )
    target_date = models.DateField()
    actual_date = models.DateField(null=True, blank=True)
    is_achieved = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    evidence = models.FileField(
        upload_to="milestones/evidence/", null=True, blank=True
    )

    class Meta:
        verbose_name = "Milestone"
        verbose_name_plural = "Milestones"
        ordering = ["project", "target_date"]

    def __str__(self):
        return f"{self.project.project_id} – {self.name}"

    def get_absolute_url(self):
        return reverse("projects:milestone_list", kwargs={"project_pk": self.project.pk})

    @property
    def delay_days(self):
        """Number of days the milestone was achieved late (negative = early)."""
        if self.actual_date and self.target_date:
            return (self.actual_date - self.target_date).days
        return None

    @property
    def is_overdue(self):
        """True if not yet achieved and target date has passed."""
        if self.is_achieved:
            return False
        from django.utils import timezone
        return self.target_date < timezone.now().date()


# ---------------------------------------------------------------------------
# Delay Event
# ---------------------------------------------------------------------------


class DelayEvent(TimeStampedModel):
    DELAY_WEATHER = "WEATHER"
    DELAY_MATERIAL = "MATERIAL"
    DELAY_DESIGN = "DESIGN"
    DELAY_CLIENT = "CLIENT"
    DELAY_LABOUR = "LABOUR"
    DELAY_FORCE_MAJEURE = "FORCE_MAJEURE"

    DELAY_TYPE_CHOICES = [
        (DELAY_WEATHER, "Weather / Rainfall"),
        (DELAY_MATERIAL, "Material Supply"),
        (DELAY_DESIGN, "Design / Drawing Issue"),
        (DELAY_CLIENT, "Client Instruction / Variation"),
        (DELAY_LABOUR, "Labour Shortage"),
        (DELAY_FORCE_MAJEURE, "Force Majeure"),
    ]

    PARTY_CLIENT = "CLIENT"
    PARTY_CONTRACTOR = "CONTRACTOR"
    PARTY_FORCE_MAJEURE = "FORCE_MAJEURE"

    RESPONSIBLE_PARTY_CHOICES = [
        (PARTY_CLIENT, "Client"),
        (PARTY_CONTRACTOR, "Contractor"),
        (PARTY_FORCE_MAJEURE, "Force Majeure"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="delay_events"
    )
    date = models.DateField()
    description = models.TextField()
    delay_type = models.CharField(max_length=30, choices=DELAY_TYPE_CHOICES)
    responsible_party = models.CharField(
        max_length=20, choices=RESPONSIBLE_PARTY_CHOICES, default=PARTY_CLIENT
    )
    impact_days = models.PositiveIntegerField(
        default=0, verbose_name="Impact (calendar days)"
    )
    linked_milestone = models.ForeignKey(
        Milestone, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="delay_events"
    )

    class Meta:
        verbose_name = "Delay Event"
        verbose_name_plural = "Delay Events"
        ordering = ["project", "-date"]

    def __str__(self):
        return f"{self.project.project_id} – {self.get_delay_type_display()} ({self.date})"

    def get_absolute_url(self):
        return reverse("projects:project_detail", kwargs={"pk": self.project.pk})
