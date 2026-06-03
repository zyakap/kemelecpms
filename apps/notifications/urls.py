from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    # Notifications
    path(
        "",
        views.NotificationListView.as_view(),
        name="notification-list",
    ),
    path(
        "<int:pk>/read/",
        views.NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
    path(
        "mark-all-read/",
        views.NotificationMarkAllReadView.as_view(),
        name="notification-read-all",
    ),
    # Tasks
    path(
        "tasks/",
        views.TaskListView.as_view(),
        name="task-list",
    ),
    path(
        "tasks/add/",
        views.TaskCreateView.as_view(),
        name="task-create",
    ),
    path(
        "tasks/<int:pk>/edit/",
        views.TaskUpdateView.as_view(),
        name="task-update",
    ),
    path(
        "tasks/<int:pk>/complete/",
        views.TaskCompleteView.as_view(),
        name="task-complete",
    ),
]
