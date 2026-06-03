from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Auth
    path("login/", views.login_view.as_view(), name="login"),
    path("logout/", views.logout_view.as_view(), name="logout"),
    # Self-service profile
    path("profile/", views.ProfileUpdateView.as_view(), name="profile"),
    # User management (admin / staff)
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/create/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_update"),
]
