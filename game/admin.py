from django.contrib import admin
from django.utils.html import format_html
from .models import Ciudad, Pokemon, PokemonLocation, UserCollection, UserProfile, Tipo, Habilidad


@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display  = ['nombre_display', 'pais', 'lat', 'lon', 'total_ubicaciones', 'activa']
    list_filter   = ['activa', 'pais']
    list_editable = ['activa']
    search_fields = ['nombre_display', 'pais']
    prepopulated_fields = {'slug': ('nombre_display',)}

    def total_ubicaciones(self, obj):
        n = obj.locations.filter(activo=True).count()
        return format_html('<b>{}</b> ubicaciones', n)
    total_ubicaciones.short_description = 'Pokémons activos'


@admin.register(Tipo)
class TipoAdmin(admin.ModelAdmin):
    list_display  = ['nombre']
    search_fields = ['nombre']


@admin.register(Habilidad)
class HabilidadAdmin(admin.ModelAdmin):
    list_display  = ['nombre']
    search_fields = ['nombre']


@admin.register(Pokemon)
class PokemonAdmin(admin.ModelAdmin):
    list_display      = ['pokedex_id', 'nombre', 'rareza', 'is_shiny', 'total_stats', 'veces_colocado']
    list_filter       = ['rareza', 'is_shiny', 'tipos']
    search_fields     = ['nombre']
    filter_horizontal = ['tipos', 'habilidades']
    readonly_fields   = ['total_stats']

    def total_stats(self, obj):
        return obj.total_stats
    total_stats.short_description = 'Total Stats'

    def veces_colocado(self, obj):
        return obj.locations.count()
    veces_colocado.short_description = 'Nº ubicaciones'


class UserCollectionInline(admin.TabularInline):
    model           = UserCollection
    extra           = 0
    readonly_fields = ['user', 'capturado_en', 'lat_captura', 'lon_captura']
    can_delete      = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PokemonLocation)
class PokemonLocationAdmin(admin.ModelAdmin):
    list_display   = ['pokemon', 'ciudad', 'poi_tipo', 'poi_nombre', 'lat', 'lon', 'radio_metros', 'total_capturas', 'activo']
    list_filter    = ['ciudad', 'activo', 'poi_tipo', 'pokemon__rareza', 'pokemon__is_shiny']
    search_fields  = ['poi_nombre', 'pokemon__nombre', 'ciudad__nombre_display']
    list_editable  = ['activo', 'radio_metros']
    readonly_fields= ['poi_osm_id', 'total_capturas', 'ver_en_osm']
    inlines        = [UserCollectionInline]

    fieldsets = [
        ('Pokémon', {
            'fields': ['pokemon', 'ciudad', 'activo']
        }),
        ('Punto de interés (OSM)', {
            'fields': ['poi_nombre', 'poi_tipo', 'poi_osm_id', 'ver_en_osm']
        }),
        ('Ubicación', {
            'fields': ['lat', 'lon', 'radio_metros', 'descripcion']
        }),
    ]

    def total_capturas(self, obj):
        n = UserCollection.objects.filter(location=obj).count()
        return format_html('<b>{}</b> capturas', n)
    total_capturas.short_description = 'Capturas totales'

    def ver_en_osm(self, obj):
        if obj.lat and obj.lon:
            url = f"https://www.openstreetmap.org/?mlat={obj.lat}&mlon={obj.lon}#map=18/{obj.lat}/{obj.lon}"
            return format_html('<a href="{}" target="_blank">Ver en OpenStreetMap ↗</a>', url)
        return '-'
    ver_en_osm.short_description = 'Mapa'


@admin.register(UserCollection)
class UserCollectionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'pokemon_nombre', 'pokemon_shiny', 'lugar', 'capturado_en']
    list_filter   = ['pokemon__rareza', 'pokemon__is_shiny', 'location__ciudad']
    search_fields = ['user__username', 'pokemon__nombre', 'location__poi_nombre']
    readonly_fields = ['capturado_en']

    def pokemon_nombre(self, obj):
        return obj.pokemon.nombre
    pokemon_nombre.short_description = 'Pokémon'

    def pokemon_shiny(self, obj):
        return '✨' if obj.pokemon.is_shiny else ''
    pokemon_shiny.short_description = 'Shiny'

    def lugar(self, obj):
        return obj.location.nombre_lugar if obj.location else '-'
    lugar.short_description = 'Lugar de captura'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display    = ['user', 'ciudad', 'puntos', 'nivel', 'total_capturas']
    list_filter     = ['ciudad']
    search_fields   = ['user__username']
    readonly_fields = ['nivel', 'total_capturas']