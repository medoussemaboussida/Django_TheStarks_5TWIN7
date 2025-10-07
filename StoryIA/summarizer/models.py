from django.db import models
from user.models import User  # Import du modèle User de ton app user

class ProblemEntry(models.Model):
    """
    Modèle pour les entrées de problèmes de l'utilisateur,
    avec résumé IA, analyse d'émotion et suggestions de solution.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='problems'
    )
    text_input = models.TextField(
        verbose_name="Texte du problème",
        help_text="Décris ici ton problème, ton ressenti ou ta situation."
    )
    summary = models.TextField(
        blank=True, null=True, verbose_name="Résumé généré par l'IA"
    )
    emotion = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Émotion dominante"
    )
    category = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Catégorie du problème"
    )
    ai_solution = models.TextField(
        blank=True, null=True, verbose_name="Solution ou conseil IA"
    )
    feedback = models.CharField(
        max_length=50, blank=True, null=True,
        choices=[
            ("helpful", "Utile"),
            ("neutral", "Neutre"),
            ("not_helpful", "Pas utile")
        ],
        verbose_name="Avis de l'utilisateur sur la réponse IA"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Entrée de problème"
        verbose_name_plural = "Entrées de problèmes"

    def __str__(self):
        return f"Problème de {self.user.username} ({self.created_at.strftime('%Y-%m-%d')})"
