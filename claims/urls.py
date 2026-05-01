from django.urls import path
from .views import (
    ClaimCreateView,
    ClaimListView,
    ClaimTimelineView,
    ClaimDetailView,
    ClaimUpdateView,
    ClaimDeleteView,
    ClaimDocumentUploadView,
    ClaimSearchView,
    ClaimFilterView,
    ClaimStatusSummaryView,
    BulkClaimCreateView,
    PS1GenerateView,
    PS1ResultView,
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

    # PS-1 output endpoints
    path('ps1/generate/<int:claim_id>/', PS1GenerateView.as_view(), name='ps1-generate'),
    path('ps1/result/<int:claim_id>/',   PS1ResultView.as_view(),   name='ps1-result'),
]