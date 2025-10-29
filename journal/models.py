from django.db import models
from django.contrib.auth.models import User


class JournalEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journal_entries')
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    entry_date = models.DateField()
    MOOD_CHOICES = [
        ("happy", "Heureux"),
        ("neutral", "Neutre"),
        ("sad", "Triste"),
        ("angry", "En colère"),
        ("excited", "Excité"),
        ("tired", "Fatigué"),
    ]
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True)
    # Heure: moment de la journée
    TIME_OF_DAY_CHOICES = [
        ("morning", "Matin"),
        ("noon", "Midi"),
        ("afternoon", "Après-midi"),
        ("evening", "Soir"),
        ("night", "Nuit"),
    ]
    time_of_day = models.CharField(max_length=20, choices=TIME_OF_DAY_CHOICES, blank=True)

    # État émotionnel & physique
    main_mood_level = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Échelle 1-5")
    energy_level = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Échelle 1-5")
    sleep_quality = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Échelle 1-5")
    HEALTH_CHOICES = [("good", "👍 Bon"), ("ok", "➡️ Moyen"), ("bad", "👎 Mauvais")]
    physical_health = models.CharField(max_length=10, choices=HEALTH_CHOICES, blank=True)

    # Contexte & environnement
    LOCATION_CHOICES = [
        ("home", "Maison"), ("work", "Travail"), ("outside", "Extérieur"), ("travel", "Voyage"), ("cafe", "Café"), ("nature", "Nature")
    ]
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, blank=True)
    WEATHER_CHOICES = [("sunny", "☀️ Ensoleillé"), ("cloudy", "⛅ Nuageux"), ("rain", "🌧️ Pluie"), ("storm", "⛈️ Orage"), ("snow", "❄️ Neige")]
    weather = models.CharField(max_length=20, choices=WEATHER_CHOICES, blank=True)
    SEASON_CHOICES = [("spring", "🌸 Printemps"), ("summer", "☀️ Été"), ("autumn", "🍂 Automne"), ("winter", "❄️ Hiver")]
    season = models.CharField(max_length=20, choices=SEASON_CHOICES, blank=True)

    # Catégorisation & thèmes
    main_subject = models.CharField(max_length=200, blank=True)
    secondary_themes = models.TextField(blank=True)

    # Moments marquants
    favorite_moment = models.TextField(blank=True)
    challenge = models.TextField(blank=True)
    achievement = models.TextField(blank=True)
    surprise = models.TextField(blank=True)

    # Objectifs & réflexions
    daily_goal = models.TextField(blank=True)
    accomplishments = models.TextField(blank=True)
    lesson_learned = models.TextField(blank=True)
    gratitude = models.TextField(blank=True, help_text="Liste (ex: 3 éléments, un par ligne)")

    # Bien-être & activités
    ACTIVITY_CHOICES = [("none", "Aucune"), ("15m", "15min"), ("30m", "30min"), ("1h", "1h"), ("1h+", "1h+")]
    physical_activity = models.CharField(max_length=10, choices=ACTIVITY_CHOICES, blank=True)
    MEDITATION_CHOICES = [("no", "Non"), ("5m", "5min"), ("10m", "10min"), ("15m+", "15min+")]
    meditation = models.CharField(max_length=10, choices=MEDITATION_CHOICES, blank=True)
    SCREEN_CHOICES = [("1-2h", "1-2h"), ("3-4h", "3-4h"), ("5h+", "5h+")]
    screen_time = models.CharField(max_length=10, choices=SCREEN_CHOICES, blank=True)
    MEAL_QUALITY_CHOICES = [("excellent", "🍎 Excellente"), ("average", "🥪 Moyenne"), ("poor", "🍟 Faible")]
    meals_quality = models.CharField(max_length=10, choices=MEAL_QUALITY_CHOICES, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']
        unique_together = ('user', 'entry_date', 'title')

    def __str__(self):
        return f"{self.entry_date} - {self.title}"


class MediaAsset(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='journal_media/', blank=True)
    caption = models.CharField(max_length=255, blank=True)
    media_type = models.CharField(max_length=20, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.caption or self.file.name


class Emotion(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class PersonCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# Relations ManyToMany après déclaration des modèles associés
JournalEntry.add_to_class('detailed_emotions', models.ManyToManyField(Emotion, blank=True, related_name='entries'))
JournalEntry.add_to_class('people_present', models.ManyToManyField(PersonCategory, blank=True, related_name='entries'))
JournalEntry.add_to_class('tags', models.ManyToManyField(Tag, blank=True, related_name='entries'))

# Create your models here.
