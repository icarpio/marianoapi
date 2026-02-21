from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Pokemon, PokemonLocation, UserCollection, UserProfile, Tipo, Habilidad, Ciudad


class CiudadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Ciudad
        fields = ['id', 'nombre_display', 'slug', 'pais', 'lat', 'lon', 'zoom_inicial']


class PokemonSerializer(serializers.ModelSerializer):
    tipos       = serializers.StringRelatedField(many=True)
    habilidades = serializers.StringRelatedField(many=True)
    stats       = serializers.SerializerMethodField()
    total_stats = serializers.ReadOnlyField()

    class Meta:
        model  = Pokemon
        fields = ['id', 'pokedex_id', 'nombre', 'imagen', 'imagen_shiny',
                  'is_shiny', 'tipos', 'habilidades', 'stats', 'total_stats', 'rareza']

    def get_stats(self, obj):
        return obj.stats_dict()


class PokemonLocationSerializer(serializers.ModelSerializer):
    pokemon   = PokemonSerializer(read_only=True)
    ciudad    = CiudadSerializer(read_only=True)
    distancia = serializers.SerializerMethodField()

    class Meta:
        model  = PokemonLocation
        fields = ['id', 'pokemon', 'ciudad', 'descripcion', 'lat', 'lon', 'radio_metros', 'distancia']

    def get_distancia(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        try:
            lat = float(request.query_params.get('lat', 0))
            lon = float(request.query_params.get('lon', 0))
            if lat and lon:
                _, dist = obj.esta_cerca(lat, lon)
                return dist
        except (ValueError, TypeError):
            pass
        return None


class UserCollectionSerializer(serializers.ModelSerializer):
    pokemon = PokemonSerializer(read_only=True)

    class Meta:
        model  = UserCollection
        fields = ['id', 'pokemon', 'location', 'capturado_en', 'lat_captura', 'lon_captura']


class UserProfileSerializer(serializers.ModelSerializer):
    username       = serializers.CharField(source='user.username', read_only=True)
    email          = serializers.CharField(source='user.email',    read_only=True)
    nivel          = serializers.ReadOnlyField()
    total_capturas = serializers.ReadOnlyField()
    ciudad         = CiudadSerializer(read_only=True)
    ciudad_id      = serializers.PrimaryKeyRelatedField(
        queryset=Ciudad.objects.filter(activa=True),
        source='ciudad', write_only=True, required=False
    )

    class Meta:
        model  = UserProfile
        fields = ['username', 'email', 'ciudad', 'ciudad_id', 'puntos', 'nivel', 'total_capturas', 'avatar_url']


class RegisterSerializer(serializers.ModelSerializer):
    password   = serializers.CharField(write_only=True, min_length=6)
    password2  = serializers.CharField(write_only=True)
    ciudad_id  = serializers.PrimaryKeyRelatedField(
        queryset=Ciudad.objects.filter(activa=True),
        required=True, write_only=True
    )

    class Meta:
        model  = User
        fields = ['username', 'email', 'password', 'password2', 'ciudad_id']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Las contraseñas no coinciden.'})
        return data

    def create(self, validated_data):
        ciudad = validated_data.pop('ciudad_id')
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user, ciudad=ciudad)
        return user