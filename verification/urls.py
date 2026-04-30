from django.urls import path
from .views import VerifyClaimView, OCRProcessView, OCRStatusView

urlpatterns = [
    path('claim/<int:claim_id>/', VerifyClaimView.as_view()),
    path('extract/', OCRProcessView.as_view()),
    path('ocr-status/<int:claim_id>/', OCRStatusView.as_view()),
]