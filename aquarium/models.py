from django.db import models
from django.conf import settings


class Fish(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fishes'
    )
    name = models.CharField(max_length=100, blank=True, default='')

    # Datos del dibujo (canvas serializado como JSON: lista de trazos/puntos)
    drawing_data = models.JSONField(default=dict, help_text='Canvas stroke data en JSON')

    # Imagen guardada en Cloudinary
    image_url      = models.URLField(blank=True, default='')
    cloudinary_id  = models.CharField(max_length=255, blank=True, default='',
                                       help_text='public_id en Cloudinary para poder borrarla')

    # Color principal del pez (opcional, para el acuario)
    color = models.CharField(max_length=20, blank=True, default='#3b82f6')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Fish of {self.user.username} — {self.name or self.pk}"
    
    

class FishLike(models.Model):
    fish = models.ForeignKey(
        Fish,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fish_likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('fish', 'user')   # un usuario, un like por pez
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} ♥ {self.fish.name}'