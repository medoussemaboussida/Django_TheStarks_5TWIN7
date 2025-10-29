from django.db import models

class Summarizer(models.Model):
    title = models.CharField(max_length=200, help_text="Titre du résumé")
    user_input = models.TextField(help_text="Entrée utilisateur (problème émotionnel ou à résoudre)")
    summary = models.TextField(
        help_text="Résumé généré (sera rempli par IA plus tard)",
        blank=True,  # Permet d'être vide dans les formulaires
        null=True    # Permet d'être NULL en BD
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
