from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    source = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['username', 'source'], name='unique_username_per_source')
        ]

    def __str__(self):
        return f"{self.username} ({self.source})"