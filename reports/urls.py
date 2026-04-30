from django.urls import path
from .views import (
    ClaimReportView,
    ComplianceCheckView,
    DashboardAnalyticsView,
    NotificationView,
    ExportReportView,
    AdminReviewView,
    ClaimHistoryView,
    ClaimInsightsView
)

urlpatterns = [
    path('claim/<int:claim_id>/', ClaimReportView.as_view()),
    path('compliance/<int:claim_id>/', ComplianceCheckView.as_view()),
    path('dashboard/', DashboardAnalyticsView.as_view()),
    path('notifications/', NotificationView.as_view()),
    path('export/', ExportReportView.as_view()),
    path('admin-review/', AdminReviewView.as_view()),
    path('history/', ClaimHistoryView.as_view()),
    path('insights/', ClaimInsightsView.as_view()),
]