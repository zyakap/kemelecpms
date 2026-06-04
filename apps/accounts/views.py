from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import (
    ProfileForm,
    UserCreationForm,
    UserLoginForm,
    UserUpdateForm,
)
from .models import User, UserProfile


class StaffOrAdminMixin(UserPassesTestMixin):
    """Restrict access to staff members or system administrators."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_staff or user.is_admin)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class login_view(LoginView):  # noqa: N801  (kept lowercase to match spec)
    """Email-based login view."""

    form_class = UserLoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("dashboard:index")


class logout_view(LoginRequiredMixin, View):  # noqa: N801
    """Log out the current user and redirect to the login page."""

    def get(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "You have been successfully logged out.")
        return redirect(reverse_lazy("accounts:login"))

    # Allow POST as well for CSRF-protected logout buttons
    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


def dashboard_redirect(request):
    """Simple redirect to the dashboard."""
    return redirect("/dashboard/")


# ---------------------------------------------------------------------------
# User management (admin / staff only)
# ---------------------------------------------------------------------------


class UserListView(StaffOrAdminMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        role = self.request.GET.get("role", "").strip()
        if q:
            qs = qs.filter(
                first_name__icontains=q
            ) | qs.filter(
                last_name__icontains=q
            ) | qs.filter(
                email__icontains=q
            ) | qs.filter(
                department__icontains=q
            )
        if role:
            qs = qs.filter(role=role)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["role_choices"] = User.ROLE_CHOICES
        ctx["selected_role"] = self.request.GET.get("role", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class UserCreateView(StaffOrAdminMixin, CreateView):
    model = User
    form_class = UserCreationForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Create New User"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"User {self.object.get_full_name()} has been created successfully.",
        )
        return response


class UserDetailView(StaffOrAdminMixin, DetailView):
    model = User
    template_name = "accounts/user_detail.html"
    context_object_name = "target_user"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx["profile"] = self.object.profile
        except UserProfile.DoesNotExist:
            ctx["profile"] = None
        return ctx


class UserUpdateView(StaffOrAdminMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "accounts/user_form.html"

    def get_success_url(self):
        return reverse_lazy("accounts:user_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = f"Edit User: {self.object.get_full_name()}"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "User account updated successfully.")
        return response


# ---------------------------------------------------------------------------
# Profile (self-service)
# ---------------------------------------------------------------------------


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "My Profile"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your profile has been updated.")
        return response


class AuditLogView(StaffOrAdminMixin, ListView):
    """System-wide audit trail — visible to staff and admins only."""

    template_name = "accounts/audit_log.html"
    context_object_name = "entries"
    paginate_by = 50

    def get_queryset(self):
        from apps.core.models import AuditLog
        qs = AuditLog.objects.select_related("user").order_by("-timestamp")
        action = self.request.GET.get("action")
        model = self.request.GET.get("model")
        user_id = self.request.GET.get("user")
        if action:
            qs = qs.filter(action=action)
        if model:
            qs = qs.filter(model_name__icontains=model)
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.core.models import AuditLog
        ctx["action_choices"] = AuditLog.ACTION_CHOICES
        ctx["selected_action"] = self.request.GET.get("action", "")
        ctx["model_filter"] = self.request.GET.get("model", "")
        return ctx
