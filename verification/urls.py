from django.urls import path
from .views import VerifyClaimView, OCRProcessView

urlpatterns = [
    path('claim/<int:claim_id>/', VerifyClaimView.as_view()),
    path('ocr/<int:claim_id>/', OCRProcessView.as_view()),
]