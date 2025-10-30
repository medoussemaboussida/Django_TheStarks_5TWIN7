from django.db import models
from django.contrib.auth.models import User


class VocalNote(models.Model):
    """Model for storing vocal notes with transcription and sentiment analysis"""
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    CATEGORY_CHOICES = [
        ('work', 'Work'),
        ('personal', 'Personal'),
        ('idea', 'Idea'),
        ('problem', 'Problem'),
        ('project', 'Project'),
        ('meeting', 'Meeting'),
        ('reminder', 'Reminder'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vocal_notes')
    audio_file = models.FileField(upload_to='uploads/vocals/')
    duration = models.FloatField(null=True, blank=True, help_text="Duration in seconds")
    
    # Transcription
    transcription = models.TextField(blank=True, null=True)
    transcribed_at = models.DateTimeField(null=True, blank=True)
    
    # Sentiment Analysis
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    sentiment_score = models.FloatField(null=True, blank=True, help_text="Confidence score 0-1")
    analyzed_at = models.DateTimeField(null=True, blank=True)
    
    # Summary
    summary = models.TextField(blank=True, null=True)
    
    # Topic Detection and Context
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', blank=True)
    topics = models.JSONField(default=list, blank=True, help_text="List of detected topics")
    keywords = models.JSONField(default=list, blank=True, help_text="List of keywords")
    context = models.TextField(blank=True, null=True, help_text="Context description")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Vocal #{self.id} by {self.user.username}"
