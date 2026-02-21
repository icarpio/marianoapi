from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import PetBase, Pet
from .serializers import PetSerializer, PetBaseSerializer
import requests
from django.http import HttpResponse

# ============ CRUD DE MASCOTAS ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_pet(request):
    """Crear una nueva mascota"""
    pet_base_id = request.data.get('pet_base')
    pet_name = request.data.get('pet_name')
    
    try:
        pet_base = PetBase.objects.get(id=pet_base_id)
    except PetBase.DoesNotExist:
        return Response(
            {'error': 'Tipo de mascota no encontrado'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    pet = Pet.objects.create(
        user=request.user,
        pet_base=pet_base,
        name=pet_name,
        current_image=pet_base.base_image
    )
    
    serializer = PetSerializer(pet)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pet_bases(request):
    """Obtener todas las opciones de mascotas predefinidas"""
    pet_bases = PetBase.objects.all()
    serializer = PetBaseSerializer(pet_bases, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pet_dashboard(request):
    """Obtener todas las mascotas del usuario"""
    pets = Pet.objects.filter(user=request.user)
    serializer = PetSerializer(pets, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pet_detail(request, pet_id):
    """Obtener detalles de una mascota específica"""
    pet = get_object_or_404(Pet, id=pet_id)
    
    # Verificar que el usuario sea el propietario
    if pet.user != request.user:
        return Response(
            {'error': 'No tienes permiso para ver esta mascota'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = PetSerializer(pet)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_pet(request, pet_id):
    """Eliminar una mascota"""
    pet = get_object_or_404(Pet, id=pet_id)
    
    if pet.user != request.user:
        return Response(
            {'error': 'No puedes eliminar esta mascota'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    pet.delete()
    return Response(
        {'message': 'Mascota eliminada exitosamente'}, 
        status=status.HTTP_200_OK
    )

# ============ ACCIONES MASIVAS ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sleep_all_pets(request):
    """Poner a dormir todas las mascotas del usuario"""
    pets = Pet.objects.filter(user=request.user)
    
    for pet in pets:
        pet.sleep()
    
    return Response({'message': 'Todas las mascotas están durmiendo'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wake_up_all_pets(request):
    """Despertar todas las mascotas del usuario"""
    pets = Pet.objects.filter(user=request.user)
    
    for pet in pets:
        pet.wake_up()
    
    return Response({'message': 'Todas las mascotas han despertado'})


# ============ ACCIONES INDIVIDUALES ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def increase_hunger(request, pet_id):
    """Aumentar el hambre de una mascota"""
    try:
        pet = Pet.objects.get(id=pet_id, user=request.user)
        pet.hunger = min(pet.hunger + 9, 100)
        evolution_message = pet.evolve()
        pet.save()
        
        return Response({
            'hunger': pet.hunger,
            'message': evolution_message,
            'current_image': pet.current_image
        })
    except Pet.DoesNotExist:
        return Response(
            {'error': 'Mascota no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def increase_energy(request, pet_id):
    """Aumentar la energía de una mascota"""
    try:
        pet = Pet.objects.get(id=pet_id, user=request.user)
        pet.energy = min(pet.energy + 9, 100)
        evolution_message = pet.evolve()
        pet.save()
        
        return Response({
            'energy': pet.energy,
            'message': evolution_message,
            'current_image': pet.current_image
        })
    except Pet.DoesNotExist:
        return Response(
            {'error': 'Mascota no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def increase_happiness(request, pet_id):
    """Aumentar la felicidad de una mascota"""
    try:
        pet = Pet.objects.get(id=pet_id, user=request.user)
        pet.happiness = min(pet.happiness + 9, 100)
        evolution_message = pet.evolve()
        pet.save()
        
        return Response({
            'happiness': pet.happiness,
            'message': evolution_message,
            'current_image': pet.current_image
        })
    except Pet.DoesNotExist:
        return Response(
            {'error': 'Mascota no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sleep(request, pet_id):
    """Poner a dormir una mascota"""
    try:
        pet = Pet.objects.get(id=pet_id, user=request.user)
        pet.sleep()
        
        return Response({
            'message': 'La mascota está descansando',
            'new_pet_image_url': pet.current_image,
            'energy': pet.energy
        })
    except Pet.DoesNotExist:
        return Response(
            {'error': 'Mascota no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wake_up(request, pet_id):
    """Despertar una mascota"""
    try:
        pet = Pet.objects.get(id=pet_id, user=request.user)
        pet.wake_up()
        
        return Response({
            'message': 'La mascota ha despertado y su energía ha sido restaurada',
            'new_pet_image_url': pet.current_image,
            'energy': pet.energy
        })
    except Pet.DoesNotExist:
        return Response(
            {'error': 'Mascota no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )


# ============ UTILIDADES ============

def image_proxy(request, image_url):
    """Proxy para imágenes externas"""
    response = requests.get(image_url)
    return HttpResponse(response.content, content_type="image/png")



#Enemigos para minijuego2
from random import choice

from random import choice
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_random_pet_images(request):
    try:
        pet_bases = PetBase.objects.all()

        if not pet_bases.exists():
            return Response(
                {'error': 'No hay mascotas registradas'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔥 Recolectar TODAS las imágenes
        all_images = []

        for pet in pet_bases:
            if pet.base_image:
                all_images.append(pet.base_image)
            if pet.evolution1_image:
                all_images.append(pet.evolution1_image)
            if pet.evolution2_image:
                all_images.append(pet.evolution2_image)

        if len(all_images) == 0:
            return Response(
                {'error': 'No hay imágenes disponibles'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔥 Generar 10 enemigos random
        enemy_images = [choice(all_images) for _ in range(10)]

        return Response({
            'enemy_images': enemy_images
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        