from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm as BaseUserCreationForm
from django.contrib.auth import authenticate

from .models import User, UserProfile


class UserLoginForm(AuthenticationForm):
    """Email-based login form."""

    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )

    error_messages = {
        "invalid_login": (
            "Please enter a correct email and password. "
            "Note that both fields may be case-sensitive."
        ),
        "inactive": "This account is inactive.",
    }


class UserCreationForm(BaseUserCreationForm):
    """Form for creating new users by an administrator."""

    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Password confirmation",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role", "phone", "department")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]  # keep username in sync
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """Form for administrators to edit user accounts."""

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "role",
            "phone",
            "department",
            "is_active",
            "is_staff",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower().strip()
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        # Keep username in sync with email for compatibility
        user.username = user.email
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Form for users to update their own profile, account details,
    notification preferences, and (optionally) their password."""

    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    old_password = forms.CharField(
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"}),
    )
    new_password1 = forms.CharField(
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    class Meta:
        model = UserProfile
        fields = (
            "profile_photo",
            "position",
            "bio",
            "signature",
            "notif_dsr",
            "notif_budget",
            "notif_safety",
            "notif_milestone",
            "notif_ipc",
        )
        widgets = {
            "position": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = getattr(self.instance, "user", None)
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone
            self.fields["department"].initial = user.department

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower().strip()
        qs = User.objects.filter(email=email)
        if self.instance.pk and self.instance.user_id:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        old = cleaned.get("old_password")
        new1 = cleaned.get("new_password1")
        new2 = cleaned.get("new_password2")
        if old or new1 or new2:
            user = self.instance.user
            if not old or not user.check_password(old):
                self.add_error("old_password", "Your current password is incorrect.")
            if not new1:
                self.add_error("new_password1", "Enter a new password.")
            elif new1 != new2:
                self.add_error("new_password2", "The new passwords do not match.")
            else:
                from django.contrib.auth import password_validation

                try:
                    password_validation.validate_password(new1, user)
                except forms.ValidationError as exc:
                    self.add_error("new_password1", exc)
        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=commit)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.username = user.email
        user.phone = self.cleaned_data.get("phone", "")
        user.department = self.cleaned_data.get("department", "")
        if self.cleaned_data.get("new_password1"):
            user.set_password(self.cleaned_data["new_password1"])
        if commit:
            user.save()
        return profile
