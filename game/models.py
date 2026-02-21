from django.db import models
from django.contrib.auth.models import User
import math
from django.conf import settings


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlam = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class Ciudad(models.Model):
    nombre_display = models.CharField(max_length=120, unique=True)
    slug           = models.SlugField(max_length=120, unique=True)
    pais           = models.CharField(max_length=100, blank=True)
    lat            = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    lon            = models.DecimalField(max_digits=9, decimal_places=6, default=0)
    zoom_inicial   = models.PositiveSmallIntegerField(default=15)
    activa         = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ciudad"
        ordering = ["nombre_display"]

    def __str__(self):
        return f"{self.nombre_display} ({self.pais})" if self.pais else self.nombre_display


class Tipo(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    class Meta:
        ordering = ["nombre"]
    def __str__(self):
        return self.nombre


class Habilidad(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    class Meta:
        ordering = ["nombre"]
    def __str__(self):
        return self.nombre


class Pokemon(models.Model):
    RAREZA_CHOICES = [
        ("comun",     "Común"),
        ("raro",      "Raro"),
        ("epico",     "Épico"),
        ("legendario","Legendario"),
    ]

    pokedex_id      = models.PositiveIntegerField(unique=True)
    nombre          = models.CharField(max_length=100)
    imagen          = models.URLField(max_length=500, blank=True)
    imagen_shiny    = models.URLField(max_length=500, blank=True)
    is_shiny        = models.BooleanField(default=False)
    tipos           = models.ManyToManyField(Tipo, blank=True)
    habilidades     = models.ManyToManyField(Habilidad, blank=True)
    hp              = models.PositiveSmallIntegerField(default=0)
    attack          = models.PositiveSmallIntegerField(default=0)
    defense         = models.PositiveSmallIntegerField(default=0)
    special_attack  = models.PositiveSmallIntegerField(default=0)
    special_defense = models.PositiveSmallIntegerField(default=0)
    speed           = models.PositiveSmallIntegerField(default=0)
    rareza          = models.CharField(max_length=20, choices=RAREZA_CHOICES, default="comun")

    class Meta:
        verbose_name = "Pokémon"
        ordering = ["pokedex_id"]

    def __str__(self):
        return f"#{self.pokedex_id} {self.nombre}"

    @property
    def total_stats(self):
        return self.hp + self.attack + self.defense + self.special_attack + self.special_defense + self.speed

    def stats_dict(self):
        return {
            "hp": self.hp, "attack": self.attack, "defense": self.defense,
            "special-attack": self.special_attack,
            "special-defense": self.special_defense,
            "speed": self.speed,
        }


# Tipos de POI de OpenStreetMap
POI_TIPO_CHOICES = [
    ("plaza",      "Plaza"),
    ("parque",     "Parque"),
    ("monumento",  "Monumento"),
    ("farmacia",   "Farmacia"),
    ("fuente",     "Fuente"),
    ("biblioteca", "Biblioteca"),
    ("museo",      "Museo"),
    ("teatro",     "Teatro"),
    ("iglesia",    "Iglesia"),
    ("mercado",    "Mercado"),
    ("otro",       "Otro"),
]


class PokemonLocation(models.Model):
    pokemon      = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name="locations")
    ciudad       = models.ForeignKey(Ciudad, on_delete=models.CASCADE, related_name="locations")

    # Datos del POI de OpenStreetMap
    poi_nombre   = models.CharField(max_length=200, blank=True, help_text="Nombre del POI en OSM")
    poi_tipo     = models.CharField(max_length=20, choices=POI_TIPO_CHOICES, default="otro")
    poi_osm_id   = models.BigIntegerField(null=True, blank=True, help_text="ID del elemento en OpenStreetMap")

    descripcion  = models.CharField(max_length=200, blank=True)
    lat          = models.DecimalField(max_digits=9, decimal_places=6)
    lon          = models.DecimalField(max_digits=9, decimal_places=6)
    radio_metros = models.PositiveSmallIntegerField(default=80)
    activo       = models.BooleanField(default=True)
    creado_en    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ubicación de Pokémon"
        verbose_name_plural = "Ubicaciones de Pokémon"
        # Evitar duplicar el mismo pokemon en el mismo POI exacto
        unique_together = [("pokemon", "poi_osm_id")]

    def __str__(self):
        poi = self.poi_nombre or f"({self.lat}, {self.lon})"
        return f"{self.pokemon.nombre} @ {poi} ({self.ciudad.nombre_display})"

    def esta_cerca(self, user_lat, user_lon):
        dist = haversine_distance(self.lat, self.lon, user_lat, user_lon)
        return dist <= self.radio_metros, round(dist)

    @property
    def nombre_lugar(self):
        """Nombre legible del lugar para mostrar en el frontend."""
        return self.poi_nombre or self.descripcion or f"{self.poi_tipo.capitalize()} ({self.lat:.4f}, {self.lon:.4f})"


class UserCollection(models.Model):
    """
    Registro de captura de un usuario.

    CLAVE: unique_together es (user, location) — NO (user, pokemon).
    Esto significa:
    - Un usuario solo puede capturar UN pokemon en cada punto concreto (location).
    - Pero DISTINTOS usuarios pueden capturar el mismo pokemon en el mismo punto.
    - El pokemon NO desaparece del mapa cuando alguien lo captura.
    - Si hay el mismo pokemon en dos puntos distintos, el usuario puede capturar ambos.
    """
    user         = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE, related_name="coleccion")
    pokemon      = models.ForeignKey(Pokemon, on_delete=models.CASCADE)
    location     = models.ForeignKey(PokemonLocation, on_delete=models.SET_NULL, null=True, blank=True)
    capturado_en = models.DateTimeField(auto_now_add=True)
    lat_captura  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lon_captura  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        # Cada usuario captura CADA PUNTO una sola vez
        # Pero el punto sigue visible para los demás usuarios
        unique_together = [("user", "location")]
        ordering = ["-capturado_en"]

    def __str__(self):
        return f"{self.user.username} capturó {self.pokemon.nombre} en {self.location}"


class UserProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='perfil')
    avatar_url = models.URLField(blank=True)
    ciudad     = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, null=True, blank=True)
    puntos     = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Perfil"

    def __str__(self):
        return f"Perfil de {self.user.username}"

    @property
    def nivel(self):
        return max(1, self.puntos // 100)

    @property
    def total_capturas(self):
        return self.user.coleccion.count()