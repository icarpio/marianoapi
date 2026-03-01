from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Fish, FishLike
from .serializers import FishSerializer, FishCreateSerializer
from .utils import upload_fish_image, delete_fish_image


# ── CREAR PEZ ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_fish(request):
    """
    Crea un pez para el usuario autenticado.

    Body:
      {
        "name": "Nemo",          # opcional
        "color": "#ff6b35",      # opcional
        "drawing_data": {...},   # JSON con los trazos del canvas
        "image_base64": "data:image/png;base64,..."  # imagen del canvas
      }
    """
    serializer = FishCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data         = serializer.validated_data
    image_base64 = data.pop('image_base64')

    # Subir imagen a Cloudinary
    try:
        cloud_result = upload_fish_image(image_base64, request.user.id)
    except Exception as e:
        return Response({'error': f'Error subiendo imagen: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    fish = Fish.objects.create(
        user          = request.user,
        name          = data.get('name', ''),
        color         = data.get('color', '#3b82f6'),
        drawing_data  = data.get('drawing_data', {}),
        image_url     = cloud_result['url'],
        cloudinary_id = cloud_result['public_id'],
    )

    return Response(FishSerializer(fish).data, status=status.HTTP_201_CREATED)


# ── MIS PECES ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_fishes(request):
    """Devuelve los peces del usuario autenticado."""
    fishes = Fish.objects.filter(user=request.user)
    return Response(FishSerializer(fishes, many=True).data)


# ── ELIMINAR PEZ ──────────────────────────────────────────────────────────────

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_fish(request, fish_id):
    """
    Elimina un pez del usuario autenticado y borra la imagen de Cloudinary.
    Solo puede borrar sus propios peces.
    """
    try:
        fish = Fish.objects.get(id=fish_id, user=request.user)
    except Fish.DoesNotExist:
        return Response({'error': 'Pez no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    # Borrar de Cloudinary primero
    try:
        delete_fish_image(fish.cloudinary_id)
    except Exception as e:
        # Log pero no bloqueamos el borrado en DB
        print(f'[aquarium] Error borrando imagen Cloudinary: {e}')

    fish.delete()
    return Response({'message': 'Pez eliminado'}, status=status.HTTP_200_OK)


# ── ACUARIO (todos los peces para animación) ──────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def aquarium(request):
    """
    Devuelve todos los peces de todos los usuarios.
    Usado para la pantalla del acuario con animación de nado.
    Filtra por source si se pasa como query param: ?source=aquarium
    """
    source = request.query_params.get('source', None)

    fishes = Fish.objects.select_related('user').all()

    if source:
        fishes = fishes.filter(user__source=source)

    return Response(FishSerializer(fishes, many=True).data)


# ── GALERÍA (cards de todos los peces) ────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def gallery(request):
    """
    Devuelve todos los peces para la pantalla de galería (cards).
    Igual que aquarium pero semánticamente diferente — puedes añadir
    paginación aquí sin tocar el endpoint del acuario.
    """
    source = request.query_params.get('source', None)
    page   = int(request.query_params.get('page', 1))
    limit  = int(request.query_params.get('limit', 20))

    fishes = Fish.objects.select_related('user').all()

    if source:
        fishes = fishes.filter(user__source=source)

    # Paginación simple
    start  = (page - 1) * limit
    end    = start + limit
    total  = fishes.count()
    fishes = fishes[start:end]

    return Response({
        'total':   total,
        'page':    page,
        'limit':   limit,
        'results': FishSerializer(fishes, many=True).data,
    })
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_like(request, fish_id):
    """
    Alterna el like del usuario sobre un pez.
    - Si no tiene like → lo crea   → { "liked": true,  "likes_count": N }
    - Si ya tiene like → lo borra  → { "liked": false, "likes_count": N }
    """
    fish = get_object_or_404(Fish, pk=fish_id)

    like, created = FishLike.objects.get_or_create(fish=fish, user=request.user)

    if not created:
        # Ya existía → quitar like
        like.delete()
        liked = False
    else:
        liked = True

    return Response({
        'liked':       liked,
        'likes_count': fish.likes.count(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def fish_likes(request, fish_id):
    """Devuelve el conteo de likes y si el usuario actual ha dado like."""
    fish = get_object_or_404(Fish, pk=fish_id)
    user = request.user if request.user.is_authenticated else None

    return Response({
        'likes_count': fish.likes.count(),
        'liked':       fish.likes.filter(user=user).exists() if user else False,
    })
