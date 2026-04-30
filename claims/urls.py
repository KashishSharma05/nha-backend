from django.urls import path
from .views import (
    ClaimCreateView,
    ClaimListView,
    ClaimTimelineView,
    ClaimDetailView,
    ClaimUpdateView,
    ClaimDeleteView,ClaimDocumentUploadView,ClaimSearchView,ClaimFilterView,ClaimStatusSummaryView,BulkClaimCreateView
)

urlpatterns = [
    path('create/', ClaimCreateView.as_view()),
    path('list/', ClaimListView.as_view()),
    path('timeline/<int:claim_id>/', ClaimTimelineView.as_view()),
    path('<int:pk>/', ClaimDetailView.as_view()),
    path('update/<int:pk>/', ClaimUpdateView.as_view()),
    path('delete/<int:pk>/', ClaimDeleteView.as_view()),
    path('upload/<int:claim_id>/', ClaimDocumentUploadView.as_view()),
    path('search/', ClaimSearchView.as_view()),
    path('filter/', ClaimFilterView.as_view()),
    path('summary/', ClaimStatusSummaryView.as_view()),
    path('bulk-create/', BulkClaimCreateView.as_view()),
]