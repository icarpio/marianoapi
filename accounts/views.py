from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import update_last_login

from .models import CustomUser
from .serializers import UserSerializer, RegisterSerializer


def _procesar_extra_data(user, source, extra_data):
    """
    Procesa los datos extra según el source de la app.
    Cada app añade su bloque aquí sin tocar el serializer base.

    PokéCity (source='pokecapture'):
      extra_data = {"ciudad_id": 1}
      → Crea UserProfile con la ciudad elegida

    Otras apps:
      Añadir sus bloques aquí cuando sea necesario.
    """
    if not extra_data:
        return {}

    resultado = {}

    # ── PokéCity ──────────────────────────────────────────────────────────────
    if source == 'pokecapture':
        ciudad_id = extra_data.get('ciudad_id')
        if ciudad_id:
            try:
                from game.models import Ciudad, UserProfile
                from game.serializers import CiudadSerializer

                ciudad = Ciudad.objects.get(id=ciudad_id, activa=True)
                UserProfile.objects.get_or_create(user=user, defaults={'ciudad': ciudad})
                resultado['ciudad'] = CiudadSerializer(ciudad).data
            except Exception as e:
                resultado['ciudad_error'] = str(e)

    # ── Otra app ──────────────────────────────────────────────────────────────
    # if source == 'otraapp':
    #     campo = extra_data.get('campo_extra')
    #     ...

    return resultado


def _get_ciudad_data(user):
    """Devuelve datos de ciudad del UserProfile si existe."""
    try:
        from game.models import UserProfile
        from game.serializers import CiudadSerializer
        profile = UserProfile.objects.select_related('ciudad').get(user=user)
        if profile.ciudad:
            return CiudadSerializer(profile.ciudad).data
    except Exception:
        pass
    return None


# ── REGISTRO ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Registro unificado para todas las apps.

    Body base (todas las apps):
      { "username", "email", "password", "password2", "source" }

    Body PokéCity (source='pokecapture'):
      { ..., "extra_data": {"ciudad_id": 1} }

    Body otras apps:
      { ..., "extra_data": {"campo_propio": "valor"} }
    """
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user        = serializer.save()
        source      = getattr(user, 'source', '') or ''
        extra_data  = getattr(user, '_extra_data', {})

        # Procesar datos extra según la app
        extra_resultado = _procesar_extra_data(user, source, extra_data)

        token, _ = Token.objects.get_or_create(user=user)

        response_data = {
            'user':    UserSerializer(user).data,
            'token':   token.key,
            'message': 'Usuario registrado exitosamente',
        }
        # Añadir datos extra al response (ciudad, etc.)
        response_data.update(extra_resultado)

        return Response(response_data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    source   = request.data.get('source', '')

    if not username or not password:
        return Response(
            {'error': 'Por favor proporciona usuario y contraseña'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(username=username, source=source)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

    update_last_login(None, user)
    token, _ = Token.objects.get_or_create(user=user)

    response_data = {
        'user':    UserSerializer(user).data,
        'token':   token.key,
        'message': 'Inicio de sesión exitoso',
    }

    # Añadir datos de ciudad si es PokéCity
    if source == 'pokecapture':
        ciudad = _get_ciudad_data(user)
        if ciudad:
            response_data['ciudad'] = ciudad

    return Response(response_data, status=status.HTTP_200_OK)


# ── LOGOUT ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Sesión cerrada exitosamente'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── USUARIO ACTUAL ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    data = UserSerializer(request.user).data
    if getattr(request.user, 'source', '') == 'pokecapture':
        ciudad = _get_ciudad_data(request.user)
        if ciudad:
            data['ciudad'] = ciudad
    return Response(data)


# ── ACTUALIZAR PERFIL ─────────────────────────────────────────────────────────

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user       = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({
            'user':    serializer.data,
            'message': 'Perfil actualizado exitosamente'
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── CAMBIAR CONTRASEÑA ────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user         = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not old_password or not new_password:
        return Response(
            {'error': 'Proporciona la contraseña actual y la nueva'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user.check_password(old_password):
        return Response(
            {'error': 'La contraseña actual es incorrecta'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(new_password) < 8:
        return Response(
            {'error': 'La nueva contraseña debe tener al menos 8 caracteres'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.save()

    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)

    return Response({
        'message': 'Contraseña actualizada exitosamente',
        'token':   token.key
    })
    
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Reseteo de contraseña en dos pasos.

    Paso 1 — Verificar identidad (step: "verify"):
      Body: { "username": "...", "email": "...", "source": "aquarium", "step": "verify" }
      Respuesta OK: { "verified": true, "message": "..." }

    Paso 2 — Establecer nueva contraseña (step: "reset"):
      Body: { "username": "...", "email": "...", "source": "aquarium",
               "step": "reset", "new_password": "...", "new_password2": "..." }
      Respuesta OK: { "message": "Contraseña actualizada" }
    """
    username     = request.data.get('username', '').strip()
    email        = request.data.get('email', '').strip()
    source       = request.data.get('source', '')
    step         = request.data.get('step', 'verify')
    new_password = request.data.get('new_password', '')
    new_password2= request.data.get('new_password2', '')

    if not username or not email:
        return Response(
            {'error': 'Usuario y email son obligatorios'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Buscar usuario por username + source (misma lógica que login)
    try:
        user = CustomUser.objects.get(username=username, source=source)
    except CustomUser.DoesNotExist:
        # Mensaje genérico para no revelar si el usuario existe
        return Response(
            {'error': 'No encontramos una cuenta con esos datos'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Verificar que el email coincide (case-insensitive)
    if user.email.lower() != email.lower():
        return Response(
            {'error': 'No encontramos una cuenta con esos datos'},
            status=status.HTTP_404_NOT_FOUND
        )

    # ── PASO 1: solo verificar identidad ──────────────────────────────────────
    if step == 'verify':
        return Response({
            'verified': True,
            'message':  'Identidad verificada. Ahora puedes establecer tu nueva contraseña.',
        })

    # ── PASO 2: cambiar contraseña ────────────────────────────────────────────
    if step == 'reset':
        if not new_password:
            return Response(
                {'error': 'La nueva contraseña es obligatoria'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(new_password) < 8:
            return Response(
                {'error': 'La contraseña debe tener al menos 8 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if new_password != new_password2:
            return Response(
                {'error': 'Las contraseñas no coinciden'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        # Invalidar todos los tokens existentes para forzar nuevo login
        Token.objects.filter(user=user).delete()

        return Response({'message': 'Contraseña actualizada correctamente'})

    return Response({'error': 'Paso no válido'}, status=status.HTTP_400_BAD_REQUEST)

