from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    birth_date = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"Profile({self.user.username})"

from django.db import models

# Create your models here.
