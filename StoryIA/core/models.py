from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    birth_date = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"Profile({self.user.username})"


class Reclamation(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reclamations')
    name = models.CharField(max_length=80)
    number = models.CharField(max_length=32)
    subject = models.CharField(max_length=120)
    message = models.TextField()
    sentiment = models.CharField(max_length=12, choices=[('positive','Positif'), ('neutral','Neutre'), ('negative','Négatif')], default='neutral')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        base = self.subject or 'Réclamation'
        return f"{base} ({self.name})"
