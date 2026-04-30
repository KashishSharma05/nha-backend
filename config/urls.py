"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, FileResponse, HttpResponseForbidden
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
import os


def home(request):
    return JsonResponse({
        "status": "success",
        "message": "Backend is live on Render"
    })


def protected_media(request, path):
    """Serve media files only to authenticated users."""
    auth = JWTAuthentication()
    try:
        result = auth.authenticate(request)
        if result is None:
            return JsonResponse({"error": "Authentication required"}, status=401)
    except Exception:
        return JsonResponse({"error": "Invalid token"}, status=401)

    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        return JsonResponse({"error": "File not found"}, status=404)

    return FileResponse(open(file_path, 'rb'))


urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/claims/', include('claims.urls')),
    path('api/verification/', include('verification.urls')),
    path('api/reports/', include('reports.urls')),
    path('media/<path:path>', protected_media),   # protected media serving
]