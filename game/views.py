from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Pokemon, PokemonLocation, UserCollection, UserProfile, Ciudad
from .serializers import (
    PokemonSerializer, PokemonLocationSerializer,
    UserCollectionSerializer, UserProfileSerializer,
    RegisterSerializer, CiudadSerializer
)


# ─────────────────────────────────────────────────────────────────────────────
# CIUDADES (público)
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def lista_ciudades(request):
    ciudades = Ciudad.objects.filter(activa=True)
    return Response(CiudadSerializer(ciudades, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    ser = RegisterSerializer(data=request.data)
    if ser.is_valid():
        user     = ser.save()
        token, _ = Token.objects.get_or_create(user=user)
        profile  = user.perfil
        return Response({
            'token':    token.key,
            'username': user.username,
            'ciudad':   CiudadSerializer(profile.ciudad).data if profile.ciudad else None,
        }, status=201)
    return Response(ser.errors, status=400)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user     = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'Credenciales incorrectas.'}, status=400)

    token, _   = Token.objects.get_or_create(user=user)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    return Response({
        'token':    token.key,
        'username': user.username,
        'ciudad':   CiudadSerializer(profile.ciudad).data if profile.ciudad else None,
        'puntos':   profile.puntos,
        'nivel':    profile.nivel,
    })


@api_view(['POST'])
def logout_view(request):
    request.user.auth_token.delete()
    return Response({'mensaje': 'Sesión cerrada.'})


