from django.contrib import admin
from .models import ImageModel, GeneratedImage


@admin.register(ImageModel)
class ImageModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'tags')
    list_filter = ('created_at',)


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'description')
    list_filter = ('created_at',)
