from django.db import models
from django.conf import settings


class Claim(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    title       = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    document    = models.FileField(upload_to='claims/', blank=True, null=True)
    source      = models.CharField(max_length=50, blank=True, default='')
    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Claim #{self.id}"