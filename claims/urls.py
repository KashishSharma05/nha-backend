from django.urls import path
from .views import ClaimCreateView, ClaimListView, ClaimTimelineView

urlpatterns = [
    path('create/', ClaimCreateView.as_view()),
    path('list/', ClaimListView.as_view()),
    path('timeline/<int:claim_id>/', ClaimTimelineView.as_view()),
]