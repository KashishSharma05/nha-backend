from django.urls import path
from .views import ClaimReportView, ComplianceCheckView

urlpatterns = [
    path('claim/<int:claim_id>/', ClaimReportView.as_view()),
    path('compliance/<int:claim_id>/', ComplianceCheckView.as_view()),
]