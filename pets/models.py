from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings

class PetBase(models.Model):
    name = models.CharField(max_length=50)
    base_image = models.URLField()
    evolution1_image = models.URLField()
    evolution2_image = models.URLField()
    
    def __str__(self):
        return self.name

class Pet(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    pet_base = models.ForeignKey(PetBase, on_delete=models.SET_NULL, null=True)
    hunger = models.IntegerField(default=60)  # Inicialmente en un valor bajo
    energy = models.IntegerField(default=60)
    happiness = models.IntegerField(default=60)
    current_image = models.URLField()  # URL de la imagen actual
    evolution_stage = models.IntegerField(default=0)  # 0 - Base, 1 - Evolución 1, 2 - Evolución 2
    last_interaction = models.DateTimeField(default=timezone.now)  # Fecha de última interacción
    is_sleeping = models.BooleanField(default=False)  # Si la mascota está dormida
    sleep_time = models.DateTimeField(null=True, blank=True)  # Hora a la que la mascota se duerme

    def evolve(self):
        """Comprueba si la mascota puede evolucionar y cambia su estado si es posible."""
        now = timezone.now()
        if self.evolution_stage == 0 and self.hunger >= 80 and self.energy >= 80 and self.happiness >= 80:
            if self.last_interaction <= now - timedelta(hours=3):
                self.evolution_stage = 1
                self.current_image = self.pet_base.evolution1_image
                self.last_interaction = now
                self.save()
                return "¡Tu mascota ha evolucionado a la etapa 1!"
        elif self.evolution_stage == 1 and self.hunger >= 90 and self.energy >= 90 and self.happiness >= 90:
            if self.last_interaction <= now - timedelta(hours=5):
                self.evolution_stage = 2
                self.current_image = self.pet_base.evolution2_image
                self.last_interaction = now
                self.save()
                return "¡Tu mascota ha evolucionado a la etapa 2!"
        return None

    def sleep(self):
        """Pone a la mascota a dormir, recuperando energía poco a poco."""
        self.is_sleeping = True
        self.sleep_time = timezone.now()  # Marca el tiempo en que la mascota se duerme
        self.current_image = "/static/images/sleeping.png"  # Imagen cuando está durmiendo
        self.save()

    def wake_up(self):
        """Despierta a la mascota, recuperando energía."""
        self.is_sleeping = False
        self.energy = min(100, self.energy + 30)  # Recupera 30 de energía, pero no pasa de 100
         # Cambiar la imagen según la etapa de evolución
        if self.pet_base:  # Verificar si hay un PetBase asociado
            if self.evolution_stage == 0 and self.pet_base.base_image:
                self.current_image = self.pet_base.base_image
            elif self.evolution_stage == 1 and self.pet_base.evolution1_image:
                self.current_image = self.pet_base.evolution1_image
            elif self.evolution_stage == 2 and self.pet_base.evolution2_image:
                self.current_image = self.pet_base.evolution2_image
        self.sleep_time = None  # Borra el tiempo de sueño
        print(f"[wake_up] pet_base: {self.pet_base}")
        print(f"[wake_up] base_image: {self.pet_base.base_image if self.pet_base else 'No pet_base'}")
        self.save()

    def update_energy(self):
        """Recupera energía mientras la mascota duerme, hasta el máximo de 100."""
        if self.is_sleeping:
            # Si la mascota ha estado dormida por 2 horas o más, se despierta automáticamente
            if timezone.now() >= self.sleep_time + timedelta(hours=4):
                self.wake_up()
            else:
                # Recupera energía mientras duerme (pero no sobrepase 100)
                self.energy = min(100, self.energy + 1)
                self.save()  
                             
    def __str__(self):
        return self.name

#USER PARAMS
class UserProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    money = models.IntegerField(default=100)  # Valor de money por defecto

    def __str__(self):
        return f"{self.user.username} Profile"
    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
    
