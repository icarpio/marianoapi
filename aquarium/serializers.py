from rest_framework import serializers
from .models import Fish


class FishSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    likes_count = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()
    
    def get_likes_count(self, obj):
        return obj.likes.count()
 
    def get_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    class Meta:
        model  = Fish
        fields = [
            'id', 'user', 'username', 'name', 'color',
            'image_url', 'cloudinary_id', 'drawing_data',
            'created_at', 'updated_at','likes_count', 'liked'
        ]
        read_only_fields = ['id', 'user', 'username', 'image_url', 'cloudinary_id', 'created_at', 'updated_at']


class FishCreateSerializer(serializers.ModelSerializer):
    """Para crear/actualizar. Acepta image_base64 en lugar de image_url."""
    image_base64 = serializers.CharField(write_only=True, help_text='Imagen PNG en base64')

    class Meta:
        model  = Fish
        fields = ['name', 'color', 'drawing_data', 'image_base64']