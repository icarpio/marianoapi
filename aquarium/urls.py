from django.urls import path
from . import views

urlpatterns = [
    # Mis peces
    path('fishes/',              views.my_fishes,   name='my-fishes'),
    path('fishes/create/',       views.create_fish, name='create-fish'),
    path('fishes/<int:fish_id>/delete/', views.delete_fish, name='delete-fish'),

    # Pantallas públicas
    path('aquarium/',            views.aquarium,    name='aquarium'),
    path('gallery/',             views.gallery,     name='gallery'),
    
    path('fishes/<int:fish_id>/like/',  views.toggle_like, name='toggle-like'),
    path('fishes/<int:fish_id>/likes/', views.fish_likes,  name='fish-likes'),
]