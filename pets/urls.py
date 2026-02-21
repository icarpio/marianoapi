
from django.urls import path
from . import views
urlpatterns = [
    # Obtener opciones y datos
    path('api/pet-bases/', views.get_pet_bases, name='get_pet_bases'),
    path('api/pets/', views.pet_dashboard, name='pet_dashboard'),
    path('api/pets/<int:pet_id>/', views.pet_detail, name='pet_detail'),
    
    # Crear y eliminar
    path('api/pets/create/', views.create_pet, name='create_pet'),
    path('api/pets/<int:pet_id>/delete/', views.delete_pet, name='delete_pet'),
    
    # Acciones masivas
    path('api/pets/sleep-all/', views.sleep_all_pets, name='sleep_all_pets'),
    path('api/pets/wake-up-all/', views.wake_up_all_pets, name='wake_up_all_pets'),
    
    # Acciones individuales
    path('api/pets/<int:pet_id>/increase-hunger/', views.increase_hunger, name='increase_hunger'),
    path('api/pets/<int:pet_id>/increase-energy/', views.increase_energy, name='increase_energy'),
    path('api/pets/<int:pet_id>/increase-happiness/', views.increase_happiness, name='increase_happiness'),
    path('api/pets/<int:pet_id>/sleep/', views.sleep, name='sleep'),
    path('api/pets/<int:pet_id>/wake-up/', views.wake_up, name='wake_up'),
    
    # Utilidades
    path('api/image-proxy/<path:image_url>/', views.image_proxy, name='image_proxy'),
    
    # Minijuego de plataformas
    path('api/random-pet-images/', views.get_random_pet_images, name='get_random_pet_images'),
]
