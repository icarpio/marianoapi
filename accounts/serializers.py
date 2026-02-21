from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CustomUser
        fields = ['id', 'username', 'email', 'date_joined', 'last_login', 'source']
        read_only_fields = ['id', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    email     = serializers.EmailField(required=True)
    source    = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Campo genérico para datos extra de cada app.
    # PokéCity manda: {"ciudad_id": 1}
    # Otras apps mandan los suyos o nada.
    # accounts no lo valida ni lo toca — cada app lo procesa en su signal/view.
    extra_data = serializers.DictField(
        child=serializers.JSONField(),
        required=False,
        write_only=True,
        default=dict,
        help_text='Datos extra específicos de cada app. Ej: {"ciudad_id": 1}'
    )

    class Meta:
        model  = CustomUser
        fields = ['username', 'email', 'password', 'password2', 'source', 'extra_data']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})

        source = attrs.get('source', '')

        if CustomUser.objects.filter(email=attrs['email'], source=source).exists():
            raise serializers.ValidationError({"email": "Este email ya está registrado"})

        if CustomUser.objects.filter(username=attrs['username'], source=source).exists():
            raise serializers.ValidationError({"username": "Este usuario ya existe"})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        extra_data = validated_data.pop('extra_data', {})  # extraer pero NO guardar en CustomUser

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            source=validated_data.get('source', ''),
        )
        user.set_password(validated_data['password'])
        user.save()

        # Guardar extra_data en el objeto para que la view lo procese
        user._extra_data = extra_data

        return user