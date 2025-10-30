from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class ImageModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='images')
    # Optional generic relation to support future Journal or other models
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    image = models.ImageField(upload_to='uploads/images/')
    thumbnail = models.ImageField(upload_to='uploads/thumbnails/', null=True, blank=True)
    tags = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class GeneratedImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_images')
    description = models.TextField()
    image = models.ImageField(upload_to='uploads/generated/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
