from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "system_admin")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    ROLE_MD = "managing_director"
    ROLE_PM = "project_manager"
    ROLE_SUPERVISOR = "site_supervisor"
    ROLE_PROCUREMENT = "procurement_officer"
    ROLE_FINANCE = "finance"
    ROLE_DOC_CTRL = "document_controller"
    ROLE_AUDITOR = "auditor"
    ROLE_ADMIN = "system_admin"

    ROLE_CHOICES = [
        (ROLE_MD, "Managing Director"),
        (ROLE_PM, "Project Manager"),
        (ROLE_SUPERVISOR, "Site Supervisor"),
        (ROLE_PROCUREMENT, "Procurement Officer"),
        (ROLE_FINANCE, "Finance / Accounts"),
        (ROLE_DOC_CTRL, "Document Controller"),
        (ROLE_AUDITOR, "Auditor / Funder Rep"),
        (ROLE_ADMIN, "System Administrator"),
    ]

    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default=ROLE_ADMIN)
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["first_name", "last_name"]

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def __str__(self):
        return self.get_full_name()

    @property
    def is_md(self):
        return self.role == self.ROLE_MD

    @property
    def is_pm(self):
        return self.role == self.ROLE_PM

    @property
    def is_supervisor(self):
        return self.role == self.ROLE_SUPERVISOR

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    bio = models.TextField(blank=True)
    position = models.CharField(max_length=100, blank=True)
    po_approval_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Maximum PGK value this user can approve a PO for",
    )
    signature = models.ImageField(upload_to="signatures/", null=True, blank=True)

    def __str__(self):
        return f"Profile: {self.user}"
