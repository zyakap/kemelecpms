from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .forms import TaskForm, TaskUpdateForm
from .models import Notification, Task


# ---------------------------------------------------------------------------
# Notification views
# ---------------------------------------------------------------------------


class NotificationListView(LoginRequiredMixin, ListView):
    """Shows all notifications for the current user, unread first."""

    model = Notification
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by(
            "is_read", "-created_at"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["unread_count"] = Notification.objects.filter(
            recipient=self.request.user, is_read=False
        ).count()
        return ctx


class NotificationMarkReadView(LoginRequiredMixin, View):
    """POST: mark a single notification as read and redirect to its link."""

    http_method_names = ["post"]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        if notification.link:
            return redirect(notification.link)
        return redirect(reverse_lazy("notifications:notification-list"))


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """POST: mark all of the current user's notifications as read."""

    http_method_names = ["post"]

    def post(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True
        )
        messages.success(request, f"{count} notification(s) marked as read.")
        return redirect(reverse_lazy("notifications:notification-list"))


# ---------------------------------------------------------------------------
# Task views
# ---------------------------------------------------------------------------


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "notifications/task_list.html"
    context_object_name = "tasks"
    paginate_by = 25

    def get_queryset(self):
        qs = Task.objects.filter(assigned_to=self.request.user).select_related(
            "project", "assigned_by"
        )
        status = self.request.GET.get("status")
        priority = self.request.GET.get("priority")
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        return qs.order_by("due_date", "-priority")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Task.STATUS_CHOICES
        ctx["priority_choices"] = Task.PRIORITY_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["selected_priority"] = self.request.GET.get("priority", "")
        ctx["overdue_count"] = Task.objects.filter(
            assigned_to=self.request.user,
            status__in=[Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS],
            due_date__lt=timezone.now().date(),
        ).count()
        return ctx


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "notifications/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.assigned_by = self.request.user
        messages.success(self.request, "Task created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("notifications:task-list")


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskUpdateForm
    template_name = "notifications/task_form.html"

    def get_queryset(self):
        """Users can edit tasks assigned to or by them."""
        return Task.objects.filter(
            assigned_to=self.request.user
        ) | Task.objects.filter(
            assigned_by=self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Task updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("notifications:task-list")


class TaskCompleteView(LoginRequiredMixin, View):
    """POST: mark a task as completed."""

    http_method_names = ["post"]

    def post(self, request, pk):
        task = get_object_or_404(
            Task,
            pk=pk,
            assigned_to=request.user,
            status__in=[Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS],
        )
        task.status = Task.STATUS_COMPLETED
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at", "updated_at"])
        messages.success(request, f'Task "{task.title}" marked as complete.')
        return redirect(reverse_lazy("notifications:task-list"))
