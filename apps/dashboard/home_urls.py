from django.urls import path
from .views import HomeRedirectView

urlpatterns = [
    path("", HomeRedirectView.as_view(), name="home"),
]
