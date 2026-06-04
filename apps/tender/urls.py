from django.urls import path

from . import views

app_name = "tender"

urlpatterns = [
    # Archive
    path("library/", views.TenderArchiveListView.as_view(), name="archive-list"),
    path("library/new/", views.TenderArchiveCreateView.as_view(), name="archive-create"),
    path("library/<int:pk>/", views.TenderArchiveDetailView.as_view(), name="archive-detail"),
    path("library/<int:pk>/edit/", views.TenderArchiveUpdateView.as_view(), name="archive-update"),
    # Cost Rates
    path("rates/", views.CostRateListView.as_view(), name="rate-list"),
    path("rates/new/", views.CostRateCreateView.as_view(), name="rate-create"),
    path("rates/<int:pk>/edit/", views.CostRateUpdateView.as_view(), name="rate-update"),
    # Bid Estimates
    path("estimates/", views.BidEstimateListView.as_view(), name="estimate-list"),
    path("estimates/new/", views.BidEstimateCreateView.as_view(), name="estimate-create"),
    path("estimates/<int:pk>/", views.BidEstimateDetailView.as_view(), name="estimate-detail"),
    path("estimates/<int:pk>/edit/", views.BidEstimateUpdateView.as_view(), name="estimate-update"),
    path("estimates/<int:pk>/clone/", views.BidEstimateCloneView.as_view(), name="estimate-clone"),
    # Lessons Learned
    path("lessons/", views.LessonsLearnedListView.as_view(), name="lessons-list"),
    path("lessons/new/", views.LessonsLearnedCreateView.as_view(), name="lessons-create"),
    path("lessons/<int:pk>/", views.LessonsLearnedDetailView.as_view(), name="lesson-detail"),
    path("lessons/<int:pk>/edit/", views.LessonsLearnedUpdateView.as_view(), name="lessons-update"),
]