# ─────────────────────────────────────────────────────────────────────────────
# PERFIL
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET', 'PATCH'])
def perfil(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'GET':
        return Response(UserProfileSerializer(profile).data)
    ser = UserProfileSerializer(profile, data=request.data, partial=True)
    if ser.is_valid():
        ser.save()
        return Response(ser.data)
    return Response(ser.errors, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# POKÉMON
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def lista_pokemon(request):
    qs = Pokemon.objects.prefetch_related('tipos', 'habilidades').all()
    return Response(PokemonSerializer(qs, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# UBICACIONES
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def ubicaciones(request):
    """
    Devuelve las ubicaciones activas de la ciudad del usuario.

    IMPORTANTE sobre ya_capturado:
      - Es TRUE solo si ESTE usuario concreto ya capturó ese punto.
      - Que otro usuario lo haya capturado NO afecta: el pokemon sigue visible.
      - El mapa muestra TODOS los pokémons; los ya capturados por ti aparecen
        con un check verde pero siguen en el mapa (no desaparecen).

    Query params opcionales:
      - ciudad_slug: para ver otra ciudad
      - lat, lon: para calcular distancias en tiempo real
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Resolver ciudad
    slug = request.query_params.get('ciudad_slug')
    if slug:
        try:
            ciudad = Ciudad.objects.get(slug=slug, activa=True)
        except Ciudad.DoesNotExist:
            return Response({'error': f'Ciudad "{slug}" no encontrada.'}, status=404)
    elif profile.ciudad:
        ciudad = profile.ciudad
    else:
        return Response({'error': 'No tienes ciudad asignada.'}, status=400)

    qs = (
        PokemonLocation.objects
        .filter(activo=True, ciudad=ciudad)
        .select_related('pokemon', 'ciudad')
        .prefetch_related('pokemon__tipos')
        .order_by('pokemon__pokedex_id')
    )

    # IDs de locations que YA capturó ESTE usuario (no afecta a otros)
    mis_capturas_ids = set(
        UserCollection.objects
        .filter(user=request.user)
        .values_list('location_id', flat=True)
    )

    user_lat = request.query_params.get('lat')
    user_lon = request.query_params.get('lon')

    data = []
    for loc in qs:
        p   = loc.pokemon
        img = p.imagen_shiny if p.is_shiny else p.imagen

        item = {
            'id':           loc.id,
            'lat':          str(loc.lat),
            'lon':          str(loc.lon),
            'radio_metros': loc.radio_metros,
            'poi_nombre':   loc.poi_nombre,
            'poi_tipo':     loc.poi_tipo,
            'descripcion':  loc.nombre_lugar,

            # Solo TRUE si TÚ ya lo capturaste en este punto
            'ya_capturado': loc.id in mis_capturas_ids,

            'pokemon': {
                'id':          p.id,
                'pokedex_id':  p.pokedex_id,
                'nombre':      p.nombre,
                'imagen':      img,
                'is_shiny':    p.is_shiny,
                'rareza':      p.rareza,
                'tipos':       [t.nombre for t in p.tipos.all()],
                'stats':       p.stats_dict(),
                'total_stats': p.total_stats,
            },
        }

        # Distancia si el usuario mandó su GPS
        if user_lat and user_lon:
            try:
                cerca, dist = loc.esta_cerca(float(user_lat), float(user_lon))
                item['en_rango']  = cerca
                item['distancia'] = dist
            except (ValueError, TypeError):
                item['en_rango']  = False
                item['distancia'] = None
        else:
            item['en_rango']  = False
            item['distancia'] = None

        data.append(item)

    return Response({
        'ciudad':      CiudadSerializer(ciudad).data,
        'total':       len(data),
        'capturados':  len(mis_capturas_ids),
        'ubicaciones': data,
    })


# ─────────────────────────────────────────────────────────────────────────────
# CAPTURA
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
def capturar(request, location_id):
    """
    Captura un pokémon en una ubicación concreta.

    Reglas:
    - Cada usuario puede capturar cada punto UNA sola vez.
    - Si otro usuario ya capturó ese punto, el punto sigue activo para todos.
    - El pokemon NUNCA desaparece del mapa por ser capturado por alguien.
    - Se valida la proximidad GPS en el servidor (anti-trampa).

    Body JSON: { "lat": float, "lon": float }
    """
    try:
        loc = PokemonLocation.objects.select_related('pokemon', 'ciudad').get(
            id=location_id, activo=True
        )
    except PokemonLocation.DoesNotExist:
        return Response({'error': 'Ubicación no encontrada o inactiva.'}, status=404)

    # Verificar que la ubicación es de la ciudad del usuario
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.ciudad and loc.ciudad != profile.ciudad:
        return Response({'error': 'Esta ubicación no pertenece a tu ciudad.'}, status=403)

    # ¿Ya capturado por ESTE usuario? (no importa si otros lo capturaron)
    if UserCollection.objects.filter(user=request.user, location=loc).exists():
        return Response({
            'error': f'Ya capturaste a {loc.pokemon.nombre} en {loc.nombre_lugar}.'
        }, status=400)

    # Validar GPS
    user_lat = request.data.get('lat')
    user_lon = request.data.get('lon')
    if user_lat is None or user_lon is None:
        return Response({'error': 'Necesitas enviar tu ubicación GPS (lat, lon).'}, status=400)

    try:
        cerca, distancia = loc.esta_cerca(float(user_lat), float(user_lon))
    except (ValueError, TypeError):
        return Response({'error': 'Coordenadas GPS inválidas.'}, status=400)

    if not cerca:
        return Response({
            'error':     f'Estás a {distancia}m. Necesitas estar a menos de {loc.radio_metros}m.',
            'distancia': distancia,
            'radio':     loc.radio_metros,
        }, status=400)

    # ¡Captura exitosa!
    UserCollection.objects.create(
        user=request.user,
        pokemon=loc.pokemon,
        location=loc,
        lat_captura=user_lat,
        lon_captura=user_lon,
    )

    # Sumar puntos según rareza
    puntos_map = {'comun': 10, 'raro': 25, 'epico': 50, 'legendario': 100}
    # Los shiny valen el doble
    puntos = puntos_map.get(loc.pokemon.rareza, 10)
    if loc.pokemon.is_shiny:
        puntos *= 2
    profile.puntos += puntos
    profile.save()

    # Cuántas veces fue capturado este punto en total (por todos los usuarios)
    total_capturas_punto = UserCollection.objects.filter(location=loc).count()

    return Response({
        'mensaje':              f'¡{loc.pokemon.nombre} capturado!',
        'lugar':                loc.nombre_lugar,
        'pokemon':              {
            'id':          loc.pokemon.id,
            'pokedex_id':  loc.pokemon.pokedex_id,
            'nombre':      loc.pokemon.nombre,
            'imagen':      loc.pokemon.imagen_shiny if loc.pokemon.is_shiny else loc.pokemon.imagen,
            'is_shiny':    loc.pokemon.is_shiny,
            'rareza':      loc.pokemon.rareza,
            'tipos':       [t.nombre for t in loc.pokemon.tipos.all()],
            'stats':       loc.pokemon.stats_dict(),
            'total_stats': loc.pokemon.total_stats,
        },
        'puntos_ganados':       puntos,
        'puntos_total':         profile.puntos,
        'nivel':                profile.nivel,
        'total_capturas_punto': total_capturas_punto,
    }, status=201)


# ─────────────────────────────────────────────────────────────────────────────
# COLECCIÓN
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def mi_coleccion(request):
    """
    Devuelve los pokémons capturados por el usuario.
    Incluye estadísticas de progreso respecto al total de la ciudad.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    capturas = (
        UserCollection.objects
        .filter(user=request.user)
        .select_related('pokemon', 'location', 'location__ciudad')
        .prefetch_related('pokemon__tipos', 'pokemon__habilidades')
        .order_by('-capturado_en')
    )

    total_ciudad = PokemonLocation.objects.filter(
        ciudad=profile.ciudad, activo=True
    ).count() if profile.ciudad else 0

    data = []
    for c in capturas:
        p   = c.pokemon
        img = p.imagen_shiny if p.is_shiny else p.imagen
        data.append({
            'id':           c.id,
            'capturado_en': c.capturado_en,
            'lugar':        c.location.nombre_lugar if c.location else '',
            'poi_tipo':     c.location.poi_tipo if c.location else '',
            'pokemon': {
                'id':           p.id,
                'pokedex_id':   p.pokedex_id,
                'nombre':       p.nombre,
                'imagen':       img,
                'is_shiny':     p.is_shiny,
                'rareza':       p.rareza,
                'tipos':        [t.nombre for t in p.tipos.all()],
                'habilidades':  [h.nombre for h in p.habilidades.all()],
                'stats':        p.stats_dict(),
                'total_stats':  p.total_stats,
            },
        })

    return Response({
        'total_capturados': len(data),
        'total_ciudad':     total_ciudad,
        'porcentaje':       round(len(data) / total_ciudad * 100, 1) if total_ciudad else 0,
        'capturas':         data,
    })


# ─────────────────────────────────────────────────────────────────────────────
# RANKING
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def ranking(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    slug = request.query_params.get('ciudad_slug')
    if slug:
        try:
            ciudad = Ciudad.objects.get(slug=slug, activa=True)
        except Ciudad.DoesNotExist:
            return Response({'error': 'Ciudad no encontrada.'}, status=404)
    elif profile.ciudad:
        ciudad = profile.ciudad
    else:
        return Response({'error': 'No tienes ciudad asignada.'}, status=400)

    perfiles = (
        UserProfile.objects
        .filter(ciudad=ciudad)
        .select_related('user')
        .order_by('-puntos')[:20]
    )

    data = [
        {
            'pos':      i + 1,
            'username': p.user.username,
            'puntos':   p.puntos,
            'nivel':    p.nivel,
            'capturas': p.total_capturas,
            'eres_tu':  p.user == request.user,
        }
        for i, p in enumerate(perfiles)
    ]

    return Response({
        'ciudad':  CiudadSerializer(ciudad).data,
        'ranking': data,
    })