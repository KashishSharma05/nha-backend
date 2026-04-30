"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def home(request):
    return JsonResponse({
        "status": "success",
        "message": "Backend is live on Render"
    })


urlpatterns = [
    path('', home),   # root route added
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/claims/', include('claims.urls')),
    path('api/verification/', include('verification.urls')),
    path('api/reports/', include('reports.urls')),
]