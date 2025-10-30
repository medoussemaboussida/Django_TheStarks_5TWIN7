from rest_framework import serializers
from .models import ImageModel, GeneratedImage


class ImageModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageModel
        fields = ['id', 'user', 'image', 'thumbnail', 'tags', 'created_at']
        read_only_fields = ['id', 'user', 'thumbnail', 'tags', 'created_at']


class GeneratedImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedImage
        fields = ['id', 'user', 'description', 'image', 'created_at']
        read_only_fields = ['id', 'user', 'image', 'created_at']
