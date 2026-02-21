from django.urls import path
from . import views

urlpatterns = [
    # Ciudades (público, necesario para el registro)
    path('ciudades/',              views.lista_ciudades, name='ciudades'),
    # Perfil
    path('perfil/',        views.perfil,       name='perfil'),
    # Pokédex
    path('pokemon/',       views.lista_pokemon,name='lista-pokemon'),
    # Mapa / ubicaciones
    path('ubicaciones/',   views.ubicaciones,  name='ubicaciones'),
    # Captura
    path('capturar/<int:location_id>/', views.capturar, name='capturar'),
    # Colección
    path('coleccion/',     views.mi_coleccion, name='mi-coleccion'),
    # Ranking
    path('ranking/',       views.ranking,      name='ranking'),
]
