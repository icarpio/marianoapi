from rest_framework import serializers
from .models import Pet, PetBase

class PetBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetBase
        fields = '__all__'

class PetSerializer(serializers.ModelSerializer):
    pet_base_name = serializers.CharField(source='pet_base.name', read_only=True)
    
    class Meta:
        model = Pet
        fields = '__all__'