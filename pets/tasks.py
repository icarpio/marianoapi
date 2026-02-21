from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Pet


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def decrease_pet_values(self):
    #print("Task ID:", self.request.id)
    #Disminuye los valores de hunger, energy y happiness en -1 cada hora
    pets = Pet.objects.all()
    now = timezone.now()
    for pet in pets:
        # Disminuir los valores en -1 si no están en un rango mínimo
        if pet.hunger > 0:
            pet.hunger -= 1
        if pet.energy > 0:
            pet.energy -= 1
        if pet.happiness > 0:
            pet.happiness -= 1
        
        # Actualizar la última interacción para que no afecte otras tareas
        #pet.last_interaction = now
        pet.save()


@shared_task
def update_pet_state():
    """Verifica si las mascotas deben recuperar energía o despertar después de 2 horas.
    # Así te asegurás de que cuando se itere sobre las mascotas, ya venga el pet_base incluido (evita lazy loading problemático dentro de Celery):"""
    pets = Pet.objects.filter(is_sleeping=True).select_related("pet_base") 
    for pet in pets:
        pet.update_energy()  # Recuperar energía o despertar
        pet.save()



        